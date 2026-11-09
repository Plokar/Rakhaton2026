"""Živé zasedání (T-357, ARCH §6.3): kde lékař má být, kde je a který pacient je právě na projektoru.

Lékař na zasedání sáhne po mobilu, když ho zajímá něco, co na projektoru není. Aplikace proto ví:

- **kde má být:** dnešní a probíhající zasedání, kde je předsedou, zadávajícím nebo přizvaným lékařem;
- **kde je:** aplikace živého zasedání se ohlašuje (`POST …/presence/`), přítomný = ohlášení za `PRESENCE_TTL`;
- **co je na slidu:** jednání komise u předsedy ukládá pacienta a slide projektoru (`PUT …/live/`) a server ho rozešle
  do streamu boardu (`event: live`, stejné SSE spojení jako chat lékařů, T-334), takže mobil přepne bez obnovení.

Pacient jen jako `Pxx` (D-018). Klinická data se nečtou tady, ale v IRIS přes existující endpointy případu.
"""
import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import roles
from .chat import _group
from .models import MdtCase, MdtSession, SessionPresence

log = logging.getLogger(__name__)

PRESENCE_TTL = timedelta(minutes=5)       # aplikace se ohlašuje každé 2 min; po 5 min bez ohlášení lékař „odešel“
LABEL_MAX = 200
CLOSED_LIVE = {'detail': 'Board je uzavřený, projektor už nic neukazuje.'}


# ── serializace ──────────────────────────────────────────────────────────────
def _present(session: MdtSession, now=None) -> list[dict]:
    since = (now or timezone.now()) - PRESENCE_TTL
    rows = (SessionPresence.objects.filter(session=session, last_seen__gte=since)
            .select_related('user__mdt_profile').order_by('joined_at'))
    out = []
    for p in rows:
        profile = getattr(p.user, 'mdt_profile', None) if hasattr(p.user, 'mdt_profile') else None
        out.append({'user_id': p.user_id, 'name': roles.display_name(p.user),
                    'specialty': (profile.specialty or None) if profile else None})
    return out


def live_state(session: MdtSession, now=None) -> dict:
    """`LiveState` (ARCH §8.6): pacient a slide na projektoru + přítomní lékaři."""
    case = session.live_case if session.live_case_id else None
    cases = list(session.cases.values_list('pk', flat=True)) if case else []
    slide = None
    if case and session.live_slides:
        slide = {'index': session.live_slide or 0, 'total': session.live_slides, 'label': session.live_label}
    return {
        'session': session.pk, 'status': session.status,
        'case': case and {'id': case.pk, 'patient_id': case.patient_fhir_id, 'status': case.status,
                          'position': cases.index(case.pk) + 1 if case.pk in cases else None, 'count': len(cases)},
        'slide': slide,
        'updated_at': session.live_updated_at.isoformat() if session.live_updated_at else None,
        'by': session.live_by_id and {'user_id': session.live_by_id, 'name': roles.display_name(session.live_by)},
        'present': _present(session, now),
    }


def _publish(sid: int, payload: dict) -> None:
    """Rozešle stav otevřeným streamům boardu. Výpadek Redisu nevadí: klient si stav načte GET po připojení."""
    try:
        async_to_sync(get_channel_layer().group_send)(_group(sid), {'type': 'chat.live', 'live': payload})
    except Exception:  # noqa: BLE001
        log.warning('T-357: živý stav boardu %s se nepodařilo rozeslat', sid, exc_info=True)


def _broadcast(session: MdtSession) -> dict:
    payload = live_state(session)
    transaction.on_commit(lambda: _publish(session.pk, payload))
    return payload


def can_present(user, session: MdtSession) -> bool:
    """Projektor řídí předseda komise (role `mdt_admin`) nebo předseda tohoto boardu."""
    return roles.role(user) == roles.ADMIN or (session.chair_id is not None and session.chair_id == user.pk)


