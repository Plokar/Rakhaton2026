"""Vektorové tabulky v IRIS SQL (ARCH §4.5): ``MDT.EvidenceChunk``, ``MDT.GuidelineChunk``, ``MDT.TrialCriterion``.

- zápis: ``replace_*`` smaže staré řádky (pacienta / sady / studie) a vloží nové s embeddingem;
- čtení: ``search_*`` (``VECTOR_COSINE``), ``get_*`` (resolver citací T-104), ``similarity`` (grounding T-213).

Každý řádek nese ``EmbeddingModel`` (např. ``gemini:gemini-embedding-001@1536``) a hledá se jen mezi řádky
aktuálního modelu: vektory z mocku a z Gemini se nikdy nesmíchají. Po změně ``AI_PROVIDER`` /
``EMBEDDING_MODEL`` je potřeba reindex (``ingest_dataset --skip-fhir``).

SQL podle AGENTS.md: parametry přes ``?``, ``SELECT TOP n``, spojení vždy zavřít (``db.connect``).

Každý text, který jde do embedding API (odstavce, dotazy, tvrzení), projde pseudonymizací (NFR-3,
``services/ai/pseudonymize.py``); v IRIS zůstává originál (offsety pro zvýraznění v UI).
"""
import logging
from contextlib import contextmanager
from dataclasses import dataclass, fields
from typing import Callable, Iterable, Sequence

from services import ai_service
from services.ai.pseudonymize import pseudonymize_text
from services.fhir.ids import parse_evidence_id
from services.iris import db

logger = logging.getLogger(__name__)

SCHEMA = 'MDT'


@dataclass
class EvidenceChunk:
    EvidenceId: str            # "P03-img03#2"
    PatientId: str             # "P03" (POVINNÝ filtr při hledání, NFR-2)
    ResourceType: str          # DocumentReference | DiagnosticReport | Composition | ServiceRequest
    ResourceId: str            # "P03-img03"
    ChunkIndex: int            # číslo odstavce = část za "#" (services/ai/text.py)
    CharStart: int             # offset v resource_text() pro zvýraznění v UI
    CharEnd: int
    DocDate: str | None        # "2026-09-21"
    Title: str                 # type.text / code.text / název záznamu MDT
    Department: str            # category[].text (A-ONK, RDG, PAT-B…)
    Text: str


@dataclass
class GuidelineChunk:
    EvidenceId: str            # "KRC-2.4"
    GuidelineSet: str          # KRC | PRS | PLI | OBC | EXT (D-016)
    Title: str
    Source: str
    Region: str                # "CZ"
    IcdPrefixes: str           # "C18,C19,C20" | "C50" | "C34" | "*"
    Text: str
    Url: str | None = None     # odkaz na zdroj, u EXT-… (T-504); u guidelines datasetu prázdné


@dataclass
class TrialCriterion:
    EvidenceId: str            # "RKT-03/V3"
    StudyId: str               # "RKT-03"
    Kind: str                  # inclusion | exclusion
    Text: str


# Délky VARCHAR podle ARCH §4.5; EmbeddingModel a Embedding přidává _ddl.
_COLUMNS = {
    'EvidenceChunk': (EvidenceChunk, {
        'EvidenceId': 'VARCHAR(200)', 'PatientId': 'VARCHAR(16)', 'ResourceType': 'VARCHAR(64)',
        'ResourceId': 'VARCHAR(128)', 'ChunkIndex': 'INTEGER', 'CharStart': 'INTEGER', 'CharEnd': 'INTEGER',
        'DocDate': 'DATE', 'Title': 'VARCHAR(500)', 'Department': 'VARCHAR(200)', 'Text': 'VARCHAR(10000)',
    }, ('PatientId', 'ResourceId')),
    'GuidelineChunk': (GuidelineChunk, {
        'EvidenceId': 'VARCHAR(50)', 'GuidelineSet': 'VARCHAR(10)', 'Title': 'VARCHAR(300)',
        'Source': 'VARCHAR(200)', 'Region': 'VARCHAR(20)', 'IcdPrefixes': 'VARCHAR(100)', 'Text': 'VARCHAR(5000)',
        'Url': 'VARCHAR(500)',
    }, ('GuidelineSet',)),
    'TrialCriterion': (TrialCriterion, {
        'EvidenceId': 'VARCHAR(50)', 'StudyId': 'VARCHAR(16)', 'Kind': 'VARCHAR(10)', 'Text': 'VARCHAR(2000)',
    }, ('StudyId',)),
}
TABLES = tuple(_COLUMNS)


def _table(name: str) -> str:
    return f'{SCHEMA}.{name}'


