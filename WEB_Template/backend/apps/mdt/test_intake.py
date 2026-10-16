"""Zařazení pacienta do boardu (T-211, FR-P4): předvyplnění, zápis ručních údajů do IRIS s Provenance."""
import pytest
from django.core.management import call_command

from apps.copilot import schemas
from apps.mdt.models import MdtCase, MdtSession
from apps.mdt.test_roles import as_user
from services.fhir import client

pytestmark = pytest.mark.django_db


@pytest.fixture
def seeded(fake_fhir_dataset):
    call_command('seed_mdt')


def _body(pid='P03', **extra):
    session = MdtCase.objects.get(patient_fhir_id=pid).session_id if MdtCase.objects.filter(patient_fhir_id=pid).exists() \
        else MdtSession.objects.get(title='Mamární komise').pk
    return {'session': session, 'patient_id': pid, 'ecog': 0, 'intent': 'C', 'imaging_recent_checked': True,
            'skipped_fields': ['bm.mmr'], 'acknowledge': ['RF-TOX:P03-neuro01'], **extra}


def test_intake_prefill(seeded):
    d = as_user('onkolog').get('/api/mdt/patients/P03/intake/').json()
    fields = {f['id']: f['status'] for f in d['fields']}
    assert d['service_request_id'] == 'P03-zad01' and fields['mdt.question'] == 'present' and fields['bm.mmr'] == 'missing'
    assert d['ecog_physician'] == {'value': 0, 'citation': 'P03-ecog03'} and d['intent_prefill'] == 'C'
    skipped = as_user('onkolog').get('/api/mdt/patients/P03/intake/?skipped=bm.mmr').json()
    assert {f['id']: f['status'] for f in skipped['fields']}['bm.mmr'] == 'skipped'
    assert as_user('onkolog').get('/api/mdt/patients/P99/intake/').status_code == 404


def test_enroll_p03_writes_manual_data_to_iris(seeded):
    """DoD: P03 jde zařadit; přeskočený údaj je jen „skipped“; ruční ECOG je v IRIS s Provenance."""
    r = as_user('onkolog').post('/api/mdt/cases/', _body(), format='json')
    assert r.status_code == 200, r.json()          # nominace už má případ ze seed_mdt → doplněn
    case = r.json()
    n = f"{case['id']:02d}"
    assert case['status'] == 'ready' and case['ecog'] == 0 and case['intent'] == 'C' and case['skipped_fields'] == ['bm.mmr']
    assert case['fhir_written'] == [f'Observation/P03-ecog-case{n}', 'ServiceRequest/P03-zad01',
                                    f'DetectedIssue/P03-case{n}-w01', f'Provenance/P03-case{n}-prov']
    ecog = client.read('Observation', f'P03-ecog-case{n}')
    assert ecog['valueInteger'] == 0 and ecog['code']['coding'][0]['code'] == '89247-1'
    assert ecog['performer'] == [{'reference': 'Practitioner/LEK-P03-01'}]
    zamer = next(e for e in client.read('ServiceRequest', 'P03-zad01')['extension'] if e['url'].endswith('mdt-predpokladany-zamer'))
    assert zamer['valueCodeableConcept']['coding'][0]['code'] == 'kurativni'
    issue = client.read('DetectedIssue', f'P03-case{n}-w01')
    assert issue['mitigation'][0]['action']['text'] == 'Beru na vědomí' and {'reference': 'Observation/P03-neuro01'} in issue['implicated']
    prov = client.read('Provenance', f'P03-case{n}-prov')
    assert {'reference': f'Observation/P03-ecog-case{n}'} in prov['target']

    again = as_user('onkolog').patch(f"/api/mdt/cases/{case['id']}/", {'acknowledge': ['RF-TOX:P03-neuro01', 'RF-ECOG:P03-ecog03']},
                                     format='json').json()
    assert again['fhir_written'] == [f'DetectedIssue/P03-case{n}-w02', f'Provenance/P03-case{n}-prov']   # jen nové


def test_question_cannot_be_skipped_and_roles(seeded):
    assert as_user('onkolog').post('/api/mdt/cases/', _body(skipped_fields=['mdt.question']), format='json').status_code == 400
    assert as_user('radiolog').post('/api/mdt/cases/', _body(), format='json').status_code == 403
    assert as_user('onkolog').post('/api/mdt/cases/', _body('P04', acknowledge=[]), format='json').status_code == 403  # pacient pneumologa
    assert as_user('onkolog').post('/api/mdt/cases/', _body(ecog=9), format='json').status_code == 400


def test_new_case_and_return_for_completion(seeded):
    MdtCase.objects.filter(patient_fhir_id='P05').delete()
    r = as_user('onkolog').post('/api/mdt/cases/', _body('P05', acknowledge=[], skipped_fields=[]), format='json')
    assert r.status_code == 201 and r.json()['created_by']['name'] == 'Klinický onkolog'
    cid = r.json()['id']
    assert as_user('onkolog').patch(f'/api/mdt/cases/{cid}/', {'status': 'returned'}, format='json').status_code == 403
    assert as_user('predseda').patch(f'/api/mdt/cases/{cid}/', {'status': 'returned'}, format='json').json()['status'] == 'returned'


def test_case_readiness_and_compatibility(seeded):
    """BON-1 a FR-D4 přes API: P03 chybí MMR a CT hrudníku; semafor ukáže všechny postupy, anti-EGFR červeně."""
    cid = MdtCase.objects.get(patient_fhir_id='P03').pk
    r = as_user('radiolog').get(f'/api/mdt/cases/{cid}/readiness/').json()
    schemas.Readiness.model_validate(r)
    assert r['patient_id'] == 'P03' and r['status'] == 'incomplete'
    assert {'bm.mmr', 'staging.chest_ct'} <= {f['id'] for f in r['unresolved']}
    procedures = as_user('radiolog').get(f'/api/mdt/cases/{cid}/compatibility/').json()
    lights = {p['id']: p['compatibility']['overall'] for p in procedures}
    assert 'red' in lights.values() and 'orange' in lights.values()
    assert as_user('radiolog').get('/api/mdt/cases/9999/readiness/').status_code == 404
