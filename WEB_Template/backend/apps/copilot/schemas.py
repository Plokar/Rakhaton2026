"""
Datové kontrakty FE ↔ BE (ARCHITEKTURA §8). Zmrazeno v T-009.

Zrcadlo: ``WEB_Template/frontend/src/types/mdt.ts``. Změna jde nejdřív do ARCHITEKTURA §8,
pak sem i do ``mdt.ts`` a do fixtures ``data/fixtures/*.json`` (+ kopie ve frontendu).

Modely slouží zároveň jako ``response_schema`` pro Gemini (``services/ai_service.py``).
Validují jen strukturu a výčty. Sémantiku (citace u tvrzení, ≥ 2 zdroje u red flagu, barva
semaforu) hlídá grounding validátor a pravidla, ne pydantic: jedna chybná citace z LLM nesmí
shodit celý podklad, má skončit jako ``verification = "unverified"``.
"""
from __future__ import annotations

from typing import Annotated, Any, Iterator, Literal

from pydantic import BaseModel, Field

# ── §8.1 Společné typy ────────────────────────────────────────────────────────
EvidenceId = Annotated[str, Field(
    description='ID zdroje z datasetu: "P03-ecog03", "P03-img03#3", "KRC-2.4", "RKT-03/V3", "EXT-…"',
)]
Verification = Literal["verified", "unverified"]
Severity = Literal["high", "moderate", "low"]
Light = Literal["green", "orange", "red", "grey", "skipped"]
RoleId = Literal[
    "surgeon", "oncologist", "radiation_oncologist", "radiologist", "pathologist",
    "pulmonologist", "cardiologist", "patient",
]
SectionId = Literal[
    "summary", "timeline", "role_views", "red_flags", "decision_support", "trials",
    "questions", "anamnesis", "modalities", "mdt_question",
]
DetailLevel = Literal["brief", "standard", "detailed"]


class Claim(BaseModel):
    id: str
    kind: Literal["claim", "missing"]
    text: str = Field(description='U "missing": co chybí')
    citations: list[EvidenceId] = Field(description='U "claim" aspoň 1')
    verification: Verification = Field(
        default="unverified",
        description="Nastavuje grounding validátor, ne LLM",
    )
    expected_source: str | None = Field(default=None, description='U "missing": kde by měl údaj být')


class Criterion(BaseModel):
    """Kritérium studie nebo posouzení role.

    ``status`` popisuje, zda je kritérium splněné. U vylučujícího kritéria (``kind="exclusion"``)
    ``met`` znamená, že vylučující okolnost platí a pacient je vyřazen.
    """
    criterion_id: EvidenceId | None = Field(default=None, description='"RKT-03/V3" (u studií)')
    text: str
    kind: Literal["inclusion", "exclusion"] | None = None
    status: Literal["met", "not_met", "unknown"]
    citations: list[EvidenceId] = Field(description="Fakta pacienta")
    guideline: EvidenceId | None = Field(default=None, description='"KRC-2.1"')
    missing: str | None = Field(default=None, description="U unknown: co dodat")


# ── §8.5 BriefConfig (snapshot je součástí Brief) ─────────────────────────────
class SectionConfig(BaseModel):
    id: SectionId
    enabled: bool
    order: int
    detail: DetailLevel | None = None


class BriefConfig(BaseModel):
    id: str | None = None
    name: str
    sections: list[SectionConfig]
    roles_present: list[RoleId] = Field(description="Ovlivní role_views, posouzení i záložky")
    detail_level: DetailLevel
    language: Literal["cs", "sk", "en"]
    hide_unverified: bool


# ── §8.2 Brief (podklad) ──────────────────────────────────────────────────────
class Diagnosis(BaseModel):
    text: str
    icd10: str
    citation: EvidenceId


class Tnm(BaseModel):
    text: str
    stage: str | None = None
    citation: EvidenceId


class EcogPhysician(BaseModel):
    value: int = Field(ge=0, le=4)
    date: str
    citation: EvidenceId = Field(description="Observation LOINC 89247-1")
    entered_by: str | None = Field(default=None, description="Zadávající lékař (FR-P4)")


