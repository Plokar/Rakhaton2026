"""Nový pacient z rodného čísla (T-323, ARCH §6.3): návrh → náhledy → úpravy → potvrzení do IRIS.

Zakládá předseda nebo lékař; návrh vidí a mění jen jeho autor a předseda. RČ se ve výstupech nevrací (jen maskované).
"""
import logging
import re

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services import new_patient as np
from services import rc as rc_module
from services.ai_service import MockAIProvider, is_synthetic_patient, provider_for_patient
from services.fhir import client as fhir

from . import roles
from .config import DEFAULT_CONFIG, PRESETS, SECTION_ORDER
from .models import BriefConfig, MdtCase, MdtSession, PatientDraft
from .views import _next_order, _require

log = logging.getLogger(__name__)

MAX_FILES = 10
MAX_FILE_BYTES = 20 * 1024 * 1024
TEXT_SUFFIXES = ('.txt', '.md', '.csv')
DETAIL_CONFIG = {**DEFAULT_CONFIG, 'name': 'Náhled nového pacienta (podrobně)', 'detail_level': 'detailed',
                 'sections': [{'id': s, 'enabled': True, 'order': i, 'detail': 'detailed'}
                              for i, s in enumerate(SECTION_ORDER)]}
NARROW_CONFIG = next(p for p in PRESETS if p['detail_level'] == 'brief')      # „Stručně (30 s)“ bez šablony


# ── pomocné ──────────────────────────────────────────────────────────────────
def _user_name(user) -> str:
    return (user.get_full_name() or user.username) if user else 'zadávající lékař'


def _draft_dict(d: PatientDraft) -> dict:
    session = d.session and {'id': d.session_id, 'title': d.session.title,
                             'date': timezone.localtime(d.session.date).isoformat()}
    return {'patient_id': d.patient_fhir_id, 'rc': d.rc, 'synthetic': d.synthetic,
            'requester': _user_name(d.created_by), 'session': session, **d.content}


def _ai_provider(d: PatientDraft):
    """LLM jen podle D-021 (syntetický pacient, nebo `AI_REAL_PATIENT_DATA=True`); mock = žádné volání ven."""
    tag = [{'resourceType': 'Patient', 'meta': {'tag': [np.FICTIONAL_TAG] if d.synthetic else []}}]
    provider = provider_for_patient(tag)
    return None if provider.is_mock else provider


def _read_inputs(request, start: int, patient_id: str, provider) -> list[dict]:
    """Vložený text (`text`) a soubory (`files`: PDF, TXT, MD) → dokumenty návrhu."""
    docs, number = [], start
    text = str(request.data.get('text') or '').strip()
    if text:
        docs.append(np.make_document(patient_id, number, text, 'vložený text'))
        number += 1
    jsons, transcripts = _uploads(request)           # FHIR JSON a jeho přepis .md nejsou podklady (T-335)
    files = [f for f in request.FILES.getlist('files') if f not in jsons and f not in transcripts]
    if len(files) > MAX_FILES:
        raise ValidationError({'files': f'Najednou nejvýš {MAX_FILES} souborů.'})
    for f in files:
        if f.size > MAX_FILE_BYTES:
            raise ValidationError({'files': f'{f.name}: soubor je větší než 20 MB.'})
        data, name = f.read(), f.name or 'soubor'
        if name.lower().endswith('.pdf') or f.content_type == 'application/pdf':
            # textová vrstva parserem bez LLM; sken přes OCR jen s povoleným LLM (D-021), jinak 400
            from services.ai.brief import _llm_call_log
            from services.ai.report_import import pdf_text
            try:
                content = pdf_text(data, provider or MockAIProvider(), _llm_call_log)
            except ValueError as e:
                raise ValidationError({'files': f'{name}: {e}'}) from None
        elif name.lower().endswith(TEXT_SUFFIXES) or (f.content_type or '').startswith('text/'):
            try:
                content = data.decode('utf-8')
            except UnicodeDecodeError:
                content = data.decode('cp1250', errors='replace')
        else:
            raise ValidationError({'files': f'{name}: podporované jsou PDF, textové soubory a FHIR JSON.'})
        try:
            docs.append(np.make_document(patient_id, number, content, f'soubor {name}'))
        except np.DraftError as e:
            raise ValidationError({'files': str(e)}) from None
        number += 1
    return docs


