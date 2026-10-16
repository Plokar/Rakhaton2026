/**
 * API podkladu pro komisi (ARCHITEKTURA §6.3): podklad, generování přes job a zdroje citací.
 */
import { apiFetch } from '@/lib/api';
import type { Brief, BriefConfig, EvidenceSource, Me, MdtSessionDetail, MdtSessionListItem } from '@/types/mdt';

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

  getBrief: (caseId: string) => apiFetch<StoredBrief>(`/api/mdt/cases/${encodeURIComponent(caseId)}/brief/`),

  generateBrief: (caseId: string, body: { config_id?: string; config?: BriefConfig } = {}) =>
    apiFetch<{ job_id: number }>(`/api/mdt/cases/${encodeURIComponent(caseId)}/brief/`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getJob: (jobId: number) => apiFetch<GenerationJob>(`/api/jobs/${jobId}/`),

  getEvidence: (evidenceId: string) =>
    apiFetch<EvidenceSource>(`/api/evidence/?id=${encodeURIComponent(evidenceId)}`),
};
