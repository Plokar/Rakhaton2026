"""MCP server nad IRIS (T-308, ARCH §4.7): stejné nástroje, jaké používá copilot, pro libovolného MCP klienta.

Jen čtení: FHIR jen ``GET`` (``services/fhir/client.py``), IRIS SQL jen ``SELECT`` (``services/iris/vector_store.py``).
V produkci navíc dedikovaný IRIS uživatel jen pro čtení (env ``IRIS_USER`` / ``IRIS_PASSWORD`` procesu serveru).

Výstup jde do LLM klienta, proto (NFR-3):
- u ``Patient`` a ``Practitioner`` se zahodí jména, kontakty, adresy, identifikátory a datum narození;
- všechny texty projdou ``services/ai/pseudonymize.py`` (RČ, e-mail, telefon, datum narození);
- base64 přílohy se neposílají, text dokumentu vrací ``get_evidence``.

Nástroje jsou obyčejné funkce (``@mcp.tool`` v fastmcp 4 vrací původní funkci), takže jdou volat i přímo.
"""
from typing import Any

from fastmcp import FastMCP

from services.ai import context_builder
from services.ai.guidelines import GuidelinesUnavailable
from services.ai.pseudonymize import pseudonymize_text
from services.ai.text import resource_paragraphs, resource_text
from services.fhir import client as fhir
from services.fhir.ids import parse_evidence_id
from services.iris import vector_store as vs
from services.rules.guideline_sets import guideline_sets_for

READ_ONLY = {'readOnlyHint': True, 'destructiveHint': False, 'idempotentHint': True, 'openWorldHint': False}
MAX_TOP_K = 20
MAX_FHIR_RESULTS = 100

# Typy a search parametry, které fhir_query pustí dál. IRIS neznámé parametry tiše ignoruje (vrátil by všechno),
# proto allowlist místo předávání čehokoli.
FHIR_TYPES = (*fhir.PATIENT_TYPES, 'Patient', 'Practitioner', 'Organization', 'ResearchStudy', 'Group', 'Questionnaire')
FHIR_PARAMS = {'_id', 'patient', 'subject', 'code', 'category', 'date', 'status', '_sort', '_tag'}
_PERSON_FIELDS = ('name', 'telecom', 'address', 'photo', 'contact', 'identifier', 'birthDate')

mcp = FastMCP(
    'MDT Copilot · IRIS',
    instructions=(
        'Data onkologických pacientů (fiktivní dataset Rakathon 2026) v InterSystems IRIS for Health: FHIR R4 + '
        'Vector Search. Pacienti P01–P06. Každé tvrzení o pacientovi cituj Evidence ID ze zdroje '
        '(např. P03-img03#1, P03-lab06-cea, KRC-2.4, RKT-03/V3); když údaj chybí, řekni to a nehádej.'
    ),
)


