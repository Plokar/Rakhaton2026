"""Plnění vektorových tabulek (ARCH §4.5).

- T-102: odstavce textů pacienta → ``MDT.EvidenceChunk``. Odstavce a jejich čísla jsou **jen** z
  ``services/ai/text.py`` (stejné jako v context builderu a resolveru, jinak ``P03-img03#2`` ukáže jinam).
- T-203: pasáže guidelines → ``MDT.GuidelineChunk`` (parser ``services/ai/guidelines.py``),
  kritéria studií (``Group.characteristic``) → ``MDT.TrialCriterion``.
- T-504: externí zdroje prahů semaforu ``EXT-…`` (``data/external_sources.json``) → ``MDT.GuidelineChunk``
  se sadou ``EXT`` a odkazem v ``Url`` (D-016). Jen pro pravidla semaforu, nikdy pro fakta pacienta.

``index_patient(pid)`` čte pacienta z IRIS FHIR, takže ho jde zavolat i po zápisu závěru komise
(T-209), aby šel nový ``Composition/Pxx-mdtNN`` vyhledat a citovat.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from services.ai.guidelines import parse_guidelines
from services.ai.text import resource_paragraphs
from services.fhir import client as fhir
from services.fhir.ids import parse_evidence_id
from services.iris import vector_store as vs
from services.rules.guideline_sets import GUIDELINE_SET_ORDER, ICD10_PREFIX_TO_SET

TEXT_TYPES = ('DocumentReference', 'DiagnosticReport', 'Composition', 'ServiceRequest')   # = services/ai/text.py
EXPECTED_GUIDELINES = {'KRC': 9, 'PRS': 14, 'PLI': 10, 'OBC': 9}                         # DATASET §7, celkem 42
EXTERNAL_SOURCES_FILE = Path(__file__).resolve().parent / 'data' / 'external_sources.json'
EXTERNAL_SET = 'EXT'
GUIDELINE_REGION = 'CZ'
_ISO_DATE = re.compile(r'\d{4}-\d{2}-\d{2}')


# ── T-102: odstavce pacienta ──────────────────────────────────────────────────

def _date(resource: dict) -> str | None:
    for field in ('date', 'effectiveDateTime', 'issued', 'authoredOn'):
        value = resource.get(field) or ''
        if _ISO_DATE.match(value):
            return value[:10]
    return None


def _title(resource: dict) -> str:
    rtype = resource['resourceType']
    if rtype == 'DocumentReference':
        return (resource.get('type') or {}).get('text') or resource.get('description') or 'Zpráva'
    if rtype == 'DiagnosticReport':
        return (resource.get('code') or {}).get('text') or 'Nález'
    if rtype == 'Composition':
        return resource.get('title') or 'Záznam'
    if rtype == 'ServiceRequest':
        return 'Nominace na MDT'
    return rtype


def _department(resource: dict) -> str:
    """Oddělení / zaměření z ``category[].text``; u DiagnosticReport pracoviště (kategorie bez kódu)."""
    categories = resource.get('category') or []
    if isinstance(categories, dict):
        categories = [categories]
    plain = [c['text'] for c in categories if c.get('text') and not c.get('coding')]
    texts = plain or [c['text'] for c in categories if c.get('text')]
    return ' · '.join(texts)


def evidence_chunks(patient_id: str, resources: Iterable[dict]) -> list[vs.EvidenceChunk]:
    """Odstavce všech textů pacienta, Evidence ID ``{resource id}#{n}``."""
    chunks = []
    for r in resources:
        if r.get('resourceType') not in TEXT_TYPES:
            continue
        title, department, date = _title(r)[:500], _department(r)[:200], _date(r)
        for p in resource_paragraphs(r):
            chunks.append(vs.EvidenceChunk(
                EvidenceId=f"{r['id']}#{p.index}", PatientId=patient_id, ResourceType=r['resourceType'],
                ResourceId=r['id'], ChunkIndex=p.index, CharStart=p.start, CharEnd=p.end,
                DocDate=date, Title=title, Department=department, Text=p.text,
            ))
    return chunks


def patient_resources_from_fhir(patient_id: str) -> list[dict]:
    return [r for rs in fhir.patient_everything(patient_id).values() for r in rs]


def index_patient(patient_id: str, resources: Iterable[dict] | None = None, provider=None) -> int:
    """Přepočítá ``MDT.EvidenceChunk`` pacienta. Bez ``resources`` čte aktuální stav z IRIS FHIR."""
    if resources is None:
        resources = patient_resources_from_fhir(patient_id)
    return vs.replace_evidence(patient_id, evidence_chunks(patient_id, resources), provider)


# ── T-203: guidelines a kritéria studií ───────────────────────────────────────

