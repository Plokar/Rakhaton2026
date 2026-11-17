"""Chatbot u zasedání (T-344, ARCH §5.12, §6.3): lékař se ptá AI, odpověď nese ke každému tvrzení zdroj.

Vedle chatu lékařů (T-334), ale soukromý: rozhovor patří lékaři a boardu, ostatní ho nevidí. Odpovídá jen AI tomu,
kdo se ptá, takže stačí jeden POST (otázka i odpověď v těle odpovědi), bez streamu. Logika je v `services/ai/chatbot.py`.

Chatbot nad kartou pacienta (T-345): stejná odpověď bez boardu a bez případu (zařazení, okno pro projektor),
nic se neukládá, rozhovor drží prohlížeč.
"""
import asyncio
import json
import logging

from django.db import close_old_connections
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services import patients
from services.ai import chatbot as ai_chatbot

from .chat import HISTORY, message_case, message_text
from .models import ChatbotMessage, MdtSession, SessionMessage

log = logging.getLogger(__name__)

CONTEXT_MESSAGES = 6     # kolik předchozích zpráv rozhovoru o stejném pacientovi dostane LLM
CLOSED_CHATBOT = {'detail': 'Board je uzavřený, chatbot je jen ke čtení.'}


def _message(m: ChatbotMessage) -> dict:
    """`ChatbotMessage` (ARCH §8.6). Pacient jen jako `Pxx` (D-018)."""
    return {'id': m.pk, 'session': m.session_id, 'role': m.role,
            'case': m.case and {'id': m.case_id, 'patient_id': m.case.patient_fhir_id},
            'text': m.text, 'claims': m.claims, 'uncertain': m.uncertain, 'model': m.model or None,
            'created_at': timezone.localtime(m.created_at).isoformat()}


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def session_chatbot(request, sid):
    """GET: vlastní rozhovor s AI u boardu od nejstarší (posledních 200 zpráv).
    POST `{text, case_id?}`: dotaz k pacientovi z agendy (bez `case_id` jen guidelines a studie) → 201
    `[dotaz, odpověď AI]`. Uzavřený board je jen ke čtení (409)."""
    session = get_object_or_404(MdtSession, pk=sid)
    mine = ChatbotMessage.objects.filter(session=session, user=request.user).select_related('case')
    if request.method == 'GET':
        return Response([_message(m) for m in reversed(mine.order_by('-id')[:HISTORY])])
    if session.status == 'closed':
        return Response(CLOSED_CHATBOT, status=409)
    text, case = message_text(request.data), message_case(request.data, session)
    history = [_message(m) for m in reversed(mine.filter(case=case).order_by('-id')[:CONTEXT_MESSAGES])]
    question = ChatbotMessage.objects.create(session=session, user=request.user, case=case, role='user', text=text)

    def work(on_stage=None) -> list[dict]:
        try:
            extra = {'on_stage': on_stage} if on_stage else {}
            result = ai_chatbot.answer(text, case.patient_fhir_id if case else None, history, **extra)
        except Exception:          # dotaz zůstane uložený, lékař vidí, že AI neodpověděla
            log.exception('T-344: chatbot neodpověděl (board %s)', session.pk)
            result = {'text': 'AI se teď nepodařilo odpovědět.', 'claims': [], 'uncertain': [], 'model': None}
        reply = ChatbotMessage.objects.create(session=session, user=request.user, case=case, role='ai',
                                              text=result['text'], claims=result['claims'],
                                              uncertain=result['uncertain'], model=result['model'] or '')
        return [_message(question), _message(reply)]

    if request.query_params.get('stream') in ('1', 'true'):
        return stream_answer(work)
    return Response(work(), status=201)


# ── T-382: průběh odpovědi, navržené otázky, hodnocení ─────────────────────────
STAGES = {'context': 'Hledám v dokumentaci…', 'llm': 'AI odpovídá…', 'grounding': 'Kontroluji citace…'}


def _sse(event: str, data) -> str:
    return f'event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n'


def stream_answer(work) -> StreamingHttpResponse:
    """SSE průběh odpovědi (T-382): `event: stage` (`{stage, label}`) a nakonec `event: answer` (stejné tělo jako POST
    bez streamu) nebo `event: error`. Text modelu se po částech neposílá: každé tvrzení musí nejdřív projít
    kontrolou citací (grounding, §5.3), proto se ukáže až ověřená odpověď."""
    async def events():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def on_stage(name: str) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, name)

        def run():
            try:
                return work(on_stage)
            finally:
                close_old_connections()            # spojení do DB z vlákna executoru

        future = loop.run_in_executor(None, run)
        while True:
            getter = asyncio.ensure_future(queue.get())
            done, _ = await asyncio.wait({getter, future}, return_when=asyncio.FIRST_COMPLETED)
            if getter in done:
                name = getter.result()
                yield _sse('stage', {'stage': name, 'label': STAGES.get(name, name)})
                continue
            getter.cancel()
            while not queue.empty():
                name = queue.get_nowait()
                yield _sse('stage', {'stage': name, 'label': STAGES.get(name, name)})
            break
        try:
            yield _sse('answer', future.result())
        except Exception:                          # noqa: BLE001
            log.exception('T-382: průběžná odpověď chatbota selhala')
            yield _sse('error', {'detail': 'AI se teď nepodařilo odpovědět.'})

    response = StreamingHttpResponse(events(), content_type='text/event-stream', status=201)
    response['Cache-Control'] = 'no-cache, no-transform'
    response['X-Accel-Buffering'] = 'no'
    return response


