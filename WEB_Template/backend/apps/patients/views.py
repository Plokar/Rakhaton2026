"""API pacientů z IRIS (T-103, ARCH §6.3). Jen pro přihlášené, data čte výhradně z IRIS."""
from django.http import Http404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services import patients
from services.fhir.client import FhirError


def _load(pid: str) -> list[dict]:
    if not patients.VALID_ID.match(pid):     # pid jde do URL FHIR serveru
        raise Http404
    try:
        rs = patients.load_patient(pid)
    except FhirError as e:
        if e.status == 404:
            raise Http404
        raise
    if not any(r['resourceType'] == 'Patient' for r in rs):
        raise Http404
    return rs


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['patients'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_list(request):
    return Response(patients.list_patients())


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['patients'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_detail(request, pid):
    return Response(patients.detail(pid, _load(pid)))


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['patients'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_timeline(request, pid):
    return Response(patients.timeline(_load(pid)))


@extend_schema(
    responses=OpenApiTypes.OBJECT, tags=['patients'],
    parameters=[OpenApiParameter('code', str, description='Kódy řad oddělené čárkou: LOINC (718-7), druh (lvef), proms:<linkId>')],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_observations(request, pid):
    codes = {c for c in request.query_params.get('code', '').split(',') if c} or None
    return Response(patients.observations(_load(pid), codes))
