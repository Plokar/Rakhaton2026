"""Resolver citací nad fake FHIR (dataset) + fake IRIS SQL (guidelines, studie)."""
import pytest

from services.fhir import client, ingest
from services.iris import indexing
from services.iris import vector_store as vs

pytestmark = pytest.mark.django_db


@pytest.fixture
def api(authenticated_client, fake_fhir_dataset, fake_iris, dataset_root):
    vs.ensure_schema()
    indexing.index_guidelines(indexing.guideline_chunks(dataset_root))
    indexing.index_trials(indexing.trial_criteria(ingest.load_studies(dataset_root)))
    return lambda eid: authenticated_client.get('/api/evidence/', {'id': eid})


def test_paragraph_has_full_text_and_highlight(api):
    d = api('P03-img03#2').json()
    assert d['resource_type'] == 'DiagnosticReport' and d['date'] == '2026-09-21'
    h = d['highlight']
    assert h['paragraph'] == 2 and 0 <= h['start'] < h['end'] <= len(d['text'])
    assert d['author']['id'].startswith('LEK-P03-') and d['author']['specialty']


def test_observation_value_and_source_document(api):
    d = api('P03-ecog03').json()
    assert d['value']['value'] == 0
    assert [s['evidence_id'] for s in d['derived_from']] == ['P03-doc07'] and d['derived_from'][0]['text']
    cea = api('P03-lab06-cea').json()['value']
    assert (cea['value'], cea['ref_high'], cea['interpretation']) == (13.9, 5.0, 'H')


def test_derived_from_extension_is_followed(api):
    """Q15: sanitizace přesune odkaz na DiagnosticReport do extension, resolver ho pořád dohledá."""
    assert 'derivedFrom' not in client.read('Observation', 'P03-tnm01')
    assert [s['evidence_id'] for s in api('P03-tnm01').json()['derived_from']] == ['P03-img01']


def test_proms_answers_as_text(api):
    text = api('P03-prom02').json()['text']
    assert 'Únava za poslední týden (0–10): 4' in text and 'řídit nemůžu' in text


def test_guideline_and_trial_criterion(api):
    g = api('KRC-2.4').json()
    assert g['kind'] == 'guideline' and g['title'] == 'KRC-2.4 – Restaging před resekcí' and g['text']
    c = api('RKT-03/V3').json()
    assert c['criterion_kind'] == 'exclusion' and 'neuropat' in c['text'].lower()


@pytest.mark.parametrize('eid, status', [('nesmysl', 400), ('', 400), ('P03-doc99', 404), ('P03-img03#99', 404), ('KRC-9.9', 404)])
def test_errors(api, eid, status):
    assert api(eid).status_code == status