def _clean(node: Any) -> Any:
    """Pseudonymizace a bez base64 příloh (do LLM klienta jde jen text)."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key == 'data' and isinstance(value, str):
                out[key] = '(base64 vynecháno, text vrací get_evidence)'
            else:
                out[key] = _clean(value)
        return out
    if isinstance(node, list):
        return [_clean(v) for v in node]
    if isinstance(node, str):
        return pseudonymize_text(node)
    return node


def _redact(resource: dict) -> dict:
    if resource.get('resourceType') in ('Patient', 'Practitioner', 'RelatedPerson'):
        resource = {k: v for k, v in resource.items() if k not in _PERSON_FIELDS}
    return _clean(resource)


def _rows(rows: list[dict], fields: tuple[str, ...]) -> list[dict]:
    out = []
    for row in rows:
        item = {f: row.get(f) for f in fields if row.get(f) not in (None, '')}
        item['Text'] = pseudonymize_text(row.get('Text'))
        item['Score'] = round(row['Score'], 4)
        out.append(item)
    return out


def _top(top_k: int) -> int:
    return max(1, min(int(top_k), MAX_TOP_K))


@mcp.tool(annotations=READ_ONLY)
def get_patient_context(patient_id: str, focus: str = '') -> str:
    """Celý kontext pacienta pro MDT jako text s Evidence ID na každém řádku (stejný jako pro Gemini v copilotu).

    patient_id: P01–P06. focus: volitelný dotaz (např. "resekabilita jater"); nejrelevantnější odstavce
    podle vektorového hledání v IRIS budou na začátku.
    """
    try:
        context = context_builder.build_context(patient_id)
    except GuidelinesUnavailable:
        context = context_builder.build_context(patient_id, guidelines=[])
    highlight = [r['EvidenceId'] for r in vs.search_evidence(patient_id, focus, top_k=8)] if focus else []
    return context.render(highlight=highlight)


@mcp.tool(annotations=READ_ONLY)
def search_evidence(patient_id: str, query: str, top_k: int = 8) -> list[dict]:
    """Odstavce zpráv, nálezů a záznamů MDT jednoho pacienta podle významové podobnosti (IRIS VECTOR_COSINE).

    Hledá vždy jen v datech daného pacienta. Vrací EvidenceId (citace), Score, datum, název a text odstavce.
    """
    rows = vs.search_evidence(patient_id, query, top_k=_top(top_k))
    return _rows(rows, ('EvidenceId', 'ResourceType', 'DocDate', 'Title', 'Department'))


@mcp.tool(annotations=READ_ONLY)
def search_guidelines(query: str, icd10: list[str] | None = None, top_k: int = 5) -> list[dict]:
    """Pasáže doporučených postupů (KRC, PRS, PLI, OBC) podle podobnosti s dotazem.

    icd10: diagnózy pacienta (např. ["C18.7", "C78.7"]) omezí sady podle diagnózy; OBC je vždy.
    Citace pasáže je její EvidenceId (např. KRC-2.4).
    """
    sets = guideline_sets_for(icd10) if icd10 else None
    rows = vs.search_guidelines(query, sets, top_k=_top(top_k))
    return _rows(rows, ('EvidenceId', 'GuidelineSet', 'Title', 'Source'))


@mcp.tool(annotations=READ_ONLY)
def search_trial_criteria(query: str, study_id: str = '', top_k: int = 5) -> list[dict]:
    """Kritéria zařazení (Zn) a vyřazení (Vn) klinických studií RKT-01…RKT-06 podle podobnosti s dotazem."""
    rows = vs.search_trial_criteria(query, [study_id] if study_id else None, top_k=_top(top_k))
    return _rows(rows, ('EvidenceId', 'StudyId', 'Kind'))


@mcp.tool(annotations=READ_ONLY)
def get_evidence(evidence_id: str) -> dict:
    """Zdroj citace: odstavec (P03-img03#1), celý resource (P03-lab06-cea), pasáž (KRC-2.4) nebo kritérium (RKT-03/V3)."""
    ref = parse_evidence_id(evidence_id)
    if ref is None:
        return {'evidence_id': evidence_id, 'error': 'neplatné Evidence ID (ARCHITEKTURA §5.2)'}
    if ref.kind in ('guideline', 'external'):
        row = vs.get_guideline(evidence_id)
        return {'evidence_id': evidence_id, 'kind': ref.kind, **(_clean(row) if row else {'error': 'pasáž nenalezena'})}
    if ref.kind == 'trial_criterion':
        row = vs.get_trial_criterion(evidence_id)
        return {'evidence_id': evidence_id, 'kind': ref.kind, **(_clean(row) if row else {'error': 'kritérium nenalezeno'})}
    try:
        resource = fhir.read(ref.resource_type, ref.resource_id)
    except fhir.FhirError as e:
        return {'evidence_id': evidence_id, 'error': f'{ref.resource_type}/{ref.resource_id}: {e}'}
    out = {'evidence_id': evidence_id, 'kind': ref.kind, 'resource_type': ref.resource_type}
    if ref.kind == 'paragraph':
        paragraphs = resource_paragraphs(resource)
        if ref.paragraph > len(paragraphs):
            return {**out, 'error': f'{ref.resource_id} má jen {len(paragraphs)} odstavců'}
        p = paragraphs[ref.paragraph - 1]
        return {**out, 'paragraph': p.index, 'char_start': p.start, 'char_end': p.end,
                'text': pseudonymize_text(p.text), 'resource_text': pseudonymize_text(resource_text(resource))}
    text = resource_text(resource)
    return {**out, 'resource': _redact(resource), **({'text': pseudonymize_text(text)} if text else {})}


@mcp.tool(annotations=READ_ONLY)
def fhir_query(resource_type: str, params: dict[str, str] | None = None) -> dict:
    """Read-only FHIR search v IRIS, např. ("Observation", {"patient": "P03", "code": "http://loinc.org|2039-6"}).

    Povolené parametry: _id, patient, subject, code, category, date, status, _sort, _tag (IRIS neznámé parametry
    tiše ignoruje, proto jiné odmítneme). Vrací nejvýš 100 resources, bez jmen, kontaktů a base64 příloh.
    """
    if resource_type not in FHIR_TYPES:
        return {'error': f'typ {resource_type} není povolený', 'allowed_types': list(FHIR_TYPES)}
    params = dict(params or {})
    unknown = set(params) - FHIR_PARAMS
    if unknown:
        return {'error': f'nepovolené parametry {sorted(unknown)}', 'allowed_params': sorted(FHIR_PARAMS)}
    resources = fhir.search(resource_type, **params)
    return {
        'resource_type': resource_type,
        'total': len(resources),
        'truncated': len(resources) > MAX_FHIR_RESULTS,
        'resources': [_redact(r) for r in resources[:MAX_FHIR_RESULTS]],
    }