def _extract_values(d: PatientDraft, docs: list[dict]) -> None:
    """Hodnoty z podkladů přes LLM jako u BON-7 (každá ověřená proti odstavci). Bez povoleného LLM nic."""
    provider = _ai_provider(d)
    ai = d.content.setdefault('ai', {})
    if provider is None:
        ai.update(used=False, reason='AI podklady nečetla (skutečný pacient bez povolení pro AI podle D-021, nebo je AI '
                                     'vypnutá). Údaje předvyplnila jen pravidla z textu, zkontrolujte je.')
        return
    from services.ai.brief import _llm_call_log
    from services.ai.report_import import propose
    for doc in docs:
        try:
            proposal = propose(d.patient_fhir_id, doc['id'], doc['text'], provider, _llm_call_log)
        except ValueError as e:
            ai.setdefault('errors', []).append(f"{doc['id']}: {e}")
            continue
        d.content.setdefault('values', []).extend(proposal['values'])
        d.content.setdefault('rejected', []).extend(proposal['rejected'])
    ai.update(used=True, reason=None)


def _uploads(request) -> tuple[list, list]:
    """FHIR JSON a přepisy `.md` k nim (T-335). Bez JSON jsou `.md` obyčejné podklady (`_read_inputs`)."""
    files = request.FILES.getlist('files')
    jsons = [f for f in files if np.is_json_upload(f.name or '', f.content_type)]
    mds = [f for f in files if (f.name or '').lower().endswith('.md')] if jsons else []
    if len(jsons) + len(mds) > MAX_FILES:
        raise ValidationError({'files': f'Najednou nejvýš {MAX_FILES} souborů.'})
    for f in jsons + mds:
        if f.size > MAX_FILE_BYTES:
            raise ValidationError({'files': f'{f.name}: soubor je větší než 20 MB.'})
    return jsons, mds


def _patient_info(d: PatientDraft) -> dict:
    """Pohlaví a věk z RČ, u importu bez RČ z `Patient` souboru (RČ se nevrací, jen maskované)."""
    if d.rc:
        rc = rc_module.parse(d.rc)
        return {'rc_masked': rc.masked, 'sex': rc.gender, 'birth_year': rc.birth_date.year,
                'age': rc.age_at(timezone.localdate())}
    patient = next(r for r in d.content['bundle'] if r['resourceType'] == 'Patient')
    year = int(patient['birthDate'][:4])
    today = timezone.localdate()
    age = today.year - year
    if len(patient['birthDate']) >= 10:
        born = patient['birthDate'][:10]
        age -= (today.month, today.day) < (int(born[5:7]), int(born[8:10]))
    return {'rc_masked': None, 'sex': patient['gender'], 'birth_year': year, 'age': age}


def _response(d: PatientDraft, status: int = 200) -> Response:
    draft = _draft_dict(d)
    body = {
        'id': d.pk, 'status': d.status, 'patient_id': d.patient_fhir_id, 'synthetic': d.synthetic,
        'session': draft['session'], 'case_id': d.case_id,
        **{k: draft.get(k) for k in ('documents', 'fields', 'edited', 'values', 'rejected', 'ai', 'import')},
    }
    if d.status == 'draft':
        body['patient'] = _patient_info(d)
        body['missing_for_confirm'] = np.missing_for_confirm(draft)
        body['preview'] = np.preview(draft, timezone.localtime(), detail_config=DETAIL_CONFIG,
                                     narrow_config=NARROW_CONFIG)
        template = body['preview']['template']
        if template:                             # preset šablony jako u GET …/cases/{cid}/template/ (T-318)
            preset = BriefConfig.objects.filter(name=template['config']['name'], is_preset=True).first()
            template['config_id'] = str(preset.pk) if preset else None
    return Response(body, status=status)


