"""Chat lékařů u zasedání (T-334, ARCH §6.3): zprávy v Postgresu, doručení přes Server-Sent Events.

Bez websocketů a bez pollingu: prohlížeč drží jedno HTTP spojení `GET …/stream/` a server do něj pošle novou
zprávu, jakmile ji někdo uloží. Mezi procesy ji předá channel layer (Redis). Po výpadku spojení pošle `EventSource`
hlavičku `Last-Event-ID` a stream nejdřív doplní zprávy, které klient nemá, takže se žádná neztratí.
"""
import asyncio
import json
import logging

from asgiref.sync import async_to_sync, sync_to_async
from channels.layers import get_channel_layer
from django.db import transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.authentication.backends import CookieJWTAuthentication

from . import roles
from .models import MdtCase, MdtSession, SessionMessage

log = logging.getLogger(__name__)

HISTORY = 200            # kolik posledních zpráv vrátí GET bez `after`
HEARTBEAT_SECONDS = 15   # komentář do streamu, aby proxy (Traefik) nečinné spojení nezavřela
CLOSED_CHAT = {'detail': 'Board je uzavřený, chat je jen ke čtení.'}


def _group(sid: int) -> str:
    return f'mdt-chat-{sid}'


def _message(m: SessionMessage) -> dict:
    """`SessionMessage` (ARCH §8.6). Pacient jen jako `Pxx` (D-018)."""
    a = m.author
    profile = getattr(a, 'mdt_profile', None) if a else None    # chybějící profil → None (AttributeError)
    return {'id': m.pk, 'session': m.session_id,
            'author': a and {'user_id': a.pk, 'name': roles.display_name(a)},
            'specialty': (profile.specialty or None) if profile else None,
            'case': m.case and {'id': m.case_id, 'patient_id': m.case.patient_fhir_id},
            'text': m.text, 'created_at': timezone.localtime(m.created_at).isoformat()}


def _messages(sid: int, after: int | None) -> list[dict]:
    """Od nejstarší: s `after` všechny novější než `after`, jinak posledních `HISTORY`."""
    qs = SessionMessage.objects.filter(session_id=sid).select_related('author__mdt_profile', 'case')
    if after is not None:
        return [_message(m) for m in qs.filter(pk__gt=after)]
    return [_message(m) for m in reversed(qs.order_by('-id')[:HISTORY])]


def _after(value) -> int | None:
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({'after': 'Očekáváno ID zprávy (celé číslo).'}) from None


def _publish(sid: int, payload: dict) -> None:
    """Rozešle zprávu otevřeným streamům boardu. Výpadek Redisu zprávu neztratí: je v DB a stream ji doplní."""
    try:
        async_to_sync(get_channel_layer().group_send)(_group(sid), {'type': 'chat.message', 'message': payload})
    except Exception:  # noqa: BLE001
        log.warning('T-334: zprávu %s se nepodařilo rozeslat přes channel layer', payload['id'], exc_info=True)


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def session_messages(request, sid):
    """GET: zprávy chatu od nejstarší; `?after=<id>` jen novější, jinak posledních 200.
    POST `{text, case_id?}`: píše každý člen komise, `case_id` = štítek pacienta z agendy boardu.
    Uzavřený board je jen ke čtení (409)."""
    session = get_object_or_404(MdtSession, pk=sid)
    if request.method == 'GET':
        return Response(_messages(session.pk, _after(request.query_params.get('after'))))
    if session.status == 'closed':
        return Response(CLOSED_CHAT, status=409)
    text = str(request.data.get('text') or '').strip()
    if not text:
        raise ValidationError({'text': 'Zpráva je prázdná.'})
    if len(text) > SessionMessage.MAX_LENGTH:
        raise ValidationError({'text': f'Zpráva má nejvýš {SessionMessage.MAX_LENGTH} znaků.'})
    case, case_id = None, request.data.get('case_id')
    if case_id is not None:
        if isinstance(case_id, int) and not isinstance(case_id, bool):
            case = MdtCase.objects.filter(pk=case_id, session=session).first()
        if case is None:
            raise ValidationError({'case_id': 'Pacient není v agendě tohoto boardu.'})
    m = SessionMessage.objects.create(session=session, author=request.user, case=case, text=text)
    payload = _message(m)
    transaction.on_commit(lambda: _publish(session.pk, payload))
    return Response(payload, status=201)


def _authenticate(request):
    """JWT z httpOnly cookie (EventSource posílá cookies, vlastní hlavičky ne) nebo z hlavičky, jako u DRF."""
    try:
        result = CookieJWTAuthentication().authenticate(request)
    except AuthenticationFailed:
        return None
    return result[0] if result else None


def _sse(m: dict) -> str:
    # json.dumps je jeden řádek (konce řádků ve zprávě escapuje), `id` vrátí EventSource v Last-Event-ID
    return f'id: {m["id"]}\ndata: {json.dumps(m, ensure_ascii=False)}\n\n'


async def _events(sid: int, after: int | None):
    layer = get_channel_layer()
    channel = await layer.new_channel()
    # Do skupiny dřív, než se načtou zmeškané: zpráva uložená mezitím přijde dvakrát (vyřadí ji `after`), ne vůbec.
    await layer.group_add(_group(sid), channel)
    receiving = None
    try:
        yield 'retry: 3000\n\n'
        if after is not None:
            for m in await sync_to_async(_messages)(sid, after):
                after = m['id']
                yield _sse(m)
        # Jeden běžící receive(): zrušený receive() v channels_redis zahodí frontu kanálu, proto heartbeat
        # čeká přes asyncio.wait s timeoutem, které úlohu neruší.
        receiving = asyncio.ensure_future(layer.receive(channel))
        while True:
            done, _ = await asyncio.wait({receiving}, timeout=HEARTBEAT_SECONDS)
            if not done:
                yield ': ping\n\n'
                continue
            m = receiving.result()['message']
            receiving = asyncio.ensure_future(layer.receive(channel))
            if after is None or m['id'] > after:
                after = m['id']
                yield _sse(m)
    finally:
        # klient se odpojil: Django zruší odesílání a iterátor zavře
        if receiving:
            receiving.cancel()
        await layer.group_discard(_group(sid), channel)


@require_GET
async def session_stream(request, sid):
    """SSE `text/event-stream`: nové zprávy chatu boardu (`id` = ID zprávy, `data` = `SessionMessage`).
    `Last-Event-ID` (EventSource po výpadku) nebo `?after=<id>` nejdřív doplní zprávy, které klient nemá."""
    user = await sync_to_async(_authenticate)(request)
    if user is None:
        return JsonResponse({'detail': 'Nejste přihlášeni.'}, status=401)
    if not await MdtSession.objects.filter(pk=sid).aexists():
        return JsonResponse({'detail': 'Board neexistuje.'}, status=404)
    try:
        after = _after(request.headers.get('Last-Event-ID') or request.GET.get('after'))
    except ValidationError:
        return JsonResponse({'after': 'Očekáváno ID zprávy (celé číslo).'}, status=400)
    response = StreamingHttpResponse(_events(sid, after), content_type='text/event-stream')
    # no-transform: proxy s kompresí (rewrite v Next.js, `next start`) by stream zabalila do gzipu a bufferovala
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'     # proxy typu nginx stream nebufferuje
    return response
