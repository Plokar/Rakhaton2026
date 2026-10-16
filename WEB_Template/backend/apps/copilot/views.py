from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import GenerationJob


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['jobs'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def job_status(request, jid):
    """Stav jobu pro polling (FE à 1 s): `{status, progress, result_id, error}`."""
    job = get_object_or_404(GenerationJob, pk=jid)
    return Response({'id': job.pk, 'kind': job.kind, 'case_id': job.case_id, 'status': job.status,
                     'progress': job.progress, 'result_id': job.result_id, 'error': job.error or None})
