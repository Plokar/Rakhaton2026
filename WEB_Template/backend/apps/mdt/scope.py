"""Kdo je pozvaný na zasedání a co vidí lékař z jiné nemocnice (T-362, D-027, docs/UCTY_A_PVW.md §2–3).

- Pozvaní na zasedání = stálí členové komise bez vyřazených + přizvaní jen na toto zasedání.
- Externí lékař vidí jen zasedání, kam je pozvaný, jejich pacienty (celý podklad) a případy, ke kterým je přizvaný
  ke spolupráci. `ExternalScopeMiddleware` mu ostatní API odmítne: povoleno je jen to, co je vyjmenované níže
  (deny by default), aby nová API nebyla omylem otevřená.
"""
from __future__ import annotations

import re

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.urls import Resolver404, resolve

from . import roles
from .models import MdtCase, MdtSession


# ── pozvaní ──────────────────────────────────────────────────────────────────
def invited_users(session: MdtSession) -> list:
    """Pozvaní lékaři zasedání: členové komise bez vyřazených + přizvaní (aktivní účty, podle jména)."""
    excluded = set(session.excluded.values_list('pk', flat=True))
    members = session.committee.members.all() if session.committee_id else get_user_model().objects.none()
    users = {u.pk: u for u in members if u.pk not in excluded}
    users.update({u.pk: u for u in session.invited.all()})
    return sorted((u for u in users.values() if u.is_active), key=lambda u: (u.last_name, u.first_name, u.username))


def visible_sessions(user):
    """Zasedání, která uživatel vidí. Interní lékař všechna, externí jen ta, kam je pozvaný nebo kde je přizvaný
    ke spolupráci u pacienta."""
    sessions = MdtSession.objects.all()
    if not roles.is_external(user):
        return sessions
    invited = (Q(committee__members=user) & ~Q(excluded=user)) | Q(invited=user) | Q(cases__collaborators=user)
    return sessions.filter(pk__in=MdtSession.objects.filter(invited).values('pk'))


def case_visible(user, case: MdtCase) -> bool:
    if not roles.is_external(user):
        return True
    return visible_sessions(user).filter(pk=case.session_id).exists()


def patient_visible(user, patient_id: str) -> bool:
    if not roles.is_external(user):
        return True
    return MdtCase.objects.filter(patient_fhir_id=patient_id, session__in=visible_sessions(user)).exists()


# ── externí lékař: povolená API ──────────────────────────────────────────────
ALWAYS = {
    'mdt-me', 'template-list', 'template-catalog', 'template-detail', 'practitioner-list', 'task-list', 'task-detail',
    'rule-catalog', 'review-list', 'session-list', 'my-rules', 'my-requirement', 'my-norms', 'my-norm-detail',
    'norm-fields', 'health-check', 'api-root', 'invitation-public', 'invitation-accept', 'committee-list',
    'my-live',                                        # filtruje viditelná zasedání sám
}
BY_SESSION = {'session-detail', 'session-invited', 'session-live', 'session-presence', 'session-messages', 'session-stream', 'session-chatbot', 'session-doctor-rules'}
BY_PATIENT = {'patient-intake', 'patient-chatbot', 'patient-detail', 'patient-timeline', 'patient-observations'}
CASE_DENIED = {'case-create', 'case-similar'}        # podobní pacienti = cizí pacienti
PATIENT_PREFIX = re.compile(r'^(P\d{2,3})-')


def external_allowed(user, request) -> bool:
    try:
        match = resolve(request.path_info)
    except Resolver404:
        return True                                   # 404 vrátí Django
    name, kwargs = match.url_name or '', match.kwargs
    if name in ALWAYS:
        return True
    if name in BY_SESSION:
        return visible_sessions(user).filter(pk=kwargs.get('sid')).exists()
    if name in BY_PATIENT:
        return patient_visible(user, kwargs.get('pid', ''))
    if name.startswith('case-') and name not in CASE_DENIED:
        case = MdtCase.objects.filter(pk=kwargs.get('cid')).first()
        return case is None or case_visible(user, case)
    if name == 'evidence-source':                     # citace pacienta jen u viditelného pacienta, guidelines vždy
        m = PATIENT_PREFIX.match(request.GET.get('id', ''))
        return not m or patient_visible(user, m[1])
    if name == 'job-status':
        from apps.copilot.models import GenerationJob
        job = GenerationJob.objects.filter(pk=kwargs.get('jid')).select_related('case').first()
        return job is None or case_visible(user, job.case)
    return False


def _api_user(request):
    """Uživatel z JWT (cookie nebo hlavička): middleware běží před autentizací DRF."""
    from apps.authentication.backends import CookieJWTAuthentication
    try:
        found = CookieJWTAuthentication().authenticate(request)
    except Exception:                                 # neplatný token odmítne až DRF
        return None
    return found[0] if found else None


class ExternalScopeMiddleware:
    """Lékař z jiné nemocnice (T-362) dostane na API mimo své komise 403."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path_info.startswith('/api/') and not request.path_info.startswith('/api/auth/'):
            user = _api_user(request)
            if user is not None and roles.is_external(user) and not external_allowed(user, request):
                return JsonResponse({'detail': 'Lékař z jiné nemocnice vidí jen komise, kam je pozvaný.'}, status=403)
        return self.get_response(request)
