/**
 * API podkladu pro komisi (ARCHITEKTURA §6.3): podklad, generování přes job a zdroje citací.
 */
import { apiFetch, apiUrl } from '@/lib/api';
import type {
  BoardRecord,
  Brief,
  BriefConfig,
  CaseAnswer,
  CaseTemplate,
  RuleInfo,
  SimilarCases,
  MdtRole,
  MyTemplates,
  ProjectorLayout,
  RoleId,
  SectionId,
  TemplateArea,
  TemplateCatalog,
  SpecialtyView,
  Decision,
  EvidenceSource,
  IntakePrefill,
  Me,
  MdtCase,
  MdtTask,
  PatientDetail,
  PatientListItem,
  Practitioner,
  ProcedureCompatibility,
  Readiness,
  TaskStatus,
  MdtSession,
  MdtSessionDetail,
  MdtSessionListItem,
  ObservationSeries,
  SessionMessage,
  TimelineEvent,
} from '@/types/mdt';

/** Úprava boardu (jen předseda); změna data přepíše termín v `Task` všech případů v IRIS. */
export type SessionInput = { title: string; date: string; status?: MdtSession['status'] };

/** GET /api/jobs/{jid}/ (polling à 1 s, D-004). */
export interface GenerationJob {
  id: number;
  kind: 'brief' | 'scribe' | 'patient_summary';
  case_id: number;
  status: 'queued' | 'running' | 'done' | 'error';
  progress: number;
  result_id: number | null;
  error: string | null;
}

/** GET /api/mdt/cases/{cid}/brief/ vrací Brief + identifikaci uloženého podkladu. */
export type StoredBrief = Brief & { brief_id?: number; created_at?: string };

/** Shrnutí pro pacienta (BON-4), `Decision.patient_summary` §8.4. */
export type PatientSummary = NonNullable<Decision['patient_summary']>;

/** Hodnota z vložené zprávy (BON-7, ARCH §6.3); `source` = znění odstavce, `reasons` jen u neověřených. */
export interface ImportValue {
  kind: 'lab' | 'biomarker' | 'ecog' | 'tnm' | 'vital';
  label: string;
  value_text: string;
  value_number?: number | null;
  unit?: string | null;
  date?: string | null;
  paragraph: number;
  citation: string;
  source?: string | null;
  reasons?: string[];
}

/** POST /api/mdt/patients/{pid}/import/: návrh, nic se nezapisuje. */
export interface ImportProposal {
  patient_id: string;
  document_id: string;
  title: string;
  date: string | null;
  text: string;
  values: ImportValue[];
  rejected: ImportValue[];
}

/** POST /api/mdt/users/ (předseda, T-338): profil a šablony nového lékaře. */
export interface NewDoctorInput {
  username: string;
  password: string;
  email?: string;
  first_name: string;
  last_name: string;
  title_before?: string;
  title_after?: string;
  specialty: RoleId;
  role: MdtRole;
  templates?: Partial<Record<TemplateArea, ProjectorLayout>>;
  preset?: string;
}

/** Údaj nominace v návrhu nového pacienta s citací odstavce podkladu (`null` = upravil lékař). */
export type DraftText = { text: string; citation: string | null };

/** Návrh nového pacienta (`/api/mdt/patient-drafts/`, T-323, ARCH §8.6); RČ se nevrací nikdy. */
export interface PatientDraft {
  id: number;
  status: 'draft' | 'confirmed';
  patient_id: string;
  synthetic: boolean;
  session: { id: number; title: string; date: string } | null;
  case_id: number | null;
  documents: { id: string; title: string; date: string | null; text?: string; source?: string }[];
  fields?: {
    nomination_type: 'primarni' | 'restaging' | 'progrese';
    question?: DraftText | null;
    histology?: DraftText | null;
    history?: DraftText | null;
    comorbidities?: DraftText | null;
    preferences?: DraftText | null;
    diagnoses: (DraftText & { code: string })[];
    tnm?: (DraftText & { date?: string | null }) | null;
    ecog?: { value: number; citation: string | null; date?: string | null } | null;
  };
  edited?: string[];
  values?: ImportValue[];
  rejected?: ImportValue[];
  ai?: { used: boolean; reason: string | null };
  /** Import z FHIR JSON (T-335): soubor, přečíslování, počty resources podle typu, lékaři z bundlu. */
  import?: {
    file: string;
    total: number;
    renamed_from: string | null;
    counts: Record<string, number>;
    practitioners: string[];
    synthetic: boolean;
    /** Přepis `.md` nahraný k bundlu a nesoulady přepisu proti bundlu (prázdné = sedí). */
    transcript?: string | null;
    validation?: string[];
  } | null;
  /** Náhledy bez LLM nad návrhem (T-323): celý podklad, úzký pás pro projektor, šablona a kontrola úplnosti. */
  preview?: { detail: Brief; narrow: Brief; template: CaseTemplate | null; intake: IntakePrefill };
  /** Jen v odpovědi na založení ze souboru s víc pacienty: návrh pro každého (T-335). */
  batch?: { id: number; patient_id: string; file: string; renamed_from: string | null }[];
  /** `rc_masked` je null u importu z FHIR JSON bez RČ (dataset RČ nemá). */
  patient?: { rc_masked: string | null; sex: 'male' | 'female'; birth_year: number; age: number };
  missing_for_confirm?: string[];
}

