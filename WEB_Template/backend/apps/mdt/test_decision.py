"""Závěr komise a zápis do IRIS (T-209) nad in-memory FHIR s datasetem a fixture decision_P03.json (T-009)."""
import json
import os
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.copilot import schemas
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


def test_export_fhir_document_and_pdf(case, decision):
    """T-210: document Bundle z IRIS + PDF; potvrzené PDF se uloží jako DocumentReference/P03-mdt02-pdf."""
    from services.ai.text import resource_text
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    assert as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/export.fhir.json').status_code == 409
    draft_pdf = as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/export.pdf')
    assert draft_pdf.status_code == 200 and draft_pdf.content.startswith(b'%PDF')
    assert not client.search('DocumentReference', _id='P03-mdt02-pdf')        # návrh se do IRIS nepíše

    as_user('predseda').post(f'/api/mdt/cases/{case.pk}/decision/confirm/')
    pdf = as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/export.pdf')
    assert pdf['Content-Disposition'] == 'attachment; filename="P03-mdt02.pdf"' and pdf.content.startswith(b'%PDF')
    doc = client.read('DocumentReference', 'P03-mdt02-pdf')
    assert doc['content'][0]['attachment']['contentType'] == 'application/pdf' and resource_text(doc) is None
    assert as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/decision/').json()['fhir_ids']['document_reference_pdf'] == 'P03-mdt02-pdf'

    r = as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/export.fhir.json')
    bundle = json.loads(r.content)
    assert r['Content-Type'] == 'application/fhir+json' and bundle['type'] == 'document'
    refs = [e['fullUrl'].split('/fhir/', 1)[1] for e in bundle['entry']]
    assert refs[0] == 'Composition/P03-mdt02'
    assert {'Patient/P03', 'Practitioner/LEK-P03-06', 'Observation/P03-neuro01', 'ResearchStudy/RKT-03',
            'DocumentReference/P03-mdt02-pdf', 'Provenance/P03-mdt02-prov'} <= set(refs)


def test_tasks_after_confirmation(case, decision):
    """T-511: po potvrzení P03 jsou jeho úkoly v přehledu, stav jde změnit (zapíše se do IRIS)."""
    assert as_user('chirurg').get('/api/mdt/tasks/').json() == []
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    as_user('predseda').post(f'/api/mdt/cases/{case.pk}/decision/confirm/')
    items = as_user('chirurg').get('/api/mdt/tasks/').json()
    [schemas.MdtTask.model_validate(t) for t in items]
    assert [t['id'] for t in items] == ['P03-mdt02-task01', 'P03-mdt02-task03', 'P03-mdt02-task02', 'P03-mdt02-task04']
    first = items[0]
    assert first['case_id'] == case.pk and first['mdt_record'] == 'P03-mdt02' and first['due_date'] == '2026-10-28'
    assert first['owner']['id'] == 'LEK-P03-01' and first['owner']['name'].startswith('LEK-P03-01')
    assert first['re_mdt']['date'] == '2026-11-04'

    assert as_user('radiolog').patch('/api/mdt/tasks/P03-mdt02-task01/', {'status': 'completed'}, format='json').status_code == 403
    assert as_user('onkolog').patch('/api/mdt/tasks/P03-mdt02-task01/', {'status': 'hotovo'}, format='json').status_code == 400
    done = as_user('onkolog').patch('/api/mdt/tasks/P03-mdt02-task01/', {'status': 'completed'}, format='json').json()
    assert done['status'] == 'completed' and client.read('Task', 'P03-mdt02-task01')['status'] == 'completed'
    assert [t['id'] for t in as_user('chirurg').get('/api/mdt/tasks/?status=completed').json()] == ['P03-mdt02-task01']
    assert as_user('chirurg').get('/api/mdt/tasks/?status=x').status_code == 400
    assert as_user('chirurg').get('/api/mdt/tasks/?patient=P04').json() == []
    assert as_user('onkolog').patch('/api/mdt/tasks/P03-zad01-task/', {'status': 'completed'}, format='json').status_code == 400


