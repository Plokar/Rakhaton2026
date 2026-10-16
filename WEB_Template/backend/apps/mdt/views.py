"""API MDT (ARCH §6.3)."""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.copilot import jobs
from apps.copilot.models import GenerationJob
from services import patients

from .models import BriefConfig, MdtCase, MdtSession

DEFAULT_CONFIG = {'name': 'Výchozí', 'sections': [], 'roles_present': [], 'detail_level': 'standard',
                  'language': 'cs', 'hide_unverified': False}


def _config(data, case: MdtCase) -> dict:
    """`{config_id}` → preset, `{config}` → konfigurace z UI, jinak výchozí boardu nebo DEFAULT_CONFIG."""
    if data.get('config_id') is not None:
        return get_object_or_404(BriefConfig, pk=data['config_id']).snapshot()
    if data.get('config') is not None:
        if not isinstance(data['config'], dict):
            raise ValidationError({'config': 'Očekáván objekt BriefConfig (ARCH §8.5).'})
        return {**DEFAULT_CONFIG, **data['config']}
    return case.session.config.snapshot() if case.session.config else dict(DEFAULT_CONFIG)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def case_brief(request, cid):
    """GET: poslední podklad (Brief §8.2). POST `{config_id | config}`: spustí generování, vrátí `{job_id}`."""
    case = get_object_or_404(MdtCase.objects.select_related('session__config'), pk=cid)
    if request.method == 'GET':
        brief = case.briefs.first()
        if brief is None:
            return Response({'detail': 'Podklad ještě nebyl vygenerován.'}, status=404)
        return Response({**brief.content, 'brief_id': brief.pk, 'created_at': brief.created_at})
    job = GenerationJob.objects.create(case=case, kind='brief', params={'config': _config(request.data, case)},
                                       created_by=request.user)
    jobs.start(job)
    return Response({'job_id': job.pk}, status=202)


def _session(s: MdtSession) -> dict:
    return {'id': s.pk, 'date': timezone.localtime(s.date).isoformat(), 'title': s.title, 'status': s.status,
            'chair': s.chair and {'user_id': s.chair_id, 'name': s.chair.get_full_name() or s.chair.username},
            'config_id': s.config_id}


def _case(c: MdtCase, patient: dict | None) -> dict:
    return {'id': c.pk, 'session': c.session_id, 'order': c.order, 'patient_id': c.patient_fhir_id,
            'service_request_id': c.service_request_fhir_id, 'question': c.question, 'status': c.status,
            'ecog': c.ecog, 'intent': c.intent, 'imaging_recent_checked': c.imaging_recent_checked,
            'skipped_fields': c.skipped_fields, 'acknowledged_warnings': c.acknowledged_warnings,
            'created_by': c.created_by and {'user_id': c.created_by_id,
                                            'name': c.created_by.get_full_name() or c.created_by.username},
            'patient': patient}


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_list(request):
    """Boardy (zasedání) s pacienty v pořadí agendy."""
    sessions = MdtSession.objects.select_related('chair').prefetch_related('cases')
    return Response([{**_session(s), 'patients': [c.patient_fhir_id for c in s.cases.all()]} for s in sessions])


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_detail(request, sid):
    """Board + agenda: případy s hlavičkou pacienta z IRIS (`PatientListItem`)."""
    s = get_object_or_404(MdtSession.objects.select_related('chair'), pk=sid)
    cases = list(s.cases.select_related('created_by'))
    by_id = {p['id']: p for p in patients.list_patients()} if cases else {}
    return Response({**_session(s), 'cases': [_case(c, by_id.get(c.patient_fhir_id)) for c in cases]})
