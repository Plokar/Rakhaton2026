"""Požadavky a normy lékaře (T-363–T-365, D-028, docs/UCTY_A_PVW.md §3, ARCH §6.3, §8.6).

Moje nastavení (mění jen lékař sám):
- `GET /api/mdt/my-rules/`: moje požadavky po oblastech a normy;
- `PUT|DELETE /api/mdt/my-rules/requirements/{area}/`: `{fields: [klíč], note?}`;
- `GET|POST /api/mdt/my-rules/norms/`, `PUT|DELETE /api/mdt/my-rules/norms/{id}/`: `{area, field, op, value, unit?,
  procedure?, note?, source?}`;
- `GET /api/mdt/norm-fields/`: číselné údaje pro editor norem;
- `GET /api/mdt/users/{uid}/rules/`: správce vidí požadavky a normy lékaře (jen čtení).

U pacienta (pozvaní lékaři zasedání bez zadávajícího lékaře):
- `GET /api/mdt/sessions/{sid}/doctor-rules/?patient=P03&skipped=…`: při zařazení (případ ještě není);
- `GET /api/mdt/cases/{cid}/doctor-rules/`: u případu, s rozhodnutím zadávajícího lékaře;
- `POST /api/mdt/cases/{cid}/doctor-rules/decision/`: `{user_id, decision: needed | not_needed, note?, prep_tasks?}`.
"""
from __future__ import annotations

import re

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services import tasks
from services.fhir.client import FhirError
from services.rules import doctor_rules as dr
from services.rules import fact_templates as ft
from services.rules.fact_categories import AREAS

from . import roles, scope
from .models import DoctorNorm, DoctorRequirement, MdtCase, MdtSession

MAX_FIELDS = 60
MAX_NORMS = 40
DECISIONS = ('needed', 'not_needed')
EVIDENCE_ID = re.compile(r'^[A-Z][A-Z0-9]*-[A-Za-z0-9.\-/#]+$')     # KRC-2.4, EXT-MK-31.3-2, RKT-03/V3


def _areas() -> list[dict]:
    return [{'id': a, 'label': label} for a, label in dr.AREA_LABELS.items()]


def requirement_keys(area: str) -> dict[str, str]:
    """Klíče, které jde vyžadovat: údaje katalogu oblasti bez upozornění (`*` = všechny oblasti)."""
    # ECOG je na PVW v hlavičce (D-018), mimo katalog šablony; vyžadovat ho jde
    out: dict[str, str] = {'ecog.physician': 'ECOG (lékař)', 'ecog.patient': 'ECOG podle pacienta (PROMs)'}
    for a in (AREAS if area == dr.AREA_ANY else [area]):
        out.update({f['key']: f['label'] for f in ft.catalog(a)['facts'] if f['category'] != 'alerts'})
    return out


def _requirement(r: DoctorRequirement) -> dict:
    return {'area': r.area, 'area_label': dr.AREA_LABELS[r.area], 'fields': r.fields, 'note': r.note,
            'updated_at': r.updated_at.isoformat()}


def _norm(n: DoctorNorm) -> dict:
    return {'id': n.pk, 'area': n.area, 'area_label': dr.AREA_LABELS[n.area], 'field': n.field,
            'label': dr.NORM_LABELS.get(n.field, n.field), 'op': n.op, 'value': n.value, 'unit': n.unit,
            'procedure': n.procedure, 'note': n.note, 'source': n.source, 'text': dr.norm_text(_norm_dict(n))}


def _norm_dict(n: DoctorNorm) -> dict:
    return {'field': n.field, 'op': n.op, 'value': n.value, 'unit': n.unit}


def rules_of(user) -> dict:
    return {'requirements': [_requirement(r) for r in DoctorRequirement.objects.filter(user=user)],
            'norms': [_norm(n) for n in DoctorNorm.objects.filter(user=user)],
            'areas': _areas(), 'ops': [{'id': k, 'label': v} for k, v in dr.OPS.items()]}


