"""Nový pacient přes aplikaci (T-323): založení v IRIS, zpráva přes import, zařazení do boardu a podklad."""
import pytest
from django.core.management import call_command

from apps.mdt.models import MdtSession
from apps.mdt.test_roles import as_user
from services import ai_service
from services.ai_service import MockAIProvider
from services.fhir import client

pytestmark = pytest.mark.django_db

NEW = {'sex': 'female', 'birth_year': 1958, 'icd10': 'c34.1', 'diagnosis': 'Zhoubný novotvar horního laloku plíce',
       'stage': 'cT2a cN1 cM0, stadium IIB', 'question': 'Je pacientka kandidátem lobektomie, nebo chemoradioterapie?'}
REPORT = ('Pneumologická zpráva 10. 10. 2026\n\nSpirometrie: FEV1 1,9 l (68 %), DLCO 55 %.\n\n'
          'Kuřačka 40 balíčkoroků, nyní nekouří. ECOG 1.')
EXTRACTION = {'title': 'Pneumologická zpráva', 'date': '2026-10-10', 'values': [
    {'kind': 'lab', 'label': 'FEV1', 'value_text': '1,9 l (68 %)', 'value_number': 1.9, 'unit': 'l', 'paragraph': 2},
    {'kind': 'ecog', 'label': 'ECOG', 'value_text': 'ECOG 1', 'value_number': 1, 'paragraph': 3}]}


@pytest.fixture
def seeded(fake_fhir_dataset, fake_iris, monkeypatch):
    call_command('seed_mdt')
    client.put({'resourceType': 'Device', 'id': 'mdt-copilot', 'deviceName': [{'name': 'MDT Copilot', 'type': 'user-friendly-name'}]})
    monkeypatch.setattr(ai_service, 'get_ai_provider', lambda *a, **k: MockAIProvider(responses={'Extraction': EXTRACTION}))


def test_validation_and_roles(seeded):
    assert as_user('chirurg').post('/api/mdt/patients/', NEW, format='json').status_code == 403
    for bad in ({'icd10': 'I25.2'}, {'icd10': 'C3'}, {'question': ' '}, {'birth_year': 1850}, {'sex': 'x'}):
        r = as_user('onkolog').post('/api/mdt/patients/', {**NEW, **bad}, format='json')
        assert r.status_code == 400 and set(r.json()) <= {'icd10', 'question', 'birth_year', 'sex'}, bad
    closed = MdtSession.objects.get(title='Mamární komise (urgentní)')
    closed.status = 'closed'
    closed.save()
    assert as_user('onkolog').post('/api/mdt/patients/', {**NEW, 'session': closed.pk}, format='json').status_code == 409


def test_new_patient_report_intake_and_brief(seeded):
    """Celá cesta nového pacienta systémem do FHIR: založení → zpráva → zařazení → podklad z IRIS."""
    board = MdtSession.objects.get(title='Hrudní – karcinom plic')
    created = as_user('pneumolog').post('/api/mdt/patients/', {**NEW, 'session': board.pk}, format='json')
    assert created.status_code == 201, created.json()
    body = created.json()
    pid = body['patient_id']
    assert pid == 'P07' and body['fhir_written'][0] == 'Patient/P07'
    assert body['patient']['display_name'] == 'P07 · žena · 68 let'
    assert body['patient']['diagnosis']['icd10'] == 'C34.1' and body['patient']['mdt_question'] == NEW['question']
    assert client.read('Task', 'P07-zad01-task')['restriction']['period']['start'].startswith('2026-10-21')
    assert {'reference': 'Patient/P07'} in client.read('Provenance', 'P07-novy-prov')['target']
    assert [p['id'] for p in as_user('chirurg').get('/api/patients/').json()][-1] == 'P07'

    proposal = as_user('pneumolog').post(f'/api/mdt/patients/{pid}/import/', {'text': REPORT}, format='json').json()
    written = as_user('pneumolog').post(f'/api/mdt/patients/{pid}/import/confirm/', proposal, format='json').json()
    assert 'Observation/P07-imp01-ecog02' in written['fhir_written']
    detail = as_user('chirurg').get(f'/api/patients/{pid}/').json()
    assert detail['ecog']['physician']['value'] == 1 and detail['diagnoses'][0]['stage'] == NEW['stage']

    intake = as_user('pneumolog').get(f'/api/mdt/patients/{pid}/intake/').json()
    assert intake['service_request_id'] == 'P07-zad01' and intake['ecog_physician']['value'] == 1
    case = as_user('pneumolog').post('/api/mdt/cases/', {
        'session': board.pk, 'patient_id': pid, 'ecog': 1, 'intent': 'C', 'imaging_recent_checked': True,
        'skipped_fields': [], 'acknowledge': [], 'acknowledged_warnings': [], 'status': 'nominated'},   # tělo jako z UI
        format='json')
    assert case.status_code == 201, case.json()
    assert pid in next(s for s in as_user('chirurg').get('/api/mdt/sessions/').json() if s['id'] == board.pk)['patients']

    from services.ai.brief import generate_brief
    from apps.mdt.models import MdtCase
    brief = generate_brief(MdtCase.objects.get(pk=case.json()['id']), {'config': None}, lambda p: None,
                           provider=MockAIProvider())
    assert brief['header']['diagnosis']['icd10'] == 'C34.1' and brief['header']['mdt_question']['citation'].startswith('P07-zad01')
    assert brief['header']['ecog']['physician']['value'] == 1