class EcogPatient(BaseModel):
    value: int = Field(ge=0, le=4)
    date: str
    citation: EvidenceId = Field(description="QuestionnaireResponse, položka samostatnost")
    answer_text: str


class Ecog(BaseModel):
    physician: EcogPhysician | None = None
    patient: EcogPatient | None = None


class Intent(BaseModel):
    letter: Literal["C", "P"]
    code: Literal["kurativni", "paliativni"]
    source: Literal["previous_mdt", "physician", "mdt_decision"]


class MdtQuestion(BaseModel):
    text: str = Field(description="ServiceRequest.reasonCode.text")
    citation: EvidenceId


class Comorbidity(BaseModel):
    text: str
    icd10: str | None = None
    citation: EvidenceId


class BriefHeader(BaseModel):
    display_name: str = Field(description='"P03 · muž · 67 let" (žádné jméno ani RČ, D-018)')
    age: int = Field(description="Extension vek-k-datu-mdt")
    sex: Literal["male", "female", "other", "unknown"]
    diagnosis: Diagnosis
    tnm: Tnm | None = Field(default=None, description="Dataset má TNM jako text")
    ecog: Ecog
    intent: Intent | None = None
    mdt_question: MdtQuestion
    mdt_date: str = Field(description="Task.restriction.period.start")
    comorbidities: list[Comorbidity]
    alerts: list[Claim] = Field(description="Alergie, implantáty, předchozí výkony (FR-A4)")


class RoleAssessment(BaseModel):
    role: RoleId
    question: str
    verdict: Literal["candidate", "conditional", "not_candidate", "insufficient_data"]
    criteria: list[Criterion]
    note: str = Field(description='"Podklad pro diskusi, rozhoduje lékař."')


class BriefSection(BaseModel):
    """Textová sekce podkladu (summary, timeline, anamnesis, role_views, modalities).

    Red flags, B2 (decision_support, trials, questions) a otázka pro MDT mají v Brief
    vlastní pole; ``config.sections`` určuje jen jejich pořadí a viditelnost.
    """
    id: SectionId
    role: RoleId | None = Field(default=None, description="Jen u role_views")
    title: str
    ai_generated: Literal[True] = True
    items: list[Claim]
    assessment: RoleAssessment | None = Field(default=None, description="Jen u role_views (FR-B7)")


class RedFlag(BaseModel):
    id: str
    rule: str = Field(description='"RF-ECOG" | "RF-TOX" | "RF-LLM" … (ARCHITEKTURA §5.4)')
    severity: Severity
    title: str
    description: str
    citations: list[EvidenceId] = Field(description="Aspoň 2 (oba zdroje)")
    guideline: EvidenceId | None = Field(default=None, description='"OBC-1.3"')
    verification: Verification = "unverified"


class TimelineEvent(BaseModel):
    """GET /api/patients/{pid}/timeline/"""
    date: str
    type: Literal["diagnosis", "procedure", "medication", "imaging", "pathology", "lab", "proms", "mdt", "document"]
    label: str
    citation: EvidenceId


# ── §8.3 DecisionSupport (B2) ─────────────────────────────────────────────────
class DerivedValue(BaseModel):
    formula: str
    inputs: list[EvidenceId]


class CompatibilityRuleResult(BaseModel):
    rule_id: str = Field(description='"VS-PLI-01" (katalog docs/POZADAVKY_LEKARE.md §5.3)')
    status: Light
    text: str = Field(description='"ppoDLCO 38 % < 60 % → zátěžový test"')
    patient_citations: list[EvidenceId]
    rule_citation: EvidenceId = Field(description='"PLI-3.1" | "RKT-06/Z4" | "EXT-…"')
    derived: DerivedValue | None = Field(default=None, description="Např. Cockcroft-Gault")


class TreatmentCompatibility(BaseModel):
    modality: str = Field(description="Kód mdt-modalita")
    owner_role: RoleId = Field(description="Kdo se k metodě vyjadřuje")
    overall: Light = Field(description="Nejhorší z rules: red > orange > grey > green")
    rules: list[CompatibilityRuleResult]
    patient_preferences: list[Claim] = Field(description="Štítek, barvu nemění")


