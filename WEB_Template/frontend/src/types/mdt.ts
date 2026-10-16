/**
 * Datové kontrakty FE ↔ BE (ARCHITEKTURA.md §8). Zmrazeno v T-009.
 *
 * Zrcadlo: WEB_Template/backend/apps/copilot/schemas.py (pydantic).
 * Změna jde nejdřív do ARCHITEKTURA §8, pak sem i do schemas.py a do fixtures
 * (data/fixtures/*.json + kopie v src/fixtures/).
 */

// ── §8.1 Společné typy ────────────────────────────────────────────────────────

/** "P03-ecog03" | "P03-img03#3" (3. odstavec) | "KRC-2.4" | "RKT-03/V3" | "EXT-EMA-DPD-2020" */
export type EvidenceId = string;
export type Verification = 'verified' | 'unverified';
export type Severity = 'high' | 'moderate' | 'low';
/** Semafor souladu postupu se stavem pacienta (§5.9); "skipped" = neposuzováno (lékař údaj přeskočil). */
export type Light = 'green' | 'orange' | 'red' | 'grey' | 'skipped';
export type RoleId =
  | 'surgeon'
  | 'oncologist'
  | 'radiation_oncologist'
  | 'radiologist'
  | 'pathologist'
  | 'pulmonologist'
  | 'cardiologist'
  | 'patient';
export type SectionId =
  | 'summary'
  | 'timeline'
  | 'role_views'
  | 'red_flags'
  | 'decision_support'
  | 'trials'
  | 'questions'
  | 'anamnesis'
  | 'modalities'
  | 'mdt_question';
export type DetailLevel = 'brief' | 'standard' | 'detailed';

export interface Claim {
  id: string;
  kind: 'claim' | 'missing';
  /** U "missing": co chybí. */
  text: string;
  /** U "claim" aspoň 1. */
  citations: EvidenceId[];
  /** Nastavuje grounding validátor, ne LLM. */
  verification: Verification;
  /** U "missing": kde by měl údaj být. */
  expected_source?: string;
}

/**
 * Kritérium studie nebo posouzení role. U vylučujícího kritéria (kind "exclusion")
 * znamená "met", že vylučující okolnost platí a pacient je vyřazen.
 */
export interface Criterion {
  /** "RKT-03/V3" (u studií). */
  criterion_id?: EvidenceId;
  text: string;
  kind?: 'inclusion' | 'exclusion';
  status: 'met' | 'not_met' | 'unknown';
  /** Fakta pacienta. */
  citations: EvidenceId[];
  /** "KRC-2.1" */
  guideline?: EvidenceId;
  /** U unknown: co dodat. */
  missing?: string;
}

// ── §8.2 Brief (podklad) ──────────────────────────────────────────────────────

export interface BriefHeader {
  /** "P03 · muž · 67 let" (žádné jméno ani RČ, D-018). */
  display_name: string;
  /** Extension vek-k-datu-mdt. */
  age: number;
  sex: 'male' | 'female' | 'other' | 'unknown';
  diagnosis: { text: string; icd10: string; citation: EvidenceId };
  /** Dataset má TNM jako text. */
  tnm?: { text: string; stage?: string; citation: EvidenceId };
  ecog: {
    /** Observation 89247-1; entered_by = zadávající lékař (FR-P4). */
    physician?: { value: number; date: string; citation: EvidenceId; entered_by?: string };
    /** PROMs samostatnost. */
    patient?: { value: number; date: string; citation: EvidenceId; answer_text: string };
  };
  /** Velké písmeno v hlavičce. */
  intent?: { letter: 'C' | 'P'; code: 'kurativni' | 'paliativni'; source: 'previous_mdt' | 'physician' | 'mdt_decision' };
  /** ServiceRequest.reasonCode.text */
  mdt_question: { text: string; citation: EvidenceId };
  /** Task.restriction.period.start */
  mdt_date: string;
  comorbidities: { text: string; icd10?: string; citation: EvidenceId }[];
  /** Alergie, implantáty, předchozí výkony (FR-A4). */
  alerts: Claim[];
}