@extend_schema(responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatbot_suggestions(request):
    """Navržené otázky (T-382): `?patient=P03` podle diagnózy pacienta z IRIS, bez pacienta obecné (guidelines)."""
    from services.ai.chatbot_suggestions import suggestions_for

    pid = request.query_params.get('patient') or ''
    if not pid:
        return Response(suggestions_for(None))
    if not patients.VALID_ID.match(pid):
        raise ValidationError({'patient': 'Neplatné ID pacienta.'})
    from .scope import patient_visible
    if not patient_visible(request.user, pid):
        return Response({'detail': 'Pacient není v zasedáních, kam jste pozvaný.'}, status=403)
    try:
        dg = patients.summary(pid, patients.load_patient(pid)).get('diagnosis') or {}
    except Exception:                              # noqa: BLE001  IRIS nedostupné: obecné otázky stačí
        dg = {}
    return Response(suggestions_for([dg['icd10']] if dg.get('icd10') else None))


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_feedback(request):
    """Hodnocení odpovědi AI (T-382) → `AiFeedback` pro eval. `{rating: "up" | "down", comment?}` a buď
    `message_id` (moje odpověď chatbota u zasedání, opakované hodnocení ho přepíše), nebo
    `{patient_id, question, answer}` (chatbot nad kartou, odpověď drží prohlížeč)."""
    from services.ai.pseudonymize import PERSONAL_DATA_LABELS, personal_data_kinds

    from .models import AiFeedback

    data = request.data
    rating = data.get('rating')
    if rating not in ('up', 'down'):
        raise ValidationError({'rating': 'Jen "up" nebo "down".'})
    comment = str(data.get('comment') or '').strip()[:AiFeedback.MAX_COMMENT]
    if kinds := personal_data_kinds(comment):
        raise ValidationError({'comment': f'Komentář obsahuje osobní údaj ({", ".join(PERSONAL_DATA_LABELS[k] for k in kinds)}).'})
    if data.get('message_id') is not None:
        reply = ChatbotMessage.objects.filter(pk=data.get('message_id'), user=request.user, role='ai').select_related('case').first()
        if reply is None:
            raise ValidationError({'message_id': 'Hodnotit jde jen vlastní odpověď AI.'})
        asked = ChatbotMessage.objects.filter(session=reply.session, user=request.user, role='user', pk__lt=reply.pk).order_by('-pk').first()
        item, _ = AiFeedback.objects.update_or_create(
            user=request.user, message=reply,
            defaults={'kind': 'session_chatbot', 'patient_fhir_id': reply.case.patient_fhir_id if reply.case else '',
                      'question': asked.text if asked else '', 'answer': _message(reply), 'rating': rating, 'comment': comment})
    else:
        pid = str(data.get('patient_id') or '')
        if not patients.VALID_ID.match(pid):
            raise ValidationError({'patient_id': 'Neplatné ID pacienta.'})
        from .scope import patient_visible
        if not patient_visible(request.user, pid):
            return Response({'detail': 'Pacient není v zasedáních, kam jste pozvaný.'}, status=403)
        question = message_text({'text': data.get('question')})
        answer = data.get('answer')
        if not isinstance(answer, dict) or len(json.dumps(answer)) > 20_000:
            raise ValidationError({'answer': 'Odpověď AI {text, claims, uncertain} (nejvýš 20 kB).'})
        item = AiFeedback.objects.create(user=request.user, kind='patient_chatbot', patient_fhir_id=pid,
                                         question=question, answer=answer, rating=rating, comment=comment)
    return Response({'id': item.pk, 'rating': item.rating}, status=201)


def _client_history(raw) -> list[dict]:
    """Předchozí zprávy z prohlížeče (T-345) ve tvaru pro prompt: posledních `CONTEXT_MESSAGES`, jen role, text a tvrzení."""
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(m, dict) and m.get('role') in ('user', 'ai') for m in raw):
        raise ValidationError({'history': 'Seznam zpráv {role: "user" | "ai", text, claims?}.'})
    out = []
    for m in raw[-CONTEXT_MESSAGES:]:
        claims = [{'kind': c['kind'], 'text': str(c.get('text') or '')[:SessionMessage.MAX_LENGTH],
                   'citations': [str(x) for x in c.get('citations') or []][:10]}
                  for c in m.get('claims') or [] if isinstance(c, dict) and c.get('kind') in ('claim', 'missing')]
        out.append({'role': m['role'], 'text': str(m.get('text') or '')[:SessionMessage.MAX_LENGTH], 'claims': claims})
    return out


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=['mdt'])
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def patient_chatbot(request, pid):
    """POST `{text, history?}`: dotaz na kartu pacienta bez boardu (zařazení, okno pro projektor) → 200
    `{text, claims, uncertain, model}` jako odpověď AI v `ChatbotMessage`. Nic se neukládá."""
    if not patients.VALID_ID.match(pid or ''):
        raise ValidationError({'patient_id': 'Neplatné ID pacienta.'})
    text, history = message_text(request.data), _client_history(request.data.get('history'))
    try:
        result = ai_chatbot.answer(text, pid, history)
    except Exception:
        log.exception('T-345: chatbot nad kartou %s neodpověděl', pid)
        result = {'text': 'AI se teď nepodařilo odpovědět.', 'claims': [], 'uncertain': [], 'model': None}
    return Response(result)
