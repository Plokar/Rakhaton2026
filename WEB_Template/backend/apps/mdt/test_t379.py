"""Opravy z auditu (T-379): úkoly lékaře z jiné nemocnice, živé zasedání, osobní údaje v chatu."""
import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.mdt import roles
from apps.mdt.models import MdtCase, MdtSession, UserProfile
from services import tasks

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')
    cache.clear()
    return fake_fhir_dataset


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def external(session: MdtSession, practitioner: str = 'LEK-EXT-01'):
    """Lékař z jiné nemocnice pozvaný jen na `session`; přes cookie, aby prošel i middleware rozsahu (T-362)."""
    user = get_user_model().objects.create_user('externi', password='x')
    UserProfile.objects.update_or_create(user=user, defaults={'is_external': True, 'organization': 'Nemocnice Jih',
                                                              'practitioner_fhir_id': practitioner})
    roles.ensure_demo_users()
    session.invited.add(user)
    client = APIClient()
    client.cookies['access_token'] = str(RefreshToken.for_user(user).access_token)
    return client


def fake_tasks(monkeypatch, owner='LEK-EXT-01'):
    items = [{'id': 'P03-mdt01-task01', 'patient_id': 'P03', 'mdt_record': None, 'description': 'CT',
              'owner': {'id': owner, 'name': 'Externí'}, 'due_date': None, 'status': 'requested'},
             {'id': 'P01-mdt01-task01', 'patient_id': 'P01', 'mdt_record': None, 'description': 'MR',
              'owner': {'id': owner, 'name': 'Externí'}, 'due_date': None, 'status': 'requested'}]
    monkeypatch.setattr(tasks, 'list_tasks', lambda status=None, patient=None, owner=None:
                        [i for i in items if not owner or i['owner']['id'] == owner])
    monkeypatch.setattr(tasks, 'set_status', lambda tid, status: {**next(i for i in items if i['id'] == tid),
                                                                    'status': status})
    return items


def test_external_doctor_sees_and_changes_only_tasks_of_own_patients(seeded, monkeypatch):
    fake_tasks(monkeypatch)
    session = MdtCase.objects.get(patient_fhir_id='P03').session
    client = external(session)
    assert [t['patient_id'] for t in client.get('/api/mdt/tasks/').json()] == ['P03']
    assert client.patch('/api/mdt/tasks/P03-mdt01-task01/', {'status': 'completed'}, format='json').status_code == 200
    assert client.patch('/api/mdt/tasks/P01-mdt01-task01/', {'status': 'completed'}, format='json').status_code == 403
    # interní lékař vidí všechny
    assert len(as_user('onkolog').get('/api/mdt/tasks/').json()) == 2


def test_external_doctor_cannot_change_someone_elses_task(seeded, monkeypatch):
    fake_tasks(monkeypatch, owner='LEK-JINY')
    client = external(MdtCase.objects.get(patient_fhir_id='P03').session)
    assert client.patch('/api/mdt/tasks/P03-mdt01-task01/', {'status': 'completed'}, format='json').status_code == 403


# ── živé zasedání: zahájení, ukončení, starý stav ──────────────────────────────
def test_projector_needs_explicit_start_and_close_clears_live(seeded):
    from apps.mdt.models import SessionPresence

    s = MdtSession.objects.get(title='Hrudní – karcinom plic')
    MdtSession.objects.filter(pk=s.pk).update(status='planned')
    case = s.cases.first()
    chair = as_user('predseda')
    url = f'/api/mdt/sessions/{s.pk}/live/'
    assert chair.put(url, {'case_id': case.pk}, format='json').status_code == 409        # otevření jednání nezahájí
    assert chair.patch(f'/api/mdt/sessions/{s.pk}/', {'status': 'in_progress'}, format='json').status_code == 200
    assert chair.put(url, {'case_id': case.pk}, format='json').json()['case']['id'] == case.pk
    as_user('chirurg').post(f'/api/mdt/sessions/{s.pk}/presence/')
    assert SessionPresence.objects.filter(session=s).exists()

    assert chair.patch(f'/api/mdt/sessions/{s.pk}/', {'status': 'closed'}, format='json').status_code == 200
    state = as_user('chirurg').get(url).json()
    assert (state['status'], state['case'], state['present']) == ('closed', None, [])


def test_live_state_goes_stale_and_repeated_put_keeps_it_fresh(seeded):
    from datetime import timedelta

    from django.utils import timezone

    from apps.mdt import live

    s = MdtSession.objects.get(title='Hrudní – karcinom plic')
    MdtSession.objects.filter(pk=s.pk).update(status='in_progress')
    case = s.cases.first()
    chair, url = as_user('predseda'), f'/api/mdt/sessions/{s.pk}/live/'
    chair.put(url, {'case_id': case.pk}, format='json')
    assert chair.get(url).json()['stale'] is False
    MdtSession.objects.filter(pk=s.pk).update(live_updated_at=timezone.now() - live.LIVE_STALE_AFTER - timedelta(1))
    assert chair.get(url).json()['stale'] is True
    chair.put(url, {'case_id': case.pk}, format='json')                                  # jednání stav opakuje
    assert chair.get(url).json()['stale'] is False


