"""Živé zasedání (T-354): pacient na projektoru, přítomní lékaři, kde lékař má být, rozeslání do streamu boardu."""
import asyncio
import json
from datetime import timedelta

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.mdt import chat, live
from apps.mdt.models import MdtCase, MdtSession, SessionPresence
from apps.mdt.test_chat import IN_MEMORY, thread_db  # noqa: F401  (fixture)


@pytest.fixture
def seeded(fake_fhir_dataset, db):
    call_command('seed_mdt')


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def board():
    return MdtSession.objects.get(title='Hrudní – karcinom plic')


def live_url(sid):
    return f'/api/mdt/sessions/{sid}/live/'


@pytest.mark.django_db
def test_chair_sets_case_on_projector_and_everyone_reads_it(seeded):
    s = board()
    MdtCase.objects.exclude(session=s).filter(pk=MdtCase.objects.exclude(session=s).first().pk).update(session=s, order=9)
    cases = list(s.cases.all())
    second = cases[1]
    assert as_user('radiolog').get(live_url(s.pk)).json()['case'] is None

    r = as_user('predseda').put(live_url(s.pk), {'case_id': second.pk,
                                                 'slide': {'index': 1, 'total': 3, 'label': 'Léčebné postupy'}},
                                format='json')
    assert r.status_code == 200
    state = as_user('radiolog').get(live_url(s.pk)).json()
    assert state['case'] == {'id': second.pk, 'patient_id': second.patient_fhir_id, 'status': second.status,
                             'position': 2, 'count': len(cases)}
    assert state['slide'] == {'index': 1, 'total': 3, 'label': 'Léčebné postupy'}
    assert state['by']['name'] == 'Předseda komise (klinický onkolog)' and state['status'] == 'in_progress'

    # bez slidu (projektor neběží) zůstane jen pacient
    as_user('predseda').put(live_url(s.pk), {'case_id': cases[0].pk}, format='json')
    assert as_user('radiolog').get(live_url(s.pk)).json()['slide'] is None
    assert as_user('predseda').put(live_url(s.pk), {'case_id': None}, format='json').json()['case'] is None


@pytest.mark.django_db
def test_only_chair_controls_projector_and_input_validated(seeded):
    s = board()
    case = s.cases.first()
    assert as_user('onkolog').put(live_url(s.pk), {'case_id': case.pk}, format='json').status_code == 403
    foreign = MdtCase.objects.exclude(session=s).first()
    chair = as_user('predseda')
    for body in ({'case_id': foreign.pk}, {'case_id': str(case.pk)},
                 {'case_id': case.pk, 'slide': {'index': 3, 'total': 3}},
                 {'case_id': case.pk, 'slide': {'index': 0, 'total': 0}}, {'case_id': case.pk, 'slide': 'x'}):
        assert chair.put(live_url(s.pk), body, format='json').status_code == 400, body
    MdtSession.objects.filter(pk=s.pk).update(status='closed')
    assert chair.put(live_url(s.pk), {'case_id': case.pk}, format='json').status_code == 409


@pytest.mark.django_db
def test_presence_one_board_at_a_time_and_expires(seeded):
    s, other = board(), MdtSession.objects.exclude(title='Hrudní – karcinom plic').first()
    doctor = as_user('chirurg')
    assert doctor.post(f'/api/mdt/sessions/{other.pk}/presence/').status_code == 200
    state = doctor.post(f'/api/mdt/sessions/{s.pk}/presence/').json()
    assert [p['name'] for p in state['present']] == ['Chirurg'] and state['present'][0]['specialty'] == 'surgeon'
    assert not SessionPresence.objects.filter(session=other).exists()       # příchod jinam = odchod odsud

    SessionPresence.objects.update(last_seen=timezone.now() - live.PRESENCE_TTL - timedelta(seconds=1))
    assert as_user('radiolog').get(live_url(s.pk)).json()['present'] == []
    doctor.post(f'/api/mdt/sessions/{s.pk}/presence/')
    assert doctor.delete(f'/api/mdt/sessions/{s.pk}/presence/').status_code == 204
    assert as_user('radiolog').get(live_url(s.pk)).json()['present'] == []


@pytest.mark.django_db
def test_my_live_knows_where_doctor_should_be_and_is(seeded):
    s = board()
    today = MdtSession.objects.exclude(pk=s.pk).first()
    MdtSession.objects.filter(pk=today.pk).update(date=timezone.now() + timedelta(minutes=30), status='planned')
    MdtSession.objects.filter(pk=s.pk).update(date=timezone.now() - timedelta(days=3), status='planned')
    requester = s.cases.first().created_by

    data = as_user(requester.username).get('/api/mdt/live/').json()
    assert [x['id'] for x in data['sessions']] == [today.pk]          # jen dnešní a probíhající, ne minulé plánované

    as_user('predseda').put(live_url(s.pk), {'case_id': s.cases.first().pk}, format='json')   # board začal
    data = as_user(requester.username).get('/api/mdt/live/').json()
    item = next(x for x in data['sessions'] if x['id'] == s.pk)
    assert item['expected'] and 'requester' in item['reasons'] and s.cases.first().patient_fhir_id in item['my_patients']
    assert item['live']['case']['id'] == s.cases.first().pk and not item['can_present']
    assert data['current'] == s.pk                                    # probíhá a má tu pacienta

    # ohlášený lékař je tam, kde je, i když tam pacienta nemá
    as_user(requester.username).post(f'/api/mdt/sessions/{today.pk}/presence/')
    data = as_user(requester.username).get('/api/mdt/live/').json()
    assert data['current'] == today.pk and next(x for x in data['sessions'] if x['id'] == today.pk)['here']


# ── stream ───────────────────────────────────────────────────────────────────
def _start():
    s = board()
    return s.pk, s.cases.first().pk


def _put(sid, cid):
    return as_user('predseda').put(live_url(sid), {'case_id': cid, 'slide': {'index': 0, 'total': 2}},
                                   format='json').json()


@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_stream_pushes_live_event_without_id(settings, fake_fhir_dataset, thread_db):  # noqa: F811
    settings.CHANNEL_LAYERS = IN_MEMORY
    await sync_to_async(call_command)('seed_mdt')
    sid, cid = await sync_to_async(_start)()
    stream = chat._events(sid, after=None)
    try:
        assert await anext(stream) == 'retry: 3000\n\n'
        waiting = asyncio.ensure_future(anext(stream))
        await asyncio.sleep(0.05)
        sent = await sync_to_async(_put)(sid, cid)
        chunk = await asyncio.wait_for(waiting, 5)
        assert chunk.startswith('event: live\ndata: ') and 'id:' not in chunk.split('data: ')[0]
        assert json.loads(chunk.split('data: ', 1)[1]) == sent
    finally:
        await stream.aclose()
