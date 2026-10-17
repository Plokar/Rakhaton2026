"""Vektorové tabulky MDT.* proti in-memory IRIS SQL (``fake_iris``). Proti IRIS: test_vector_store_integration.py."""
import base64
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


def test_other_dimension_recreates_tables(indexed, monkeypatch):
    """Přechod embeddingů (Gemini @1536 → NVIDIA @2048): stará dimenze se do sloupce nevejde, tabulky vzniknou znovu."""
    monkeypatch.setenv('EMBEDDING_DIM', '8')
    assert vs.ensure_schema() == ['MDT.EvidenceChunk', 'MDT.GuidelineChunk', 'MDT.TrialCriterion']
    assert indexed.rows('MDT.EvidenceChunk') == [] and indexed.tables['MDT.EvidenceChunk']['dim'] == 8
    assert vs.ensure_schema() == []


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


def test_external_sources_resolve_with_url_and_stay_out_of_guideline_sets(indexed):
    """T-504: EXT-… je v MDT.GuidelineChunk se znením a odkazem; do sad podle diagnózy se nemíchá (D-016)."""
    indexing.index_guidelines(indexing.external_chunks())
    row = vs.get_guideline('EXT-EMA-DPD-2020')
    assert row['GuidelineSet'] == 'EXT' and row['Url'].startswith('https://www.ema.europa.eu/')
    assert 'Úplný deficit → nepodávat' in row['Text'] and 'VS-KRC-09' in row['Text']
    assert vs.get_guideline('KRC-2.4')['Url'] is None
    assert vs.search_guidelines('deficit DPD fluoropyrimidiny', ['EXT'], top_k=1)[0]['EvidenceId'] == 'EXT-EMA-DPD-2020'
    assert all(r['GuidelineSet'] != 'EXT' for r in vs.search_guidelines('DPD', ['KRC', 'OBC'], top_k=50))
    assert vs.similarity('úplný deficit DPD', ['EXT-EMA-DPD-2020'])['EXT-EMA-DPD-2020'] > 0


def test_ensure_schema_adds_missing_columns(fake_iris):
    """Tabulka ze starší verze (bez Url) se doplní ALTER TABLE, data zůstanou."""
    old_ddl = vs._ddl('GuidelineChunk', 1536).replace(', Url VARCHAR(500)', '')
    fake_iris.execute(old_ddl, [])
    fake_iris.rows('MDT.GuidelineChunk').append({'EvidenceId': 'KRC-1.1', 'EmbeddingModel': 'mock:hashed@1536'})
    changes = vs.ensure_schema()
    assert 'MDT.GuidelineChunk.Url' in changes and 'MDT.EvidenceChunk' in changes
    assert 'Url' in fake_iris.tables['MDT.GuidelineChunk']['columns'] and len(fake_iris.rows('MDT.GuidelineChunk')) == 1
    assert vs.ensure_schema() == []


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


def test_indexing_creates_missing_schema(fake_iris, dataset_root):
    """Reindex po zápisu závěru (T-209) i testy groundingu (T-213) zapisují bez předchozího ensure_schema."""
    assert indexing.index_patient('P03', ingest.load_patient(dataset_root, 'P03')) == 85
    assert set(fake_iris.tables) >= {'MDT.EvidenceChunk', 'MDT.GuidelineChunk', 'MDT.TrialCriterion'}


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
    assert "'KRC': 9" in text and "'EXT': 106" in text and 'MDT.TrialCriterion:' in text and 'Embeddingy mock' in text
    assert {r['PatientId'] for r in fake_iris.rows('MDT.EvidenceChunk')} == {'P03'}
    assert len(fake_iris.rows('MDT.GuidelineChunk')) == 42 + 106 and fake_iris.open_connections == 0


def test_ingest_command_dry_run_counts_vectors_offline(dataset_root):
    out = StringIO()
    call_command('ingest_dataset', '--dry-run', dataset_dir=str(dataset_root), stdout=out)
    assert '= 665, guidelines 148 (z toho EXT 106)' in out.getvalue()