def _get_draft(request, draft_id: int) -> PatientDraft:
    d = get_object_or_404(PatientDraft.objects.select_related('session', 'created_by'), pk=draft_id)
    if roles.role(request.user) != roles.ADMIN and d.created_by_id != request.user.pk:
        raise PermissionDenied('Návrh pacienta smí vidět a měnit jen jeho autor a předseda.')
    return d


def _session(value) -> MdtSession | None:
    if value in (None, ''):
        return None
    session = get_object_or_404(MdtSession, pk=value)
    if session.status == 'closed':
        raise ValidationError({'session': 'Board je uzavřený.'})
    return session


# ── endpointy ────────────────────────────────────────────────────────────────
@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def draft_list(request):
    """GET: rozpracované návrhy (moje, předseda všechny). POST: `rc` (+ `text`, `files`, `synthetic`, `session`)
    → návrh s předvyplněnou nominací a náhledy. Pacient se stejným RČ už v IRIS → 409 s `patient_id`."""
    _require(request, roles.ADMIN, roles.DOCTOR)
    if request.method == 'GET':
        drafts = PatientDraft.objects.filter(status='draft')
        if roles.role(request.user) != roles.ADMIN:
            drafts = drafts.filter(created_by=request.user)
        return Response([{'id': d.pk, 'patient_id': d.patient_fhir_id, 'documents': len(d.content.get('documents', [])),
                          'created_at': d.created_at, 'updated_at': d.updated_at} for d in drafts])
    jsons, mds = _uploads(request)
    raw_rc = str(request.data.get('rc') or '').strip()
    rc = None
    if raw_rc or not jsons:                      # u FHIR JSON je RČ nepovinné (dataset ho nemá), jinak povinné
        try:
            rc = rc_module.parse(raw_rc)
        except rc_module.RcError as e:
            raise ValidationError({'rc': str(e)}) from None
    imports = _parse_imports(jsons, mds) if jsons else [None]
    if len(imports) > 1 and (rc or request.data.get('text') or [f for f in request.FILES.getlist('files')
                                                                 if f not in jsons and f not in mds]):
        raise ValidationError({'files': f'Soubory obsahují {len(imports)} pacienty: RČ, text a PDF přidejte až ke '
                                        'konkrétnímu návrhu (RČ může být v přepisu .md).'})
    patients = fhir.search('Patient')
    for item in imports:
        candidate = rc or (item and item['rc'])
        existing = candidate and np.patient_with_rc(patients, candidate.value)
        if existing:
            return Response({'detail': 'Pacient s tímto rodným číslem už v IRIS je.', 'patient_id': existing}, status=409)
        open_draft = candidate and PatientDraft.objects.filter(status='draft', rc=candidate.value).first()
        if open_draft:
            return Response({'detail': 'Pro toto rodné číslo už rozpracovaný návrh je.', 'draft_id': open_draft.pk},
                            status=409)
    synthetic = str(request.data.get('synthetic', '')).lower() in ('1', 'true', 'yes')
    session = _session(request.data.get('session'))
    drafts = []
    with transaction.atomic():
        taken = [p['id'] for p in patients] + list(PatientDraft.objects.filter(status='draft')
                                                   .values_list('patient_fhir_id', flat=True))
        for item in imports:
            patient_rc = rc or (item and item['rc'])
            d = PatientDraft(created_by=request.user, patient_fhir_id=np.next_patient_id(taken),
                             rc=patient_rc.value if patient_rc else '', synthetic=synthetic, session=session, content={})
            taken.append(d.patient_fhir_id)
            content = _import_json(d, item, patient_rc) if item else {}
            docs = _read_inputs(request, 1, d.patient_fhir_id, _ai_provider(d)) if len(imports) == 1 else []
            fields = np.prefill(docs, content.get('fields'), [])
            d.content = {**content, 'documents': docs, 'fields': fields, 'edited': [], 'values': [], 'rejected': [],
                         'ai': {}}
            _extract_values(d, docs)
            d.save()
            drafts.append(d)
    response = _response(drafts[0], status=201)
    if len(drafts) > 1:                          # víc pacientů: návrh prvního + seznam všech (T-335)
        response.data['batch'] = [{'id': d.pk, 'patient_id': d.patient_fhir_id,
                                   'file': d.content['import']['file'], 'renamed_from': d.content['import']['renamed_from']}
                                  for d in drafts]
    return response


