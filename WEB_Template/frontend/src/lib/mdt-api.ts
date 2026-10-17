/**
 * API podkladu pro komisi (ARCHITEKTURA §6.3): podklad, generování přes job a zdroje citací.
 */
import { apiFetch } from '@/lib/api';
import type {
  Brief,
  BriefConfig,
  CaseTemplate,
  MdtRole,
  RoleId,
  SpecialtyView,
  Decision,
  EvidenceSource,
  IntakePrefill,
  Me,
  MdtCase,
  MdtTask,
  PatientListItem,
  ProcedureCompatibility,
  Readiness,
  TaskStatus,
  MdtSession,
  MdtSessionDetail,
  MdtSessionListItem,
  ObservationSeries,
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

export const mdtApi = {
  getMe: () => apiFetch<Me>('/api/mdt/me/'),

  /** Uživatelé s rolí a odborností (`Me[]`), jen předseda (T-319). */
  getUsers: () => apiFetch<Me[]>('/api/mdt/users/'),

  /** Změna role a odbornosti uživatele (jen předseda; sám sobě roli předsedy odebrat nejde). */
  updateUser: (userId: number, input: { role?: MdtRole; specialty?: RoleId }) =>
    apiFetch<Me>(`/api/mdt/users/${userId}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  /** Doporučená šablona projektoru podle diagnózy (T-318); 404 bez báze nebo diagnózy. */
  getTemplate: (caseId: number) => apiFetch<CaseTemplate>(`/api/mdt/cases/${caseId}/template/`),

  /** Pohled „pro mě“ podle odbornosti přihlášeného nebo `specialty` (T-319). */
  getForMe: (caseId: number, specialty?: RoleId) =>
    apiFetch<SpecialtyView>(`/api/mdt/cases/${caseId}/for-me/${specialty ? `?specialty=${specialty}` : ''}`),

  /** Boardy (zasedání) s pacienty v pořadí agendy. */
  getSessions: () => apiFetch<MdtSessionListItem[]>('/api/mdt/sessions/'),

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

  updateSession: (sessionId: number, input: Partial<SessionInput> & { config_id?: number | null }) =>
    apiFetch<MdtSession>(`/api/mdt/sessions/${sessionId}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  /** Jen prázdný board (409, když má pacienty). */
  deleteSession: (sessionId: number) => apiFetch<void>(`/api/mdt/sessions/${sessionId}/`, { method: 'DELETE' }),

  /** Přesun do jiného boardu (`session`), ECOG, záměr, checkbox, `acknowledge` (D-019), `status` (jen předseda). */
  updateCase: (caseId: number, input: Partial<Pick<MdtCase, 'session' | 'ecog' | 'intent' | 'imaging_recent_checked' | 'skipped_fields' | 'status'>> & { acknowledge?: string[] }) =>
    apiFetch<MdtCase>(`/api/mdt/cases/${caseId}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  getBrief: (caseId: string) => apiFetch<StoredBrief>(`/api/mdt/cases/${encodeURIComponent(caseId)}/brief/`),

  generateBrief: (caseId: string, body: { config_id?: string; config?: BriefConfig } = {}) =>
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

  getEvidence: (evidenceId: string) =>
    apiFetch<EvidenceSource>(`/api/evidence/?id=${encodeURIComponent(evidenceId)}`),

  /** Pacienti z IRIS (hlavička bez jména a RČ). */
  getPatients: () => apiFetch<PatientListItem[]>('/api/patients/'),

  /** Předvyplnění formuláře zařazení: povinné údaje s citacemi a varování (FR-P4, §8.6). */
  getIntake: (patientId: string) =>
    apiFetch<IntakePrefill>(`/api/mdt/patients/${encodeURIComponent(patientId)}/intake/`),

  /** Zařazení pacienta do boardu (FR-P4); ruční ECOG a záměr se zapíší do IRIS s Provenance. */
  createCase: (body: MdtCase & { acknowledge?: string[] }) =>
    apiFetch<MdtCase>('/api/mdt/cases/', { method: 'POST', body: JSON.stringify(body) }),

  /** Kontrola připravenosti případu (BON-1): skóre úplnosti, nevyřešené údaje, zastaralý staging. */
  getReadiness: (caseId: number) => apiFetch<Readiness>(`/api/mdt/cases/${caseId}/readiness/`),

  /** Semafor souladu všech postupů se stavem pacienta (FR-D4), i červené. */
  getCompatibility: (caseId: number) =>
    apiFetch<ProcedureCompatibility[]>(`/api/mdt/cases/${caseId}/compatibility/`),

  /** Úkoly po zasedání z IRIS (FR-P3), filtr `status` a `patient`. */
  getTasks: (filter: { status?: TaskStatus; patient?: string } = {}) => {
    const query = new URLSearchParams(Object.entries(filter).filter(([, v]) => v) as [string, string][]).toString();
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