# ── moje nastavení ───────────────────────────────────────────────────────────
@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_rules(request):
    return Response(rules_of(request.user))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def norm_fields(request):
    return Response(dr.norm_fields())


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def my_requirement(request, area):
    if area not in dr.AREA_LABELS:
        raise ValidationError({'area': f'Jen {", ".join(dr.AREA_LABELS)}.'})
    if request.method == 'DELETE':
        DoctorRequirement.objects.filter(user=request.user, area=area).delete()
        return Response(status=204)
    fields = request.data.get('fields')
    allowed = requirement_keys(area)
    if not (isinstance(fields, list) and len(fields) <= MAX_FIELDS and len(set(fields)) == len(fields)
            and all(isinstance(f, str) and f in allowed for f in fields)):
        raise ValidationError({'fields': f'Seznam nejvýš {MAX_FIELDS} údajů z katalogu oblasti, bez opakování.'})
    note = str(request.data.get('note') or '').strip()
    if len(note) > 500:
        raise ValidationError({'note': 'Nejvýš 500 znaků.'})
    if not fields and not note:
        DoctorRequirement.objects.filter(user=request.user, area=area).delete()
        return Response(status=204)
    r, _ = DoctorRequirement.objects.update_or_create(user=request.user, area=area,
                                                      defaults={'fields': fields, 'note': note})
    return Response(_requirement(r))


def _clean_norm(data) -> dict:
    area = data.get('area') or dr.AREA_ANY
    if area not in dr.AREA_LABELS:
        raise ValidationError({'area': f'Jen {", ".join(dr.AREA_LABELS)}.'})
    if data.get('field') not in dr.NORM_KEYS:
        raise ValidationError({'field': 'Vyberte číselný údaj z nabídky.'})
    if data.get('op') not in dr.OPS:
        raise ValidationError({'op': f'Jen {", ".join(dr.OPS)}.'})
    try:
        value = float(str(data.get('value')).replace(',', '.'))
    except (TypeError, ValueError):
        raise ValidationError({'value': 'Číslo.'}) from None
    out = {'area': area, 'field': data['field'], 'op': data['op'], 'value': value}
    for key, limit in (('unit', 20), ('procedure', 120), ('note', 300), ('source', 60)):
        text = str(data.get(key) or '').strip()
        if len(text) > limit:
            raise ValidationError({key: f'Nejvýš {limit} znaků.'})
        out[key] = text
    if out['source'] and not EVIDENCE_ID.match(out['source']):
        raise ValidationError({'source': 'Evidence ID guidelines (např. KRC-2.1, EXT-MK-31.3-2).'})
    return out


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def my_norms(request):
    if request.method == 'GET':
        return Response([_norm(n) for n in DoctorNorm.objects.filter(user=request.user)])
    if DoctorNorm.objects.filter(user=request.user).count() >= MAX_NORMS:
        raise ValidationError({'detail': f'Nejvýš {MAX_NORMS} norem.'})
    n = DoctorNorm.objects.create(user=request.user, **_clean_norm(request.data))
    return Response(_norm(n), status=201)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def my_norm_detail(request, norm_id):
    n = get_object_or_404(DoctorNorm, pk=norm_id, user=request.user)     # cizí normu nikdo jiný nemění
    if request.method == 'DELETE':
        n.delete()
        return Response(status=204)
    for key, value in _clean_norm(request.data).items():
        setattr(n, key, value)
    n.save()
    return Response(_norm(n))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_rules(request, uid):
    """Správce vidí požadavky a normy lékaře; měnit je nemůže (D-028)."""
    if not roles.is_manager(request.user):
        raise PermissionDenied('Požadavky a normy lékařů vidí správce MDT.')
    return Response(rules_of(get_object_or_404(get_user_model(), pk=uid)))


# ── u pacienta ───────────────────────────────────────────────────────────────
def _doctor(u) -> dict:
    profile = getattr(u, 'mdt_profile', None)
    return {'user_id': u.pk, 'name': roles.display_name(u), 'specialty': roles.specialty(u),
            'organization': profile.organization if profile else '',
            'is_external': profile.is_external if profile else False}


def latest_decisions(decisions: list[dict]) -> dict[int, dict]:
    return {d['user_id']: d for d in decisions}            # poslední záznam pro lékaře platí