def _column_types(name: str, dim: int) -> dict[str, str]:
    _, columns, _ = _COLUMNS[name]
    return {**columns, 'EmbeddingModel': 'VARCHAR(100)', 'Embedding': f'VECTOR(DOUBLE, {dim})'}


def _ddl(name: str, dim: int) -> str:
    cols = [f'{col} {sql_type}' for col, sql_type in _column_types(name, dim).items()]
    return f'CREATE TABLE {_table(name)} ({", ".join(cols)})'


# ── Embeddingy ────────────────────────────────────────────────────────────────

def embedding_model_id(provider=None) -> str:
    """Identita vektorů v tabulkách: provider, model a dimenze (mock a Gemini se nesmí míchat)."""
    provider = ai_service.embedding_provider(provider)
    model = 'hashed' if provider.is_mock else ai_service.embedding_model()
    return f'{provider.provider_name}:{model}@{ai_service.embedding_dim()}'


def _vector_param(vector: Sequence[float]) -> str:
    return str([float(x) for x in vector])          # TO_VECTOR přijímá "[0.1, 0.2, …]"


def embed(texts: Sequence[str], task_type: str, provider=None,
          prepare: Callable[[str], str] = pseudonymize_text) -> list[list[float]]:
    """Embeddingy přes provider (T-012). ``prepare`` = pseudonymizace před odesláním (NFR-3)."""
    provider = ai_service.embedding_provider(provider)
    return provider.embed([prepare(t) for t in texts], task_type=task_type) if texts else []


# ── Spojení a schéma ──────────────────────────────────────────────────────────

@contextmanager
def _cursor(commit: bool = False):
    with db.connect() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        finally:
            cursor.close()


def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        'SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?', [SCHEMA, name],
    )
    return cursor.fetchone()[0] > 0


def _missing_columns(cursor, name: str, dim: int) -> dict[str, str]:
    cursor.execute(
        'SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?', [SCHEMA, name],
    )
    existing = {row[0].lower() for row in cursor.fetchall()}
    return {col: t for col, t in _column_types(name, dim).items() if col.lower() not in existing}


def _other_dimension(cursor, name: str, dim: int) -> bool:
    """Vektory jiné dimenze (přechod Gemini @1536 → NVIDIA @2048): sloupec `VECTOR` má pevnou dimenzi, IRIS ji
    v katalogu neukazuje, takže se pozná podle `EmbeddingModel` (`…@dim`)."""
    cursor.execute(f'SELECT %EXACT(EmbeddingModel), COUNT(*) FROM {_table(name)} GROUP BY %EXACT(EmbeddingModel)')
    other = [model for model, _ in cursor.fetchall() if model and not str(model).endswith(f'@{dim}')]
    if other:
        logger.warning('%s: vektory %s nemají dimenzi %d, zakládám tabulku znovu', _table(name), other, dim)
    return bool(other)


def ensure_schema(recreate: bool = False) -> list[str]:
    """Založí chybějící tabulky a doplní chybějící sloupce (idempotentní, vrací provedené změny).

    ``recreate`` = zahodit a založit znovu; stane se samo, když v tabulce jsou vektory jiné dimenze
    (jiný ``EMBEDDING_PROVIDER``). Data jsou odvozená, volající je hned přepočítá (ingest, reindex).
    """
    dim = ai_service.embedding_dim()
    changes = []
    with _cursor(commit=True) as cursor:
        for name, (_, _, indexed) in _COLUMNS.items():
            exists = _table_exists(cursor, name)
            if exists and (recreate or _other_dimension(cursor, name, dim)):
                cursor.execute(f'DROP TABLE {_table(name)}')
                exists = False
            if not exists:
                cursor.execute(_ddl(name, dim))
                for col in indexed:
                    cursor.execute(f'CREATE INDEX {name}{col}Idx ON {_table(name)} ({col})')
                changes.append(_table(name))
                continue
            for col, sql_type in _missing_columns(cursor, name, dim).items():   # novější verze schématu (Url, T-504)
                cursor.execute(f'ALTER TABLE {_table(name)} ADD {col} {sql_type}')
                changes.append(f'{_table(name)}.{col}')
    return changes


# ── Zápis ─────────────────────────────────────────────────────────────────────

def _embedding_text(row) -> str:
    title = getattr(row, 'Title', '')
    return f'{title}: {row.Text}' if title else row.Text


