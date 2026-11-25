"""Zasedání do kalendáře (T-384): `.ics` (RFC 5545) pro Outlook, Google a Apple kalendář.

Události nesou jen název komise, čas, předsedu a pacienty jako `Pxx` (D-018) s odkazem na „Živě na MDT“.
"""
from datetime import UTC, timedelta

from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from . import roles
from .live import minutes_per_case
from .models import MdtSession
from .scope import visible_sessions


def _escape(text: str) -> str:
    return text.replace('\\', '\\\\').replace(';', '\;').replace(',', '\\,').replace('\n', '\\n')


def _fold(line: str) -> str:
    """Řádky nejvýš 75 oktetů (RFC 5545 §3.1), pokračování začíná mezerou."""
    data, out = line.encode(), []
    while len(data) > 75:
        cut = 75
        while (data[cut] & 0xC0) == 0x80:        # nerozdělit znak UTF-8
            cut -= 1
        out.append(data[:cut].decode())
        data = b' ' + data[cut:]
    out.append(data.decode())
    return '\r\n'.join(out)


def _stamp(dt) -> str:
    return dt.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')


def _event(s: MdtSession, base: str, now) -> list[str]:
    patients = [c.patient_fhir_id for c in s.cases.all()]
    minutes = max(60, len(patients) * minutes_per_case())
    url = f'{base}/dashboard/live?zasedani={s.pk}'
    description = '\n'.join(filter(None, [
        f'Předseda: {roles.display_name(s.chair)}' if s.chair else '',
        f'Pacienti: {", ".join(patients)}' if patients else 'Agenda zatím prázdná',
        f'Živě na MDT: {url}']))
    lines = ['BEGIN:VEVENT', f'UID:mdt-session-{s.pk}@mdtcore', f'DTSTAMP:{_stamp(now)}',
             f'DTSTART:{_stamp(s.date)}', f'DTEND:{_stamp(s.date + timedelta(minutes=minutes))}',
             f'SUMMARY:{_escape("MDT: " + s.title)}', f'DESCRIPTION:{_escape(description)}', f'URL:{url}',
             f'STATUS:{"CANCELLED" if s.status == "closed" and not patients else "CONFIRMED"}', 'END:VEVENT']
    return lines


def _calendar(sessions, request, filename: str) -> HttpResponse:
    from apps.authentication.views import _frontend_url
    base = _frontend_url(request)          # MDT_FRONTEND_URL, jinak důvěryhodný Origin (jako odkaz v e-mailu, T-371)
    now = timezone.now()
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//MDTcore//MDT zasedání//CS', 'CALSCALE:GREGORIAN',
             'METHOD:PUBLISH', 'X-WR-CALNAME:MDT zasedání']
    for s in sessions:
        lines += _event(s, base, now)
    lines.append('END:VCALENDAR')
    response = HttpResponse('\r\n'.join(_fold(line) for line in lines) + '\r\n', content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@extend_schema(responses={(200, 'text/calendar'): OpenApiTypes.BINARY}, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_calendar(request, sid):
    """Jedno zasedání jako `.ics`."""
    s = get_object_or_404(visible_sessions(request.user).select_related('chair').prefetch_related('cases'), pk=sid)
    return _calendar([s], request, f'mdt-zasedani-{s.pk}.ics')


@extend_schema(responses={(200, 'text/calendar'): OpenApiTypes.BINARY}, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_calendar(request):
    """Nadcházející zasedání (90 dní) jako `.ics`; `?mine=1` jen ta, kde lékař předsedá, má pacienta, je přizvaný
    nebo pozvaný."""
    now = timezone.now()
    sessions = visible_sessions(request.user).filter(date__gte=now - timedelta(hours=12), date__lte=now + timedelta(days=90))
    if request.query_params.get('mine') in ('1', 'true'):
        u = request.user
        sessions = sessions.filter(Q(chair=u) | Q(cases__created_by=u) | Q(cases__collaborators=u) | Q(invited=u)
                                   | (Q(committee__members=u) & ~Q(excluded=u)))
    sessions = sessions.distinct().select_related('chair').prefetch_related('cases').order_by('date')
    return _calendar(list(sessions), request, 'mdt-moje-zasedani.ics')