class TreatmentOption(BaseModel):
    id: str
    title: str
    rationale: list[Claim] = Field(description="Vazba na fakta pacienta")
    guideline_citations: list[EvidenceId]
    prerequisites_missing: list[Claim] = Field(description='Co chybí (kind "missing")')
    considerations: list[str] = Field(description="Rizika, kontraindikace (citované v rationale)")
    compatibility: TreatmentCompatibility = Field(description="Semafor (FR-D4, §5.9); počítá kód, ne LLM")


class TrialScreening(BaseModel):
    study_id: str = Field(description='"RKT-03"')
    title: str
    overall: Literal["eligible", "potentially_eligible", "not_eligible"]
    criteria: list[Criterion] = Field(description='criterion_id "RKT-03/Z1"…')


class DiscussionQuestion(BaseModel):
    text: str
    citations: list[EvidenceId]


class DecisionSupport(BaseModel):
    treatment_options: list[TreatmentOption]
    trials: list[TrialScreening]
    discussion_questions: list[DiscussionQuestion] = Field(description="2–3 otázky")
    disclaimer: str = Field(description='"AI předkládá možnosti, nerozhoduje."')


class BriefStats(BaseModel):
    claims_total: int
    claims_unverified: int
    missing_total: int


class Brief(BaseModel):
    case_id: str
    patient_id: str = Field(description='"P03"')
    generated_at: str = Field(description="ISO 8601")
    model: str
    config: BriefConfig = Field(description="Snapshot")
    status: Literal["draft", "confirmed"]
    header: BriefHeader
    sections: list[BriefSection] = Field(description="V pořadí podle config")
    red_flags: list[RedFlag]
    decision_support: DecisionSupport | None = None
    stats: BriefStats


# ── §8.4 Decision (závěr komise) ──────────────────────────────────────────────
Source = Literal["ai", "human", "ai_edited"]


class Attendee(BaseModel):
    user_id: str
    name: str
    role: RoleId | Literal["chair"]


class SourcedText(BaseModel):
    text: str
    source: Source


class CitedText(BaseModel):
    text: str
    source: Source
    citations: list[EvidenceId]


class Recommendation(BaseModel):
    modality: str = Field(description="Kód mdt-modalita → CarePlan.activity")
    text: str
    source: Source


class TrialDecision(BaseModel):
    text: str
    study_ids: list[str]
    source: Source


class ReMdt(BaseModel):
    date: str
    reason: str


class ConditionalRecommendation(BaseModel):
    text: str
    missing: list[str]
    source: Source


class DecisionSections(BaseModel):
    """Sekce Composition „Záznam MDT“ v pořadí datasetu."""
    question: SourcedText = Field(description="Projednaná otázka")
    assessment: CitedText = Field(description="Klinické zhodnocení")
    intent: Literal["kurativni", "paliativni", "odlozeno"] = Field(description="Léčebný záměr")
    recommendation: list[Recommendation] = Field(description="Doporučený postup")
    extra_diagnostics: SourcedText | None = Field(default=None, description="Doplňující diagnostika")
    trial: TrialDecision | None = Field(default=None, description="Klinická studie")
    re_mdt: ReMdt | None = Field(default=None, description="Plánované re-MDT")
    conclusion: SourcedText = Field(description="Závěr MDT")
    conditional: ConditionalRecommendation | None = Field(
        default=None, description="Podmíněné doporučení u neúplného případu (OBC-1.1)",
    )
    tumor_priority: SourcedText | None = Field(
        default=None, description="Duplicita malignit: priorita a plán druhého nádoru (OBC-1.4)",
    )


class DecisionTask(BaseModel):
    id: str
    description: str
    owner: str = Field(description="LEK-… / role")
    due_date: str = Field(description="YYYY-MM-DD")
    status: Literal["requested", "in-progress", "completed"]
    source: Source


class ConfirmedBy(BaseModel):
    user_id: str
    name: str


class FhirIds(BaseModel):
    composition: str
    careplan: str
    careteam: str
    tasks: list[str]
    detected_issues: list[str]
    research_subjects: list[str]
    provenance: str
    document_reference_pdf: str | None = None