def _replace(name: str, rows: list, delete_where: str, delete_params: list, provider=None,
             prepare: Callable[[str], str] = pseudonymize_text) -> int:
    """Smaže řádky podle ``delete_where`` a vloží ``rows`` s embeddingy (RETRIEVAL_DOCUMENT).

    Schéma založí, když chybí (reindex po zápisu závěru T-209 na čistém IRIS, testy s ``fake_iris``).
    """
    ensure_schema()
    provider = ai_service.embedding_provider(provider)
    vectors = embed([_embedding_text(r) for r in rows], ai_service.TASK_RETRIEVAL_DOCUMENT, provider, prepare)
    model_id = embedding_model_id(provider)
    cls = _COLUMNS[name][0]
    cols = [f.name for f in fields(cls)]
    sql = (
        f'INSERT INTO {_table(name)} ({", ".join(cols)}, EmbeddingModel, Embedding) '
        f'VALUES ({", ".join("?" * len(cols))}, ?, TO_VECTOR(?, DOUBLE))'
    )
    params = [[getattr(r, c) for c in cols] + [model_id, _vector_param(v)] for r, v in zip(rows, vectors)]
    with _cursor(commit=True) as cursor:
        # Jen řádky stejného modelu: mock a Gemini vektory žijí vedle sebe (dev, demo), `similarity` filtruje model.
        cursor.execute(f'DELETE FROM {_table(name)} WHERE {delete_where} AND EmbeddingModel = ?',
                       [*delete_params, model_id])
        if params:
            cursor.executemany(sql, params)
    return len(rows)


def replace_evidence(patient_id: str, chunks: list[EvidenceChunk], provider=None,
                     pseudonymizer: Callable[[str], str] | None = None) -> int:
    """Všechny odstavce pacienta znovu (smaže staré řádky téhož embedding modelu, jiné modely nechá).

    ``pseudonymizer`` = ``Pseudonymizer`` se jmény pacienta a lékařů (``indexing.index_patient``);
    bez něj jen vzory (RČ, e-mail, telefon, datum narození).
    """
    if any(c.PatientId != patient_id for c in chunks):
        raise ValueError(f'Chunky musí patřit pacientovi {patient_id}')
    return _replace('EvidenceChunk', chunks, 'PatientId = ?', [patient_id], provider,
                    pseudonymizer or pseudonymize_text)


def replace_guidelines(guideline_set: str, passages: list[GuidelineChunk], provider=None) -> int:
    if any(p.GuidelineSet != guideline_set for p in passages):
        raise ValueError(f'Pasáže musí patřit sadě {guideline_set}')
    return _replace('GuidelineChunk', passages, 'GuidelineSet = ?', [guideline_set], provider)


def replace_trial_criteria(study_id: str, criteria: list[TrialCriterion], provider=None) -> int:
    if any(c.StudyId != study_id for c in criteria):
        raise ValueError(f'Kritéria musí patřit studii {study_id}')
    return _replace('TrialCriterion', criteria, 'StudyId = ?', [study_id], provider)


# ── Čtení ─────────────────────────────────────────────────────────────────────

def _select(name: str, where: dict[str, object], top: int | None = None, query_vector=None) -> list[dict]:
    """SELECT nad tabulkou; ``where`` = {sloupec: hodnota | seznam (IN)}; s ``query_vector`` přidá Score."""
    cls = _COLUMNS[name][0]
    cols = [f.name for f in fields(cls)]
    select = ', '.join(cols)
    params: list = []
    if query_vector is not None:
        select += ', VECTOR_COSINE(Embedding, TO_VECTOR(?, DOUBLE)) AS Score'
        params.append(_vector_param(query_vector))
    clauses = []
    for col, value in where.items():
        if isinstance(value, (list, tuple, set)):
            values = list(value)
            clauses.append(f'{col} IN ({", ".join("?" * len(values))})')
            params += values
        else:
            clauses.append(f'{col} = ?')
            params.append(value)
    sql = f'SELECT {f"TOP {int(top)} " if top else ""}{select} FROM {_table(name)}'
    if clauses:
        sql += ' WHERE ' + ' AND '.join(clauses)
    if query_vector is not None:
        sql += ' ORDER BY Score DESC'
    with _cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    out = []
    for row in rows:
        item = dict(zip(cols + (['Score'] if query_vector is not None else []), row))
        if item.get('DocDate') is not None:
            item['DocDate'] = str(item['DocDate'])
        if 'Score' in item:
            item['Score'] = float(item['Score'])
        out.append(item)
    return out


def _search(name: str, query: str, where: dict, top_k: int, provider=None) -> list[dict]:
    provider = ai_service.embedding_provider(provider)
    vector = embed([query], ai_service.TASK_RETRIEVAL_QUERY, provider)[0]
    rows = _select(name, {**where, 'EmbeddingModel': embedding_model_id(provider)}, top_k, vector)
    if not rows:
        logger.warning('%s: žádné řádky pro %s a model %s (chybí ingest / reindex?)',
                       _table(name), where, embedding_model_id(provider))
    return rows


