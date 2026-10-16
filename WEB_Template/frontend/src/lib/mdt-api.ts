/**
 * API podkladu pro komisi (ARCHITEKTURA §6.3): podklad, generování přes job a zdroje citací.
 */
import { apiFetch } from '@/lib/api';
import type {
  Brief,
  BriefConfig,
  Decision,
  EvidenceSource,
  Me,
  MdtCase,
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

  /** Přesun do jiného boardu (`session`), ECOG, záměr, checkbox, `acknowledge` (D-019). */
  updateCase: (caseId: number, input: Partial<Pick<MdtCase, 'session' | 'ecog' | 'intent' | 'imaging_recent_checked' | 'skipped_fields'>> & { acknowledge?: string[] }) =>
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

  /** Časová osa pacienta z IRIS (seřazená podle data). */
  getTimeline: (patientId: string) =>
    apiFetch<TimelineEvent[]>(`/api/patients/${encodeURIComponent(patientId)}/timeline/`),

  /** Číselné řady (labs, hmotnost, ECOG, PROMs `proms:<linkId>`). */
  getObservations: (patientId: string, codes?: string[]) =>
    apiFetch<ObservationSeries[]>(
      `/api/patients/${encodeURIComponent(patientId)}/observations/${codes?.length ? `?code=${encodeURIComponent(codes.join(','))}` : ''}`,
    ),
};