def evaluate(session: MdtSession, resources: list[dict], skipped=(), exclude_user_id: int | None = None,
             decisions: list[dict] | None = None, extra_users=()) -> dict:
    """`DoctorRules` (§8.6): pro každého pozvaného lékaře (bez zadávajícího) jeho požadavky a normy u pacienta."""
    area = dr.patient_area(resources)
    facts = dr.patient_facts(resources, skipped)
    users = {u.pk: u for u in scope.invited_users(session)}
    users.update({u.pk: u for u in extra_users if u.is_active})
    users.pop(exclude_user_id, None)
    areas = [area, dr.AREA_ANY]
    reqs: dict[int, list[DoctorRequirement]] = {}
    for r in DoctorRequirement.objects.filter(user_id__in=users, area__in=areas):
        reqs.setdefault(r.user_id, []).append(r)
    norms: dict[int, list[DoctorNorm]] = {}
    for n in DoctorNorm.objects.filter(user_id__in=users, area__in=areas):
        norms.setdefault(n.user_id, []).append(n)
    chosen = latest_decisions(decisions or [])
    labels = requirement_keys(area)
    doctors = []
    for uid, user in users.items():
        if uid not in reqs and uid not in norms:
            continue
        requirement = None
        if uid in reqs:
            keys = [k for r in sorted(reqs[uid], key=lambda r: r.area != area) for k in r.fields]
            items = dr.requirement_items(keys, facts, {**requirement_keys(dr.AREA_ANY), **labels})
            requirement = {'note': ' · '.join(r.note for r in reqs[uid] if r.note), 'items': items,
                           'missing': [i['key'] for i in items if i['status'] != 'present']}
        doctors.append({
            **_doctor(user), 'requirement': requirement, 'decision': chosen.get(uid),
            'norms': [{**_norm(n), 'result': dr.evaluate_norm(_norm_dict(n), facts)} for n in norms.get(uid, [])],
        })
    doctors.sort(key=lambda d: d['name'])
    return {'area': area, 'area_label': dr.AREA_LABELS[area], 'doctors': doctors}


def _resources(pid: str) -> list[dict]:
    from .views import _patient_resources
    return _patient_resources(pid)


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_doctor_rules(request, sid):
    """Při zařazení: požadavky a normy pozvaných lékařů zasedání u pacienta `?patient=` (bez přihlášeného)."""
    session = get_object_or_404(MdtSession, pk=sid)
    pid = request.query_params.get('patient', '')
    if not re.fullmatch(r'P\d{2,3}', pid):
        raise ValidationError({'patient': 'ID pacienta (P03).'})
    if not scope.patient_visible(request.user, pid):
        raise PermissionDenied('Pacient není na vašich zasedáních.')
    skipped = [s for s in request.query_params.get('skipped', '').split(',') if s]
    return Response(evaluate(session, _resources(pid), skipped, exclude_user_id=request.user.pk))


def _case_rules(case: MdtCase) -> dict:
    return evaluate(case.session, _resources(case.patient_fhir_id), case.skipped_fields,
                    exclude_user_id=case.created_by_id, decisions=case.requirement_decisions,
                    extra_users=case.collaborators.all())


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def case_doctor_rules(request, cid):
    """U případu (kontrola, detail, PVW): požadavky, rozhodnutí zadávajícího lékaře a normy s výsledkem."""
    case = get_object_or_404(MdtCase.objects.select_related('session', 'session__committee'), pk=cid)
    return Response(_case_rules(case))


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def case_doctor_rules_decision(request, cid):
    """Zadávající lékař rozhodne, zda pozvaného lékaře u pacienta potřebuje. Záznam se jen přidává (D-019).
    `prep_tasks: true` u `needed` založí úkoly na chybějící vyžadované údaje (T-350)."""
    from .views import _require_case_edit
    case = get_object_or_404(MdtCase.objects.select_related('session'), pk=cid)
    _require_case_edit(request, case)
    data = request.data
    if data.get('decision') not in DECISIONS:
        raise ValidationError({'decision': 'needed nebo not_needed.'})
    note = str(data.get('note') or '').strip()
    if len(note) > 300:
        raise ValidationError({'note': 'Nejvýš 300 znaků.'})
    rules = _case_rules(case)
    doctor = next((d for d in rules['doctors'] if d['user_id'] == data.get('user_id')), None)
    if doctor is None or doctor['requirement'] is None:
        raise ValidationError({'user_id': 'Lékař není pozvaný nebo u pacienta nic nevyžaduje.'})
    written = []
    if data.get('prep_tasks') and data['decision'] == 'needed':
        owner = roles.practitioner_id(case.created_by) if case.created_by else None
        if owner is None:
            raise ValidationError({'prep_tasks': 'Zadávající lékař nemá propojeného lékaře v IRIS.'})
        items = [f"{i['label']} (vyžaduje {doctor['name']})" for i in doctor['requirement']['items']
                 if i['status'] != 'present']
        try:
            written = tasks.create_prep_tasks(case.patient_fhir_id, case.service_request_fhir_id, owner, items,
                                              timezone.localtime(case.session.date))
        except FhirError as e:
            return Response({'detail': f'Úkoly se nepodařilo zapsat do IRIS ({e}).'}, status=502)
    case.requirement_decisions = [*case.requirement_decisions, {
        'user_id': doctor['user_id'], 'decision': data['decision'], 'note': note,
        'by': roles.display_name(request.user), 'at': timezone.now().isoformat()}]
    case.save(update_fields=['requirement_decisions', 'updated_at'])
    return Response({**_case_rules(case), 'fhir_written': written})