export interface Brief {
  case_id: string;
  /** "P03" */
  patient_id: string;
  /** ISO 8601 */
  generated_at: string;
  /** "gemini-3.8-flash" */
  model: string;
  /** Snapshot. */
  config: BriefConfig;
  status: 'draft' | 'confirmed';
  header: BriefHeader;
  /** Textové sekce v pořadí podle config. */
  sections: BriefSection[];
  red_flags: RedFlag[];
  decision_support?: DecisionSupport;
  /** Ze všech Claim v podkladu (hlavička, sekce i B2). */
  stats: { claims_total: number; claims_unverified: number; missing_total: number };
}

/**
 * Textová sekce (summary, timeline, anamnesis, role_views, modalities). Red flags, B2
 * a otázka pro MDT mají v Brief vlastní pole; config.sections určuje jen jejich pořadí.
 */
export interface BriefSection {
  id: SectionId;
  /** Jen u role_views. */
  role?: RoleId;
  title: string;
  ai_generated: true;
  items: Claim[];
  /** Jen u role_views (FR-B7). */
  assessment?: RoleAssessment;
}

export interface RoleAssessment {
  role: RoleId;
  /** "Je pacient kandidátem resekce jaterních metastáz?" */
  question: string;
  verdict: 'candidate' | 'conditional' | 'not_candidate' | 'insufficient_data';
  criteria: Criterion[];
  /** "Podklad pro diskusi, rozhoduje lékař." */
  note: string;
}

export interface RedFlag {
  id: string;
  /** "RF-ECOG" | "RF-TOX" | "RF-LLM" … (ARCHITEKTURA §5.4) */
  rule: string;
  severity: Severity;
  title: string;
  description: string;
  /** Aspoň 2 (oba zdroje). */
  citations: EvidenceId[];
  /** "OBC-1.3" */
  guideline?: EvidenceId;
  verification: Verification;
}

/** GET /api/patients/{pid}/timeline/ → TimelineEvent[] (seřazené podle data) */
export interface TimelineEvent {
  /** "2026-09-21", může být částečné "2019-03". */
  date: string;
  type: 'diagnosis' | 'procedure' | 'medication' | 'imaging' | 'pathology' | 'lab' | 'proms' | 'mdt' | 'document';
  label: string;
  citation: EvidenceId;
}

/** GET /api/patients/ → PatientListItem[] */
export interface PatientListItem {
  /** "P03" */
  id: string;
  /** "P03 · muž · 67 let" */
  display_name: string;
  sex: 'male' | 'female' | 'other' | 'unknown';
  age: number | null;
  /** První onkologická. */
  diagnosis: { text: string; icd10: string; citation: EvidenceId } | null;
  /** ServiceRequest.reasonCode.text */
  mdt_question: string | null;
  /** "P03-zad01" */
  mdt_question_citation: EvidenceId | null;
  /** Task.restriction.period.start (ISO) */
  mdt_date: string | null;
}

/** GET /api/patients/{pid}/ */
export interface PatientDetail extends PatientListItem {
  diagnoses: { text: string; icd10: string; onset?: string; verification: string; stage: string | null; citation: EvidenceId }[];
  comorbidities: { text: string; icd10: string | null; citation: EvidenceId }[];
  /** Observation tnm, chronologicky. */
  tnm: { text: string; kind: string; date: string; citation: EvidenceId }[];
  ecog: {
    /** Poslední Observation 89247-1. */
    physician: { value: number; date: string; citation: EvidenceId } | null;
    /** Poslední PROMs samostatnost. */
    patient: { value: number; date: string; citation: EvidenceId; answer_text: string } | null;
  };
}

/** GET /api/evidence/?id=P03-img03%232 (400 neplatné ID, 404 nenalezeno) */
export interface EvidenceSource {
  evidence_id: EvidenceId;
  kind: 'resource' | 'paragraph' | 'guideline' | 'trial_criterion' | 'external';
  /** "CT břicha a pánve…", "KRC-2.4 – Restaging před resekcí", "RKT-03 – kritérium vyřazení V3" */
  title: string;
  /** Celý text zprávy / PROMs „otázka: odpověď“ / znění pasáže či kritéria. */
  text?: string | null;
  /** U "#n": text.slice(start, end). */
  highlight?: { paragraph: number; start: number; end: number } | null;
  resource_type?: string | null;
  resource_id?: string | null;
  patient_id?: string | null;
  date?: string | null;
  /** Category text ("RDG – Radiodiagnostické oddělení"). */
  department?: string | null;
  /** LEK-… + odbornost. */
  author?: { id: string; text: string; specialty: string | null } | null;
  /** Observation. */
  value?: {
    text: string;
    value: number | null;
    unit: string | null;
    ref_low: number | null;
    ref_high: number | null;
    interpretation: string | null;
  } | null;
  /** Observation → zdrojový dokument (derivedFrom + extension derived-from), bez další rekurze. */
  derived_from?: EvidenceSource[] | null;
  /** Guidelines. */
  source?: string | null;
  region?: string | null;
  /** Kritérium studie. */
  study_id?: string | null;
  criterion_kind?: 'inclusion' | 'exclusion' | null;
}

