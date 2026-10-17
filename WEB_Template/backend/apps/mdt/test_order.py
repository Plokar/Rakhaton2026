"""Pořadí pacientů na boardu (T-324): mění jen předseda, přesun na jiný board zařadí případ na konec."""
import pytest
from django.core.management import call_command

from apps.mdt.models import MdtCase, MdtSession
from apps.mdt.test_roles import as_user

pytestmark = pytest.mark.django_db


@pytest.fixture
def board(fake_fhir_dataset):
    call_command('seed_mdt')
    return MdtSession.objects.get(title='Mamární komise')          # P01, P05, P06


def _agenda(board) -> list[str]:
    return [c['patient_id'] for c in as_user('chirurg').get(f'/api/mdt/sessions/{board.pk}/').json()['cases']]


def test_chair_reorders_agenda(board):
    assert _agenda(board) == ['P01', 'P05', 'P06']
    ids = {c.patient_fhir_id: c.pk for c in board.cases.all()}
    r = as_user('predseda').put(f'/api/mdt/sessions/{board.pk}/order/', {'cases': [ids['P06'], ids['P01'], ids['P05']]},
                                format='json')
    assert r.status_code == 200, r.json()
    assert [c['patient_id'] for c in r.json()['cases']] == ['P06', 'P01', 'P05'] == _agenda(board)


def test_only_chair_and_complete_list(board):
    ids = list(board.cases.values_list('pk', flat=True))
    url = f'/api/mdt/sessions/{board.pk}/order/'
    assert as_user('onkolog').put(url, {'cases': ids[::-1]}, format='json').status_code == 403
    assert as_user('predseda').put(url, {'cases': ids[:2]}, format='json').status_code == 400        # chybí případ
    assert as_user('predseda').put(url, {'cases': ids + ids[:1]}, format='json').status_code == 400  # duplicita
    other = MdtCase.objects.exclude(session=board).first().pk
    assert as_user('predseda').put(url, {'cases': ids[:2] + [other]}, format='json').status_code == 400


def test_moved_case_goes_to_end(board):
    p03 = MdtCase.objects.get(patient_fhir_id='P03')
    r = as_user('predseda').patch(f'/api/mdt/cases/{p03.pk}/', {'session': board.pk}, format='json')
    assert r.status_code == 200, r.json()
    assert _agenda(board) == ['P01', 'P05', 'P06', 'P03']


def test_calendar_sessions_with_case_summaries(board):
    """T-518: `?from&to&expand=cases` → zasedání v rozsahu s `MdtCaseSummary` (hlavička, ECOG, záměr, připravenost)."""
    from apps.copilot import schemas
    r = as_user('chirurg').get('/api/mdt/sessions/?from=2026-10-20&to=2026-10-25&expand=cases')
    assert r.status_code == 200
    sessions = r.json()
    assert {s['title'] for s in sessions} >= {'Mamární komise'} and all(s['date'] >= '2026-10-20' for s in sessions)
    assert not any('urgentní' in s['title'] for s in sessions)                 # 14. 10. je mimo rozsah
    mamarni = next(s for s in sessions if s['title'] == 'Mamární komise')
    for c in mamarni['cases']:
        schemas.MdtCaseSummary.model_validate(c)
    p01 = mamarni['cases'][0]
    assert p01['patient_id'] == 'P01' and p01['display_name'].startswith('P01 · žena')
    assert p01['diagnosis']['icd10'].startswith('C50') and 0 < p01['readiness'] <= 1
    assert 'cases' not in as_user('chirurg').get('/api/mdt/sessions/').json()[0]     # bez expand beze změny
    assert as_user('chirurg').get('/api/mdt/sessions/?from=21.10.').status_code == 400