# ── osobní údaje v chatu a chatbotu ───────────────────────────────────────────
@pytest.mark.parametrize('text', ['Pacient 760104/0018 má progresi', 'nar. 4. 1. 1976', 'pište na jan@nemocnice.cz',
                                  'volejte 603 123 456'])
def test_chat_and_chatbot_refuse_personal_data(seeded, text):
    from apps.mdt.models import ChatbotMessage, SessionMessage

    s = MdtSession.objects.get(title='Hrudní – karcinom plic')
    doctor = as_user('onkolog')
    r = doctor.post(f'/api/mdt/sessions/{s.pk}/messages/', {'text': text}, format='json')
    assert r.status_code == 400 and 'osobní údaj' in str(r.json()['text'])
    assert doctor.post(f'/api/mdt/sessions/{s.pk}/chatbot/', {'text': text}, format='json').status_code == 400
    assert doctor.post('/api/mdt/patients/P03/chatbot/', {'text': text}, format='json').status_code == 400
    assert not SessionMessage.objects.exists() and not ChatbotMessage.objects.exists()


def test_chat_allows_ordinary_clinical_text(seeded):
    s = MdtSession.objects.get(title='Hrudní – karcinom plic')
    text = 'P03: CEA 12,4 µg/l, pokles o 30 % od 10/2026, ECOG 1, T2N1M0'
    assert as_user('onkolog').post(f'/api/mdt/sessions/{s.pk}/messages/', {'text': text},
                                   format='json').status_code == 201


# ── ochrana proti instrukcím v podkladech ─────────────────────────────────────
def test_every_provider_gets_untrusted_data_rule(monkeypatch):
    from services import ai_service

    seen = []

    class Spy(ai_service.MockAIProvider):
        def generate(self, prompt, system_prompt="", model=None, temperature=None, max_tokens=None,
                     response_schema=None):
            seen.append(system_prompt)
            return {'status': 'success'}

    Spy().generate('otázka', 'Jsi asistent MDT.')
    Spy().generate('otázka')
    assert ai_service.UNTRUSTED_DATA_RULE in seen[0] and seen[0].startswith('Jsi asistent MDT.')
    assert seen[1] == ai_service.UNTRUSTED_DATA_RULE
    assert ai_service.guard_system_prompt(seen[0]) == seen[0]          # nepřidá se dvakrát
    for cls in (ai_service.MockAIProvider, *[c for _, c in ai_service.PROVIDERS.values()]):
        assert getattr(cls.generate, '_guarded', False), cls


# ── RČ v návrhu pacienta šifrované ────────────────────────────────────────────
def test_draft_rc_is_encrypted_at_rest_and_searchable(db):
    from django.db import connection

    from apps.mdt.models import PatientDraft
    from core.crypto import digest

    d = PatientDraft.objects.create(patient_fhir_id='P99', rc='760104/0018')
    with connection.cursor() as cur:
        cur.execute('SELECT rc, rc_digest FROM mdt_patientdraft WHERE id = %s', [d.pk])
        raw, stored_digest = cur.fetchone()
    assert '760104' not in raw and raw.startswith('enc1:')
    assert PatientDraft.objects.get(pk=d.pk).rc == '760104/0018'
    assert PatientDraft.objects.filter(rc_digest=digest('760104/0018')).get().pk == d.pk == \
        PatientDraft.objects.get(rc_digest=stored_digest).pk
    d.rc = ''
    d.save(update_fields=['rc'])
    assert PatientDraft.objects.get(pk=d.pk).rc_digest == ''


def test_prune_access_log(db):
    from datetime import timedelta
    from io import StringIO

    from django.core.management import CommandError
    from django.utils import timezone

    from apps.mdt.models import AccessLog

    for age in (10, 400):
        log = AccessLog.objects.create(username='u', action='view', path='/x', method='GET', status_code=200)
        AccessLog.objects.filter(pk=log.pk).update(created_at=timezone.now() - timedelta(days=age))
    out = StringIO()
    call_command('prune_access_log', '--days', '365', '--dry-run', stdout=out)
    assert 'Smazalo by se 1' in out.getvalue() and AccessLog.objects.count() == 2
    call_command('prune_access_log', '--days', '365', stdout=StringIO())
    assert AccessLog.objects.count() == 1
    with pytest.raises(CommandError):
        call_command('prune_access_log', '--days', '5')