def _icd_prefixes(guideline_set: str) -> str:
    prefixes = sorted(p for p, s in ICD10_PREFIX_TO_SET.items() if s == guideline_set)
    return ','.join(prefixes) or '*'


def guideline_chunks(root: Path) -> list[vs.GuidelineChunk]:
    """Pasáže ze všech ``guidelines/*.md`` datasetu. Zdroj = nadpis souboru."""
    out = []
    for path in sorted((root / 'guidelines').glob('*.md')):
        markdown = path.read_text(encoding='utf-8')
        heading = next((line[2:].strip() for line in markdown.splitlines() if line.startswith('# ')), path.stem)
        for p in parse_guidelines(markdown):
            out.append(vs.GuidelineChunk(
                EvidenceId=p.evidence_id, GuidelineSet=p.guideline_set, Title=p.title[:300],
                Source=f'Rakathon 2026 – {heading}'[:200], Region=GUIDELINE_REGION,
                IcdPrefixes=_icd_prefixes(p.guideline_set), Text=p.text,
            ))
    return sorted(out, key=lambda c: (_set_order(c.GuidelineSet), _passage_number(c.EvidenceId)))


def _set_order(guideline_set: str) -> int:
    return GUIDELINE_SET_ORDER.index(guideline_set) if guideline_set in GUIDELINE_SET_ORDER else 99


def _passage_number(evidence_id: str) -> tuple[int, int]:
    major, minor = evidence_id.split('-', 1)[1].split('.')
    return int(major), int(minor)


def index_guidelines(chunks: list[vs.GuidelineChunk], provider=None) -> dict[str, int]:
    """Každou sadu zvlášť (smaže a vloží), takže jde přidat i ``EXT`` bez zásahu do ostatních (T-504)."""
    by_set: dict[str, list] = defaultdict(list)
    for c in chunks:
        by_set[c.GuidelineSet].append(c)
    return {s: vs.replace_guidelines(s, rows, provider) for s, rows in by_set.items()}


def external_chunks(path: Path = EXTERNAL_SOURCES_FILE) -> list[vs.GuidelineChunk]:
    """Katalog ``EXT-…`` (přepis docs/POZADAVKY_LEKARE.md §5.3, §6.1, §13). Stav ověření je součást textu."""
    out = []
    for item in json.loads(path.read_text(encoding='utf-8'))['sources']:
        ref = parse_evidence_id(item['evidence_id'])
        if ref is None or ref.kind != 'external':
            raise ValueError(f"{item['evidence_id']}: neplatné Evidence ID externího zdroje (EXT-…, ARCH §5.2)")
        out.append(vs.GuidelineChunk(
            EvidenceId=item['evidence_id'], GuidelineSet=EXTERNAL_SET, Title=item['title'][:300],
            Source=item['source'][:200], Region=item['region'], IcdPrefixes=item['icd_prefixes'],
            Text=f"{item['text']} [{item['verified']}; pravidla {', '.join(item['rules'])}]", Url=item['url'],
        ))
    return out


def trial_criteria(resources: Iterable[dict]) -> list[vs.TrialCriterion]:
    """Kritéria ze ``Group.characteristic`` studií; Evidence ID ``RKT-03/V3`` (DATASET §8)."""
    resources = list(resources)
    groups = {r['id']: r for r in resources if r.get('resourceType') == 'Group'}
    out = []
    for study in sorted((r for r in resources if r.get('resourceType') == 'ResearchStudy'), key=lambda r: r['id']):
        for enrollment in study.get('enrollment', []):
            group = groups.get(enrollment.get('reference', '').split('/')[-1])
            for ch in (group or {}).get('characteristic', []):
                code = (ch.get('code') or {}).get('text', '').strip()
                text = (ch.get('valueCodeableConcept') or {}).get('text') or ch.get('valueString') or ''
                if code and text:
                    out.append(vs.TrialCriterion(
                        EvidenceId=f"{study['id']}/{code}", StudyId=study['id'],
                        Kind='exclusion' if ch.get('exclude') else 'inclusion', Text=text[:2000],
                    ))
    return out


def trial_resources_from_fhir() -> list[dict]:
    return fhir.search('ResearchStudy') + fhir.search('Group')


def index_trials(criteria: list[vs.TrialCriterion], provider=None) -> dict[str, int]:
    by_study: dict[str, list] = defaultdict(list)
    for c in criteria:
        by_study[c.StudyId].append(c)
    return {s: vs.replace_trial_criteria(s, rows, provider) for s, rows in sorted(by_study.items())}


def guideline_count_warnings(chunks: list[vs.GuidelineChunk]) -> list[str]:
    got = Counter(c.GuidelineSet for c in chunks)
    return [f'guidelines {s}: {got.get(s, 0)} pasáží, DATASET §7 uvádí {n}'
            for s, n in EXPECTED_GUIDELINES.items() if got.get(s, 0) != n]
