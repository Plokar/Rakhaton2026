"""Lékaři nemocnice z IRIS a „moje úkoly“ (T-328)."""
import pytest
from django.contrib.auth import get_user_model

from apps.copilot import schemas
from apps.mdt.test_decision import case, decision  # noqa: F401  (fixture)
from apps.mdt.test_roles import as_user
from services.fhir import client

pytestmark = pytest.mark.django_db


def _with_tasks(decision, owner='LEK-APP-chirurg', name='Chirurg'):
    tasks = [{**decision['tasks'][0], 'id': 'task01', 'owner': owner, 'owner_name': name, 'description': 'MR jater'},
             {**decision['tasks'][1], 'id': 'task02', 'owner': 'LEK-P03-01', 'owner_name': None}]
    attendees = [{'user_id': 'LEK-APP-predseda', 'name': 'Předseda komise (klinický onkolog)', 'role': 'chair'},
                 {'user_id': 'LEK-APP-chirurg', 'name': 'Chirurg', 'role': 'surgeon'}]
    return {**decision, 'tasks': tasks, 'attendees': attendees}


def test_demo_accounts_are_doctors_in_iris(case):
    me = schemas.Me.model_validate(as_user('onkolog').get('/api/mdt/me/').json())
    assert me.practitioner_id == 'LEK-APP-onkolog'
    p = client.read('Practitioner', 'LEK-APP-onkolog')
    assert p['name'][0]['text'] == 'Klinický onkolog' and p['qualification'][0]['code']['text'] == 'klinický onkolog'


def test_directory_search(case):
    everyone = as_user('chirurg').get('/api/mdt/practitioners/?limit=500').json()
    assert len(everyone) == 57 + 7 and everyone[0]['user'] is not None          # lékaři s účtem nahoře
    found = as_user('chirurg').get('/api/mdt/practitioners/?q=radiacni onkolog').json()  # bez diakritiky
    assert found and all(x['role'] == 'radiation_oncologist' for x in found)
    assert {x['id'] for x in found} >= {'LEK-APP-radioterapeut', 'LEK-P01-07'}
    patolog = as_user('chirurg').get('/api/mdt/practitioners/?q=patolog&with_user=1').json()
    assert [x['id'] for x in patolog] == ['LEK-APP-patolog'] and patolog[0]['user']['username'] == 'patolog'


def test_assigned_task_is_visible_to_its_doctor(case, decision):
    url = f'/api/mdt/cases/{case.pk}/decision/'
    assert as_user('onkolog').put(url, _with_tasks(decision), format='json').status_code == 200
    drafts = as_user('chirurg').get('/api/mdt/tasks/?mine=1&drafts=1').json()
    assert [(t['description'], t['draft']) for t in drafts] == [('MR jater', True)]   # před potvrzením jako návrh
    for t in drafts:
        schemas.MdtTask.model_validate(t)
    assert as_user('chirurg').get('/api/mdt/tasks/?mine=1').json() == []          # oficiální jen po potvrzení

    assert as_user('predseda').post(f'{url}confirm/').status_code == 200
    task = client.read('Task', 'P03-mdt02-task01')
    assert task['owner'] == {'reference': 'Practitioner/LEK-APP-chirurg', 'display': 'Chirurg'}
    team = client.read('CareTeam', 'P03-mdt02-careteam')
    assert {'reference': 'Practitioner/LEK-APP-chirurg', 'display': 'Chirurg'} in [p['member'] for p in team['participant']]

    mine = as_user('chirurg').get('/api/mdt/tasks/?mine=1&patient=P03').json()
    assert [t['id'] for t in mine] == ['P03-mdt02-task01'] and mine[0]['owner']['name'] == 'Chirurg'
    assert mine[0]['case_id'] == case.pk and not mine[0]['draft']
    # prohlížející člen komise smí odškrtnout jen svůj úkol
    assert as_user('chirurg').patch('/api/mdt/tasks/P03-mdt02-task01/', {'status': 'completed'},
                                    format='json').status_code == 200
    assert as_user('chirurg').patch('/api/mdt/tasks/P03-mdt02-task02/', {'status': 'completed'},
                                    format='json').status_code == 403
    assert as_user('radiolog').get('/api/mdt/tasks/?mine=1').json() == []


def test_chair_links_account_to_hospital_doctor(case):
    onkolog = get_user_model().objects.get(username='onkolog')
    url = f'/api/mdt/users/{onkolog.pk}/'
    r = as_user('predseda').patch(url, {'practitioner_id': 'LEK-P03-01'}, format='json')
    assert r.status_code == 200 and r.json()['practitioner_id'] == 'LEK-P03-01'
    assert as_user('predseda').patch(url, {'practitioner_id': 'LEK-NEEXISTUJE'}, format='json').status_code == 400
    chirurg = get_user_model().objects.get(username='chirurg')
    taken = as_user('predseda').patch(f'/api/mdt/users/{chirurg.pk}/', {'practitioner_id': 'LEK-P03-01'}, format='json')
    assert taken.status_code == 400
    assert as_user('onkolog').patch(url, {'practitioner_id': 'LEK-P03-02'}, format='json').status_code == 403
