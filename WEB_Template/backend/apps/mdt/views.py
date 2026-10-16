"""API MDT (ARCH §6.3). Oprávnění podle rolí (D-014, POZADAVKY_LEKARE §1)."""
import json

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from pydantic import ValidationError as SchemaError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.copilot import jobs
from apps.copilot.models import GenerationJob
from apps.copilot.schemas import Decision as DecisionSchema
from services import patients
from services.fhir import export, writeback
from services.fhir.client import FhirError

from . import config as cfg
from . import roles
from .config import DEFAULT_CONFIG, BriefConfigSerializer
from .models import BriefConfig, Decision, MdtCase, MdtSession


# ── oprávnění ────────────────────────────────────────────────────────────────
def _require(request, *allowed: str) -> None:
    if roles.role(request.user) not in allowed:
        raise PermissionDenied('Na tuto akci nemáte oprávnění (role MDT).')


def _require_case_edit(request, case: MdtCase) -> None:
    """Předseda jakýkoli případ, zadávající lékař jen svého pacienta."""
    r = roles.role(request.user)
    if not (r == roles.ADMIN or (r == roles.DOCTOR and case.created_by_id == request.user.pk)):
        raise PermissionDenied('Případ smí měnit jen zadávající lékař nebo předseda.')


# ── serializace ──────────────────────────────────────────────────────────────
def _user(u) -> dict | None:
    return u and {'user_id': u.pk, 'name': u.get_full_name() or u.username}


def _session(s: MdtSession) -> dict:
    return {'id': s.pk, 'date': timezone.localtime(s.date).isoformat(), 'title': s.title, 'status': s.status,
            'chair': _user(s.chair), 'config_id': s.config_id}


def _case(c: MdtCase, patient: dict | None = None) -> dict:
    return {'id': c.pk, 'session': c.session_id, 'order': c.order, 'patient_id': c.patient_fhir_id,
            'service_request_id': c.service_request_fhir_id, 'question': c.question, 'status': c.status,
            'ecog': c.ecog, 'intent': c.intent, 'imaging_recent_checked': c.imaging_recent_checked,
            'skipped_fields': c.skipped_fields, 'acknowledged_warnings': c.acknowledged_warnings,
            'created_by': _user(c.created_by), 'patient': patient}


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
    u = request.user
    return Response({'user_id': u.pk, 'username': u.username, 'name': u.get_full_name() or u.username,
                     'role': roles.role(u), 'specialty': roles.specialty(u)})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def session_list(request):
    """GET: boardy s pacienty v pořadí agendy. POST (jen předseda): `{date, title, config_id?}`."""
    if request.method == 'POST':
        _require(request, roles.ADMIN)
        if not request.data.get('title'):
            raise ValidationError({'title': 'Povinné (zaměření komise).'})
        s = MdtSession.objects.create(date=_datetime(request.data.get('date')), title=request.data['title'],
                                      chair=request.user, config_id=request.data.get('config_id'))
        return Response(_session(s), status=201)
    sessions = MdtSession.objects.select_related('chair').prefetch_related('cases')
    return Response([{**_session(s), 'patients': [c.patient_fhir_id for c in s.cases.all()]} for s in sessions])


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
    cases = list(s.cases.select_related('created_by'))
    by_id = {p['id']: p for p in patients.list_patients()} if cases else {}
    return Response({**_session(s), 'cases': [_case(c, by_id.get(c.patient_fhir_id)) for c in cases]})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def case_detail(request, cid):
    """Přesun do jiného boardu (zapíše termín do `Task` v IRIS), ECOG, záměr C/P, checkbox snímku,
    přeskočené údaje a `acknowledge: [warning_id]` (odkliknutí se jen přidává, D-019)."""
    case = get_object_or_404(MdtCase.objects.select_related('session', 'created_by'), pk=cid)
    _require_case_edit(request, case)
    data = request.data
    if 'ecog' in data and data['ecog'] is not None and data['ecog'] not in range(5):
        raise ValidationError({'ecog': 'ECOG 0–4 nebo null.'})
    if 'intent' in data and data['intent'] not in ('C', 'P', None):
        raise ValidationError({'intent': 'C, P nebo null.'})
    with transaction.atomic():
        if 'session' in data and data['session'] != case.session_id:
            target = get_object_or_404(MdtSession, pk=data['session'])
            writeback.set_mdt_date(case.patient_fhir_id, case.service_request_fhir_id, timezone.localtime(target.date))
            case.session = target
        for field in ('ecog', 'intent', 'imaging_recent_checked', 'skipped_fields'):
            if field in data:
                setattr(case, field, data[field])
        known = {w['id'] for w in case.acknowledged_warnings}
        now = timezone.now().isoformat()
        case.acknowledged_warnings += [{'id': w, 'by': request.user.pk, 'at': now}
                                       for w in data.get('acknowledge', []) if w not in known]
        case.save()
    return Response(_case(case))


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def case_brief(request, cid):
    """GET: poslední podklad (Brief §8.2). POST `{config_id | config}` (předseda, lékař): spustí generování → `{job_id}`."""
    case = get_object_or_404(MdtCase.objects.select_related('session__config'), pk=cid)
    if request.method == 'GET':
        brief = case.briefs.first()
        if brief is None:
            return Response({'detail': 'Podklad ještě nebyl vygenerován.'}, status=404)
        return Response({**brief.content, 'brief_id': brief.pk, 'created_at': brief.created_at})
    _require(request, roles.ADMIN, roles.DOCTOR)
    job = GenerationJob.objects.create(case=case, kind='brief', params={'config': _config(request.data, case)},
                                       created_by=request.user)
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
    return Response(BriefConfigSerializer(BriefConfig.objects.order_by('-is_preset', 'name'), many=True).data)


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
    """Draft závěru (Decision §8.4). PUT (předseda, lékař) validuje schéma; potvrzený závěr nejde měnit."""
    case = get_object_or_404(MdtCase, pk=cid)
    decision = Decision.objects.filter(case=case).first()
    if request.method == 'GET':
        if decision is None:
            return Response({'detail': 'Závěr ještě není.'}, status=404)
        return Response(decision.content)
    _require(request, roles.ADMIN, roles.DOCTOR)
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