/** GET /api/patients/{pid}/observations/?code=718-7,lvef,proms:brneni → ObservationSeries[] */
export interface ObservationSeries {
  /** LOINC | druh z ID bez LOINC ("lvef") | "proms:<linkId>" */
  code: string;
  label: string;
  unit: string | null;
  points: {
    date: string;
    value: number;
    citation: EvidenceId;
    ref_low?: number;
    ref_high?: number;
    interpretation?: 'H' | 'L';
  }[];
}

// ── §8.3 DecisionSupport (B2) ─────────────────────────────────────────────────

export interface TreatmentOption {
  id: string;
  /** Např. "Resekce jater dvoudobě + resekce primárního tumoru". */
  title: string;
  /** Vazba na fakta pacienta. */
  rationale: Claim[];
  /** ["KRC-2.1", "KRC-2.5"] */
  guideline_citations: EvidenceId[];
  /** Co chybí (kind "missing"). */
  prerequisites_missing: Claim[];
  /** Rizika, kontraindikace (citované v rationale). */
  considerations: string[];
  /** Semafor souladu se stavem pacienta (FR-D4, §5.9); počítá kód, ne LLM. */
  compatibility: TreatmentCompatibility;
}

export interface TrialScreening {
  /** "RKT-03" */
  study_id: string;
  title: string;
  overall: 'eligible' | 'potentially_eligible' | 'not_eligible';
  /** criterion_id "RKT-03/Z1"… ; kind inclusion/exclusion */
  criteria: Criterion[];
}

export interface DecisionSupport {
  treatment_options: TreatmentOption[];
  trials: TrialScreening[];
  /** 2–3 otázky. */
  discussion_questions: { text: string; citations: EvidenceId[] }[];
  /** "AI předkládá možnosti, nerozhoduje." */
  disclaimer: string;
}

export interface CompatibilityRuleResult {
  /** "VS-PLI-01" (katalog docs/POZADAVKY_LEKARE.md §5.3) */
  rule_id: string;
  status: Light;
  /** "ppoDLCO 38 % < 60 % → zátěžový test" */
  text: string;
  /** ["P04-spiro04"] */
  patient_citations: EvidenceId[];
  /** "PLI-3.1" | "RKT-06/Z4" | "EXT-…" */
  rule_citation: EvidenceId;
  /** Např. Cockcroft-Gault. */
  derived?: { formula: string; inputs: EvidenceId[] };
}

export interface TreatmentCompatibility {
  /** Kód mdt-modalita. */
  modality: string;
  /** Kdo se k metodě vyjadřuje. */
  owner_role: RoleId;
  /** Nejhorší z rules: red > orange > grey > skipped > green. */
  overall: Light;
  rules: CompatibilityRuleResult[];
  /** Štítek, barvu nemění. */
  patient_preferences: Claim[];
}

/** GET /api/mdt/cases/{cid}/compatibility/ → ProcedureCompatibility[] (všechny postupy, i červené) */
export interface ProcedureCompatibility {
  id: string;
  title: string;
  guideline_citations: EvidenceId[];
  compatibility: TreatmentCompatibility;
}

// ── §8.4 Decision (závěr komise) ──────────────────────────────────────────────

export type Source = 'ai' | 'human' | 'ai_edited';

