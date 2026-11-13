"""T-349: kontrola před zasedáním přes API (stav, potvrzení, moje kontroly pro upozornění)."""
import pytest
from django.utils import timezone

from apps.mdt.models import MdtCase
from apps.mdt.test_roles import as_user, seeded  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


def _soon(case: MdtCase, hours: int = 24) -> MdtCase:
    case.session.date = timezone.now() + timezone.timedelta(hours=hours)
    case.session.save(update_fields=['date'])
    return case


def test_review_state_and_check_by_requester(seeded):  # noqa: F811
    p04 = _soon(MdtCase.objects.select_related('session').get(patient_fhir_id='P04'))      # zadal pneumolog
    url = f'/api/mdt/cases/{p04.pk}/review/'
    r = as_user('chirurg').get(url).json()
    assert (r['status'], r['can_check']) == ('due', False) and r['since']
    assert as_user('chirurg').post(url).status_code == 403
    r = as_user('pneumolog').post(url).json()
    assert (r['status'], r['checked_by']['name']) == ('checked', 'Pneumolog')
    agenda = as_user('chirurg').get(f'/api/mdt/sessions/{p04.session_id}/').json()
    assert next(c for c in agenda['cases'] if c['id'] == p04.pk)['checked_at']


def test_missed_when_meeting_started_without_check(seeded):  # noqa: F811
    p03 = _soon(MdtCase.objects.select_related('session').get(patient_fhir_id='P03'), hours=-1)
    assert as_user('chirurg').get(f'/api/mdt/cases/{p03.pk}/review/').json()['status'] == 'missed'


def test_my_reviews_only_due_and_mine(seeded):  # noqa: F811
    p04 = _soon(MdtCase.objects.select_related('session').get(patient_fhir_id='P04'))
    _soon(MdtCase.objects.select_related('session').get(patient_fhir_id='P03'), hours=24 * 5)   # mimo okno
    mine = as_user('pneumolog').get('/api/mdt/reviews/').json()
    assert [(r['case_id'], r['patient_id'], r['status']) for r in mine] == [(p04.pk, 'P04', 'due')]
    assert mine[0]['session']['title'] and mine[0]['display_name'].startswith('P04')
    assert as_user('onkolog').get('/api/mdt/reviews/').json() == []          # P04 nezadával
    assert [r['patient_id'] for r in as_user('predseda').get('/api/mdt/reviews/?all=1').json()] == ['P04']
    as_user('pneumolog').post(f'/api/mdt/cases/{p04.pk}/review/')
    assert as_user('pneumolog').get('/api/mdt/reviews/').json() == []
