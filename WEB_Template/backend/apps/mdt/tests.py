"""seed_mdt a čtení boardů nad in-memory FHIR s celým datasetem (T-109)."""
import pytest
from django.core.management import call_command

from apps.mdt.models import MdtCase, MdtSession

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')


def test_seed_creates_four_boards_from_nominations(seeded):
    boards = {(f'{s.date:%m-%d}', s.title): sorted(s.cases.values_list('patient_fhir_id', flat=True))
              for s in MdtSession.objects.all()}
    assert boards == {
        ('10-14', 'Mamární komise (urgentní)'): ['P02'],
        ('10-21', 'Mamární komise'): ['P01', 'P05', 'P06'],
        ('10-21', 'GIT – kolorektální karcinom / hepatobiliární'): ['P03'],
        ('10-21', 'Hrudní – karcinom plic'): ['P04'],
    }
    p03 = MdtCase.objects.get(patient_fhir_id='P03')
    assert p03.service_request_fhir_id == 'P03-zad01' and 'resekabilní' in p03.question


def test_seed_is_idempotent_and_keeps_moved_case(seeded):
    case = MdtCase.objects.get(patient_fhir_id='P01')
    case.session = MdtSession.objects.get(title='Hrudní – karcinom plic')
    case.save()
    call_command('seed_mdt')
    assert (MdtSession.objects.count(), MdtCase.objects.count()) == (4, 6)
    assert MdtCase.objects.get(patient_fhir_id='P01').session.title == 'Hrudní – karcinom plic'


def test_sessions_api_with_agenda(authenticated_client, seeded):
    sessions = authenticated_client.get('/api/mdt/sessions/').json()
    assert sessions[0]['patients'] == ['P02'] and sessions[0]['date'] == '2026-10-14T14:00:00+02:00'
    breast = next(s for s in sessions if s['title'] == 'Mamární komise')
    detail = authenticated_client.get(f"/api/mdt/sessions/{breast['id']}/").json()
    assert [c['patient_id'] for c in detail['cases']] == ['P01', 'P05', 'P06']
    assert detail['cases'][0]['patient']['display_name'] == 'P01 · žena · 63 let'
    assert detail['cases'][0]['status'] == 'nominated'


def test_sessions_require_login(api_client):
    assert api_client.get('/api/mdt/sessions/').status_code in (401, 403)
