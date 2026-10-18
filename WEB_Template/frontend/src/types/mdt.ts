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
  /** Odkaz na externí zdroj EXT-… (T-504). */
  url?: string | null;
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
  /** → CareTeam; `user_id` = lékař v IRIS „LEK-…“ z výběru (T-328) */
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
    /** Zvažované možnosti z B2 a zvolený postup; `light` = semafor v okamžiku zápisu (zadání C, T-326). */
    options_considered?: { id: string; title: string; light?: Light | null; chosen: boolean }[];
    /** Soulad s doporučenými postupy: ano / ne + důvod odchylky (zadání B2, C). Odchylka neblokuje, chce zdůvodnění. */
    guideline_compliance?: { compliant: boolean; reason: string; citations: EvidenceId[] } | null;
    /** Odlišná stanoviska členů komise. */
    dissent?: { member: string; role: RoleId | 'chair'; text: string }[];
  };
  /** → Task */
  tasks: {
    id: string;
    description: string;
    /** Lékař v IRIS „LEK-…“ z výběru (T-328), u starších záznamů role */
    owner: string;
    /** Jméno lékaře pro zobrazení (T-328) */
    owner_name?: string | null;
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
    /** "P03-mdt02-pacient" (BON-4) */
    document_reference_patient?: string;
  };
  /** Shrnutí pro pacienta (BON-4): z potvrzeného závěru, každá věta s citací. */
  patient_summary?: { items: Claim[]; generated_at: string; document_reference: string };
}

// ── §8.5 BriefConfig ──────────────────────────────────────────────────────────

