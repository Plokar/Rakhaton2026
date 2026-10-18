"""Chatbot u zasedání (T-344, ARCH §5.12, §6.3): lékař se ptá AI, odpověď nese ke každému tvrzení zdroj.

Vedle chatu lékařů (T-334), ale soukromý: rozhovor patří lékaři a boardu, ostatní ho nevidí. Odpovídá jen AI tomu,
kdo se ptá, takže stačí jeden POST (otázka i odpověď v těle odpovědi), bez streamu. Logika je v `services/ai/chatbot.py`.
"""
import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from services.ai import chatbot as ai_chatbot

from .chat import HISTORY, message_case, message_text
from .models import ChatbotMessage, MdtSession

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
    try:
        result = ai_chatbot.answer(text, case.patient_fhir_id if case else None, history)
    except Exception:          # dotaz zůstane uložený, lékař vidí, že AI neodpověděla
        log.exception('T-344: chatbot neodpověděl (board %s)', session.pk)
        result = {'text': 'AI se teď nepodařilo odpovědět.', 'claims': [], 'uncertain': [], 'model': None}
    reply = ChatbotMessage.objects.create(session=session, user=request.user, case=case, role='ai',
                                          text=result['text'], claims=result['claims'],
                                          uncertain=result['uncertain'], model=result['model'] or '')
    return Response([_message(question), _message(reply)], status=201)