/** PATCH návrhu: pole nominace upravená lékařem (text `''` = smazat). */
export type PatientDraftEdits = {
  question?: string;
  tnm?: string;
  ecog?: number | null;
  diagnoses?: { code: string; text?: string }[];
};

const fileBody = (name: string, file: Blob) => {
  const data = new FormData();
  data.append(name, file);
  return data;
};

export const mdtApi = {
  getMe: () => apiFetch<Me>('/api/mdt/me/'),
  /** Tituly si lékař upraví sám (T-338); roli a odbornost mění předseda. */
  updateMyTitles: (input: { title_before?: string; title_after?: string }) =>
    apiFetch<Me>('/api/mdt/me/', { method: 'PATCH', body: JSON.stringify(input) }),

  /** Uživatelé s rolí a odborností (`Me[]`), jen předseda (T-319). */
  getUsers: () => apiFetch<Me[]>('/api/mdt/users/'),
  /** Předseda založí lékaře s profilem a šablonou (T-338). */
  createUser: (input: NewDoctorInput) => apiFetch<Me>('/api/mdt/users/', { method: 'POST', body: JSON.stringify(input) }),

  /** Šablony klíčových údajů přihlášeného lékaře po oblastech + presety (T-338). */
  getTemplates: () => apiFetch<MyTemplates>('/api/mdt/templates/'),
  saveTemplate: (area: TemplateArea, layout: ProjectorLayout, preset?: string) =>
    apiFetch<MyTemplates['templates'][number]>(`/api/mdt/templates/${area}/`, { method: 'PUT', body: JSON.stringify({ layout, preset }) }),
  deleteTemplate: (area: TemplateArea) =>
    apiFetch<MyTemplates['templates'][number]>(`/api/mdt/templates/${area}/`, { method: 'DELETE' }),
  getTemplateCatalog: (area: TemplateArea) => apiFetch<TemplateCatalog>(`/api/mdt/templates/catalog/?area=${area}`),

  /** Lékaři nemocnice z IRIS pro výběr přítomných, vlastníků úkolů a spolupracovníků (T-328). */
  getPractitioners: (filter: { q?: string; withUser?: boolean; limit?: number } = {}) => {
    const params = new URLSearchParams();
    if (filter.q) params.set('q', filter.q);
    if (filter.withUser) params.set('with_user', '1');
    params.set('limit', String(filter.limit ?? 500));
    return apiFetch<Practitioner[]>(`/api/mdt/practitioners/?${params}`);
  },

  /** Změna role, odbornosti a propojení s lékařem v IRIS (jen předseda; sám sobě roli předsedy odebrat nejde). */
  updateUser: (userId: number, input: { role?: MdtRole; specialty?: RoleId; practitioner_id?: string; title_before?: string; title_after?: string; first_name?: string; last_name?: string }) =>
    apiFetch<Me>(`/api/mdt/users/${userId}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  /** Doporučená šablona projektoru podle diagnózy (T-318); 404 bez báze nebo diagnózy. */
  getTemplate: (caseId: number) => apiFetch<CaseTemplate>(`/api/mdt/cases/${caseId}/template/`),

  /** Pohled „pro mě“ podle odbornosti přihlášeného nebo `specialty` (T-319). */
  getForMe: (caseId: number, specialty?: RoleId) =>
    apiFetch<SpecialtyView>(`/api/mdt/cases/${caseId}/for-me/${specialty ? `?specialty=${specialty}` : ''}`),

  /** Boardy (zasedání) s pacienty v pořadí agendy, s agendami a připraveností (`expand=cases`, T-518). */
  getSessions: () => apiFetch<MdtSessionListItem[]>('/api/mdt/sessions/'),

  /** Záznam boardů (T-333, jen předseda): uzavřené boardy s přítomnými a výstupy pacientů. */
  getRecords: () => apiFetch<BoardRecord[]>('/api/mdt/records/'),
  getSessionRecord: (sessionId: number) => apiFetch<BoardRecord>(`/api/mdt/sessions/${sessionId}/record/`),

  /** Board + agenda: případy s hlavičkou pacienta z IRIS. */
  getSession: (sessionId: string) =>
    apiFetch<MdtSessionDetail>(`/api/mdt/sessions/${encodeURIComponent(sessionId)}/`),

  createSession: (input: SessionInput) =>
    apiFetch<MdtSession>('/api/mdt/sessions/', { method: 'POST', body: JSON.stringify(input) }),

  /** Presety a konfigurace podkladu (FR-R1); zakládá a mění jen předseda. */
  getConfigs: () => apiFetch<BriefConfig[]>('/api/mdt/configs/'),

  createConfig: (config: BriefConfig) =>
    apiFetch<BriefConfig>('/api/mdt/configs/', { method: 'POST', body: JSON.stringify(config) }),

  updateConfig: (configId: string, config: BriefConfig) =>
    apiFetch<BriefConfig>(`/api/mdt/configs/${encodeURIComponent(configId)}/`, { method: 'PUT', body: JSON.stringify(config) }),

  /** Pořadí pacientů v agendě (T-324, jen předseda): ID všech případů boardu v novém pořadí → agenda. */
  setAgendaOrder: (sessionId: number, caseIds: number[]) =>
    apiFetch<MdtSessionDetail>(`/api/mdt/sessions/${sessionId}/order/`, { method: 'PUT', body: JSON.stringify({ cases: caseIds }) }),

  updateSession: (sessionId: number, input: Partial<SessionInput> & { config_id?: number | null }) =>
    apiFetch<MdtSession>(`/api/mdt/sessions/${sessionId}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  /** Jen prázdný board (409, když má pacienty). */
  deleteSession: (sessionId: number) => apiFetch<void>(`/api/mdt/sessions/${sessionId}/`, { method: 'DELETE' }),

  /** Chat lékařů u zasedání (T-334): posledních 200 zpráv od nejstarší. */
  getSessionMessages: (sessionId: number) => apiFetch<SessionMessage[]>(`/api/mdt/sessions/${sessionId}/messages/`),

  /** Píše každý člen komise; `case_id` = štítek pacienta z agendy boardu. Uzavřený board 409. */
  postSessionMessage: (sessionId: number, input: { text: string; case_id?: number | null }) =>
    apiFetch<SessionMessage>(`/api/mdt/sessions/${sessionId}/messages/`, { method: 'POST', body: JSON.stringify(input) }),

  /** SSE stream nových zpráv pro `EventSource` (JWT jde v cookie); `after` doplní zprávy novější než toto ID. */
  sessionStreamUrl: (sessionId: number, after: number) => apiUrl(`/api/mdt/sessions/${sessionId}/stream/?after=${after}`),

  /** Přesun do jiného boardu (`session`), ECOG, záměr, checkbox, `acknowledge` (D-019), `status` (jen předseda). */
  updateCase: (caseId: number, input: Partial<Pick<MdtCase, 'session' | 'ecog' | 'intent' | 'imaging_recent_checked' | 'skipped_fields' | 'status' | 'projector_layout'>> & { acknowledge?: string[]; collaborators?: number[] }) =>
    apiFetch<MdtCase>(`/api/mdt/cases/${caseId}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  getBrief: (caseId: string) => apiFetch<StoredBrief>(`/api/mdt/cases/${encodeURIComponent(caseId)}/brief/`),

  /** Nový podklad; `feedback` = co bylo v předchozí verzi špatně (jde do promptů vybraných částí, T-323). */
  generateBrief: (caseId: string, body: { config_id?: string; config?: BriefConfig; feedback?: { text: string; sections?: SectionId[] } } = {}) =>
    apiFetch<{ job_id: number }>(`/api/mdt/cases/${encodeURIComponent(caseId)}/brief/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getJob: (jobId: number) => apiFetch<GenerationJob>(`/api/jobs/${jobId}/`),

  /** Draft nebo potvrzený závěr komise (404, dokud není). */
  getDecision: (caseId: string) => apiFetch<Decision>(`/api/mdt/cases/${encodeURIComponent(caseId)}/decision/`),

  /** Uložení draftu (předseda, lékař); server ho validuje podle §8.4, potvrzený závěr nejde měnit (409). */
  saveDecision: (caseId: string, decision: Decision) =>
    apiFetch<Decision>(`/api/mdt/cases/${encodeURIComponent(caseId)}/decision/`, {
      method: 'PUT',
      body: JSON.stringify(decision),
    }),

  /** Potvrzení předsedou (FR-C3): zápis do IRIS, vrátí závěr s `fhir_ids`. */
  confirmDecision: (caseId: string) =>
    apiFetch<Decision>(`/api/mdt/cases/${encodeURIComponent(caseId)}/decision/confirm/`, { method: 'POST' }),

  /** AI zapisovatel (BON-3): nahrávka nebo text přepisu → job → draft závěru s citacemi úseků. */
  scribe: (caseId: string, input: { audio: File } | { transcript: string }) =>
    apiFetch<{ job_id: number }>(`/api/mdt/cases/${encodeURIComponent(caseId)}/scribe/`, {
      method: 'POST',
      body: 'audio' in input ? fileBody('audio', input.audio) : JSON.stringify(input),
    }),

  /** Shrnutí pro pacienta (BON-4); 404, dokud nevzniklo. */
  getPatientSummary: (caseId: string) =>
    apiFetch<PatientSummary>(`/api/mdt/cases/${encodeURIComponent(caseId)}/patient-summary/`),

  /** Zpráva pro praktického lékaře (T-332); 404, dokud nevznikne se shrnutím pro pacienta. */
  getGpReport: (caseId: string) =>
    apiFetch<PatientSummary>(`/api/mdt/cases/${encodeURIComponent(caseId)}/gp-report/`),

  /** Nová verze potvrzeného závěru s důvodem změny (T-332, předseda). */
  reviseDecision: (caseId: string, reason: string) =>
    apiFetch<Decision>(`/api/mdt/cases/${encodeURIComponent(caseId)}/decision/revise/`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),

  /** Otázka nad případem: odpověď jen z dat pacienta v IRIS, s citacemi (T-332). */
  askCase: (caseId: number, question: string) =>
    apiFetch<CaseAnswer>(`/api/mdt/cases/${caseId}/ask/`, { method: 'POST', body: JSON.stringify({ question }) }),

  /** Podobné případy: předchozí závěry MDT jiných pacientů s obdobnou diagnózou (T-332). */
  getSimilarCases: (caseId: number) => apiFetch<SimilarCases>(`/api/mdt/cases/${caseId}/similar/`),

  /** Katalog pravidel varovných signálů pro nastavení podkladu (T-332). */
  getRules: () => apiFetch<RuleInfo[]>('/api/mdt/rules/'),

  /** Spustí shrnutí z potvrzeného závěru (409 bez potvrzení) → job. */
  generatePatientSummary: (caseId: string) =>
    apiFetch<{ job_id: number }>(`/api/mdt/cases/${encodeURIComponent(caseId)}/patient-summary/`, { method: 'POST' }),

  /** Vstup zprávy (BON-7): text nebo PDF → návrh hodnot s citací odstavce, nic se nezapisuje. */
  proposeImport: (patientId: string, input: { text: string } | { pdf: File }) =>
    apiFetch<ImportProposal>(`/api/mdt/patients/${encodeURIComponent(patientId)}/import/`, {
      method: 'POST',
      body: 'pdf' in input ? fileBody('pdf', input.pdf) : JSON.stringify(input),
    }),

  /** Potvrzení lékařem: server návrh znovu ověří a zapíše do IRIS s Provenance. */
  confirmImport: (proposal: ImportProposal) =>
    apiFetch<{ fhir_written: string[] }>(`/api/mdt/patients/${encodeURIComponent(proposal.patient_id)}/import/confirm/`, {
      method: 'POST',
      body: JSON.stringify(proposal),
    }),

  getEvidence: (evidenceId: string) =>
    apiFetch<EvidenceSource>(`/api/evidence/?id=${encodeURIComponent(evidenceId)}`),

  /** Pacienti z IRIS (hlavička bez jména a RČ). */
  getPatients: () => apiFetch<PatientListItem[]>('/api/patients/'),

  /** Nový pacient z RČ (T-323): rozpracované návrhy, založení z textu / souborů, úpravy, zápis do IRIS. */
  getPatientDrafts: () =>
    apiFetch<{ id: number; patient_id: string; documents: number; created_at: string; updated_at: string }[]>('/api/mdt/patient-drafts/'),
  getPatientDraft: (id: number) => apiFetch<PatientDraft>(`/api/mdt/patient-drafts/${id}/`),
  /** `rc` (u FHIR JSON nepovinné), `text?`, `files[]?` (PDF, TXT, jeden FHIR JSON), `synthetic?`, `session?`; 409 = RČ už v IRIS (`patient_id`) nebo v návrhu (`draft_id`). */
  createPatientDraft: (body: FormData) => apiFetch<PatientDraft>('/api/mdt/patient-drafts/', { method: 'POST', body }),
  addPatientDraftDocuments: (id: number, body: FormData) =>
    apiFetch<PatientDraft>(`/api/mdt/patient-drafts/${id}/documents/`, { method: 'POST', body }),
  updatePatientDraft: (id: number, fields: PatientDraftEdits) =>
    apiFetch<PatientDraft>(`/api/mdt/patient-drafts/${id}/`, { method: 'PATCH', body: JSON.stringify({ fields }) }),
  deletePatientDraft: (id: number) => apiFetch<void>(`/api/mdt/patient-drafts/${id}/`, { method: 'DELETE' }),
  confirmPatientDraft: (id: number) =>
    apiFetch<{ patient_id: string; case_id: number | null; synthetic: boolean; fhir_written: string[] }>(
      `/api/mdt/patient-drafts/${id}/confirm/`,
      { method: 'POST' },
    ),

  /** Detail pacienta: diagnózy, komorbidity, TNM v čase, ECOG lékař i pacient. */
  getPatient: (patientId: string) => apiFetch<PatientDetail>(`/api/patients/${encodeURIComponent(patientId)}/`),

  /** Předvyplnění formuláře zařazení: povinné údaje s citacemi a varování (FR-P4, §8.6). */
  getIntake: (patientId: string) =>
    apiFetch<IntakePrefill>(`/api/mdt/patients/${encodeURIComponent(patientId)}/intake/`),

  /** Zařazení pacienta do boardu (FR-P4); ruční ECOG a záměr se zapíší do IRIS s Provenance. */
  createCase: (
    body: Pick<MdtCase, 'session' | 'patient_id' | 'service_request_id' | 'ecog' | 'intent' | 'imaging_recent_checked' | 'skipped_fields'>
      & { acknowledge?: string[] },
  ) =>
    apiFetch<MdtCase>('/api/mdt/cases/', { method: 'POST', body: JSON.stringify(body) }),

  /** Kontrola připravenosti případu (BON-1): skóre úplnosti, nevyřešené údaje, zastaralý staging. */
  getReadiness: (caseId: number) => apiFetch<Readiness>(`/api/mdt/cases/${caseId}/readiness/`),

  /** Semafor souladu všech postupů se stavem pacienta (FR-D4), i červené. */
  getCompatibility: (caseId: number) =>
    apiFetch<ProcedureCompatibility[]>(`/api/mdt/cases/${caseId}/compatibility/`),

  /** Úkoly po zasedání z IRIS (FR-P3), filtr `status` a `patient`; `mine` jen moje, `drafts` i z nepotvrzených závěrů (T-328). */
  getTasks: (filter: { status?: TaskStatus; patient?: string; mine?: boolean; drafts?: boolean } = {}) => {
    const query = new URLSearchParams(
      Object.entries(filter).filter(([, v]) => v).map(([k, v]) => [k, v === true ? '1' : String(v)]),
    ).toString();
    return apiFetch<MdtTask[]>(`/api/mdt/tasks/${query ? `?${query}` : ''}`);
  },

  /** Změna stavu úkolu → `Task.status` v IRIS (předseda, lékař). */
  updateTask: (taskId: string, status: TaskStatus) =>
    apiFetch<MdtTask>(`/api/mdt/tasks/${encodeURIComponent(taskId)}/`, { method: 'PATCH', body: JSON.stringify({ status }) }),

  /** Časová osa pacienta z IRIS (seřazená podle data). */
  getTimeline: (patientId: string) =>
    apiFetch<TimelineEvent[]>(`/api/patients/${encodeURIComponent(patientId)}/timeline/`),

  /** Číselné řady (labs, hmotnost, ECOG, PROMs `proms:<linkId>`). */
  getObservations: (patientId: string, codes?: string[]) =>
    apiFetch<ObservationSeries[]>(
      `/api/patients/${encodeURIComponent(patientId)}/observations/${codes?.length ? `?code=${encodeURIComponent(codes.join(','))}` : ''}`,
    ),
};

/** Odkazy ke stažení výstupů (cookie relace jde s požadavkem, server vrátí přílohu). */
export const exportUrl = {
  pdf: (caseId: number | string) => apiUrl(`/api/mdt/cases/${encodeURIComponent(String(caseId))}/export.pdf`),
  fhir: (caseId: number | string) => apiUrl(`/api/mdt/cases/${encodeURIComponent(String(caseId))}/export.fhir.json`),
  /** Všechna PDF a FHIR boardu v jednom ZIP (T-333, jen předseda). */
  zip: (sessionId: number) => apiUrl(`/api/mdt/sessions/${sessionId}/export.zip`),
};
