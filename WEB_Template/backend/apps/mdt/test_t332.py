"""T-332: katalog pravidel, podobné případy, otázka nad případem, zpráva pro praktického lékaře, verze závěru."""
import json

import pytest

from apps.copilot import schemas
from apps.mdt.models import MdtCase
from apps.mdt.test_decision import case, decision  # noqa: F401  (fixtures)
from apps.mdt.test_roles import as_user
from services.fhir import client

pytestmark = pytest.mark.django_db


@pytest.fixture
def confirmed(case, decision, settings):  # noqa: F811
    settings.MDT_JOBS_SYNC = True
    as_user('predseda').put(f'/api/mdt/cases/{case.pk}/decision/', decision, format='json')
    r = as_user('predseda').post(f'/api/mdt/cases/{case.pk}/decision/confirm/')
    assert r.status_code == 200, r.json()
    return case


def test_rule_catalog_and_disabled_rules_in_config(case):  # noqa: F811
    rules = as_user('chirurg').get('/api/mdt/rules/').json()
    ids = {r['id'] for r in rules}
    assert {'RF-ECOG', 'RF-TOX', 'RF-LLM'} <= ids and all(r['title'] for r in rules)
    base = {'name': 'Bez geriatrie', 'sections': [{'id': 'summary', 'enabled': True, 'order': 0}],
            'roles_present': ['oncologist'], 'detail_level': 'brief', 'language': 'cs', 'hide_unverified': False}
    assert as_user('predseda').post('/api/mdt/configs/', {**base, 'disabled_rules': ['RF-XYZ']}, format='json').status_code == 400
    r = as_user('predseda').post('/api/mdt/configs/', {**base, 'disabled_rules': ['RF-GERI', 'RF-GERI']}, format='json')
    assert r.status_code == 201, r.json()
    assert r.json()['disabled_rules'] == ['RF-GERI']


def test_similar_cases_same_diagnosis_anonymized(case):  # noqa: F811
    p05 = MdtCase.objects.get(patient_fhir_id='P05')
    out = as_user('chirurg').get(f'/api/mdt/cases/{p05.pk}/similar/').json()
    assert out['diagnosis']['icd10'] == 'C50.4' and out['cases']
    first = out['cases'][0]
    assert first['match'] == 'code' and first['citations'] == [first['composition_id']]
    assert not first['composition_id'].startswith('P05-')               # jen jiní pacienti
    assert 'P0' not in first['patient'] and first['conclusion']         # bez pseudonymu, jen pohlaví a věk
    assert as_user('chirurg').get(f'/api/mdt/cases/{case.pk}/similar/').json()['cases'] == []   # P03 C18 nemá obdobu


def test_ask_answers_from_patient_data(case):  # noqa: F811
    url = f'/api/mdt/cases/{case.pk}/ask/'
    assert as_user('chirurg').post(url, {'question': ''}, format='json').status_code == 400
    r = as_user('chirurg').post(url, {'question': 'Jaký je výsledek CEA?'}, format='json')
    assert r.status_code == 200, r.json()
    out = r.json()
    assert out['question'] == 'Jaký je výsledek CEA?' and out['items']
    [schemas.Claim.model_validate(i) for i in out['items']]


def test_gp_report_with_patient_summary(confirmed):
    r = as_user('onkolog').post(f'/api/mdt/cases/{confirmed.pk}/patient-summary/')
    job = as_user('onkolog').get(f"/api/jobs/{r.json()['job_id']}/").json()
    assert job['status'] == 'done', job['error']
    report = as_user('radiolog').get(f'/api/mdt/cases/{confirmed.pk}/gp-report/').json()
    schemas.PatientSummary.model_validate(report)
    assert report['document_reference'] == 'P03-mdt02-pl' and report['items']
    assert all(i['citations'] for i in report['items'])
    assert client.read('DocumentReference', 'P03-mdt02-pl')['type']['text'] == 'Zpráva MDT pro praktického lékaře'
    bundle = json.loads(as_user('chirurg').get(f'/api/mdt/cases/{confirmed.pk}/export.fhir.json').content)
    assert any(e['fullUrl'].endswith('DocumentReference/P03-mdt02-pl') for e in bundle['entry'])


def test_new_version_of_confirmed_decision(confirmed, decision):  # noqa: F811
    url = f'/api/mdt/cases/{confirmed.pk}/decision/'
    assert as_user('predseda').put(url, decision, format='json').status_code == 409          # zamčeno
    assert as_user('onkolog').post(f'{url}revise/', {'reason': 'oprava'}, format='json').status_code == 403
    assert as_user('predseda').post(f'{url}revise/', {'reason': ' '}, format='json').status_code == 400
    r = as_user('predseda').post(f'{url}revise/', {'reason': 'Doplněno stanovisko HPB chirurga.'}, format='json')
    assert r.status_code == 200, r.json()
    draft = r.json()
    assert draft['status'] == 'draft' and draft['version'] == 2 and draft['revision_of'] == 'P03-mdt02'
    assert draft['history'][0]['version'] == 1 and draft['history'][0]['reason'].startswith('Doplněno')
    assert MdtCase.objects.get(pk=confirmed.pk).status == 'decided'

    # klient verzi ani historii nepřepíše
    saved = as_user('predseda').put(url, {**decision, 'version': 9, 'history': []}, format='json').json()
    assert saved['version'] == 2 and len(saved['history']) == 1
    done = as_user('predseda').post(f'{url}confirm/').json()
    assert done['status'] == 'confirmed' and done['fhir_ids']['composition'] == 'P03-mdt02'   # stejné ID, nová verze
    assert client.read('Composition', 'P03-mdt02')['status'] == 'amended'
    pdf = as_user('chirurg').get(f'/api/mdt/cases/{confirmed.pk}/export.pdf')
    assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF')
