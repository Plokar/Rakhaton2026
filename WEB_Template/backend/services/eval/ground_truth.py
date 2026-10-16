"""Dev ground truth (T-013, ARCH §5.8): formát, načtení a kontrola proti datasetu.

Struktura kopíruje ohlášený oficiální ground truth (README datasetu): časová osa, klíčová fakta, red flags se
závažností, chybějící údaje s očekávanou reakcí AI, otázky k diskusi, RECIST, studie po kritériích a relevantní
pasáže guidelines. Navíc barvy semaforu (docs/POZADAVKY_LEKARE.md §5.4) a nejistoty AI (FR-R5).

Zdroj: DATASET.md §9 + ruční průzkum dat. **Není to oficiální ground truth.** Nesmí se odvozovat z výstupu
aplikace (pravidel ani LLM), jinak by eval (T-301) měřil sám sebe.

- ``also_acceptable`` / ``also_rules``: obhajitelné alternativy (např. nevyšetřené kritérium = ``unknown`` i
  ``not_met``); eval je má počítat jako shodu.
- ``importance``: ``key`` = hlavní nález datasetu, ``secondary`` = konvence týmu nebo vedlejší nález.
"""
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal['high', 'moderate', 'low']
Status = Literal['met', 'not_met', 'unknown']
Overall = Literal['eligible', 'potentially_eligible', 'not_eligible']
Light = Literal['green', 'orange', 'red', 'grey', 'skipped']
EventType = Literal['diagnosis', 'procedure', 'medication', 'imaging', 'pathology', 'lab', 'proms', 'mdt', 'document']
FactCategory = Literal['diagnosis', 'stage', 'histology', 'biomarker', 'performance', 'treatment', 'response',
                       'toxicity', 'imaging', 'lab', 'comorbidity', 'patient_voice', 'mdt', 'other']

# ARCHITEKTURA §5.4 (red flags); eval porovnává podle pravidla a citovaných ID
RED_FLAG_RULES = frozenset({
    'RF-ECOG', 'RF-PROMS', 'RF-TOX', 'RF-STALE', 'RF-MISSING', 'RF-MED', 'RF-NEWSYMPTOM', 'RF-LAB', 'RF-WEIGHT',
    'RF-GERI', 'RF-LESION', 'RF-GENETIC', 'RF-NOMINATION', 'RF-TNM', 'RF-IDENTITY', 'RF-PRIOR-PROC',
    'RF-DATAQUALITY', 'RF-PALIATIVE', 'RF-ROLES', 'RF-STEROID', 'RF-LLM',
})


class _Item(BaseModel):
    citations: list[str] = Field(min_length=1)


class MdtQuestion(BaseModel):
    text: str
    citation: str


class TimelineEvent(_Item):
    date: str                       # YYYY-MM-DD (nebo YYYY-MM)
    type: EventType
    label: str


class KeyFact(_Item):
    id: str                         # "P03-F01"
    category: FactCategory
    text: str


class RedFlag(BaseModel):
    id: str                         # "P03-RF01"
    rule: str                       # RF-* (ARCH §5.4)
    also_rules: list[str] = []      # obhajitelné jiné zařazení (např. RF-LLM vs. RF-TNM)
    severity: Severity
    importance: Literal['key', 'secondary']
    title: str
    description: str
    citations: list[str] = Field(min_length=2)   # oba zdroje (zadání: citace obou zdrojů)
    guideline: str | None = None    # pasáž guidelines; None jen u pravidel bez pasáže (ARCH §5.4 „—“)
    basis: str | None = None        # u guideline=None: proč (konvence týmu, konzultace…)

    @field_validator('rule')
    @classmethod
    def _known_rule(cls, v):
        if v not in RED_FLAG_RULES:
            raise ValueError(f'neznámé pravidlo {v}')
        return v


class MissingData(_Item):
    id: str
    field: str | None = None        # IntakeField.id (ARCH §8.6), když existuje: "bm.mmr"
    item: str
    required_by: str | None = None  # "KRC-1.1"
    expected_ai_reaction: str       # co má podklad říct („Údaj chybí…“), nikdy domýšlet


class Uncertainty(_Item):
    id: str
    text: str
    expected_ai_reaction: str       # NEJISTOTA AI (FR-R5)


class DiscussionQuestion(_Item):
    text: str
    guideline: list[str] = []


class RecistPoint(BaseModel):
    date: str
    sum_mm: float
    citation: str


