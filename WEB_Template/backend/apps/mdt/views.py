"""API MDT (ARCH §6.3). Oprávnění podle rolí (D-014, POZADAVKY_LEKARE §1)."""
import base64
import json
import logging
import re

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from pydantic import ValidationError as SchemaError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.copilot import jobs
from apps.copilot.models import GenerationJob
from apps.copilot.schemas import Decision as DecisionSchema
from services import patients, tasks
from services.fhir import export, writeback
from services.fhir.client import FhirError
from services.rules import intake, readiness
from services.rules.compatibility import evaluate_compatibility

from . import config as cfg
from . import roles
from .config import DEFAULT_CONFIG, BriefConfigSerializer
from .models import BriefConfig, Decision, MdtCase, MdtSession

logger = logging.getLogger(__name__)


# ── oprávnění ────────────────────────────────────────────────────────────────
def _require(request, *allowed: str) -> None:
    if roles.role(request.user) not in allowed:
        raise PermissionDenied('Na tuto akci nemáte oprávnění (role MDT).')


def can_edit_case(user, case: MdtCase) -> bool:
    """Předseda jakýkoli případ, zadávající lékař svého pacienta, přizvaný lékař případ, ke kterému byl přizván
    (T-326; přizvání dává právo úprav i členovi komise s rolí jen ke čtení, např. chirurgovi k resekabilitě)."""
    r = roles.role(user)
    if r == roles.ADMIN or (r == roles.DOCTOR and case.created_by_id == user.pk):
        return True
    return case.pk is not None and case.collaborators.filter(pk=user.pk).exists()


def _require_case_edit(request, case: MdtCase) -> None:
    if not can_edit_case(request.user, case):
        raise PermissionDenied('Případ smí měnit jen zadávající lékař, přizvaný lékař nebo předseda.')


# ── serializace ──────────────────────────────────────────────────────────────
def _user(u) -> dict | None:
    return u and {'user_id': u.pk, 'name': u.get_full_name() or u.username}


def _member(u) -> dict:
    """`Me` (§8.6): role a odbornost uživatele."""
    return {'user_id': u.pk, 'username': u.username, 'name': u.get_full_name() or u.username,
            'role': roles.role(u), 'specialty': roles.specialty(u), 'practitioner_id': roles.practitioner_id(u)}


def _session(s: MdtSession) -> dict:
    return {'id': s.pk, 'date': timezone.localtime(s.date).isoformat(), 'title': s.title, 'status': s.status,
            'chair': _user(s.chair), 'config_id': s.config_id}


def _case(c: MdtCase, patient: dict | None = None) -> dict:
    return {'id': c.pk, 'session': c.session_id, 'order': c.order, 'patient_id': c.patient_fhir_id,
            'service_request_id': c.service_request_fhir_id, 'question': c.question, 'status': c.status,
            'ecog': c.ecog, 'intent': c.intent, 'imaging_recent_checked': c.imaging_recent_checked,
            'skipped_fields': c.skipped_fields, 'acknowledged_warnings': c.acknowledged_warnings,
            'created_by': _user(c.created_by), 'collaborators': [_user(u) for u in c.collaborators.all()],
            'patient': patient}


def _datetime(value) -> timezone.datetime:
    dt = parse_datetime(str(value or ''))
    if dt is None:
        raise ValidationError({'date': 'Očekáváno datum a čas ISO 8601.'})
    return dt if timezone.is_aware(dt) else timezone.make_aware(dt)


def _config(data, case: MdtCase) -> dict:
    """`{config_id}` → preset, `{config}` → konfigurace z UI, jinak výchozí boardu nebo DEFAULT_CONFIG."""
    if data.get('config_id') is not None:
        return get_object_or_404(BriefConfig, pk=data['config_id']).snapshot()
    if data.get('config') is not None:
        if not isinstance(data['config'], dict):
            raise ValidationError({'config': 'Očekáván objekt BriefConfig (ARCH §8.5).'})
        return cfg.validated(data['config'])
    return case.session.config.snapshot() if case.session.config else dict(DEFAULT_CONFIG)