def test_search_iris_command(indexed):
    out = StringIO()
    call_command('search_iris', 'hrudník nebyl požadován', patient='P03', stdout=out)
    assert out.getvalue().splitlines()[0].split()[1] == '[P03-img03#1]'


class SpyProvider(MockAIProvider):
    """Mock, který si pamatuje, co šlo do embedding API."""

    def __init__(self):
        super().__init__()
        self.sent: list[str] = []

    def embed(self, texts, task_type='RETRIEVAL_DOCUMENT', model=None, dim=None):
        self.sent += list(texts)
        return super().embed(texts, task_type, model, dim)


def test_embedding_input_is_pseudonymized_but_iris_keeps_original(fake_iris, dataset_root):
    """NFR-3: jména pacienta a lékařů, RČ, telefon… do embedding API nejdou; v IRIS zůstává originál (offsety)."""
    vs.ensure_schema()
    resources = ingest.load_patient(dataset_root, 'P03')
    patient = next(r for r in resources if r['resourceType'] == 'Patient')
    patient['name'] = [{'text': 'Jan Novák', 'given': ['Jan'], 'family': 'Novák'}]
    doc = next(r for r in resources if r['id'] == 'P03-doc02')
    doc['content'][0]['attachment']['data'] = base64.b64encode(
        'Pacient Jan Novák, RČ 590101/1234, tel. 603 123 456.\n\nZávěr: bez nálezu.'.encode()).decode()
    spy = SpyProvider()
    indexing.index_patient('P03', resources, provider=spy)
    sent = next(t for t in spy.sent if 'Závěr' not in t and 'P03' in t and '[telefon]' in t)
    assert 'Novák' not in sent and '[RČ]' in sent
    stored = next(r for r in fake_iris.rows('MDT.EvidenceChunk') if r['EvidenceId'] == 'P03-doc02#1')
    assert 'Jan Novák' in stored['Text']
    vs.search_evidence('P03', 'volat 603 123 456', provider=spy)
    assert spy.sent[-1] == 'volat [telefon]'


def test_ingest_if_empty_skips_loaded_data_and_rebuilds_for_new_model(fake_fhir, fake_iris, dataset_root, monkeypatch):
    call_command('ingest_dataset', patients='P03', dataset_dir=str(dataset_root), stdout=StringIO())
    puts = len([r for r in fake_fhir.requests if r[0] == 'POST'])
    rows = len(fake_iris.rows('MDT.EvidenceChunk'))

    out = StringIO()
    call_command('ingest_dataset', '--if-empty', patients='P03', dataset_dir=str(dataset_root), stdout=out)
    assert 'už v IRIS je, přeskakuji' in out.getvalue() and 'Vektory (mock:hashed@1536) už v IRIS jsou' in out.getvalue()
    assert len([r for r in fake_fhir.requests if r[0] == 'POST']) == puts          # nic se neposlalo

    monkeypatch.setattr('services.ai_service.get_ai_provider', lambda *a, **k: OtherModel())
    out = StringIO()
    call_command('ingest_dataset', '--if-empty', patients='P03', dataset_dir=str(dataset_root), stdout=out)
    assert 'MDT.EvidenceChunk P03: 85 odstavců' in out.getvalue()                    # nový model → přepočítat
    models = [r['EmbeddingModel'] for r in fake_iris.rows('MDT.EvidenceChunk')]
    assert models.count('jiny:hashed@1536') == rows and models.count('mock:hashed@1536') == rows   # modely vedle sebe


def test_ingest_if_empty_loads_missing_fhir(fake_fhir, fake_iris, dataset_root):
    out = StringIO()
    call_command('ingest_dataset', '--if-empty', patients='P03', dataset_dir=str(dataset_root), stdout=out)
    assert 'nahráno a ověřeno' in out.getvalue() and 'Patient/P03' in fake_fhir.store
