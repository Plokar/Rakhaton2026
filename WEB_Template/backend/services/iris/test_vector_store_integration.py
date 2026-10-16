"""Vektorové tabulky proti skutečnému IRIS SQL (ověří syntaxi IRIS: TO_VECTOR, VECTOR_COSINE, DATE, TOP).

Běží ve schématu ``MDTTEST`` (ostré ``MDT.*`` nechá být) s mock embeddingy. Bez IRIS se přeskočí:

    docker compose -f docker-compose.dev.yml exec backend pytest -m integration services/iris
"""
import pytest

from services.fhir import ingest
from services.iris import db, indexing
from services.iris import vector_store as vs


def _iris_sql_up():
    try:
        with db.connect():
            return True
    except Exception:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _iris_sql_up(), reason='IRIS SQL nedostupný (dev.ps1 up)'),
]


@pytest.fixture
def test_schema(monkeypatch):
    monkeypatch.setenv('AI_PROVIDER', 'mock')
    monkeypatch.setattr(vs, 'SCHEMA', 'MDTTEST')
    vs.ensure_schema(recreate=True)
    yield
    with db.connect() as conn:
        cursor = conn.cursor()
        for name in vs.TABLES:
            cursor.execute(f'DROP TABLE MDTTEST.{name}')
        conn.commit()


def test_index_search_and_similarity_in_iris(test_schema, dataset_root):
    assert vs.ensure_schema() == []
    n = indexing.index_patient('P03', ingest.load_patient(dataset_root, 'P03'))
    assert n == 85
    indexing.index_guidelines(indexing.guideline_chunks(dataset_root))
    indexing.index_trials(indexing.trial_criteria(ingest.load_studies(dataset_root)))

    rows = vs.search_evidence('P03', 'CT hrudník nebyl požadován', top_k=3)
    assert rows[0]['EvidenceId'] == 'P03-img03#1' and rows[0]['DocDate'] == '2026-09-21'
    assert rows[0]['Score'] >= rows[-1]['Score']
    assert vs.search_evidence('P05', 'hrudník') == []
    assert vs.search_guidelines('bevacizumab před operací', ['KRC', 'OBC'], top_k=1)[0]['EvidenceId'] == 'KRC-2.3'
    assert vs.get_trial_criterion('RKT-03/V3')['Kind'] == 'exclusion'
    assert vs.similarity('hrudník nebyl vyšetřen', ['P03-img03#1', 'KRC-2.4'])['P03-img03#1'] > 0
    assert vs.counts()['MDTTEST.EvidenceChunk'] == {vs.embedding_model_id(): 85}