def _parse_imports(jsons, mds) -> list[dict]:
    """Soubory FHIR JSON → pacienti (soubor může mít víc pacientů) s přepisem `.md` a RČ z přepisu."""
    transcripts = {}
    for f in mds:
        text = f.read().decode('utf-8-sig', errors='replace')
        transcripts[np.transcript_patient(text) or f.name] = (f.name, text)
    out = []
    for f in jsons:
        name = f.name or 'soubor.json'
        try:
            resources, full_urls, tags = np.fhir_resources(f.read(), name)
            groups = np.split_by_patient(resources, full_urls)
        except np.DraftError as e:
            raise ValidationError({'files': str(e)}) from None
        for group in groups:
            patient = next((r for r in group if r['resourceType'] == 'Patient'), None)
            transcript = transcripts.pop(patient['id'], None) if patient else None
            if transcript is None and len(jsons) == 1 and len(groups) == 1 and len(transcripts) == 1:
                transcript = transcripts.popitem()[1]          # jeden soubor, jeden přepis: patří k sobě
            validation, md_rc = (np.check_transcript(transcript[1], group) if transcript and patient else ([], None))
            try:
                rc = rc_module.parse(md_rc) if md_rc else None
            except rc_module.RcError as e:
                raise ValidationError({'files': f'{transcript[0]}: RČ v přepisu je neplatné ({e}).'}) from None
            out.append({'file': name, 'resources': group, 'full_urls': full_urls, 'tags': tags, 'rc': rc,
                        'transcript': transcript[0] if transcript else None, 'validation': validation})
    if transcripts:
        raise ValidationError({'files': f'Přepis {", ".join(n for n, _ in transcripts.values())} nepatří k žádnému '
                                        'pacientovi v nahraných souborech FHIR JSON.'})
    return out


