"""Role a boardy (T-501): oprávnění podle ARCH §6.3, přesun případu zapíše termín do Task v IRIS."""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.mdt.models import MdtCase, MdtSession
from services.fhir import writeback

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')


def as_user(username):
    from django.contrib.auth import get_user_model
    client = APIClient()
    client.force_authenticate(get_user_model().objects.get(username=username))
    return client


def test_demo_users_roles_and_me(seeded):
    me = as_user('predseda').get('/api/mdt/me/').json()
    assert (me['role'], me['specialty']) == ('mdt_admin', 'oncologist')
    assert as_user('pneumolog').get('/api/mdt/me/').json()['role'] == 'mdt_doctor'
    assert as_user('chirurg').get('/api/mdt/me/').json() | {'user_id': 0} == {
        'user_id': 0, 'username': 'chirurg', 'name': 'Chirurg', 'role': 'mdt_viewer', 'specialty': 'surgeon'}
    assert MdtCase.objects.get(patient_fhir_id='P04').created_by.username == 'pneumolog'
    assert MdtSession.objects.filter(chair__username='predseda').count() == 4


def test_seed_backfills_requester_and_chair(seeded):
    MdtCase.objects.update(created_by=None)
    MdtSession.objects.update(chair=None)
    call_command('seed_mdt')
    assert not MdtCase.objects.filter(created_by__isnull=True).exists()
    assert MdtCase.objects.get(patient_fhir_id='P04').created_by.username == 'pneumolog'
    assert not MdtSession.objects.filter(chair__isnull=True).exists()


def test_only_chair_manages_boards(seeded):
    new = {'date': '2026-10-28T14:00:00+01:00', 'title': 'Mamární komise'}
    for user in ('onkolog', 'chirurg'):
        assert as_user(user).post('/api/mdt/sessions/', new, format='json').status_code == 403
    created = as_user('predseda').post('/api/mdt/sessions/', new, format='json')
    assert created.status_code == 201 and created.json()['date'] == '2026-10-28T14:00:00+01:00'
    sid = created.json()['id']
    assert as_user('onkolog').patch(f'/api/mdt/sessions/{sid}/', {'title': 'x'}, format='json').status_code == 403
    assert as_user('predseda').delete(f'/api/mdt/sessions/{sid}/').status_code == 204
    full = MdtSession.objects.get(title='Hrudní – karcinom plic').pk
    assert as_user('predseda').delete(f'/api/mdt/sessions/{full}/').status_code == 409


def test_move_case_updates_task_in_iris(seeded):
    """DoD: přesun P01 na jiný board změní datum v Task."""
    target = MdtSession.objects.get(title='Mamární komise (urgentní)')
    case = MdtCase.objects.get(patient_fhir_id='P01')
    r = as_user('onkolog').patch(f'/api/mdt/cases/{case.pk}/', {'session': target.pk}, format='json')
    assert r.status_code == 200 and r.json()['session'] == target.pk
    task = writeback.nomination_task('P01', 'P01-zad01')
    assert task['restriction']['period']['start'] == '2026-10-14T14:00:00+02:00'


def test_closed_board_rejects_move_and_intake(seeded):
    """Na uzavřený board nejde pacienta přesunout ani zařadit (409, T-518); úpravy v něm ano."""
    closed = MdtSession.objects.get(title='Mamární komise (urgentní)')
    closed.status = 'closed'
    closed.save()
    case = MdtCase.objects.get(patient_fhir_id='P01')
    assert as_user('onkolog').patch(f'/api/mdt/cases/{case.pk}/', {'session': closed.pk}, format='json').status_code == 409
    body = {'session': closed.pk, 'patient_id': 'P01', 'ecog': 1, 'intent': 'C', 'skipped_fields': []}
    assert as_user('onkolog').post('/api/mdt/cases/', body, format='json').status_code == 409
    p02 = MdtCase.objects.get(patient_fhir_id='P02')        # už na uzavřeném boardu
    assert as_user('predseda').patch(f'/api/mdt/cases/{p02.pk}/', {'session': closed.pk, 'ecog': 1},
                                     format='json').status_code == 200


def test_case_edit_permissions(seeded):
    p04 = MdtCase.objects.get(patient_fhir_id='P04')       # zadal pneumolog
    assert as_user('onkolog').patch(f'/api/mdt/cases/{p04.pk}/', {'ecog': 1}, format='json').status_code == 403
    assert as_user('chirurg').patch(f'/api/mdt/cases/{p04.pk}/', {'ecog': 1}, format='json').status_code == 403
    assert as_user('pneumolog').patch(f'/api/mdt/cases/{p04.pk}/', {'ecog': 1, 'intent': 'C'},
                                      format='json').json()['ecog'] == 1
    assert as_user('predseda').patch(f'/api/mdt/cases/{p04.pk}/', {'ecog': 7}, format='json').status_code == 400


def test_acknowledged_warnings_are_only_appended(seeded):
    case = MdtCase.objects.get(patient_fhir_id='P03')
    client = as_user('onkolog')
    client.patch(f'/api/mdt/cases/{case.pk}/', {'acknowledge': ['RF-ECOG:P03-ecog03']}, format='json')
    data = client.patch(f'/api/mdt/cases/{case.pk}/', {'acknowledge': ['RF-ECOG:P03-ecog03', 'RF-TOX:P03-neuro01']},
                        format='json').json()
    assert [w['id'] for w in data['acknowledged_warnings']] == ['RF-ECOG:P03-ecog03', 'RF-TOX:P03-neuro01']
    assert data['acknowledged_warnings'][0]['by'] == case.created_by_id


def test_viewer_cannot_generate_brief(seeded):
    case = MdtCase.objects.get(patient_fhir_id='P03')
    assert as_user('radiolog').post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json').status_code == 403
