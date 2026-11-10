"""Záznam přístupů k pacientům (T-370, ARCH §6.2, §6.3, docs/PILOT.md §6).

`AccessLogMiddleware` zapíše po odpovědi jeden řádek `AccessLog` pro API nad konkrétním pacientem, případem
nebo exportem. Ukládá jen ID (Pxx, číslo případu), nikdy jméno, RČ, hledaný výraz ani tělo požadavku.
Opakované zobrazení stejného pacienta stejným uživatelem se zapíše nejvýš jednou za `VIEW_WINDOW` (polling
by jinak tabulku zahltil); export, zápis a dotaz na AI vždy. Chyba zápisu požadavek nikdy neshodí.

`GET /api/mdt/access-log/?patient=&user=&action=&from=&to=&page=` jen pro správce MDT (`mdt_manager`).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.core.cache import cache
from django.urls import Resolver404, resolve
from django.utils import timezone
from django.utils.dateparse import parse_date
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import roles
from .models import AccessLog, MdtCase

log = logging.getLogger(__name__)

VIEW_WINDOW = timedelta(minutes=5)
PAGE_SIZE = 50
EXPORTS = {'case-export-pdf', 'case-export-fhir', 'session-export-zip'}
AI = {'case-ask', 'case-brief', 'case-scribe', 'case-patient-summary', 'patient-chatbot', 'case-similar',
      'case-gp-report'}
PATIENT_ROUTES = {'patient-detail', 'patient-timeline', 'patient-observations', 'patient-intake', 'patient-import',
                  'patient-import-confirm', 'patient-chatbot'}


def _action(name: str, method: str) -> str:
    if name in EXPORTS:
        return 'export'
    if method in ('GET', 'HEAD', 'OPTIONS'):
        return 'view'
    return 'ai' if name in AI else 'write'


def _client_ip(request) -> str | None:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    ip = (forwarded.split(',')[0] if forwarded else request.META.get('REMOTE_ADDR', '')).strip()
    return ip or None


def _user(request):
    user = getattr(request, 'user', None)                 # DRF předá ověřeného uživatele i do HttpRequest
    if user is not None and user.is_authenticated:
        return user
    from .scope import _api_user                          # požadavek odmítnutý middlewarem před view (403)
    return _api_user(request)


def _targets(request, response, name: str, kwargs: dict) -> list[dict]:
    """Pacienti (a případ), kterých se požadavek týká; prázdný seznam = nelogovat."""
    if name.startswith('case-') and 'cid' in kwargs:
        case = MdtCase.objects.filter(pk=kwargs['cid']).only('pk', 'patient_fhir_id').first()
        return [{'patient_fhir_id': case.patient_fhir_id if case else '', 'case': case}]
    if name in PATIENT_ROUTES:
        return [{'patient_fhir_id': str(kwargs.get('pid', ''))[:64]}]
    if name == 'session-export-zip':
        return [{'session_id_ref': kwargs.get('sid')}]
    if name == 'evidence-source':                         # citace z dokumentace pacienta (P03-img03#2)
        from .scope import PATIENT_PREFIX
        m = PATIENT_PREFIX.match(request.GET.get('id', ''))
        return [{'patient_fhir_id': m[1]}] if m else []
    if name == 'patient-search' and response.status_code == 200:   # hledaný výraz (RČ, jméno) se neukládá
        found = getattr(response, 'data', None)
        if isinstance(found, list):
            return [{'patient_fhir_id': str(p.get('id', ''))[:64]} for p in found[:20] if isinstance(p, dict)]
    return []


def _fresh_view(user, patient_id: str) -> bool:
    """`True` = zobrazení zapsat (v okně `VIEW_WINDOW` ještě nebylo)."""
    key = f'access-log:{user.pk if user else "anon"}:{patient_id}'
    try:
        return cache.add(key, 1, int(VIEW_WINDOW.total_seconds()))
    except Exception:                                     # Redis dole: rozhodne DB
        since = timezone.now() - VIEW_WINDOW
        return not AccessLog.objects.filter(user=user, patient_fhir_id=patient_id, action='view',
                                            created_at__gte=since).exists()


def record(request, response) -> None:
    path = request.path_info
    if not path.startswith('/api/') or path.startswith('/api/auth/'):
        return
    try:
        match = resolve(path)
    except Resolver404:
        return
    name = match.url_name or ''
    targets = _targets(request, response, name, match.kwargs)
    if not targets:
        return
    user = _user(request)
    action = _action(name, request.method)
    rows = []
    for target in targets:
        if action == 'view' and not _fresh_view(user, target.get('patient_fhir_id') or path):
            continue
        rows.append(AccessLog(user=user, username=user.get_username() if user else '', action=action,
                              path=path[:300], method=request.method[:8], status_code=response.status_code,
                              ip=_client_ip(request), **target))
    if rows:
        AccessLog.objects.bulk_create(rows)


class AccessLogMiddleware:
    """Za autentizací, před `ExternalScopeMiddleware`: zapíše i požadavek, který odmítne (403)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            record(request, response)
        except Exception:
            log.exception('AccessLog: zápis selhal (%s %s)', request.method, request.path_info)
        return response


# ── přehled pro správce ──────────────────────────────────────────────────────
def _row(entry: AccessLog) -> dict:
    return {'id': entry.pk, 'created_at': entry.created_at, 'user_id': entry.user_id, 'username': entry.username,
            'user_name': (entry.user.get_full_name() or entry.user.first_name) if entry.user else '',
            'patient_id': entry.patient_fhir_id, 'case_id': entry.case_id, 'session_id': entry.session_id_ref,
            'action': entry.action, 'method': entry.method, 'path': entry.path, 'status': entry.status_code,
            'ip': entry.ip}


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def access_log_list(request):
    """Záznam přístupů, nejnovější nahoře, po 50: `{count, page, page_size, results: [...]}`. Jen správce MDT."""
    if not roles.is_manager(request.user):
        raise PermissionDenied('Záznam přístupů vidí jen správce MDT.')
    entries = AccessLog.objects.select_related('user')
    params = request.query_params
    if patient := params.get('patient', '').strip():
        entries = entries.filter(patient_fhir_id__iexact=patient)
    if (uid := params.get('user', '').strip()).isdigit():
        entries = entries.filter(user_id=int(uid))
    if (action := params.get('action', '')) in dict(AccessLog.ACTIONS):
        entries = entries.filter(action=action)
    if day := parse_date(params.get('from', '') or ''):
        entries = entries.filter(created_at__date__gte=day)
    if day := parse_date(params.get('to', '') or ''):
        entries = entries.filter(created_at__date__lte=day)
    page = max(1, int(params['page'])) if params.get('page', '').isdigit() else 1
    count = entries.count()
    chunk = entries[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]
    return Response({'count': count, 'page': page, 'page_size': PAGE_SIZE, 'results': [_row(e) for e in chunk]})