export interface BriefConfig {
  id?: string;
  name: string;
  /** Preset nabízený v konfigurátoru (GET /api/mdt/configs/). */
  is_preset?: boolean;
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

/** Blok úzkého panelu (okno projektoru, boční panel). */
export type ProjectorSection = 'anamnesis' | 'facts' | 'template' | 'treatments';

/** Pořadí na projektoru (T-332): bloky a ID klíčových údajů; prázdné = výchozí pořadí. */
export interface ProjectorLayout {
  sections?: ProjectorSection[];
  /** KeyFact.id v pořadí; ostatní údaje za nimi výchozím pořadím. */
  facts?: string[];
}

/** POST /api/mdt/cases/, PATCH /api/mdt/cases/{cid}/ */
export interface MdtCase {
  id?: number;
  /** Board. */
  session: number;
  patient_id: string;
  service_request_id: string;
  created_by?: { user_id: number; name: string };
  /** Přizvaní ke spolupráci (T-326): smějí případ upravovat; mění je předseda nebo zadávající lékař. */
  collaborators?: { user_id: number; name: string }[];
  ecog: number | null;
  intent: 'C' | 'P' | null;
  /** „Snímek mladší než 3 měsíce“ */
  imaging_recent_checked: boolean;
  /** IntakeField.id */
  skipped_fields: string[];
  acknowledged_warnings: { id: string; by: number; at: string }[];
  /** returned = vráceno k doplnění (OBC-1.1). */
  status: 'nominated' | 'ready' | 'in_discussion' | 'decided' | 'confirmed' | 'returned';
  /** Pořadí v agendě (jen čtení). */
  order?: number;
  /** Otázka pro MDT z nominace (jen čtení). */
  question?: string;
  /** Jen v detailu boardu (hlavička z IRIS, §8.2). */
  patient?: PatientListItem | null;
  /** Pořadí na projektoru (T-332); mění zadávající, přizvaný lékař nebo předseda. */
  projector_layout?: ProjectorLayout;
}

/** Stav údaje z katalogu `data/onko/udaje.tsv`: mention = jen zmínka („doporučeno“, „probíhá“). */
export type KbItemStatus = 'present' | 'mention' | 'stale' | 'missing' | 'not_applicable';

/** Údaj z katalogu báze u pacienta (T-318). */
export interface KbItem {
  /** "pli.vo2max" (ID báze; jde i do skipped_fields) */
  id: string;
  label: string;
  status: KbItemStatus;
  /** Kde je údaj (nebo zmínka) v podkladech. */
  citations: EvidenceId[];
  /** U "stale": stáří posledního výsledku. */
  age_days?: number;
  /** Jen ve SpecialtyView: "Chybí: …" / "Doporučeno: …" */
  warning?: IntakeWarning;
}

/** GET /api/mdt/cases/{cid}/template/ (T-318): doporučená šablona projektoru podle diagnózy. */
export interface CaseTemplate {
  /** "sab-pli-radikalni" */
  template_id: string;
  /** "NSCLC I–III: operabilita vs. chemoradioterapie" */
  name: string;
  /** Kdo má být u stolu (text pro konfigurátor). */
  specialties: string;
  sources: EvidenceId[];
  /** name "Šablona: …", is_preset */
  config: BriefConfig;
  /** Preset se stejným názvem (seed_mdt), pro POST …/brief/ {config_id}. */
  config_id: string | null;
  /** Klíčové údaje na projektor (T-310). */
  projector: KbItem[];
  trials: EvidenceId[];
  /** Všechna varování katalogu údajů (CHYBI:* i DOP:*). */
  warnings: IntakeWarning[];
}

/** GET /api/mdt/cases/{cid}/for-me/ (T-319): co jde lékaři dané odbornosti nahoru. */
export interface SpecialtyView {
  role: RoleId;
  template_id: string;
  /** "summary" první, pak sekce odbornosti, pak ostatní ze šablony. */
  sections: SectionId[];
  /** Údaje odbornosti v pořadí podle odbornosti, s varováním. */
  items: KbItem[];
  /** Postupy modalit, o kterých odbornost rozhoduje. */
  procedures: { id: string; title: string; sources: EvidenceId[] }[];
  interests: { specialty: string; what: string; why: string; sources: EvidenceId[] }[];
}

export type MdtRole = 'mdt_admin' | 'mdt_doctor' | 'mdt_viewer';

/** GET /api/mdt/me/ */
export interface Me {
  user_id: number;
  /** Demo: predseda | onkolog | pneumolog | chirurg | radiolog | patolog | radioterapeut */
  username: string;
  name: string;
  /** Superuser = mdt_admin, bez skupiny = mdt_viewer. */
  role: MdtRole;
  specialty: RoleId | null;
  /** Lékař v IRIS „LEK-…“, se kterým je účet propojený; podle něj „moje úkoly“ (T-328). */
  practitioner_id?: string | null;
}

/** GET /api/mdt/practitioners/ — lékař nemocnice z IRIS (FHIR Practitioner, T-328). */
export interface Practitioner {
  /** "LEK-P03-01" (dataset) | "LEK-APP-onkolog" (účet aplikace) */
  id: string;
  name: string;
  /** Text kvalifikace: „klinický onkolog (ošetřující lékař)“ */
  specialty: string;
  /** Odbornost odvozená z kvalifikace, `null` = neznámá */
  role: RoleId | null;
  /** Účet v aplikaci, když je s lékařem propojený */
  user: { user_id: number; username: string } | null;
}

/** Board = zasedání MDT (D-014). */
export interface MdtSession {
  id: number;
  /** Místní čas "2026-10-21T14:00:00+02:00". */
  date: string;
  /** "Mamární komise", "GIT – kolorektální karcinom / hepatobiliární" */
  title: string;
  status: 'planned' | 'in_progress' | 'closed';
  chair: { user_id: number; name: string } | null;
  /** Výchozí BriefConfig boardu. */
  config_id: number | null;
}

/**
 * Zpráva v chatu lékařů u zasedání (T-334): GET/POST /api/mdt/sessions/{sid}/messages/, nové zprávy
 * živě přes Server-Sent Events /api/mdt/sessions/{sid}/stream/. Zpráva se neupravuje ani nemaže.
 */
export interface SessionMessage {
  id: number;
  session: number;
  author: { user_id: number; name: string } | null;
  specialty: RoleId | null;
  /** Štítek pacienta, který byl při psaní na řadě; `null` = zpráva k celému zasedání. */
  case: { id: number; patient_id: string } | null;
  text: string;
  /** Místní čas "2026-10-21T14:03:12+02:00". */
  created_at: string;
}

/**
 * Chatbot u zasedání (T-338): dotaz lékaře (`role: "user"`) nebo odpověď AI (`"ai"`). Rozhovor je soukromý
 * (lékař + board), GET /api/mdt/sessions/{sid}/chatbot/; POST vrátí `[dotaz, odpověď]`. Odpověď AI není oficiální záznam.
 */
export interface ChatbotMessage {
  id: number;
  session: number;
  role: 'user' | 'ai';
  /** Pacient, na kterého se lékař ptal; `null` = obecný dotaz (jen guidelines a studie). */
  case: { id: number; patient_id: string } | null;
  /** Dotaz lékaře; u AI poznámka (např. bez jazykového modelu jen nejbližší místa v dokumentaci), jinak "". */
  text: string;
  /** Jen AI: tvrzení s citacemi po grounding validátoru, `"missing"` = údaj chybí. */
  claims: Claim[];
  /** Jen AI: NEJISTOTA AI (rozmezí, nejednoznačná zkratka, rozpor zdrojů). */
  uncertain: { text: string; citations: EvidenceId[] }[];
  /** Jen AI: model, který odpověděl; `null` = odpověď bez LLM. */
  model: string | null;
  created_at: string;
}

/** Přítomný lékař v záznamu boardu (z `Decision.attendees` všech závěrů boardu, T-333). */
export interface BoardRecordAttendee {
  /** Lékař v IRIS „LEK-…“, jinak volný kód. */
  id: string | null;
  name: string;
  role: RoleId | 'chair' | null;
  /** U kterých pacientů byl uvedený v závěru. */
  patients: string[];
}

/** Pacient v záznamu boardu: jméno a maskované RČ z IRIS jen tady (předseda), ne v hlavičkách (D-018). */
export interface BoardRecordCase {
  id: number;
  order: number;
  patient_id: string;
  status: MdtCase['status'];
  display_name: string;
  name: string | null;
  /** Maskované RČ, vidět jen poslední 4 číslice (T-323); u pacientů z datasetu null. */
  rc: string | null;
  diagnosis: { icd10: string; text: string } | null;
  decision: {
    status: 'draft' | 'confirmed';
    record_id: string | null;
    confirmed_at: string | null;
    confirmed_by: { user_id: number; name: string } | null;
  } | null;
  /** PDF jde u každého závěru (i návrhu), FHIR document Bundle jen u potvrzeného. */
  exports: { pdf: boolean; fhir: boolean };
}

/** GET /api/mdt/records/ (uzavřené boardy) a /api/mdt/sessions/{sid}/record/ (T-333, jen předseda). */
export interface BoardRecord extends MdtSession {
  attendees: BoardRecordAttendee[];
  cases: BoardRecordCase[];
  counts: { patients: number; confirmed: number };
}

/** GET /api/mdt/sessions/ */
export type MdtSessionListItem = MdtSession & { patients: string[] };

/** GET /api/mdt/sessions/{sid}/ (agenda) */
export type MdtSessionDetail = MdtSession & { cases: MdtCase[] };

/** GET /api/mdt/cases/{cid}/readiness/ (BON-1, OBC-1.1 / OBC-1.2) */
export interface Readiness {
  patient_id: string;
  status: 'ready' | 'incomplete';
  score: { present: number; total: number; percent: number };
  /** missing, pending nebo skipped; se zachovaným stavem (D-019). */
  unresolved: IntakeField[];
  stale_staging: { id: string; age_days: number; citation?: EvidenceId }[];
}

export type TaskStatus = 'requested' | 'in-progress' | 'completed';

/** GET /api/mdt/tasks/ → MdtTask[] (FR-P3) */
export interface MdtTask {
  /** "P03-mdt02-task01" (FHIR Task) */
  id: string;
  patient_id: string;
  /** "P03-mdt02" (Composition); `null` u úkolu z nepotvrzeného závěru */
  mdt_record: string | null;
  /** MdtCase se závěrem. */
  case_id: number | null;
  description: string;
  /** LEK-… / role */
  owner: { id: string | null; name: string };
  /** Task.restriction.period.end */
  due_date: string | null;
  status: TaskStatus;
  authored_on: string | null;
  /** Z CarePlan (activity „Plánované re-MDT“, scheduledPeriod.start). */
  re_mdt: { date: string | null; reason: string } | null;
  /** Úkol z nepotvrzeného závěru (`?drafts=1`, T-328): ještě není v IRIS, stav nejde měnit. */
  draft?: boolean;
}