# ── endpointy ────────────────────────────────────────────────────────────────
def _slide(raw) -> tuple[int | None, int | None, str]:
    if raw is None:
        return None, None, ''
    if not isinstance(raw, dict):
        raise ValidationError({'slide': 'Očekáváno {index, total, label?}.'})
    index, total = raw.get('index'), raw.get('total')
    ok = all(isinstance(v, int) and not isinstance(v, bool) for v in (index, total))
    if not ok or total < 1 or not 0 <= index < total or total > 99:
        raise ValidationError({'slide': 'index 0…total-1, total 1…99.'})
    return index, total, str(raw.get('label') or '')[:LABEL_MAX]


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def session_live(request, sid):
    """GET: `LiveState` boardu (kdokoli přihlášený). PUT `{case_id: int | null, slide?: {index, total, label?}}`:
    co je na projektoru (předseda); první PUT na naplánovaný board ho přepne na „probíhá“. Uzavřený board 409.
    Změna se rozešle do streamu boardu jako `event: live`."""
    session = get_object_or_404(MdtSession.objects.select_related('live_case', 'live_by'), pk=sid)
    if request.method == 'GET':
        return Response(live_state(session))
    if not can_present(request.user, session):
        raise PermissionDenied('Projektor řídí předseda komise.')
    if session.status == 'closed':
        return Response(CLOSED_LIVE, status=409)
    case_id = request.data.get('case_id')
    case = None
    if case_id is not None:
        if isinstance(case_id, int) and not isinstance(case_id, bool):
            case = MdtCase.objects.filter(pk=case_id, session=session).first()
        if case is None:
            raise ValidationError({'case_id': 'Pacient není v agendě tohoto boardu.'})
    index, total, label = _slide(request.data.get('slide')) if case else (None, None, '')
    changed = (session.live_case_id, session.live_slide, session.live_slides, session.live_label) != (
        case and case.pk, index, total, label)
    if not changed and session.status == 'in_progress':
        return Response(live_state(session))              # stejný stav: nic nerozesílat (jednání ho posílá opakovaně)
    session.live_case, session.live_slide, session.live_slides, session.live_label = case, index, total, label
    session.live_by, session.live_updated_at = request.user, timezone.now()
    if session.status == 'planned':
        session.status = 'in_progress'
    session.save(update_fields=['live_case', 'live_slide', 'live_slides', 'live_label', 'live_by', 'live_updated_at',
                                'status'])
    return Response(_broadcast(session))


@extend_schema(request=None, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def session_presence(request, sid):
    """POST: jsem na zasedání (ohlášení; aplikace ho opakuje každé 2 min) → `LiveState`. DELETE: odcházím → 204.
    Nový příchod a odchod se rozešlou do streamu boardu (seznam přítomných)."""
    session = get_object_or_404(MdtSession.objects.select_related('live_case', 'live_by'), pk=sid)
    now = timezone.now()
    if request.method == 'DELETE':
        deleted, _ = SessionPresence.objects.filter(session=session, user=request.user).delete()
        if deleted:
            _broadcast(session)
        return Response(status=204)
    if session.status == 'closed':
        return Response(CLOSED_LIVE, status=409)
    presence = SessionPresence.objects.filter(session=session, user=request.user).first()
    arrived = presence is None or presence.last_seen < now - PRESENCE_TTL
    # lékař je v jednu chvíli jen na jednom zasedání: příchod jinam ho z ostatních odhlásí
    SessionPresence.objects.filter(user=request.user).exclude(session=session).delete()
    SessionPresence.objects.update_or_create(session=session, user=request.user, defaults={'last_seen': now})
    return Response(_broadcast(session) if arrived else live_state(session, now))


def _reasons(user, session: MdtSession) -> list[str]:
    """Proč tu lékař má být: předseda boardu, zadávající lékař nebo přizvaný k pacientovi z agendy."""
    reasons = []
    if session.chair_id == user.pk:
        reasons.append('chair')
    cases = list(session.cases.all())
    if any(c.created_by_id == user.pk for c in cases):
        reasons.append('requester')
    if any(user.pk in {u.pk for u in c.collaborators.all()} for c in cases):
        reasons.append('collaborator')
    return reasons


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_live(request):
    """`MyLive` (ARCH §8.6): dnešní a probíhající zasedání s živým stavem; `current` = kde lékař je (ohlášený),
    jinak probíhající zasedání, kde má být, jinak jakékoli probíhající, jinak nejbližší dnešní, kde má být."""
    now = timezone.now()
    today = timezone.localdate(now)
    sessions = list(MdtSession.objects.filter(Q(status='in_progress') | Q(date__date=today))
                    .exclude(status='closed').select_related('chair', 'live_case', 'live_by')
                    .prefetch_related('cases__collaborators').order_by('date', 'title'))
    mine = {p.session_id: p for p in SessionPresence.objects.filter(user=request.user, session__in=sessions,
                                                                     last_seen__gte=now - PRESENCE_TTL)}
    out = []
    for s in sessions:
        reasons = _reasons(request.user, s)
        out.append({
            'id': s.pk, 'date': timezone.localtime(s.date).isoformat(), 'title': s.title, 'status': s.status,
            'chair': s.chair_id and {'user_id': s.chair_id, 'name': roles.display_name(s.chair)},
            'expected': bool(reasons), 'reasons': reasons, 'here': s.pk in mine,
            'my_patients': sorted({c.patient_fhir_id for c in s.cases.all()
                                   if c.created_by_id == request.user.pk
                                   or request.user.pk in {u.pk for u in c.collaborators.all()}}),
            'can_present': can_present(request.user, s),
            'live': live_state(s, now),
        })

    def pick() -> int | None:
        for test in (lambda x: x['here'],
                     lambda x: x['status'] == 'in_progress' and x['expected'],
                     lambda x: x['status'] == 'in_progress',
                     lambda x: x['expected']):
            hit = next((x for x in out if test(x)), None)
            if hit:
                return hit['id']
        return None

    return Response({'now': timezone.localtime(now).isoformat(), 'current': pick(), 'sessions': out})