def test_decision_only_by_creator_collaborator_or_chair(case, decision):
    """T-326: závěr upravuje zadávající lékař (P03 = onkolog), přizvaný lékař nebo předseda, ne jiný lékař."""
    from django.contrib.auth import get_user_model
    url = f'/api/mdt/cases/{case.pk}/decision/'
    assert as_user('pneumolog').put(url, decision, format='json').status_code == 403
    assert as_user('pneumolog').post(f'/api/mdt/cases/{case.pk}/brief/', {}, format='json').status_code == 403
    pneumolog = get_user_model().objects.get(username='pneumolog')
    r = as_user('onkolog').patch(f'/api/mdt/cases/{case.pk}/', {'collaborators': [pneumolog.pk]}, format='json')
    assert r.status_code == 200, r.json()
    assert as_user('pneumolog').put(url, decision, format='json').status_code == 200


def test_guideline_deviation_needs_reason(case, decision):
    """Zadání B2 a C: zvolený postup s „pozor“ / „vylučuje“ nebo „není v souladu“ chce zdůvodnění; zápis do Composition a PDF."""
    url = f'/api/mdt/cases/{case.pk}/decision/'
    sections = {**decision['sections'],
                'options_considered': [
                    {'id': 'krc-resekce', 'title': 'Resekce jaterních metastáz', 'light': 'orange', 'chosen': True},
                    {'id': 'krc-anti-egfr', 'title': 'Anti-EGFR', 'light': 'red', 'chosen': False}],
                'dissent': [{'member': 'LEK-P03-03', 'role': 'surgeon', 'text': 'Preferuje nejdřív konverzní chemoterapii.'}]}
    assert as_user('predseda').put(url, {**decision, 'sections': sections}, format='json').status_code == 200
    r = as_user('predseda').post(f'{url}confirm/')
    assert r.status_code == 400 and r.json()['field'] == 'guideline_compliance' and 'Resekce' in r.json()['detail']

    sections['guideline_compliance'] = {'compliant': False, 'reason': ' ', 'citations': ['KRC-2.1']}
    as_user('predseda').put(url, {**decision, 'sections': sections}, format='json')
    assert as_user('predseda').post(f'{url}confirm/').status_code == 400

    sections['guideline_compliance']['reason'] = 'FLR 38 % jen po dvoudobém výkonu, HPB chirurg souhlasí.'
    as_user('predseda').put(url, {**decision, 'sections': sections}, format='json')
    r = as_user('predseda').post(f'{url}confirm/')
    assert r.status_code == 200, r.json()
    titles = {s['title']: s['text']['div'] for s in client.read('Composition', 'P03-mdt02')['section']}
    assert 'zvoleno' in titles['Zvažované možnosti'] and 'pozor' in titles['Zvažované možnosti']
    assert 'Ne. Zdůvodnění: FLR 38 %' in titles['Soulad s doporučenými postupy'] and 'KRC-2.1' in titles['Soulad s doporučenými postupy']
    assert 'LEK-P03-03 (chirurg)' in titles['Odlišná stanoviska']
    assert as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/export.pdf').content.startswith(b'%PDF')


def test_guideline_deviation_rule():
    from services.fhir.writeback import guideline_deviation
    assert guideline_deviation({}) is None
    assert guideline_deviation({'options_considered': [{'id': 'a', 'title': 'A', 'light': 'green', 'chosen': True}]}) is None
    assert guideline_deviation({'options_considered': [{'id': 'a', 'title': 'A', 'light': 'red', 'chosen': False}]}) is None
    assert 'A' in guideline_deviation({'options_considered': [{'id': 'a', 'title': 'A', 'light': 'red', 'chosen': True}]})
    assert guideline_deviation({'guideline_compliance': {'compliant': False, 'reason': ''}})
    assert guideline_deviation({'guideline_compliance': {'compliant': True, 'reason': ''}}) is None
