"""Shrnutí pro pacienta k tisku a bezpečný odkaz (T-384).

Lékař z potvrzeného závěru (shrnutí BON-4) vytvoří odkaz pro pacienta: platí 14 dní, jde zrušit, ukládá se jen
hash tokenu. Veřejná stránka ukáže jen věty shrnutí a datum zasedání: žádné jméno, RČ, ID pacienta ani citace.
"""
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import Decision, MdtCase, PatientShareLink
from .views import _require_case_edit

LINK_DAYS = 14


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _summary(case: MdtCase) -> dict | None:
    decision = Decision.objects.filter(case=case, status='confirmed').first()
    return (decision.content.get('patient_summary') if decision else None) or None


@extend_schema(request=None, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def summary_links(request, cid):
    """GET: platné odkazy (bez tokenu). POST: nový odkaz → `{url, expires_at}` (token jen teď). DELETE: zruší
    všechny. Smí předseda, zadávající nebo přizvaný lékař; shrnutí musí existovat (409)."""
    case = get_object_or_404(MdtCase.objects.select_related('session'), pk=cid)
    _require_case_edit(request, case)
    now = timezone.now()
    active = case.share_links.filter(revoked_at__isnull=True, expires_at__gt=now)
    if request.method == 'GET':
        return Response([{'id': link.pk, 'created_at': link.created_at.isoformat(), 'expires_at': link.expires_at.isoformat(),
                          'views': link.views} for link in active])
    if request.method == 'DELETE':
        active.update(revoked_at=now)
        return Response(status=204)
    if _summary(case) is None:
        return Response({'detail': 'Shrnutí pro pacienta zatím není (vzniká z potvrzeného závěru).'}, status=409)
    token = secrets.token_urlsafe(24)
    link = PatientShareLink.objects.create(token_hash=_hash(token), case=case, created_by=request.user,
                                           expires_at=now + timedelta(days=LINK_DAYS))
    base = (getattr(settings, 'MDT_FRONTEND_URL', '') or request.build_absolute_uri('/')).rstrip('/')
    return Response({'url': f'{base}/pacient/{token}', 'expires_at': link.expires_at.isoformat()}, status=201)


class ShareThrottle(AnonRateThrottle):
    rate = '30/hour'                                   # odkaz nejde hádat hrubou silou


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['public'])
@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([ShareThrottle])
def public_summary(request, token):
    """Veřejné čtení přes odkaz: `{title, mdt_date, items: [{text}], generated_at}`; neplatný, zrušený nebo
    prošlý odkaz 404 (bez rozlišení, proč)."""
    link = PatientShareLink.objects.filter(token_hash=_hash(token), revoked_at__isnull=True,
                                           expires_at__gt=timezone.now()).select_related('case__session').first()
    summary = _summary(link.case) if link else None
    if not summary:
        return Response({'detail': 'Odkaz neplatí. Požádejte lékaře o nový.'}, status=404)
    PatientShareLink.objects.filter(pk=link.pk).update(views=F('views') + 1)
    return Response({'title': 'Shrnutí z multidisciplinární onkologické komise',
                     'mdt_date': timezone.localtime(link.case.session.date).date().isoformat(),
                     'items': [{'text': item.get('text', '')} for item in summary.get('items') or []],
                     'generated_at': summary.get('generated_at'), 'expires_at': link.expires_at.isoformat()})
