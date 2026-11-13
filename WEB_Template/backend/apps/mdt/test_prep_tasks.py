"""T-350: chybějící údaj nebo varování „do mých úkolů“ při zařazení → FHIR Task v IRIS, vidět v Moje úkoly."""
import pytest

from apps.mdt.models import MdtCase, MdtSession
from apps.mdt.test_roles import as_user, resolved_intake, seeded  # noqa: F401  (fixture)

pytestmark = pytest.mark.django_db


def test_missing_field_and_warning_to_my_tasks(seeded, fake_fhir):  # noqa: F811
    board = MdtSession.objects.get(title='Hrudní – karcinom plic')
    resolved = resolved_intake('P04', 'pneumolog')
    field, warning = resolved['skipped_fields'][0], resolved['acknowledge'][0]
    body = {'session': board.pk, 'patient_id': 'P04', 'ecog': 1, 'intent': 'C', 'imaging_recent_checked': True,
            'skipped_fields': [f for f in resolved['skipped_fields'] if f != field],
            'acknowledge': [w for w in resolved['acknowledge'] if w != warning], 'prep_tasks': [field, warning]}
    client = as_user('pneumolog')
    r = client.post('/api/mdt/cases/', body, format='json')
    assert r.status_code in (200, 201), r.json()
    assert {'Task/P04-zad01-prep01', 'Task/P04-zad01-prep02'} <= set(r.json()['fhir_written'])
    assert field in r.json()['skipped_fields']               # v podkladu „Chybí (přeskočeno lékařem)“ (D-019)
    task = fake_fhir.store['Task/P04-zad01-prep01']
    assert task['description'].startswith('Doplnit před MDT: ') and task['owner']['reference'].startswith('Practitioner/')
    assert task['restriction']['period']['end'].startswith(board.date.date().isoformat()[:4])
    mine = client.get('/api/mdt/tasks/?mine=1').json()
    prep = [t for t in mine if t['id'].startswith('P04-zad01-prep')]
    assert len(prep) == 2 and all(t['case_id'] == MdtCase.objects.get(patient_fhir_id='P04').pk for t in prep)
    assert prep[0]['mdt_record'] is None and prep[0]['status'] == 'requested'
    # opakované zařazení stejné úkoly nezaloží podruhé
    client.post('/api/mdt/cases/', body, format='json')
    assert len([k for k in fake_fhir.store if k.startswith('Task/P04-zad01-prep')]) == 2
    assert client.patch(f'/api/mdt/tasks/{prep[0]["id"]}/', {'status': 'completed'}, format='json').status_code == 200


def test_prep_tasks_validation(seeded):  # noqa: F811
    board = MdtSession.objects.get(title='Hrudní – karcinom plic')
    body = {'session': board.pk, 'patient_id': 'P04', 'ecog': 1, 'intent': 'C', 'imaging_recent_checked': True,
            **resolved_intake('P04', 'pneumolog'), 'prep_tasks': ['neexistuje']}
    assert as_user('pneumolog').post('/api/mdt/cases/', body, format='json').status_code == 400