def search_evidence(patient_id: str, query: str, top_k: int = 8, provider=None) -> list[dict]:
    """Odstavce **jen tohoto pacienta** seřazené podle podobnosti s dotazem (T-102 DoD, NFR-2)."""
    if not patient_id:
        raise ValueError('search_evidence vyžaduje patient_id (grounding = filtr na pacienta)')
    return _search('EvidenceChunk', query, {'PatientId': patient_id}, top_k, provider)


def search_guidelines(query: str, guideline_sets: Iterable[str] | None = None, top_k: int = 8,
                      provider=None) -> list[dict]:
    """Pasáže guidelines; ``guideline_sets`` typicky z ``rules.guideline_sets.guideline_sets_for(icd10)``."""
    where = {'GuidelineSet': list(guideline_sets)} if guideline_sets else {}
    return _search('GuidelineChunk', query, where, top_k, provider)


def search_trial_criteria(query: str, study_ids: Iterable[str] | None = None, top_k: int = 8,
                          provider=None) -> list[dict]:
    where = {'StudyId': list(study_ids)} if study_ids else {}
    return _search('TrialCriterion', query, where, top_k, provider)


def get_evidence_chunks(patient_id: str, resource_id: str | None = None) -> list[dict]:
    where = {'PatientId': patient_id, **({'ResourceId': resource_id} if resource_id else {})}
    return sorted(_select('EvidenceChunk', where), key=lambda r: (r['ResourceId'], r['ChunkIndex']))


def get_guideline(evidence_id: str) -> dict | None:
    rows = _select('GuidelineChunk', {'EvidenceId': evidence_id})
    return rows[0] if rows else None


def get_trial_criterion(evidence_id: str) -> dict | None:
    rows = _select('TrialCriterion', {'EvidenceId': evidence_id})
    return rows[0] if rows else None


def counts() -> dict[str, dict[str, int]]:
    """Počty řádků podle modelu embeddingů: {"MDT.EvidenceChunk": {"mock:hashed@1536": 555}}."""
    out = {}
    with _cursor() as cursor:
        for name in TABLES:
            if not _table_exists(cursor, name):
                continue
            # %EXACT: GROUP BY v IRIS vrací hodnotu v kolaci SQLUPPER ("MOCK:HASHED@1536"), Q16
            cursor.execute(
                f'SELECT %EXACT(EmbeddingModel), COUNT(*) FROM {_table(name)} GROUP BY %EXACT(EmbeddingModel)'
            )
            out[_table(name)] = {model: n for model, n in cursor.fetchall()}
    return out


def similarity(text: str, evidence_ids: Iterable[str], task_type: str | None = None,
               provider=None) -> dict[str, float]:
    """Kosinová podobnost tvrzení s citovanými zdroji (grounding v2, T-213, ARCH §5.3 bod 4).

    Odstavec ``P03-img03#2`` → ten odstavec; resource ``P03-img03`` → nejlepší z jeho odstavců;
    ``KRC-2.4`` / ``EXT-…`` → pasáž; ``RKT-03/V3`` → kritérium. ID bez vektoru ve výsledku chybí.
    """
    provider = ai_service.embedding_provider(provider)
    model_id = embedding_model_id(provider)
    by_table: dict[tuple[str, str], list[str]] = {}
    for eid in evidence_ids:
        ref = parse_evidence_id(eid)
        if ref is None:
            continue
        if ref.kind == 'paragraph':
            by_table.setdefault(('EvidenceChunk', 'EvidenceId'), []).append(eid)
        elif ref.kind == 'resource' and ref.patient_id:
            by_table.setdefault(('EvidenceChunk', 'ResourceId'), []).append(eid)
        elif ref.kind in ('guideline', 'external'):
            by_table.setdefault(('GuidelineChunk', 'EvidenceId'), []).append(eid)
        elif ref.kind == 'trial_criterion':
            by_table.setdefault(('TrialCriterion', 'EvidenceId'), []).append(eid)
    if not by_table:
        return {}
    vector = embed([text], task_type or ai_service.TASK_FACT_VERIFICATION, provider)[0]
    scores: dict[str, float] = {}
    for (name, col), ids in by_table.items():
        for row in _select(name, {col: ids, 'EmbeddingModel': model_id}, query_vector=vector):
            eid = row[col]
            scores[eid] = max(scores.get(eid, -1.0), row['Score'])
    return scores