class Decision(BaseModel):
    case_id: str
    status: Literal["draft", "confirmed"]
    mdt_type: Literal["primarni", "progrese", "restaging"]
    attendees: list[Attendee] = Field(description="→ CareTeam")
    patient_present: bool
    sections: DecisionSections
    tasks: list[DecisionTask]
    red_flags_acknowledged: list[str] = Field(description="RedFlag.id → DetectedIssue")
    transcript_ref: EvidenceId | None = Field(default=None, description='"P03-mdt02-prepis" (BON-3)')
    confirmed_by: ConfirmedBy | None = None
    confirmed_at: str | None = None
    fhir_ids: FhirIds | None = Field(default=None, description="Po potvrzení")


# ── §8.6 Zařazení pacienta (MdtCase, IntakeWarning) ───────────────────────────
WarningKind = Literal["missing", "out_of_range", "conflict", "ai_uncertain"]   # CHYBÍ · MIMO NORMU · ROZPOR · NEJISTOTA AI


class IntakeField(BaseModel):
    id: str = Field(description='"bm.mmr" | "spiro.ppo_dlco" | "ecog.physician"')
    label: str
    value: str | None = None
    citation: EvidenceId | None = None
    status: Literal["present", "missing", "pending", "skipped"]
    required_by: EvidenceId | None = Field(default=None, description='Proč je údaj povinný: "KRC-1.1"')


class IntakeWarning(BaseModel):
    id: str = Field(description='Stabilní: pravidlo + citace, např. "RF-TOX:P03-neuro01"')
    kind: WarningKind
    severity: Severity
    title: str
    detail: str
    citations: list[EvidenceId]


class EcogPrefill(BaseModel):
    value: int = Field(ge=0, le=4)
    citation: EvidenceId


class IntakePrefill(BaseModel):
    """GET /api/mdt/patients/{pid}/intake/"""
    patient_id: str
    service_request_id: str = Field(description='"P03-zad01"')
    fields: list[IntakeField]
    warnings: list[IntakeWarning]
    ecog_physician: EcogPrefill | None = None
    intent_prefill: Literal["C", "P"] | None = Field(
        default=None, description="Z poslední MDT; „odloženo“ → nepředvyplněno",
    )


class CaseAuthor(BaseModel):
    user_id: int
    name: str


class AcknowledgedWarning(BaseModel):
    id: str
    by: int
    at: str


class MdtCase(BaseModel):
    """POST /api/mdt/cases/, PATCH /api/mdt/cases/{cid}/"""
    id: int | None = None
    session: int = Field(description="Board")
    patient_id: str
    service_request_id: str
    created_by: CaseAuthor | None = None
    ecog: int | None = Field(ge=0, le=4)
    intent: Literal["C", "P"] | None
    imaging_recent_checked: bool = Field(description="„Snímek mladší než 3 měsíce“")
    skipped_fields: list[str] = Field(description="IntakeField.id")
    acknowledged_warnings: list[AcknowledgedWarning]
    status: Literal["nominated", "ready", "in_discussion", "decided", "confirmed", "returned"]


# ── Pomocné funkce ────────────────────────────────────────────────────────────
def iter_claims(node: Any) -> Iterator[Claim]:
    """Všechny ``Claim`` v modelu (hlavička, sekce, B2…), do hloubky."""
    if isinstance(node, Claim):
        yield node
    elif isinstance(node, BaseModel):
        for name in type(node).model_fields:
            yield from iter_claims(getattr(node, name))
    elif isinstance(node, (list, tuple)):
        for item in node:
            yield from iter_claims(item)


def compute_stats(brief: Brief) -> BriefStats:
    """``Brief.stats`` ze všech ``Claim`` v podkladu (hlavička, sekce i B2)."""
    claims = list(iter_claims(brief))
    return BriefStats(
        claims_total=sum(c.kind == "claim" for c in claims),
        claims_unverified=sum(c.kind == "claim" and c.verification == "unverified" for c in claims),
        missing_total=sum(c.kind == "missing" for c in claims),
    )
