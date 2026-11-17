"""Živé zasedání (T-380): další na řadě, odhad konce, přítomní s lékařem v IRIS."""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.mdt.models import MdtCase, MdtSession, UserProfile

pytestmark = pytest.mark.django_db


@pytest.fixture
def board(fake_fhir_dataset, monkeypatch):
    call_command('seed_mdt')
    cache.clear()
    monkeypatch.setenv('MDT_MINUTES_PER_CASE', '10')
    s = MdtSession.objects.get(title='Mamární komise')                  # P01, P05, P06
    MdtSession.objects.filter(pk=s.pk).update(status='in_progress')
    s.refresh_from_db()
    return s


def as_user(username):
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def test_next_case_skips_decided_and_estimate_counts_remaining(board):
    first, second, third = board.cases.all()
    chair, url = as_user('predseda'), f'/api/mdt/sessions/{board.pk}/live/'
    state = chair.get(url).json()
    assert state['next']['id'] == first.pk                                    # bez projektoru první neprojednaný
    assert state['estimate']['remaining'] == 3 and state['estimate']['minutes_per_case'] == 10

    MdtCase.objects.filter(pk=second.pk).update(status='decided')
    state = chair.put(url, {'case_id': first.pk}, format='json').json()
    assert state['next'] == {'id': third.pk, 'patient_id': third.patient_fhir_id}   # projednaného přeskočí
    end = timezone.datetime.fromisoformat(state['estimate']['end'])
    assert timedelta(minutes=19) < end - timezone.now() <= timedelta(minutes=20)     # zbytek prvního + třetí
    assert state['estimate']['remaining'] == 2 and state['estimate']['over'] is False

    MdtSession.objects.filter(pk=board.pk).update(live_case_since=timezone.now() - timedelta(minutes=12))
    state = chair.get(url).json()
    assert state['estimate']['over'] is True                                  # přes plánovaný čas na pacienta
    assert timezone.datetime.fromisoformat(state['estimate']['end']) - timezone.now() <= timedelta(minutes=10)

    state = chair.put(url, {'case_id': third.pk}, format='json').json()
    assert state['next'] is None and state['case']['since']                   # poslední, čas běží znovu


def test_case_since_only_changes_with_patient(board):
    first = board.cases.first()
    chair, url = as_user('predseda'), f'/api/mdt/sessions/{board.pk}/live/'
    since = chair.put(url, {'case_id': first.pk}, format='json').json()['case']['since']
    later = chair.put(url, {'case_id': first.pk, 'slide': {'index': 1, 'total': 2}}, format='json').json()
    assert later['case']['since'] == since                                    # jiný slide = stejný pacient


def test_present_carries_practitioner_for_decision(board):
    user = get_user_model().objects.get(username='chirurg')
    UserProfile.objects.filter(user=user).update(practitioner_fhir_id='LEK-CHIR-01')
    present = as_user('chirurg').post(f'/api/mdt/sessions/{board.pk}/presence/').json()['present']
    assert present == [{'user_id': user.pk, 'name': 'Chirurg', 'specialty': 'surgeon', 'practitioner_id': 'LEK-CHIR-01'}]