# ── endpointy ────────────────────────────────────────────────────────────────
@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Role a odbornost přihlášeného (FR-U1)."""
    return Response(_member(request.user))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list(request):
    """Uživatelé s rolí a odborností (`Me[]`, T-319). Číst smí předseda a lékař (T-326: zadávající lékař vybírá,
    koho přizvat ke spolupráci); role a odbornost mění jen předseda (`user_detail`)."""
    _require(request, roles.ADMIN, roles.DOCTOR)
    users = get_user_model().objects.filter(is_active=True).order_by('username')
    return Response([_member(u) for u in users])


def _link_practitioner(user, pid: str) -> None:
    from services import practitioners
    from .models import UserProfile
    if not practitioners.exists(pid):
        raise ValidationError({'practitioner_id': f'Lékař {pid} v IRIS není.'})
    if UserProfile.objects.filter(practitioner_fhir_id=pid).exclude(user=user).exists():
        raise ValidationError({'practitioner_id': f'Lékař {pid} už je propojený s jiným účtem.'})
    UserProfile.objects.update_or_create(user=user, defaults={'practitioner_fhir_id': pid})


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def practitioner_list(request):
    """Lékaři nemocnice z IRIS pro výběr (T-328): `?q=` (jméno, odbornost, ID; bez diakritiky), `?with_user=1` jen
    s účtem v aplikaci, `?limit=` (výchozí 50). Nejdřív lékaři s účtem."""
    from services import practitioners
    users = roles.users_by_practitioner()
    try:
        limit = min(int(request.query_params.get('limit') or 50), 500)
    except ValueError:
        raise ValidationError({'limit': 'Číslo.'}) from None
    items = practitioners.search(request.query_params.get('q', ''), users, limit=500)
    if request.query_params.get('with_user') in ('1', 'true'):
        items = [i for i in items if i['user']]
    return Response(items[:limit])


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def user_detail(request, uid):
    """Předseda mění roli (`mdt_admin` / `mdt_doctor` / `mdt_viewer`) a odbornost (RoleId) uživatele (T-319)
    a propojení s lékařem v IRIS `practitioner_id` (T-328)."""
    _require(request, roles.ADMIN)
    user = get_object_or_404(get_user_model(), pk=uid)
    role, specialty = request.data.get('role'), request.data.get('specialty')
    if request.data.get('practitioner_id'):
        _link_practitioner(user, str(request.data['practitioner_id']))
    if role is not None and role not in roles.ROLES:
        raise ValidationError({'role': f'Jen {", ".join(roles.ROLES)}.'})
    if specialty is not None and specialty not in roles.SPECIALTIES:
        raise ValidationError({'specialty': f'Jen {", ".join(roles.SPECIALTIES)}.'})
    if user.pk == request.user.pk and role not in (None, roles.ADMIN):
        raise ValidationError({'role': 'Sám sobě roli předsedy odebrat nejde.'})
    roles.assign(user, role=role, specialty=specialty)
    if specialty is not None:
        try:                                     # odbornost i u lékaře účtu v IRIS (LEK-APP-…, T-328)
            roles.ensure_practitioner(user)
        except FhirError:
            pass
    return Response(_member(user))


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def session_list(request):
    """GET: boardy s pacienty v pořadí agendy; `?from=&to=` (YYYY-MM-DD, včetně) omezí rozsah, `?expand=cases`
    přidá `cases: MdtCaseSummary[]` pro kalendář (T-518). POST (jen předseda): `{date, title, config_id?}`."""
    if request.method == 'POST':
        _require(request, roles.ADMIN)
        if not request.data.get('title'):
            raise ValidationError({'title': 'Povinné (zaměření komise).'})
        s = MdtSession.objects.create(date=_datetime(request.data.get('date')), title=request.data['title'],
                                      chair=request.user, config_id=request.data.get('config_id'))
        return Response(_session(s), status=201)
    sessions = MdtSession.objects.select_related('chair').prefetch_related('cases')
    for param, lookup in (('from', 'date__date__gte'), ('to', 'date__date__lte')):
        if request.query_params.get(param):
            day = parse_date(request.query_params[param])
            if day is None:
                raise ValidationError({param: 'Datum YYYY-MM-DD.'})
            sessions = sessions.filter(**{lookup: day})
    sessions = list(sessions)
    out = [{**_session(s), 'patients': [c.patient_fhir_id for c in s.cases.all()]} for s in sessions]
    if 'cases' in request.query_params.get('expand', '').split(','):
        summaries = _case_summaries([c for s in sessions for c in s.cases.all()])
        for item, s in zip(out, sessions):
            item['cases'] = [summaries[c.pk] for c in s.cases.all()]
    return Response(out)


def _case_summaries(cases: list[MdtCase]) -> dict[int, dict]:
    """`MdtCaseSummary` (ARCH §8.6): hlavička z IRIS jedním seznamem pacientů, připravenost (T-303) jednou na pacienta."""
    if not cases:
        return {}
    by_id = {p['id']: p for p in patients.list_patients()}
    scores: dict[tuple[str, tuple], float | None] = {}
    out = {}
    for c in cases:
        key = (c.patient_fhir_id, tuple(c.skipped_fields))
        if key not in scores:
            try:
                score = readiness.evaluate_readiness(patients.load_patient(c.patient_fhir_id), c.skipped_fields)['score']
                scores[key] = round(score['present'] / score['total'], 2) if score['total'] else None
            except FhirError:
                scores[key] = None                      # pacient v IRIS není: nespočteno
        p = by_id.get(c.patient_fhir_id) or {}
        dg = p.get('diagnosis')
        out[c.pk] = {'id': c.pk, 'order': c.order, 'status': c.status, 'patient_id': c.patient_fhir_id,
                     'display_name': p.get('display_name') or c.patient_fhir_id,
                     'diagnosis': {'icd10': dg['icd10'], 'text': dg['text']} if dg else None,
                     'ecog': c.ecog, 'intent': c.intent, 'readiness': scores[key]}
    return out


def _next_order(session: MdtSession) -> int:
    last = session.cases.order_by('-order').values_list('order', flat=True).first()
    return 0 if last is None else last + 1


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def session_order(request, sid):
    """Pořadí pacientů v agendě boardu (T-324), jen předseda: `{cases: [cid, …]}` = všechny případy boardu."""
    _require(request, roles.ADMIN)
    session = get_object_or_404(MdtSession, pk=sid)
    order = request.data.get('cases')
    current = set(session.cases.values_list('pk', flat=True))
    if not isinstance(order, list) or len(order) != len(set(order)) or set(order) != current:
        raise ValidationError({'cases': 'Pošlete ID všech případů boardu, každé jednou, v novém pořadí.'})
    with transaction.atomic():
        for position, cid in enumerate(order):
            MdtCase.objects.filter(pk=cid, session=session).update(order=position)
    return _agenda_response(session)


def _agenda_response(s: MdtSession) -> Response:
    """Board + agenda v pořadí `MdtCase.order` (hlavička pacienta z IRIS)."""
    cases = list(s.cases.select_related('created_by').prefetch_related('collaborators'))
    by_id = {p['id']: p for p in patients.list_patients()} if cases else {}
    return Response({**_session(s), 'cases': [_case(c, by_id.get(c.patient_fhir_id)) for c in cases]})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def session_detail(request, sid):
    """GET: board + agenda (`MdtCase` + hlavička z IRIS). PATCH/DELETE jen předseda."""
    s = get_object_or_404(MdtSession.objects.select_related('chair'), pk=sid)
    if request.method == 'DELETE':
        _require(request, roles.ADMIN)
        if s.cases.exists():
            return Response({'detail': 'Board má pacienty, nejdřív je přesuňte.'}, status=409)
        s.delete()
        return Response(status=204)
    if request.method == 'PATCH':
        _require(request, roles.ADMIN)
        data = request.data
        for field in ('title', 'status', 'config_id'):
            if field in data:
                setattr(s, field, data[field])
        if 'date' in data:
            s.date = _datetime(data['date'])
            # ponytail: Task v IRIS po jednom; když jeden zápis selže, předchozí zůstanou (IRIS = zdroj pravdy)
            for c in s.cases.all():
                writeback.set_mdt_date(c.patient_fhir_id, c.service_request_fhir_id, timezone.localtime(s.date))
        s.full_clean(exclude=['chair', 'config'])
        s.save()
    return _agenda_response(s)


CLOSED_BOARD = {'detail': 'Board je uzavřený, pacienta na něj nejde zařadit ani přesunout.'}


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def case_detail(request, cid):
    """Přesun do jiného boardu (zapíše termín do `Task` v IRIS), ECOG, záměr C/P, checkbox snímku,
    přeskočené údaje, `acknowledge: [warning_id]` (odkliknutí se jen přidává, D-019), `status` (jen předseda)."""
    case = get_object_or_404(MdtCase.objects.select_related('session', 'created_by'), pk=cid)
    _require_case_edit(request, case)
    _validate_case_input(request, request.data, case)
    _validate_collaborators(request, request.data, case)
    if request.data.get('session', case.session_id) != case.session_id and \
            MdtSession.objects.filter(pk=request.data['session'], status='closed').exists():
        return Response(CLOSED_BOARD, status=409)
    with transaction.atomic():
        written = _apply_case_input(request, case, request.data)
    return Response({**_case(case), 'fhir_written': written})


def _validate_case_input(request, data, case: MdtCase | None = None) -> None:
    if 'ecog' in data and data['ecog'] is not None and data['ecog'] not in range(5):
        raise ValidationError({'ecog': 'ECOG 0–4 nebo null.'})
    if 'intent' in data and data['intent'] not in ('C', 'P', None):
        raise ValidationError({'intent': 'C, P nebo null.'})
    for field in ('skipped_fields', 'acknowledge'):
        if field in data and not (isinstance(data[field], list) and all(isinstance(x, str) for x in data[field])):
            raise ValidationError({field: 'Seznam ID.'})
    if 'mdt.question' in data.get('skipped_fields', []):
        raise ValidationError({'skipped_fields': 'Otázku pro MDT nelze přeskočit (OBC-1.1).'})
    if 'status' in data:
        _require(request, roles.ADMIN)
        if data['status'] not in dict(MdtCase.STATUS):
            raise ValidationError({'status': f'Jen {", ".join(dict(MdtCase.STATUS))}.'})


def _validate_collaborators(request, data, case: MdtCase | None) -> None:
    """`collaborators: [user_id]` mění jen předseda nebo zadávající lékař; přizvaný lékař další nepřizývá."""
    if 'collaborators' not in data:
        return
    ids = data['collaborators']
    if not (isinstance(ids, list) and all(isinstance(x, int) and not isinstance(x, bool) for x in ids)):
        raise ValidationError({'collaborators': 'Seznam ID uživatelů.'})
    creator = case.created_by_id if case else request.user.pk
    if not (roles.role(request.user) == roles.ADMIN or creator == request.user.pk):
        raise PermissionDenied('Ke spolupráci přizývá zadávající lékař nebo předseda.')
    known = set(get_user_model().objects.filter(pk__in=ids, is_active=True).values_list('pk', flat=True))
    if missing := sorted(set(ids) - known):
        raise ValidationError({'collaborators': f'Neznámí uživatelé: {missing}.'})


def _apply_case_input(request, case: MdtCase, data, warnings: dict | None = None) -> list[str]:
    """Společné pro zařazení (POST) i úpravu (PATCH). Ruční ECOG, záměr C/P a odkliknutá varování jdou do IRIS
    (`writeback.write_intake`, s Provenance). Vrací zapsané FHIR resources."""
    if 'session' in data and data['session'] != case.session_id:
        target = get_object_or_404(MdtSession, pk=data['session'])
        writeback.set_mdt_date(case.patient_fhir_id, case.service_request_fhir_id, timezone.localtime(target.date))
        case.session = target
        case.order = _next_order(target)               # T-324: na konec agendy nového boardu
    for field in ('ecog', 'intent', 'imaging_recent_checked', 'skipped_fields', 'status'):
        if field in data:
            setattr(case, field, data[field])
    known = {w['id'] for w in case.acknowledged_warnings}
    now = timezone.localtime()
    new_acks = [{'id': w, 'by': request.user.pk, 'at': now.isoformat()}
                for w in dict.fromkeys(data.get('acknowledge', [])) if w not in known]
    start = len(case.acknowledged_warnings)
    case.acknowledged_warnings += new_acks
    case.save()
    if 'collaborators' in data:      # ověřeno v _validate_collaborators; zadávající lékař sám sebe nepřizývá
        case.collaborators.set([uid for uid in data['collaborators'] if uid != case.created_by_id])
    ecog = data.get('ecog') if 'ecog' in data else None
    intent = data.get('intent')
    if ecog is None and not intent and not new_acks:
        return []
    if new_acks and warnings is None:
        prefill = intake.intake_prefill(patients.load_patient(case.patient_fhir_id), case.skipped_fields)
        warnings = {w['id']: w for w in prefill['warnings']}
    return writeback.write_intake(
        patient_id=case.patient_fhir_id, case_no=case.pk, service_request_id=case.service_request_fhir_id,
        ecog=ecog, intent=intent, acknowledged=list(enumerate(new_acks, start + 1)), warnings=warnings or {},
        entered_by=request.user.get_full_name() or request.user.username, now=now)


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_intake(request, pid):
    """Předvyplnění formuláře zařazení (IntakePrefill §8.6): povinné údaje s citacemi a varování. `?skipped=a,b`."""
    resources = _patient_resources(pid)
    skipped = [s for s in request.query_params.get('skipped', '').split(',') if s]
    return Response(intake.intake_prefill(resources, skipped))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_readiness(request, cid):
    """Kontrola připravenosti (BON-1, `Readiness` §8.6): checklist OBC-1.1, staging ≤ 42 dní (OBC-1.2), biomarkery."""
    case = get_object_or_404(MdtCase, pk=cid)
    return Response(readiness.evaluate_readiness(_patient_resources(case.patient_fhir_id), case.skipped_fields))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_compatibility(request, cid):
    """Semafor souladu postupů se stavem pacienta (FR-D4, §8.3): všechny postupy ze sady guidelines, i červené."""
    from services.rules.onko_kb import kb_for_patient

    case = get_object_or_404(MdtCase, pk=cid)
    resources = _patient_resources(case.patient_fhir_id)
    # T-316: katalog (barvy P03/P04 beze změny) + další postupy pro diagnózu ze znalostní báze data/onko
    return Response(evaluate_compatibility(resources, skipped_fields=case.skipped_fields) + kb_for_patient(resources))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_template(request, cid):
    """Doporučená šablona projektoru podle diagnózy (T-318, `CaseTemplate` §6.3): `BriefConfig` + preset,
    klíčové údaje na projektor se stavem a citací, studie a varování z katalogu údajů `data/onko`."""
    from services.rules.templates import case_template as template_for

    case = get_object_or_404(MdtCase, pk=cid)
    template = template_for(_patient_resources(case.patient_fhir_id))
    if template is None:
        return Response({'detail': 'Pro diagnózu pacienta není šablona (chybí báze data/onko nebo diagnóza).'},
                        status=404)
    preset = BriefConfig.objects.filter(name=template['config']['name'], is_preset=True).first()
    return Response({**template, 'config_id': str(preset.pk) if preset else None})


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_for_me(request, cid):
    """„Pro mě nahoře“ (T-319, `SpecialtyView` §6.3): sekce, údaje, varování a postupy podle odbornosti
    přihlášeného (`UserProfile.specialty`) nebo `?specialty=` (RoleId). Pořadí předsedy se nemění."""
    from services.rules.templates import view_for

    specialty = request.query_params.get('specialty') or roles.specialty(request.user)
    if specialty not in cfg.ROLE_IDS:
        raise ValidationError({'specialty': f'Odbornost jen z RoleId: {sorted(cfg.ROLE_IDS)} (doplňte v profilu).'})
    case = get_object_or_404(MdtCase, pk=cid)
    view = view_for(specialty, _patient_resources(case.patient_fhir_id))
    if view is None:
        return Response({'detail': 'Pro diagnózu pacienta není pohled (chybí báze data/onko nebo diagnóza).'},
                        status=404)
    return Response(view)


def _patient_resources(pid: str) -> list[dict]:
    if not patients.VALID_ID.match(pid or ''):
        raise ValidationError({'patient_id': 'Neplatné ID pacienta.'})
    try:
        resources = patients.load_patient(pid)
    except FhirError as e:
        if e.status != 404:
            raise
        resources = []
    if not any(r['resourceType'] == 'Patient' for r in resources):
        raise NotFound('Pacient v IRIS není.')
    return resources


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def case_create(request):
    """Zařazení pacienta do boardu (FR-P4): `{session, patient_id, ecog, intent, imaging_recent_checked,
    skipped_fields, acknowledge}`. Nominace už má případ (seed_mdt) → doplní ho a přesune (200), jinak založí (201)."""
    _require(request, roles.ADMIN, roles.DOCTOR)
    data = request.data
    _validate_case_input(request, data)
    _validate_collaborators(request, data, None)
    session = get_object_or_404(MdtSession, pk=data.get('session'))
    if session.status == 'closed':
        return Response(CLOSED_BOARD, status=409)
    pid = data.get('patient_id')
    prefill = intake.intake_prefill(_patient_resources(pid), data.get('skipped_fields', []))
    question = next((f for f in prefill['fields'] if f['id'] == 'mdt.question'), {})
    if question.get('status') != 'present':
        raise ValidationError({'mdt.question': 'Bez otázky pro MDT nelze pacienta zařadit (OBC-1.1).'})
    sr_id = data.get('service_request_id') or prefill['service_request_id']
    with transaction.atomic():
        case = MdtCase.objects.select_for_update().filter(service_request_fhir_id=sr_id).first()
        created = case is None
        if created:
            case = MdtCase.objects.create(session=session, patient_fhir_id=pid, service_request_fhir_id=sr_id,
                                          question=question.get('value') or '', created_by=request.user,
                                          order=_next_order(session))
            writeback.set_mdt_date(pid, sr_id, timezone.localtime(session.date))
        else:
            _require_case_edit(request, case)
        written = _apply_case_input(request, case, {**data, 'session': session.pk},
                                    warnings={w['id']: w for w in prefill['warnings']})
        if case.status in ('nominated', 'returned'):
            case.status = 'ready'
            case.save(update_fields=['status', 'updated_at'])
    return Response({**_case(case), 'fhir_written': written}, status=201 if created else 200)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def case_brief(request, cid):
    """GET: poslední podklad (Brief §8.2). POST `{config_id | config}` (předseda, zadávající nebo přizvaný lékař): spustí generování → `{job_id}`."""
    case = get_object_or_404(MdtCase.objects.select_related('session__config'), pk=cid)
    if request.method == 'GET':
        brief = case.briefs.first()
        if brief is None:
            return Response({'detail': 'Podklad ještě nebyl vygenerován.'}, status=404)
        return Response({**brief.content, 'brief_id': brief.pk, 'created_at': brief.created_at})
    _require_case_edit(request, case)
    job = GenerationJob.objects.create(case=case, kind='brief', params={'config': _config(request.data, case)},
                                       created_by=request.user)
    jobs.start(job)
    return Response({'job_id': job.pk}, status=202)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def case_patient_summary(request, cid):
    """Shrnutí pro pacienta (BON-4). GET: uložené shrnutí. POST (předseda, zadávající nebo přizvaný lékař): job z potvrzeného závěru → 202 `{job_id}`."""
    case = get_object_or_404(MdtCase, pk=cid)
    decision = Decision.objects.filter(case=case).first()
    if request.method == 'GET':
        summary = (decision.content if decision else {}).get('patient_summary')
        return Response(summary) if summary else Response({'detail': 'Shrnutí ještě není.'}, status=404)
    _require_case_edit(request, case)
    if not decision or decision.status != 'confirmed':
        return Response({'detail': 'Shrnutí pro pacienta vzniká až z potvrzeného závěru.'}, status=409)
    job = GenerationJob.objects.create(case=case, kind='patient_summary', params={}, created_by=request.user)
    jobs.start(job)
    return Response({'job_id': job.pk}, status=202)


def _next_import_id(pid: str) -> str:
    from services.fhir import client as fhir
    numbers = [int(m[1]) for d in fhir.search('DocumentReference', patient=pid)
               if (m := re.match(rf'^{re.escape(pid)}-imp(\d+)$', d['id']))]
    return f'{pid}-imp{max(numbers, default=0) + 1:02d}'


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def patient_import(request, pid):
    """BON-7: vložený text (`{text}`) nebo multipart `pdf` → návrh hodnot s citací odstavce. Nic se nezapisuje."""
    from services.ai import report_import
    from services.ai.brief import _llm_call_log
    from services.ai_service import provider_for_patient

    _require(request, roles.ADMIN, roles.DOCTOR)
    provider = provider_for_patient(_patient_resources(pid))      # D-021
    pdf = request.FILES.get('pdf')
    if pdf:
        if pdf.size > AUDIO_MAX_BYTES:
            raise ValidationError({'pdf': 'PDF je větší než 20 MB.'})
        text = report_import.pdf_text(pdf.read(), provider, _llm_call_log)
    else:
        text = str(request.data.get('text', ''))
    if not text.strip():
        raise ValidationError({'text': 'Vlož text zprávy nebo nahraj PDF.'})
    try:
        return Response(report_import.propose(pid, _next_import_id(pid), text, provider, _llm_call_log))
    except ValueError as e:
        raise ValidationError({'text': str(e)}) from None


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def patient_import_confirm(request, pid):
    """BON-7: potvrzení lékařem → server návrh znovu ověří a zapíše jednou transakcí (+ Provenance)."""
    from services.ai import report_import
    from services.fhir import client as fhir

    _require(request, roles.ADMIN, roles.DOCTOR)
    proposal = request.data
    if not isinstance(proposal, dict) or proposal.get('patient_id') != pid:
        raise ValidationError({'patient_id': 'Návrh nepatří tomuto pacientovi.'})
    try:
        resources = report_import.confirm(proposal, user_name=request.user.get_full_name() or request.user.username)
    except (KeyError, ValueError) as e:
        raise ValidationError({'values': str(e)}) from None
    fhir.transaction({'resourceType': 'Bundle', 'type': 'transaction', 'entry': [
        {'resource': r, 'request': {'method': 'PUT', 'url': f"{r['resourceType']}/{r['id']}"}} for r in resources]})
    writeback._reindex_vectors(pid)
    return Response({'fhir_written': [f"{r['resourceType']}/{r['id']}" for r in resources]}, status=201)


AUDIO_MAX_BYTES = 20 * 1024 * 1024          # inline limit Gemini (ARCH §5.6)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def case_scribe(request, cid):
    """AI zapisovatel (BON-3): multipart `audio` nebo JSON `{transcript}` / `{segments}` → job → draft závěru (202 `{job_id}`)."""
    case = get_object_or_404(MdtCase, pk=cid)
    _require_case_edit(request, case)
    if Decision.objects.filter(case=case, status='confirmed').exists():
        return Response({'detail': 'Závěr je potvrzený, zapisovatel ho nemůže přepsat.'}, status=409)
    audio = request.FILES.get('audio')
    if audio:
        if audio.size > AUDIO_MAX_BYTES:
            raise ValidationError({'audio': 'Nahrávka je větší než 20 MB.'})
        # ponytail: audio jako base64 v params jobu (≤ 20 MB); větší soubory až přes úložiště
        params = {'audio_b64': base64.b64encode(audio.read()).decode(), 'mime_type': audio.content_type or 'audio/mp4'}
    elif isinstance(request.data.get('segments'), list) and request.data['segments']:
        params = {'segments': [{'speaker': str(s.get('speaker', '')), 'start': str(s.get('start', '')),
                                'text': str(s.get('text', ''))} for s in request.data['segments'] if isinstance(s, dict)]}
    elif str(request.data.get('transcript', '')).strip():
        params = {'transcript': str(request.data['transcript'])}
    else:
        raise ValidationError({'audio': 'Pošli nahrávku (`audio`), nebo přepis (`transcript` / `segments`).'})
    job = GenerationJob.objects.create(case=case, kind='scribe', params=params, created_by=request.user)
    jobs.start(job)
    return Response({'job_id': job.pk}, status=202)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def config_list(request):
    """Presety konfigurace podkladu (FR-R1). Zakládá jen předseda."""
    if request.method == 'POST':
        _require(request, roles.ADMIN)
        s = BriefConfigSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return Response(BriefConfigSerializer(s.save(owner=request.user)).data, status=201)
    # presety v pořadí založení: obecné, pak šablony projektoru (T-318); vlastní konfigurace za nimi
    return Response(BriefConfigSerializer(BriefConfig.objects.order_by('-is_preset', 'pk'), many=True).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def config_detail(request, cfg_id):
    obj = get_object_or_404(BriefConfig, pk=cfg_id)
    if request.method == 'PUT':
        _require(request, roles.ADMIN)
        s = BriefConfigSerializer(obj, data=request.data)
        s.is_valid(raise_exception=True)
        obj = s.save()
    return Response(BriefConfigSerializer(obj).data)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def case_decision(request, cid):
    """Draft závěru (Decision §8.4). PUT (předseda, zadávající nebo přizvaný lékař, T-326) validuje schéma; potvrzený závěr nejde měnit."""
    case = get_object_or_404(MdtCase, pk=cid)
    decision = Decision.objects.filter(case=case).first()
    if request.method == 'GET':
        if decision is None:
            return Response({'detail': 'Závěr ještě není.'}, status=404)
        return Response(decision.content)
    _require_case_edit(request, case)
    if decision and decision.status == 'confirmed':
        return Response({'detail': 'Závěr je potvrzený a zapsaný v IRIS, nelze ho měnit.'}, status=409)
    try:
        content = DecisionSchema.model_validate(
            {**request.data, 'case_id': str(case.pk), 'status': 'draft', 'confirmed_by': None,
             'confirmed_at': None, 'fhir_ids': None}).model_dump(mode='json')
    except SchemaError as e:
        return Response({'detail': 'Neplatný závěr (ARCH §8.4).', 'errors': e.errors(include_url=False)}, status=400)
    decision, _ = Decision.objects.update_or_create(case=case, defaults={'content': content})
    return Response(decision.content)


@extend_schema(request=None, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def case_decision_confirm(request, cid):
    """Potvrzení předsedou (FR-C3): jeden transaction Bundle do IRIS (ARCH §4.3), vrátí závěr s `fhir_ids`."""
    _require(request, roles.ADMIN)
    case = get_object_or_404(MdtCase.objects.select_related('session'), pk=cid)
    with transaction.atomic():
        decision = get_object_or_404(Decision.objects.select_for_update(), case=case)
        if decision.status == 'confirmed':
            return Response({'detail': 'Závěr už je potvrzený.', 'fhir_ids': decision.fhir_ids}, status=409)
        deviation = writeback.guideline_deviation(decision.content['sections'])
        if deviation:                                   # zadání B2: odchylka od guidelines chce krátké zdůvodnění
            return Response({'detail': deviation, 'field': 'guideline_compliance'}, status=400)
        brief = case.briefs.first()
        red_flags = {f['id']: f for f in (brief.content.get('red_flags', []) if brief else [])}
        now = timezone.localtime()
        confirmed_by = {'user_id': str(request.user.pk), 'name': request.user.get_full_name() or request.user.username}
        try:
            ids = writeback.confirm_decision(
                decision.content, patient_id=case.patient_fhir_id, service_request_id=case.service_request_fhir_id,
                mdt_date=timezone.localtime(case.session.date), confirmed_by=confirmed_by, red_flags=red_flags, now=now)
        except (FhirError, LookupError) as e:
            return Response({'detail': f'IRIS zápis odmítl: {e}', 'outcome': getattr(e, 'outcome', None)}, status=502)
        decision.content = {**decision.content, 'status': 'confirmed', 'confirmed_by': confirmed_by,
                            'confirmed_at': now.isoformat(), 'fhir_ids': ids}
        decision.status, decision.confirmed_by, decision.confirmed_at, decision.fhir_ids = 'confirmed', request.user, now, ids
        decision.save()
        case.status = 'confirmed'
        case.save(update_fields=['status', 'updated_at'])
    return Response(decision.content)


def _attachment(content, content_type: str, filename: str) -> HttpResponse:
    response = HttpResponse(content, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@extend_schema(responses={(200, 'application/fhir+json'): OpenApiTypes.OBJECT}, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_export_fhir(request, cid):
    """FHIR document Bundle potvrzeného záznamu z IRIS (FR-C4)."""
    decision = get_object_or_404(Decision, case_id=cid)
    if decision.status != 'confirmed':
        return Response({'detail': 'FHIR export je až po potvrzení závěru.'}, status=409)
    bundle = export.document_bundle(decision.fhir_ids, timezone.localtime())
    return _attachment(json.dumps(bundle, ensure_ascii=False, indent=1), 'application/fhir+json',
                       f"{decision.fhir_ids['composition']}.fhir.json")


@extend_schema(responses={(200, 'application/pdf'): OpenApiTypes.BINARY}, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_export_pdf(request, cid):
    """PDF závěru; potvrzený závěr se poprvé uloží i jako `DocumentReference/Pxx-mdtNN-pdf` do IRIS."""
    decision = get_object_or_404(Decision.objects.select_related('case__session'), case_id=cid)
    case = decision.case
    patient = next((p for p in patients.list_patients() if p['id'] == case.patient_fhir_id), None)
    pdf = export.decision_pdf(decision.content, title=case.session.title,
                              mdt_date=timezone.localtime(case.session.date), patient=patient)
    if decision.status == 'confirmed' and not decision.fhir_ids.get('document_reference_pdf'):
        rid = export.store_pdf(case.patient_fhir_id, decision.fhir_ids['composition'], pdf, timezone.localtime())
        decision.fhir_ids = {**decision.fhir_ids, 'document_reference_pdf': rid}
        decision.content = {**decision.content, 'fhir_ids': decision.fhir_ids}
        decision.save(update_fields=['fhir_ids', 'content', 'updated_at'])
    name = decision.fhir_ids.get('composition') or f'{case.patient_fhir_id}-navrh'
    return _attachment(pdf, 'application/pdf', f'{name}.pdf')


def _with_case(items: list[dict]) -> list[dict]:
    case_by_record = {d.fhir_ids.get('composition'): d.case_id for d in Decision.objects.filter(status='confirmed')}
    return [{**i, 'case_id': case_by_record.get(i['mdt_record'])} for i in items]


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def task_list(request):
    """Úkoly po zasedání z IRIS (FR-P3): `?status=requested|in-progress|completed&patient=P03`.
    `?mine=1` jen úkoly přiřazené přihlášenému (jeho lékař v IRIS, T-328), `?drafts=1` přidá úkoly z dosud
    nepotvrzených závěrů (`draft: true`, stav jde měnit až po potvrzení)."""
    status = request.query_params.get('status') or None
    if status and status not in tasks.STATUSES:
        raise ValidationError({'status': f'Jen {", ".join(tasks.STATUSES)}.'})
    patient = request.query_params.get('patient') or None
    owner = None
    if request.query_params.get('mine') in ('1', 'true'):
        owner = roles.practitioner_id(request.user)
        if owner is None:
            return Response([])
    items = _with_case(tasks.list_tasks(status, patient, owner))
    if request.query_params.get('drafts') in ('1', 'true'):
        items += _draft_tasks(status, patient, owner)
    return Response(items)


def _draft_tasks(status: str | None, patient: str | None, owner: str | None) -> list[dict]:
    """Úkoly z návrhů závěru (ještě nejsou v IRIS): lékař vidí, co mu komise přiděluje, ještě před potvrzením."""
    out = []
    for d in Decision.objects.filter(status='draft').select_related('case'):
        if patient and d.case.patient_fhir_id != patient:
            continue
        for t in d.content.get('tasks') or []:
            if (owner and t.get('owner') != owner) or (status and t.get('status') != status):
                continue
            out.append({'id': f"draft-{d.case_id}-{t['id']}", 'patient_id': d.case.patient_fhir_id, 'mdt_record': None,
                        'case_id': d.case_id, 'description': t.get('description', ''),
                        'owner': {'id': t.get('owner') if str(t.get('owner', '')).startswith('LEK-') else None,
                                  'name': t.get('owner_name') or t.get('owner', '')},
                        'due_date': t.get('due_date') or None, 'status': t.get('status', 'requested'),
                        'authored_on': None, 're_mdt': None, 'draft': True})
    return out


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def task_detail(request, tid):
    """Změna stavu úkolu `{status}` → `Task.status` v IRIS. Smí předseda, lékař a ten, komu je úkol přiřazený
    (T-328: i prohlížející člen komise si svůj úkol odškrtne)."""
    if roles.role(request.user) not in (roles.ADMIN, roles.DOCTOR):
        mine = roles.practitioner_id(request.user)
        if not mine or not any(t['id'] == tid for t in tasks.list_tasks(owner=mine)):
            raise PermissionDenied('Stav úkolu mění předseda, lékař, nebo ten, komu je úkol přiřazený.')
    try:
        item = tasks.set_status(tid, request.data.get('status'))
    except ValueError:
        raise ValidationError({'status': f'Jen {", ".join(tasks.STATUSES)} a ID úkolu Pxx-mdtNN-taskNN.'})
    except FhirError as e:
        if e.status == 404:
            return Response({'detail': 'Úkol v IRIS není.'}, status=404)
        raise
    return Response(_with_case([item])[0])
