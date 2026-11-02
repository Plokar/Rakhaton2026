"""Chat lékařů u zasedání (T-334): zprávy po boardech, štítek pacienta, uzavřený board, doručení přes SSE."""
import asyncio
import json

import pytest
import pytest_asyncio
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connections
from django.test import AsyncClient, Client
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.mdt import chat
from apps.mdt.models import MdtCase, MdtSession, SessionMessage

IN_MEMORY = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


@pytest.fixture
def seeded(fake_fhir_dataset, db):
    call_command('seed_mdt')


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def url(sid):
    return f'/api/mdt/sessions/{sid}/messages/'


def board():
    return MdtSession.objects.get(title='Hrudní – karcinom plic')


@pytest.mark.django_db
def test_doctors_chat_per_board_with_patient_label(seeded):
    s = board()
    case = s.cases.first()
    first = as_user('onkolog').post(url(s.pk), {'text': '  Navrhuji chemoradioterapii.  ', 'case_id': case.pk},
                                    format='json')
    assert first.status_code == 201
    assert first.json() | {'id': 0, 'created_at': ''} == {
        'id': 0, 'session': s.pk, 'author': {'user_id': first.json()['author']['user_id'], 'name': 'Klinický onkolog'},
        'specialty': 'oncologist', 'case': {'id': case.pk, 'patient_id': case.patient_fhir_id},
        'text': 'Navrhuji chemoradioterapii.', 'created_at': ''}
    # píše i člen komise s rolí jen ke čtení, bez štítku = zpráva k celému zasedání
    assert as_user('chirurg').post(url(s.pk), {'text': 'Resekabilní?'}, format='json').status_code == 201

    messages = as_user('radiolog').get(url(s.pk)).json()
    assert [(m['author']['name'], m['specialty'], m['case']) for m in messages] == [
        ('Klinický onkolog', 'oncologist', {'id': case.pk, 'patient_id': case.patient_fhir_id}),
        ('Chirurg', 'surgeon', None)]
    other = MdtSession.objects.exclude(pk=s.pk).first()
    assert as_user('onkolog').get(url(other.pk)).json() == []


@pytest.mark.django_db
def test_after_returns_only_newer(seeded):
    s = board()
    ids = [as_user('onkolog').post(url(s.pk), {'text': t}, format='json').json()['id'] for t in ('a', 'b', 'c')]
    assert [m['text'] for m in as_user('onkolog').get(url(s.pk), {'after': ids[0]}).json()] == ['b', 'c']
    assert as_user('onkolog').get(url(s.pk), {'after': 'x'}).status_code == 400


@pytest.mark.django_db
def test_invalid_messages_rejected(seeded):
    s = board()
    foreign = MdtCase.objects.exclude(session=s).first()
    doctor = as_user('onkolog')
    for body in ({'text': '   '}, {'text': 'x' * 2001}, {'text': 'ok', 'case_id': foreign.pk},
                 {'text': 'ok', 'case_id': str(s.cases.first().pk)}):
        assert doctor.post(url(s.pk), body, format='json').status_code == 400, body
    assert doctor.post(url(9999), {'text': 'ok'}, format='json').status_code == 404
    assert not SessionMessage.objects.exists()


@pytest.mark.django_db
def test_closed_board_is_read_only(seeded):
    s = board()
    as_user('onkolog').post(url(s.pk), {'text': 'Před ukončením'}, format='json')
    MdtSession.objects.filter(pk=s.pk).update(status='closed')
    assert as_user('predseda').post(url(s.pk), {'text': 'Po ukončení'}, format='json').status_code == 409
    assert [m['text'] for m in as_user('chirurg').get(url(s.pk)).json()] == ['Před ukončením']


@pytest.mark.django_db
def test_anonymous_cannot_read_or_stream(seeded):
    s = board()
    assert APIClient().get(url(s.pk)).status_code in (401, 403)
    assert Client().get(f'/api/mdt/sessions/{s.pk}/stream/').status_code == 401
    client = Client()
    client.cookies['access_token'] = str(AccessToken.for_user(get_user_model().objects.get(username='onkolog')))
    assert client.get('/api/mdt/sessions/9999/stream/').status_code == 404


# ── stream (SSE) ──────────────────────────────────────────────────────────────
def _board_with_message():
    user = get_user_model().objects.create_user('doktor', password='x', first_name='Doktor')
    s = MdtSession.objects.create(date=timezone.now(), title='Test')
    m = SessionMessage.objects.create(session=s, author=user, text='první')
    return s.pk, m.pk, str(AccessToken.for_user(user))


def _post(sid, text):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username='doktor'))
    return client.post(url(sid), {'text': text}, format='json').json()


@pytest_asyncio.fixture
async def thread_db():
    """Spojení z vlákna `sync_to_async` zavřít, jinak teardown testovací DB selže ("accessed by other users")."""
    yield
    await sync_to_async(connections.close_all)()


def _data(chunk: str) -> dict:
    return json.loads(chunk.split('data: ', 1)[1])


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_stream_catches_up_then_pushes_new_message(settings, thread_db):
    settings.CHANNEL_LAYERS = IN_MEMORY
    sid, first, _ = await sync_to_async(_board_with_message)()
    stream = chat._events(sid, after=0)
    try:
        assert await anext(stream) == 'retry: 3000\n\n'
        caught = await anext(stream)
        assert caught.startswith(f'id: {first}\n') and _data(caught)['text'] == 'první'
        waiting = asyncio.ensure_future(anext(stream))
        sent = await sync_to_async(_post)(sid, 'Souhlasím s resekcí')
        pushed = _data(await asyncio.wait_for(waiting, 5))
        assert pushed == sent and pushed['author']['name'] == 'Doktor'
    finally:
        await stream.aclose()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_stream_heartbeat_and_endpoint(settings, monkeypatch, thread_db):
    settings.CHANNEL_LAYERS = IN_MEMORY
    monkeypatch.setattr(chat, 'HEARTBEAT_SECONDS', 0.01)
    sid, first, token = await sync_to_async(_board_with_message)()
    stream = chat._events(sid, after=first)
    try:
        assert [await anext(stream), await anext(stream)] == ['retry: 3000\n\n', ': ping\n\n']
    finally:
        await stream.aclose()

    client = AsyncClient()
    client.cookies['access_token'] = token
    response = await client.get(f'/api/mdt/sessions/{sid}/stream/', headers={'Last-Event-ID': '0'})
    assert response.status_code == 200 and response['Content-Type'] == 'text/event-stream'
    assert 'no-transform' in response['Cache-Control']      # jinak proxy s kompresí stream bufferuje
    content = aiter(response.streaming_content)
    try:
        assert await anext(content) == b'retry: 3000\n\n'
        assert _data((await anext(content)).decode())['id'] == first     # Last-Event-ID doplní zmeškané
    finally:
        await content.aclose()