export interface Decision {
  case_id: string;
  status: 'draft' | 'confirmed';
  /** mdt-typ-projednani */
  mdt_type: 'primarni' | 'progrese' | 'restaging';
  /** → CareTeam */
  attendees: { user_id: string; name: string; role: RoleId | 'chair' }[];
  /** Extension mdt-ucast-pacienta. */
  patient_present: boolean;
  /** → Composition.section (pořadí jako záznam MDT v datasetu). */
  sections: {
    /** Projednaná otázka. */
    question: { text: string; source: Source };
    /** Klinické zhodnocení. */
    assessment: { text: string; source: Source; citations: EvidenceId[] };
    /** Léčebný záměr (mdt-lecebny-zamer). */
    intent: 'kurativni' | 'paliativni' | 'odlozeno';
    /** Doporučený postup (mdt-modalita) → CarePlan.activity. */
    recommendation: { modality: string; text: string; source: Source }[];
    /** Doplňující diagnostika. */
    extra_diagnostics?: { text: string; source: Source };
    /** Klinická studie. */
    trial?: { text: string; study_ids: string[]; source: Source };
    /** Plánované re-MDT. */
    re_mdt?: { date: string; reason: string };
    /** Závěr MDT. */
    conclusion: { text: string; source: Source };
    /** Podmíněné doporučení u neúplného případu (OBC-1.1). */
    conditional?: { text: string; missing: string[]; source: Source };
    /** Duplicita malignit: priorita a plán druhého nádoru (OBC-1.4). */
    tumor_priority?: { text: string; source: Source };
  };
  /** → Task */
  tasks: {
    id: string;
    description: string;
    /** LEK-… / role */
    owner: string;
    /** YYYY-MM-DD */
    due_date: string;
    status: 'requested' | 'in-progress' | 'completed';
    source: Source;
  }[];
  /** RedFlag.id → DetectedIssue */
  red_flags_acknowledged: string[];
  /** "P03-mdt02-prepis" (BON-3) */
  transcript_ref?: EvidenceId;
  confirmed_by?: { user_id: string; name: string };
  confirmed_at?: string;
  /** Po potvrzení. */
  fhir_ids?: {
    composition: string;
    careplan: string;
    careteam: string;
    tasks: string[];
    detected_issues: string[];
    research_subjects: string[];
    provenance: string;
    document_reference_pdf?: string;
  };
}

// ── §8.5 BriefConfig ──────────────────────────────────────────────────────────

export interface BriefConfig {
  id?: string;
  name: string;
  sections: { id: SectionId; enabled: boolean; order: number; detail?: DetailLevel }[];
  /** Ovlivní role_views, posouzení i záložky. */
  roles_present: RoleId[];
  detail_level: DetailLevel;
  language: 'cs' | 'sk' | 'en';
  hide_unverified: boolean;
}

// ── §8.6 Zařazení pacienta (MdtCase, IntakeWarning) ───────────────────────────

/** CHYBÍ · MIMO NORMU · ROZPOR · NEJISTOTA AI */
export type WarningKind = 'missing' | 'out_of_range' | 'conflict' | 'ai_uncertain';

export interface IntakeField {
  /** "bm.mmr" | "spiro.ppo_dlco" | "ecog.physician" */
  id: string;
  label: string;
  value?: string;
  citation?: EvidenceId;
  status: 'present' | 'missing' | 'pending' | 'skipped';
  /** Proč je údaj povinný: "KRC-1.1". */
  required_by?: EvidenceId;
}

export interface IntakeWarning {
  /** Stabilní: pravidlo + citace, např. "RF-TOX:P03-neuro01". */
  id: string;
  kind: WarningKind;
  severity: Severity;
  title: string;
  detail: string;
  citations: EvidenceId[];
}

/** GET /api/mdt/patients/{pid}/intake/ */
export interface IntakePrefill {
  patient_id: string;
  /** "P03-zad01" */
  service_request_id: string;
  fields: IntakeField[];
  warnings: IntakeWarning[];
  ecog_physician?: { value: number; citation: EvidenceId };
  /** Z poslední MDT; „odloženo“ → nepředvyplněno. */
  intent_prefill?: 'C' | 'P';
}

/** POST /api/mdt/cases/, PATCH /api/mdt/cases/{cid}/ */
export interface MdtCase {
  id?: number;
  /** Board. */
  session: number;
  patient_id: string;
  service_request_id: string;
  created_by?: { user_id: number; name: string };
  ecog: number | null;
  intent: 'C' | 'P' | null;
  /** „Snímek mladší než 3 měsíce“ */
  imaging_recent_checked: boolean;
  /** IntakeField.id */
  skipped_fields: string[];
  acknowledged_warnings: { id: string; by: number; at: string }[];
  /** returned = vráceno k doplnění (OBC-1.1). */
  status: 'nominated' | 'ready' | 'in_discussion' | 'decided' | 'confirmed' | 'returned';
}