def _import_json(d: PatientDraft, item: dict, rc) -> dict:
    """FHIR JSON → `bundle` (sanitizovaný, přečíslovaný na `d.patient_fhir_id`) a nominace ze strukturovaných dat."""
    def in_iris(rtype: str, rid: str) -> bool:
        try:
            return bool(fhir.read(rtype, rid))
        except Exception:
            return False

    try:
        bundle, info = np.import_bundle(item['resources'], d.patient_fhir_id, rc, d.synthetic, item['full_urls'],
                                        item['tags'], in_iris)
    except np.DraftError as e:
        raise ValidationError({'files': f"{item['file']}: {e}"}) from None
    d.synthetic = info['synthetic']
    fields, request_id = np.prefill_from_resources(bundle)
    return {'bundle': bundle, 'service_request_id': request_id, 'fields': fields,
            'import': {**info, 'file': item['file'], 'total': len(bundle), 'transcript': item['transcript'],
                       'validation': item['validation']}}


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def draft_detail(request, draft_id):
    """GET: návrh + náhledy. PATCH: úpravy lékaře (`fields`, `values`, `remove_documents`, `synthetic`, `session`)
    → nové náhledy. DELETE: zahodit návrh (nic v IRIS)."""
    _require(request, roles.ADMIN, roles.DOCTOR)
    d = _get_draft(request, draft_id)
    if request.method == 'GET':
        return _response(d)
    if d.status != 'draft':
        return Response({'detail': 'Návrh je potvrzený, pacient je v IRIS.', 'patient_id': d.patient_fhir_id}, status=409)
    if request.method == 'DELETE':
        d.delete()
        return Response(status=204)
    data = request.data
    content = d.content
    for doc_id in data.get('remove_documents') or []:
        content['documents'] = [x for x in content['documents'] if x['id'] != doc_id]
        content['values'] = [v for v in content.get('values', []) if not v['citation'].startswith(f'{doc_id}#')]
        content['fields'] = _drop_citations(content['fields'], doc_id)
    if 'values' in data:                         # lékař ponechá jen část navržených hodnot (ověří se znovu při zápisu)
        keep = {v.get('citation') + '|' + v.get('label', '') for v in data['values'] or [] if isinstance(v, dict)}
        content['values'] = [v for v in content.get('values', []) if v['citation'] + '|' + v['label'] in keep]
    if 'fields' in data:
        locked = {'diagnoses', 'tnm', 'ecog'} & set(data['fields'] or {}) if content.get('bundle') else set()
        if locked:                               # strukturovaná data ze souboru se opravují v souboru (T-335)
            raise ValidationError({'fields': f'{", ".join(sorted(locked))}: údaje jsou ze souboru FHIR JSON, '
                                             'opravte je v souboru a nahrajte znovu.'})
        content['fields'], edited = _edit_fields(content['fields'], data['fields'])
        content['edited'] = sorted(set(content.get('edited', [])) | edited)
    if 'synthetic' in data:
        d.synthetic = bool(data['synthetic'])
    if 'session' in data:
        d.session = _session(data['session'])
    d.content = content
    d.save()
    return _response(d)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def draft_documents(request, draft_id):
    """Další podklady do návrhu: `text` a/nebo `files`. Prázdná pole nominace se z nich doplní."""
    _require(request, roles.ADMIN, roles.DOCTOR)
    d = _get_draft(request, draft_id)
    if d.status != 'draft':
        return Response({'detail': 'Návrh je potvrzený, další zprávy přidejte přes vložení zprávy (BON-7).'}, status=409)
    if _uploads(request)[0]:
        raise ValidationError({'files': 'FHIR JSON jde nahrát jen při založení nového pacienta.'})
    numbers = [int(x['id'].rsplit('imp', 1)[1]) for x in d.content.get('documents', [])]
    docs = _read_inputs(request, max(numbers, default=0) + 1, d.patient_fhir_id, _ai_provider(d))
    if not docs:
        raise ValidationError({'text': 'Vložte text nebo nahrajte soubor.'})
    d.content['documents'] = d.content.get('documents', []) + docs
    d.content['fields'] = np.prefill(docs, d.content.get('fields'), d.content.get('edited', []))
    _extract_values(d, docs)
    d.save()
    return _response(d)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def draft_confirm(request, draft_id):
    """Potvrzení lékařem: jedna transakce do IRIS (+ `Provenance`), vektory, případ na boardu návrhu.
    Bez otázky pro MDT nebo diagnózy 400 (`missing`)."""
    _require(request, roles.ADMIN, roles.DOCTOR)
    d = _get_draft(request, draft_id)
    if d.status != 'draft':
        return Response({'detail': 'Návrh už je potvrzený.', 'patient_id': d.patient_fhir_id, 'case_id': d.case_id},
                        status=409)
    missing = np.missing_for_confirm(_draft_dict(d))
    if missing:
        return Response({'detail': 'K potvrzení chybí údaje.', 'missing': missing}, status=400)
    patients = fhir.search('Patient')
    existing = d.rc and np.patient_with_rc(patients, d.rc)
    if existing:
        return Response({'detail': 'Pacient s tímto rodným číslem už v IRIS je.', 'patient_id': existing}, status=409)
    if any(p['id'] == d.patient_fhir_id for p in patients):    # ID mezitím obsadil jiný pacient → přečíslovat
        _renumber(d, np.next_patient_id([p['id'] for p in patients] + list(
            PatientDraft.objects.filter(status='draft').values_list('patient_fhir_id', flat=True))))
    resources = np.build_resources(_draft_dict(d), timezone.localtime())
    fhir.transaction(np.transaction(resources))
    try:                                         # vektory pro hledání a grounding; selhání zápis nezruší
        from services.iris import indexing
        indexing.index_patient(d.patient_fhir_id, resources)
    except Exception:
        log.warning('Vektory nového pacienta %s se nepodařilo spočítat (ručně: ingest_dataset --skip-fhir)',
                    d.patient_fhir_id, exc_info=True)
    with transaction.atomic():
        if d.session:
            question = d.content['fields']['question']['text']
            request_id = resources[-1]['id'].removesuffix('-prov')       # Provenance nominace je vždy poslední
            d.case = MdtCase.objects.create(
                session=d.session, patient_fhir_id=d.patient_fhir_id, service_request_fhir_id=request_id,
                question=question, created_by=request.user, order=_next_order(d.session))
        d.status, d.rc = 'confirmed', ''         # data jsou v IRIS; RČ a texty podkladů z návrhu pryč
        d.content = {'documents': [{'id': x['id'], 'title': x['title']} for x in d.content.get('documents', [])]}
        d.save()
    return Response({'patient_id': d.patient_fhir_id, 'case_id': d.case_id, 'synthetic': is_synthetic_patient(resources),
                     'fhir_written': [f"{r['resourceType']}/{r['id']}" for r in resources]}, status=201)


