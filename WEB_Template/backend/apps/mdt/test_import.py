"""Vstup vloženého textu → FHIR (BON-7, T-510): návrh s ověřením, potvrzení lékařem, zápis s Provenance."""
import pytest
from django.core.management import call_command

from apps.mdt.test_roles import as_user
from services import ai_service
from services.ai import report_import
from services.ai_service import MockAIProvider
from services.fhir import client

pytestmark = pytest.mark.django_db

TEXT = "Laboratoř 12. 10. 2026\n\nCEA 15,2 µg/l, CA 19-9 40 kU/l.\n\nHemoglobin 118 g/l."
EXTRACTION = {"title": "Laboratoř", "date": "2026-10-12", "values": [
    {"kind": "lab", "label": "CEA", "value_text": "15,2 µg/l", "value_number": 15.2, "unit": "µg/l", "paragraph": 2},
    {"kind": "lab", "label": "Hemoglobin", "value_text": "118 g/l", "value_number": 118, "unit": "g/l", "paragraph": 3},
    {"kind": "lab", "label": "Albumin", "value_text": "30 g/l", "value_number": 30, "unit": "g/l", "paragraph": 3},
]}


@pytest.fixture
def mocked(fake_fhir_dataset, monkeypatch):
    call_command('seed_mdt')
    client.put({'resourceType': 'Device', 'id': 'mdt-copilot', 'deviceName': [{'name': 'MDT Copilot', 'type': 'user-friendly-name'}]})
    monkeypatch.setattr(ai_service, 'get_ai_provider', lambda *a, **k: MockAIProvider(responses={'Extraction': EXTRACTION}))


def test_propose_verifies_every_value_against_its_paragraph():
    proposal = report_import.propose('P03', 'P03-imp01', TEXT, MockAIProvider(responses={'Extraction': EXTRACTION}),
                                     lambda *a: None)
    assert [v['label'] for v in proposal['values']] == ['CEA', 'Hemoglobin']
    assert proposal['values'][0]['citation'] == 'P03-imp01#2'
    assert proposal['values'][0]['source'] == 'CEA 15,2 µg/l, CA 19-9 40 kU/l.'      # znění odstavce pro lékaře
    assert proposal['rejected'][0]['label'] == 'Albumin' and 'číslo 30 není v odstavci' in proposal['rejected'][0]['reasons']


def test_import_api_proposes_then_doctor_confirms(mocked):
    url = '/api/mdt/patients/P03/import/'
    assert as_user('radiolog').post(url, {'text': TEXT}, format='json').status_code == 403
    proposal = as_user('onkolog').post(url, {'text': TEXT}, format='json').json()
    assert proposal['document_id'] == 'P03-imp01' and not client.search('DocumentReference', _id='P03-imp01')
    tampered = {**proposal, 'values': [*proposal['values'], {**proposal['values'][0], 'value_text': '99 µg/l', 'value_number': 99}]}
    r = as_user('onkolog').post(url + 'confirm/', tampered, format='json')
    assert r.status_code == 201
    assert r.json()['fhir_written'] == ['DocumentReference/P03-imp01', 'Observation/P03-imp01-lab01',
                                        'Observation/P03-imp01-lab02', 'Provenance/P03-imp01-prov']   # podvrh vypadl
    cea = client.read('Observation', 'P03-imp01-lab01')
    assert cea['valueQuantity'] == {'value': 15.2, 'unit': 'µg/l'} and cea['effectiveDateTime'] == '2026-10-12'
    assert cea['derivedFrom'] == [{'reference': 'DocumentReference/P03-imp01'}]
    prov = client.read('Provenance', 'P03-imp01-prov')
    assert {'reference': 'Device/mdt-copilot'} in [a['who'] for a in prov['agent']]
    again = as_user('onkolog').post(url, {'text': TEXT}, format='json').json()
    assert again['document_id'] == 'P03-imp02'                                                       # další číslo


def test_confirm_rejects_foreign_or_empty_proposal(mocked):
    proposal = report_import.propose('P03', 'P03-imp01', TEXT, MockAIProvider(responses={'Extraction': EXTRACTION}),
                                     lambda *a: None)
    assert as_user('onkolog').post('/api/mdt/patients/P05/import/confirm/', proposal, format='json').status_code == 400
    blank = {**proposal, 'text': '   '}
    assert as_user('onkolog').post('/api/mdt/patients/P03/import/confirm/', blank, format='json').status_code == 400


def test_value_number_unit_and_loinc_like_dataset(mocked):
    """Model nevyplnil číslo: doplní se z textu; Hb dostane LOINC jako dataset, takže ho vidí pravidla i grafy."""
    extraction = {'title': 'Laboratoř', 'date': '2026-10-12', 'values': [
        {'kind': 'lab', 'label': 'Hemoglobin', 'value_text': '118 g/l', 'paragraph': 3},
        {'kind': 'lab', 'label': 'Leukocyty', 'value_text': '8,4 10^9/l', 'paragraph': 3},
        {'kind': 'lab', 'label': 'CRP', 'value_text': '<5 mg/l', 'paragraph': 3}]}
    text = 'Laboratoř 12. 10. 2026\n\nCEA 15,2 µg/l.\n\nHemoglobin 118 g/l, leukocyty 8,4 10^9/l, CRP <5 mg/l.'
    proposal = report_import.propose('P03', 'P03-imp01', text, MockAIProvider(responses={'Extraction': extraction}),
                                     lambda *a: None)
    assert [(v['value_number'], v.get('unit')) for v in proposal['values']] == [(118.0, 'g/l'), (8.4, '10^9/l'), (None, None)]
    as_user('onkolog').post('/api/mdt/patients/P03/import/confirm/', proposal, format='json')
    hb = client.read('Observation', 'P03-imp01-lab01')
    assert hb['valueQuantity'] == {'value': 118.0, 'unit': 'g/l'} and hb['code']['coding'][0]['code'] == '718-7'
    assert client.read('Observation', 'P03-imp01-lab03')['valueString'] == '<5 mg/l'
    series = {s['code']: s for s in as_user('chirurg').get('/api/patients/P03/observations/').json()}
    assert 'P03-imp01-lab01' in [p['citation'] for p in series['718-7']['points']]       # v řadě Hb s datasetem
    assert 'text:leukocyty' in series


def test_report_without_values_is_stored_and_citable(mocked):
    """Zpráva bez čísel (anamnéza) se zapíše jen jako dokument; citace odstavce jde otevřít (resolver)."""
    proposal = report_import.propose('P03', 'P03-imp01', TEXT, MockAIProvider(responses={'Extraction': EXTRACTION}),
                                     lambda *a: None)
    r = as_user('onkolog').post('/api/mdt/patients/P03/import/confirm/', {**proposal, 'values': []}, format='json')
    assert r.status_code == 201 and r.json()['fhir_written'] == ['DocumentReference/P03-imp01', 'Provenance/P03-imp01-prov']
    source = as_user('chirurg').get('/api/evidence/?id=P03-imp01%232').json()
    assert source['resource_type'] == 'DocumentReference' and source['text'][source['highlight']['start']:].startswith('CEA')
