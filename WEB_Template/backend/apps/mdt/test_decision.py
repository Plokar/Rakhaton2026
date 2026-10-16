"""Závěr komise a zápis do IRIS (T-209) nad in-memory FHIR s datasetem a fixture decision_P03.json (T-009)."""
import json
import os
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.mdt.models import MdtCase
from apps.mdt.test_roles import as_user
from services.fhir import client

pytestmark = pytest.mark.django_db
_REPO = next((p for p in Path(__file__).resolve().parents if (p / 'WEB_Template').is_dir()), None)
FIXTURES = Path(os.environ.get('FIXTURES_DIR') or (_REPO / 'data' / 'fixtures' if _REPO else '/nonexistent'))


@pytest.fixture
def decision():
    path = FIXTURES / 'decision_P03.json'
    if not path.is_file():
        pytest.skip('chybí data/fixtures/decision_P03.json')
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.fixture
def case(fake_fhir_dataset):
    call_command('seed_mdt')
    client.put({'resourceType': 'Device', 'id': 'mdt-copilot', 'deviceName': [{'name': 'MDT Copilot', 'type': 'user-friendly-name'}]})
    return MdtCase.objects.get(patient_fhir_id='P03')


def test_draft_validated_and_saved(case, decision):
    url = f'/api/mdt/cases/{case.pk}/decision/'
    assert as_user('predseda').get(url).status_code == 404
    assert as_user('radiolog').put(url, decision, format='json').status_code == 403
    bad = {**decision, 'sections': {**decision['sections'], 'intent': 'nevim'}}
    assert as_user('predseda').put(url, bad, format='json').status_code == 400
    saved = as_user('onkolog').put(url, decision, format='json').json()
    assert saved['case_id'] == str(case.pk) and saved['status'] == 'draft'
    assert as_user('chirurg').get(url).json()['sections']['intent'] == 'kurativni'


def test_confirm_writes_mdt02_to_iris(case, decision):
    """DoD: po potvrzení P03 je v IRIS Composition/P03-mdt02 s vazbami a fhir_ids v Decision."""
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    assert as_user('onkolog').post(f'/api/mdt/cases/{case.pk}/decision/confirm/').status_code == 403
    r = as_user('predseda').post(f'/api/mdt/cases/{case.pk}/decision/confirm/')
    assert r.status_code == 200, r.json()
    d = r.json()
    ids = d['fhir_ids']
    assert d['status'] == 'confirmed' and d['confirmed_by']['name']
    assert ids['composition'] == 'P03-mdt02' and ids['tasks'] == [f'P03-mdt02-task0{i}' for i in range(1, 5)]
    assert ids['detected_issues'] == ['P03-mdt02-rf01', 'P03-mdt02-rf02', 'P03-mdt02-rf03']
    assert ids['research_subjects'] == ['P03-mdt02-rs01', 'P03-mdt02-rs02']

    comp = client.read('Composition', 'P03-mdt02')
    assert [s['title'] for s in comp['section']][:4] == ['Projednaná otázka', 'Klinické zhodnocení', 'Léčebný záměr', 'Doporučený postup']
    assert comp['section'][-1]['title'] == 'Varovné signály' and comp['meta']['security'][0]['code'] == 'AIAST'
    assert comp['event'][0]['detail'] == [{'reference': 'CarePlan/P03-mdt02-careplan'}, {'reference': 'CareTeam/P03-mdt02-careteam'}]
    assert {'reference': 'Observation/P03-neuro01'} in comp['section'][1]['entry']
    plan = client.read('CarePlan', 'P03-mdt02-careplan')
    assert plan['category'][0]['coding'][0]['code'] == 'kurativni' and len(plan['activity']) == 3   # 2 postupy + re-MDT
    assert client.read('Task', 'P03-mdt02-task02')['owner'] == {'reference': 'Practitioner/LEK-P03-03'}
    nomination = client.read('Task', 'P03-zad01-task')
    assert nomination['businessStatus']['coding'][0]['code'] == 'projednana' and nomination['status'] == 'completed'
    assert client.read('ServiceRequest', 'P03-zad01')['status'] == 'completed'
    prov = client.read('Provenance', 'P03-mdt02-prov')
    assert {'reference': 'Composition/P03-mdt02'} in prov['target']
    assert prov['agent'][0]['who'] == {'reference': 'Device/mdt-copilot'}
    assert MdtCase.objects.get(pk=case.pk).status == 'confirmed'

    assert as_user('predseda').post(f'/api/mdt/cases/{case.pk}/decision/confirm/').status_code == 409
    assert as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json').status_code == 409


def test_next_number_after_existing(case, decision):
    """P05 má mdt01 a mdt02 → další je mdt03."""
    from services.fhir.writeback import next_mdt_id
    assert next_mdt_id('P05') == 'P05-mdt03' and next_mdt_id('P03') == 'P03-mdt02'