class Recist(BaseModel):
    baseline: RecistPoint
    nadir: RecistPoint | None = None
    current: RecistPoint
    change_from_baseline_pct: float
    change_from_nadir_pct: float | None = None
    new_lesions: bool
    response: Literal['CR', 'PR', 'SD', 'PD']
    target_lesions: str
    note: str | None = None


class Criterion(_Item):
    criterion_id: str               # "RKT-03/V3"
    kind: Literal['inclusion', 'exclusion']
    status: Status                  # u vyřazovacího kritéria: met = kritérium platí (pacient vyřazen)
    also_acceptable: list[Status] = []
    missing: str | None = None      # u unknown: co dodat
    note: str | None = None


class Trial(BaseModel):
    study_id: str
    overall: Overall
    also_acceptable: list[Overall] = []
    criteria: list[Criterion] = []  # prázdné = vyřazeno už podle diagnózy
    note: str | None = None


class RuleColor(BaseModel):
    rule_id: str                    # "VS-KRC-01" (docs/POZADAVKY_LEKARE.md §5.3)
    status: Light
    patient_citations: list[str] = []
    note: str | None = None


class TreatmentOption(BaseModel):
    option: str
    guideline: list[str] = []
    overall: Light
    rules: list[RuleColor]


class PatientGroundTruth(BaseModel):
    patient_id: str
    version: str
    source: str
    mdt_date: str
    mdt_question: MdtQuestion
    timeline: list[TimelineEvent]
    key_facts: list[KeyFact]
    red_flags: list[RedFlag]
    missing_data: list[MissingData]
    ai_uncertainty: list[Uncertainty] = []
    discussion_questions: list[DiscussionQuestion] = Field(min_length=2)
    recist: Recist | None = None
    recist_note: str | None = None
    trials: list[Trial]
    guideline_passages: list[str]
    compatibility: list[TreatmentOption] = []     # celé možnosti léčby (POZADAVKY §5.4: P03, P04)
    compatibility_rules: list[RuleColor] = []     # jednotlivá pravidla z katalogu (sloupec Dataset v §5.3)
    new_findings: list[str] = []                  # nálezy nad rámec DATASET §9


def _repo_dir() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'data' / 'dev_ground_truth').is_dir():
            return parent / 'data' / 'dev_ground_truth'
    return None


def ground_truth_dir(path: str | Path | None = None) -> Path:
    root = Path(path) if path else _repo_dir()
    if root is None or not root.is_dir():
        raise FileNotFoundError('data/dev_ground_truth nenalezen (zadej cestu, např. --gt data/dev_ground_truth)')
    return root


def load(path: str | Path | None = None) -> dict[str, PatientGroundTruth]:
    """Všechny ``Pxx.json`` z adresáře, zvalidované modelem."""
    root = ground_truth_dir(path)
    out = {}
    for file in sorted(root.glob('P*.json')):
        gt = PatientGroundTruth.model_validate(json.loads(file.read_text(encoding='utf-8')))
        out[gt.patient_id] = gt
    return out


def source_of(evidence_id: str) -> str:
    """Citace se porovnávají na úrovni resource: ``P03-img03#2`` i ``P03-img03`` → ``P03-img03``."""
    return evidence_id.split('#', 1)[0]


def same_source(expected, got) -> bool:
    """Shoda citací pro eval (T-301): sdílí aspoň jeden zdroj (resource, pasáž, kritérium)."""
    return bool({source_of(e) for e in expected} & {source_of(g) for g in got})


def all_citations(gt: PatientGroundTruth) -> set[str]:
    """Všechna Evidence ID v souboru (kontrola, že existují v datasetu / guidelines / studiích)."""
    ids = {gt.mdt_question.citation}
    for group in (gt.timeline, gt.key_facts, gt.missing_data, gt.ai_uncertainty, gt.discussion_questions):
        for item in group:
            ids |= set(item.citations)
    for rf in gt.red_flags:
        ids |= set(rf.citations) | ({rf.guideline} if rf.guideline else set())
    for m in gt.missing_data:
        ids |= {m.required_by} if m.required_by and '-' in m.required_by else set()
    for q in gt.discussion_questions:
        ids |= set(q.guideline)
    if gt.recist:
        ids |= {p.citation for p in (gt.recist.baseline, gt.recist.nadir, gt.recist.current) if p}
    for t in gt.trials:
        for c in t.criteria:
            ids |= set(c.citations) | {c.criterion_id}
    for opt in gt.compatibility:
        ids |= set(opt.guideline)
        for r in opt.rules:
            ids |= set(r.patient_citations)
    for r in gt.compatibility_rules:
        ids |= set(r.patient_citations)
    ids |= set(gt.guideline_passages)
    return ids
