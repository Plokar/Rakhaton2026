"""Vektorové tabulky MDT.* proti in-memory IRIS SQL (``fake_iris``). Proti IRIS: test_vector_store_integration.py."""
from io import StringIO

import pytest
from django.core.management import call_command

from services.ai import guidelines as ai_guidelines
from services.ai_service import MockAIProvider
from services.fhir import ingest
from services.iris import indexing
from services.iris import vector_store as vs
from services.rules.guideline_sets import guideline_sets_for


class OtherModel(MockAIProvider):
    """Stejné vektory jako mock, ale jiná identita modelu (jako kdyby se přepnulo na Gemini)."""

    @property
    def provider_name(self):
        return 'jiny'


@pytest.fixture
def indexed(fake_iris, dataset_root):
    vs.ensure_schema()
    for pid in ('P03', 'P05'):
        indexing.index_patient(pid, ingest.load_patient(dataset_root, pid))
    indexing.index_guidelines(indexing.guideline_chunks(dataset_root))
    indexing.index_trials(indexing.trial_criteria(ingest.load_studies(dataset_root)))
    return fake_iris


def test_ensure_schema_is_idempotent(fake_iris):
    assert vs.ensure_schema() == ['MDT.EvidenceChunk', 'MDT.GuidelineChunk', 'MDT.TrialCriterion']
    assert vs.ensure_schema() == []
    fake_iris.rows('MDT.GuidelineChunk').append({'EvidenceId': 'x'})
    assert len(vs.ensure_schema(recreate=True)) == 3
    assert fake_iris.rows('MDT.GuidelineChunk') == []
    assert fake_iris.tables['MDT.EvidenceChunk']['dim'] == 1536
    assert fake_iris.open_connections == 0


def test_search_evidence_only_for_patient(indexed):
    """DoD T-102: dotaz vrací jen odstavce daného pacienta se skóre, seřazené."""
    rows = vs.search_evidence('P03', 'CT hrudník nebyl požadován', top_k=5)
    assert rows[0]['EvidenceId'] == 'P03-img03#1'
    assert {r['PatientId'] for r in rows} == {'P03'}
    scores = [r['Score'] for r in rows]
    assert scores == sorted(scores, reverse=True) and len(rows) == 5
    assert {r['PatientId'] for r in vs.search_evidence('P05', 'třezalka', top_k=20)} == {'P05'}
    with pytest.raises(ValueError):
        vs.search_evidence('', 'cokoli')
    assert indexed.open_connections == 0


def test_reindex_replaces_rows(indexed, dataset_root):
    before = len(indexed.rows('MDT.EvidenceChunk'))
    indexing.index_patient('P03', ingest.load_patient(dataset_root, 'P03'))
    assert len(indexed.rows('MDT.EvidenceChunk')) == before


def test_vectors_of_other_model_are_never_mixed(indexed):
    assert vs.search_evidence('P03', 'neuropatie', provider=OtherModel()) == []
    assert vs.similarity('neuropatie', ['P03-doc07#1'], provider=OtherModel()) == {}


def test_search_guidelines_by_diagnosis(indexed):
    sets = guideline_sets_for(['C18.7', 'C78.7'])
    rows = vs.search_guidelines('bevacizumab vysadit před operací jater', sets, top_k=5)
    assert rows[0]['EvidenceId'] == 'KRC-2.3'
    assert {r['GuidelineSet'] for r in rows} <= {'KRC', 'OBC'}
    assert vs.get_guideline('KRC-2.4')['Title'] == 'Restaging před resekcí'
    assert vs.get_guideline('XYZ-1.1') is None


def test_context_builder_reads_guidelines_written_by_ingest(indexed):
    """Spoj T-203 → T-105: ``load_guidelines`` (services/ai) čte, co sem zapsal ingest."""
    passages = ai_guidelines.load_guidelines(['KRC', 'OBC'])
    assert len(passages) == 18 and passages[0].evidence_id == 'KRC-1.1'


def test_search_trial_criteria(indexed):
    rows = vs.search_trial_criteria('periferní neuropatie stupně 2', ['RKT-03'], top_k=3)
    assert rows[0]['EvidenceId'] == 'RKT-03/V3' and rows[0]['Kind'] == 'exclusion'
    assert vs.get_trial_criterion('RKT-03/V3')['StudyId'] == 'RKT-03'


def test_get_evidence_chunks_for_resolver(indexed):
    rows = vs.get_evidence_chunks('P03', 'P03-img03')
    assert [r['ChunkIndex'] for r in rows] == list(range(1, len(rows) + 1))
    assert rows[0]['CharStart'] == 0 and rows[0]['DocDate'] == '2026-09-21'


def test_similarity_for_grounding(indexed):
    scores = vs.similarity(
        'Hrudník nebyl na restagingovém CT vyšetřen.',
        ['P03-img03#1', 'P03-img03#3', 'P03-img03', 'KRC-2.4', 'RKT-03/V3', 'neplatne-id', 'P03-lab06-cea'],
    )
    assert scores['P03-img03#1'] > scores['P03-img03#3']
    assert scores['P03-img03'] == scores['P03-img03#1']             # resource = nejlepší odstavec
    assert {'KRC-2.4', 'RKT-03/V3'} <= set(scores)
    assert 'neplatne-id' not in scores and 'P03-lab06-cea' not in scores   # bez textu → bez vektoru


def test_counts_by_model(indexed):
    counts = vs.counts()
    assert counts['MDT.GuidelineChunk'] == {'mock:hashed@1536': 42}
    assert counts['MDT.EvidenceChunk']['mock:hashed@1536'] == len(indexed.rows('MDT.EvidenceChunk'))


# ── příkazy ──

def test_ingest_command_builds_vectors_from_iris(fake_fhir, fake_iris, dataset_root):
    out = StringIO()
    call_command('ingest_dataset', patients='P03', dataset_dir=str(dataset_root), stdout=out)
    text = out.getvalue()
    from_files = len(indexing.evidence_chunks('P03', ingest.load_patient(dataset_root, 'P03')))
    assert from_files == 85 and f'MDT.EvidenceChunk P03: {from_files} odstavců' in text    # čteno z FHIR = soubory
    assert "'KRC': 9" in text and 'MDT.TrialCriterion:' in text and 'AI_PROVIDER=mock' in text
    assert {r['PatientId'] for r in fake_iris.rows('MDT.EvidenceChunk')} == {'P03'}
    assert len(fake_iris.rows('MDT.GuidelineChunk')) == 42 and fake_iris.open_connections == 0


def test_ingest_command_dry_run_counts_vectors_offline(dataset_root):
    out = StringIO()
    call_command('ingest_dataset', '--dry-run', dataset_dir=str(dataset_root), stdout=out)
    assert '= 665, guidelines 42' in out.getvalue()


def test_search_iris_command(indexed):
    out = StringIO()
    call_command('search_iris', 'hrudník nebyl požadován', patient='P03', stdout=out)
    assert out.getvalue().splitlines()[0].split()[1] == '[P03-img03#1]'
