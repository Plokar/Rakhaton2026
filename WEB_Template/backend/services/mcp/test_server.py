"""MCP server (T-308) nad fake FHIR + fake IRIS SQL; registrace nástrojů přes in-memory klienta fastmcp."""
import asyncio

import pytest
from fastmcp import Client

from services.fhir import ingest
from services.iris import indexing
from services.iris import vector_store as vs
from services.mcp import server


@pytest.fixture
def iris(fake_fhir_dataset, fake_iris, dataset_root):
    """IRIS jako po ``ingest_dataset``: FHIR s datasetem + vektorové tabulky (P03, P05, guidelines, studie)."""
    vs.ensure_schema()
    for pid in ('P03', 'P05'):
        indexing.index_patient(pid)
    indexing.index_guidelines(indexing.guideline_chunks(dataset_root))
    indexing.index_trials(indexing.trial_criteria(ingest.load_studies(dataset_root)))
    return fake_fhir_dataset


def test_tools_are_registered_read_only():
    async def list_tools():
        async with Client(server.mcp) as client:
            return await client.list_tools()
    tools = {t.name: t for t in asyncio.run(list_tools())}
    assert set(tools) == {'get_patient_context', 'search_evidence', 'search_guidelines',
                          'search_trial_criteria', 'get_evidence', 'fhir_query'}
    assert all(t.annotations.read_only_hint for t in tools.values())


def test_call_tool_through_mcp_client(iris):
    async def call():
        async with Client(server.mcp) as client:
            return await client.call_tool('search_evidence', {'patient_id': 'P03', 'query': 'hrudník nebyl požadován'})
    result = asyncio.run(call())
    assert result.data[0]['EvidenceId'] == 'P03-img03#1'


def test_get_patient_context_with_focus(iris):
    text = server.get_patient_context('P03', focus='CT hrudník nebyl požadován')
    assert '## Nejrelevantnější odstavce' in text and '[P03-img03#1]' in text
    assert '[KRC-2.4]' in text                                          # guidelines z MDT.GuidelineChunk


def test_search_tools(iris):
    rows = server.search_evidence('P05', 'třezalka', top_k=50)
    assert rows and len(rows) <= server.MAX_TOP_K and {r['EvidenceId'][:3] for r in rows} == {'P05'}
    assert 'Embedding' not in rows[0] and isinstance(rows[0]['Score'], float)
    assert server.search_guidelines('bevacizumab před operací', icd10=['C18.7'], top_k=1)[0]['EvidenceId'] == 'KRC-2.3'
    assert server.search_trial_criteria('neuropatie', study_id='RKT-03', top_k=1)[0]['EvidenceId'] == 'RKT-03/V3'


def test_get_evidence_kinds(iris):
    para = server.get_evidence('P03-img03#1')
    assert para['kind'] == 'paragraph' and 'hrudník nebyl požadován' in para['text']
    assert para['resource_text'][para['char_start']:para['char_end']] == para['text']
    obs = server.get_evidence('P03-lab06-cea')
    assert obs['resource']['valueQuantity']['value'] == 13.9
    assert server.get_evidence('KRC-2.4')['Title'] == 'Restaging před resekcí'
    assert server.get_evidence('RKT-03/V3')['Kind'] == 'exclusion'
    indexing.index_guidelines(indexing.external_chunks())
    ext = server.get_evidence('EXT-EMA-DPD-2020')                      # T-504: znění a odkaz
    assert ext['kind'] == 'external' and ext['Url'].startswith('https://') and 'DPD' in ext['Text']
    assert 'error' in server.get_evidence('P03-img03#99')
    assert 'error' in server.get_evidence('nesmysl')
    assert 'error' in server.get_evidence('P03-doc99')


def test_fhir_query_allowlist_and_redaction(iris):
    result = server.fhir_query('Observation', {'patient': 'P03', 'code': 'http://loinc.org|2039-6'})
    assert result['total'] == 6 and all(r['code']['text'] == 'CEA' for r in result['resources'])
    patient = server.fhir_query('Patient', {'_id': 'P03'})['resources'][0]
    assert 'name' not in patient and 'birthDate' not in patient and patient['gender'] == 'male'
    doc = server.fhir_query('DocumentReference', {'_id': 'P03-doc02'})['resources'][0]
    assert doc['content'][0]['attachment']['data'].startswith('(base64 vynecháno')
    assert 'error' in server.fhir_query('Observation', {'patinet': 'P03'})        # překlep by IRIS ignoroval
    assert 'error' in server.fhir_query('Account')
    assert iris.ignored_params == set()


def test_texts_are_pseudonymized(iris):
    iris.store['DocumentReference/P03-doc02']['description'] = 'kontakt jan.novak@example.cz, tel. 603 123 456'
    doc = server.fhir_query('DocumentReference', {'_id': 'P03-doc02'})['resources'][0]
    assert doc['description'] == 'kontakt [e-mail], tel. [telefon]'