# ── úpravy polí ───────────────────────────────────────────────────────────────
def _drop_citations(fields: dict, doc_id: str) -> dict:
    """Údaje převzaté z odebraného dokumentu zmizí (lékařem upravené zůstanou, nemají citaci dokumentu)."""
    out = {}
    for key, value in fields.items():
        if key == 'diagnoses':
            out[key] = [x for x in value if not (x.get('citation') or '').startswith(f'{doc_id}#')]
        elif isinstance(value, dict) and (value.get('citation') or '').startswith(f'{doc_id}#'):
            continue
        else:
            out[key] = value
    return out


def _edit_fields(fields: dict, edits) -> tuple[dict, set[str]]:
    """Úpravy lékaře. Upravený údaj nemá citaci dokumentu: cituje se nominace, do které ho lékař napsal."""
    if not isinstance(edits, dict):
        raise ValidationError({'fields': 'Očekáván objekt polí nominace.'})
    fields, edited = dict(fields), set()
    for name in np.TEXT_FIELDS:
        if name in edits:
            text = str(edits[name] or '').strip()
            fields[name] = {'text': text, 'citation': None} if text else None
            edited.add(name)
    if 'nomination_type' in edits:
        if edits['nomination_type'] not in np.NOMINATION_TYPES:
            raise ValidationError({'nomination_type': f'Jen {", ".join(np.NOMINATION_TYPES)}.'})
        fields['nomination_type'] = edits['nomination_type']
    if 'tnm' in edits:
        text = str(edits['tnm'] or '').strip()
        fields['tnm'] = {'text': text, 'citation': None} if text else None
        edited.add('tnm')
    if 'ecog' in edits:
        if edits['ecog'] is not None and edits['ecog'] not in range(5):
            raise ValidationError({'ecog': 'ECOG 0–4 nebo null.'})
        fields['ecog'] = None if edits['ecog'] is None else {'value': edits['ecog'], 'citation': None}
        edited.add('ecog')
    if 'diagnoses' in edits:
        before = {x['code']: x for x in fields.get('diagnoses') or []}
        diagnoses = []
        for item in edits['diagnoses'] or []:
            code = str((item or {}).get('code', '')).strip().upper()
            if not re.fullmatch(r'[CD]\d{2}(\.\d{1,2})?', code) or not np.is_oncologic_code(code):
                raise ValidationError({'diagnoses': f'{code or "?"}: jen onkologický kód MKN-10 (C00–C97, D00–D09, D37–D48).'})
            text = str(item.get('text') or '').strip() or before.get(code, {}).get('text') or code
            same = before.get(code)
            diagnoses.append({'code': code, 'text': text,
                              'citation': same.get('citation') if same and same.get('text') == text else None})
        fields['diagnoses'] = diagnoses
        edited.add('diagnoses')
    return fields, edited


def _renumber(d: PatientDraft, new_id: str) -> None:
    """Přečísluje návrh na jiné `Pnn` (ID dokumentů a citace obsahují ID pacienta)."""
    import json
    old = d.patient_fhir_id
    content = dict(d.content)
    bundle = content.pop('bundle', None)
    content = json.loads(json.dumps(content).replace(f'"{old}-', f'"{new_id}-').replace(f'{old}-imp', f'{new_id}-imp'))
    if bundle:                                   # import z FHIR JSON: i `Patient/Pxx`, `LEK-Pxx-…` (T-335)
        content['bundle'] = np.renumber_resources(bundle, old, new_id)
    d.content = content
    d.patient_fhir_id = new_id
