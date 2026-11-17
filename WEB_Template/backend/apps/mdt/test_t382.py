"""AI chatbot (T-382): průběh odpovědi (SSE), navržené otázky podle diagnózy, hodnocení odpovědí."""
import json
from io import StringIO

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import AsyncClient
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.mdt.models import AiFeedback, ChatbotMessage, MdtCase, MdtSession
from apps.mdt.test_chat import thread_db  # noqa: F401  (fixture)
from services.ai import chatbot as ai_chatbot
from services.ai.chatbot_suggestions import suggestions_for


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


@pytest.fixture
def seeded(fake_fhir_dataset, db):
    call_command('seed_mdt')
    cache.clear()


def test_suggestions_by_area():
    assert suggestions_for(None)['area'] is None and suggestions_for(None)['questions']
    assert suggestions_for(['C18.7'])['area'] == 'KRC' and 'CEA' in suggestions_for(['C18.7'])['questions'][0]
    assert suggestions_for(['C34.1'])['area'] == 'PLI'
    assert suggestions_for(['C50.4'])['area'] == 'PRS'
    assert suggestions_for(['C71.1'])['area'] == 'OBC'


@pytest.mark.django_db
def test_suggestions_endpoint(seeded):
    data = as_user('onkolog').get('/api/mdt/chatbot/suggestions/', {'patient': 'P03'}).json()
    assert data['area'] == 'KRC' and len(data['questions']) == 4
    assert as_user('onkolog').get('/api/mdt/chatbot/suggestions/').json()['area'] is None
    assert as_user('onkolog').get('/api/mdt/chatbot/suggestions/', {'patient': 'P03/..'}).status_code == 400


def test_answer_reports_stages_in_order():
    from services.ai.context_builder import general_context
    from services.ai_service import MockAIProvider

    stages = []
    ai_chatbot.answer_from_context('Jak se vyvíjí CEA?', general_context(), [], MockAIProvider(), lambda *a: None,
                                   on_stage=stages.append)
    assert stages == ['llm', 'grounding']


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_stream_sends_stages_then_verified_answer(fake_fhir_dataset, thread_db):  # noqa: F811
    await sync_to_async(call_command)('seed_mdt')

    def prepare():
        s = MdtSession.objects.get(title='Hrudní – karcinom plic')
        user = get_user_model().objects.get(username='onkolog')
        return s.pk, s.cases.first().pk, str(RefreshToken.for_user(user).access_token)

    sid, cid, token = await sync_to_async(prepare)()
    client = AsyncClient()
    client.cookies['access_token'] = token
    response = await client.post(f'/api/mdt/sessions/{sid}/chatbot/?stream=1', {'text': 'Jaký je ECOG?', 'case_id': cid},
                                 content_type='application/json')
    assert response.status_code == 201 and response['Content-Type'] == 'text/event-stream'
    chunks = [c.decode() async for c in response.streaming_content]
    events = [(c.split('\n')[0][len('event: '):], json.loads(c.split('data: ', 1)[1])) for c in chunks]
    assert [e for e, _ in events] == ['stage', 'stage', 'stage', 'answer']
    assert [d['stage'] for _, d in events[:3]] == ['context', 'llm', 'grounding']
    question, reply = events[-1][1]
    assert question['role'] == 'user' and reply['role'] == 'ai' and reply['case']['id'] == cid
    assert await ChatbotMessage.objects.filter(session_id=sid).acount() == 2


@pytest.mark.django_db
def test_feedback_on_own_answer_and_patient_card(seeded, tmp_path):
    s = MdtSession.objects.get(title='Hrudní – karcinom plic')
    case = MdtCase.objects.filter(session=s).first()
    question, reply = as_user('onkolog').post(f'/api/mdt/sessions/{s.pk}/chatbot/', {'text': 'Jaký je ECOG?', 'case_id': case.pk},
                                              format='json').json()
    url = '/api/mdt/ai-feedback/'
    assert as_user('chirurg').post(url, {'message_id': reply['id'], 'rating': 'down'}, format='json').status_code == 400
    assert as_user('onkolog').post(url, {'message_id': question['id'], 'rating': 'up'}, format='json').status_code == 400
    assert as_user('onkolog').post(url, {'message_id': reply['id'], 'rating': 'meh'}, format='json').status_code == 400
    assert as_user('onkolog').post(url, {'message_id': reply['id'], 'rating': 'down', 'comment': 'Chybí citace.'},
                                   format='json').status_code == 201
    as_user('onkolog').post(url, {'message_id': reply['id'], 'rating': 'up'}, format='json')      # změna názoru
    item = AiFeedback.objects.get()
    assert (item.rating, item.question, item.patient_fhir_id) == ('up', 'Jaký je ECOG?', case.patient_fhir_id)

    card = {'patient_id': 'P03', 'question': 'CEA?', 'rating': 'down', 'answer': {'text': '', 'claims': []}}
    assert as_user('onkolog').post(url, card, format='json').status_code == 201
    assert as_user('onkolog').post(url, {**card, 'comment': 'volejte 603 123 456'}, format='json').status_code == 400

    out = tmp_path / 'fb.jsonl'
    call_command('export_ai_feedback', str(out), '--rating', 'down', stdout=StringIO())
    rows = [json.loads(line) for line in out.read_text(encoding='utf-8').splitlines()]
    assert [(r['kind'], r['patient_id'], r['specialty']) for r in rows] == [('patient_chatbot', 'P03', 'oncologist')]
