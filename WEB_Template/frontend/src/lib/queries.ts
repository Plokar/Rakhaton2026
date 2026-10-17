'use client';

import * as React from 'react';
import { QueryClient, useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/lib/api';
import { mdtApi, type SessionInput, type StoredBrief } from '@/lib/mdt-api';
import type { Me, MdtCase, MdtRole, MdtSessionDetail, MdtSessionListItem, RoleId } from '@/types/mdt';

/**
 * Serverová data pro UI v2 (docs/NAVRH_UI.md §10.3): jedna cache pro sidebar, kalendář, jednání,
 * detail i okno projektoru, optimistický přesun pacienta s návratem.
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        refetchOnWindowFocus: true,     // na stejné boardy se dívá víc lékařů najednou
        retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
      },
    },
  });
}

export const queryKeys = {
  users: ['users'] as const,
  template: (caseId: number | string) => ['case', String(caseId), 'template'] as const,
  forMe: (caseId: number | string, specialty: string) => ['case', String(caseId), 'for-me', specialty] as const,
  sessions: ['sessions'] as const,
  session: (id: number | string) => ['session', String(id)] as const,
  tasks: ['tasks'] as const,
  myTasks: (patientId?: string | null) => ['tasks', 'mine', patientId ?? 'all'] as const,
  practitioners: ['practitioners'] as const,
  patients: ['patients'] as const,
  brief: (caseId: number | string) => ['case', String(caseId), 'brief'] as const,
  compatibility: (caseId: number | string) => ['case', String(caseId), 'compatibility'] as const,
  readiness: (caseId: number | string) => ['case', String(caseId), 'readiness'] as const,
  intake: (patientId: string) => ['patient', patientId, 'intake'] as const,
  patient: (patientId: string) => ['patient', patientId, 'detail'] as const,
  observations: (patientId: string) => ['patient', patientId, 'observations'] as const,
  timeline: (patientId: string) => ['patient', patientId, 'timeline'] as const,
};

/** 404 u podkladu znamená „ještě nevznikl“, ne chybu. */
const briefOrNull = (caseId: number | string) =>
  mdtApi.getBrief(String(caseId)).catch((err: unknown) => {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  });

const queryOptions = {
  brief: (caseId: number | string) => ({ queryKey: queryKeys.brief(caseId), queryFn: () => briefOrNull(caseId) }),
  compatibility: (caseId: number | string) => ({
    queryKey: queryKeys.compatibility(caseId),
    queryFn: () => mdtApi.getCompatibility(Number(caseId)),
  }),
  intake: (patientId: string) => ({ queryKey: queryKeys.intake(patientId), queryFn: () => mdtApi.getIntake(patientId) }),
  observations: (patientId: string) => ({
    queryKey: queryKeys.observations(patientId),
    queryFn: () => mdtApi.getObservations(patientId),
  }),
  session: (id: number | string) => ({ queryKey: queryKeys.session(id), queryFn: () => mdtApi.getSession(String(id)) }),
};

export function useSessionsQuery() {
  return useQuery({ queryKey: queryKeys.sessions, queryFn: () => mdtApi.getSessions() });
}

export function useSessionQuery(id: number | string | null | undefined) {
  return useQuery({ ...queryOptions.session(id ?? ''), enabled: id !== null && id !== undefined && id !== '' });
}

export function useTasksQuery() {
  return useQuery({ queryKey: queryKeys.tasks, queryFn: () => mdtApi.getTasks(), staleTime: 60_000 });
}

/** Úkoly přiřazené přihlášenému lékaři, i z nepotvrzených závěrů (T-328); volitelně jen u pacienta. */
export function useMyTasksQuery(patientId?: string | null, enabled = true) {
  return useQuery({
    queryKey: queryKeys.myTasks(patientId),
    queryFn: () => mdtApi.getTasks({ mine: true, drafts: true, patient: patientId ?? undefined }),
    enabled,
    staleTime: 60_000,
  });
}

/** Všichni lékaři nemocnice z IRIS (jeden dotaz, filtruje se v popupu). */
export function usePractitionersQuery(enabled = true) {
  return useQuery({ queryKey: queryKeys.practitioners, queryFn: () => mdtApi.getPractitioners(), enabled, staleTime: 5 * 60_000 });
}

export function usePatientsQuery(enabled = true) {
  return useQuery({ queryKey: queryKeys.patients, queryFn: () => mdtApi.getPatients(), enabled, staleTime: 5 * 60_000 });
}

export function usePatientQuery(patientId: string) {
  return useQuery({ queryKey: queryKeys.patient(patientId), queryFn: () => mdtApi.getPatient(patientId) });
}

export function useBriefQuery(caseId: number | string | null | undefined) {
  return useQuery({ ...queryOptions.brief(caseId ?? ''), enabled: Boolean(caseId) });
}

export function useCompatibilityQuery(caseId: number | string | null | undefined) {
  return useQuery({ ...queryOptions.compatibility(caseId ?? ''), enabled: Boolean(caseId) });
}

export function useReadinessQuery(caseId: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.readiness(caseId ?? ''),
    queryFn: () => mdtApi.getReadiness(caseId as number),
    enabled: Boolean(caseId),
    staleTime: 60_000,
  });
}

export function useIntakeQuery(patientId: string | null | undefined) {
  return useQuery({ ...queryOptions.intake(patientId ?? ''), enabled: Boolean(patientId) });
}

export function useObservationsQuery(patientId: string | null | undefined) {
  return useQuery({ ...queryOptions.observations(patientId ?? ''), enabled: Boolean(patientId) });
}

export function useTimelineQuery(patientId: string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.timeline(patientId ?? ''),
    queryFn: () => mdtApi.getTimeline(patientId as string),
    enabled: Boolean(patientId),
  });
}

/** 404 = pro diagnózu není šablona (bez báze `data/onko`); to není chyba, jen nic k nabídnutí. */
const orNullOn404 = <T,>(promise: Promise<T>) =>
  promise.catch((err: unknown) => {
    if (err instanceof ApiError && (err.status === 404 || err.status === 400)) return null;
    throw err;
  });

/** Doporučená šablona projektoru podle diagnózy (T-318). */
export function useTemplateQuery(caseId: number | null | undefined) {
  return useQuery({
    queryKey: queryKeys.template(caseId ?? ''),
    queryFn: () => orNullOn404(mdtApi.getTemplate(caseId as number)),
    enabled: Boolean(caseId),
    staleTime: 5 * 60_000,
  });
}

/** Pohled „pro mě“ podle odbornosti (T-319); bez odbornosti nebo šablony `null`. */
export function useForMeQuery(caseId: number | null | undefined, specialty: RoleId | null | undefined) {
  return useQuery({
    queryKey: queryKeys.forMe(caseId ?? '', specialty ?? ''),
    queryFn: () => orNullOn404(mdtApi.getForMe(caseId as number, specialty ?? undefined)),
    enabled: Boolean(caseId && specialty),
    staleTime: 5 * 60_000,
  });
}

/** Tým komise: uživatelé s rolí a odborností (jen předseda). */
export function useUsersQuery(enabled: boolean) {
  return useQuery({ queryKey: queryKeys.users, queryFn: () => mdtApi.getUsers(), enabled });
}

export function useUpdateUser() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, input }: { userId: number; input: { role?: MdtRole; specialty?: RoleId } }) => mdtApi.updateUser(userId, input),
    onSuccess: (saved) => {
      client.setQueryData<Me[]>(queryKeys.users, (prev) => prev?.map((u) => (u.user_id === saved.user_id ? saved : u)));
    },
  });
}

/**
 * Načte rychlý přehled dopředu (najetí myší na čip, NAVRH_UI §10.3, pravidlo `bundle-preload`):
 * board, podklad, semafor, údaje šablony a laboratoř souběžně, panel se pak otevře bez čekání.
 */
export function prefetchQuickView(client: QueryClient, target: { sessionId: number; caseId: number; patientId: string }) {
  void client.prefetchQuery(queryOptions.session(target.sessionId));
  void client.prefetchQuery(queryOptions.brief(target.caseId));
  void client.prefetchQuery(queryOptions.compatibility(target.caseId));
  void client.prefetchQuery(queryOptions.intake(target.patientId));
  void client.prefetchQuery(queryOptions.observations(target.patientId));
}

/**
 * Zasedání i s případy: seznam + detail každého boardu souběžně (bez waterfallu).
 * `sessions?expand=cases` (T-518) vrací jen `MdtCaseSummary`; agenda potřebuje celé `MdtCase` (zadávající, spolupracovníci).
 */
export function useSessionsWithCases(filter: (session: MdtSessionListItem) => boolean) {
  const sessions = useSessionsQuery();
  const visible = React.useMemo(() => (sessions.data ?? []).filter(filter), [sessions.data, filter]);
  const details = useQueries({ queries: visible.map((s) => queryOptions.session(s.id)) });
  const byId = new Map<number, MdtSessionDetail>();
  details.forEach((d, i) => d.data && byId.set(visible[i].id, d.data));
  return {
    sessions: visible,
    detail: byId,
    loading: sessions.isLoading,
    detailsLoading: details.some((d) => d.isLoading),
    error: sessions.error,
  };
}

const ALL = () => true;

/** Případ podle ID: API nemá `GET /cases/{id}/`, proto se hledá v agendách boardů (sdílená cache). */
export function useCaseLocation(caseId: number | null) {
  const { sessions, detail, loading, detailsLoading, error } = useSessionsWithCases(ALL);
  if (caseId === null) return { session: null, item: null, loading: false, error: null };
  for (const s of sessions) {
    const item = detail.get(s.id)?.cases.find((c) => c.id === caseId);
    if (item) return { session: detail.get(s.id) as MdtSessionDetail, item, loading: false, error: null };
  }
  return { session: null, item: null, loading: loading || detailsLoading, error };
}

/** Případy boardu v pořadí agendy. */
export const agendaOrder = (session: MdtSessionDetail | null | undefined): MdtCase[] =>
  session ? session.cases.toSorted((a, b) => (a.order ?? 0) - (b.order ?? 0)) : [];

/** Přesun pacienta na jiný board: optimisticky v cache obou boardů, při chybě návrat. */
export function useMoveCase() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, to }: { caseId: number; from: number; to: number }) => mdtApi.updateCase(caseId, { session: to }),
    onMutate: async ({ caseId, from, to }) => {
      const fromKey = queryKeys.session(from);
      const toKey = queryKeys.session(to);
      await Promise.all([client.cancelQueries({ queryKey: fromKey }), client.cancelQueries({ queryKey: toKey })]);
      const prevFrom = client.getQueryData<MdtSessionDetail>(fromKey);
      const prevTo = client.getQueryData<MdtSessionDetail>(toKey);
      const prevList = client.getQueryData<MdtSessionListItem[]>(queryKeys.sessions);
      const moved = prevFrom?.cases.find((c) => c.id === caseId);
      if (prevFrom && moved) client.setQueryData(fromKey, { ...prevFrom, cases: prevFrom.cases.filter((c) => c.id !== caseId) });
      if (prevTo && moved) {
        const order = Math.max(0, ...prevTo.cases.map((c) => c.order ?? 0)) + 1;
        client.setQueryData(toKey, { ...prevTo, cases: [...prevTo.cases, { ...moved, session: to, order } satisfies MdtCase] });
      }
      if (prevList && moved) {
        client.setQueryData(queryKeys.sessions, prevList.map((s) =>
          s.id === from ? { ...s, patients: s.patients.filter((p) => p !== moved.patient_id) }
            : s.id === to ? { ...s, patients: [...s.patients, moved.patient_id] } : s));
      }
      return { prevFrom, prevTo, prevList };
    },
    onError: (_error, { from, to }, context) => {
      if (context?.prevFrom) client.setQueryData(queryKeys.session(from), context.prevFrom);
      if (context?.prevTo) client.setQueryData(queryKeys.session(to), context.prevTo);
      if (context?.prevList) client.setQueryData(queryKeys.sessions, context.prevList);
    },
    onSettled: (_data, _error, { from, to }) => {
      void client.invalidateQueries({ queryKey: queryKeys.session(from) });
      void client.invalidateQueries({ queryKey: queryKeys.session(to) });
      void client.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

/** Stav případu v agendě (jen předseda): projednáno / zpět na řadu. Optimisticky v cache boardu. */
export function useCaseStatus(sessionId: number | null | undefined) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ caseId, status }: { caseId: number; status: MdtCase['status'] }) => mdtApi.updateCase(caseId, { status }),
    onMutate: async ({ caseId, status }) => {
      if (!sessionId) return {};
      const key = queryKeys.session(sessionId);
      await client.cancelQueries({ queryKey: key });
      const prev = client.getQueryData<MdtSessionDetail>(key);
      if (prev) client.setQueryData(key, { ...prev, cases: prev.cases.map((c) => (c.id === caseId ? { ...c, status } : c)) });
      return { prev };
    },
    onError: (_error, _vars, context) => {
      if (sessionId && context?.prev) client.setQueryData(queryKeys.session(sessionId), context.prev);
    },
    onSettled: () => {
      if (sessionId) void client.invalidateQueries({ queryKey: queryKeys.session(sessionId) });
    },
  });
}

/** Zařazení pacienta (FR-P4): po uložení se obnoví board, seznam zasedání i připravenost. */
export function useCreateCase() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof mdtApi.createCase>[0]) => mdtApi.createCase(body),
    onSuccess: (created) => {
      void client.invalidateQueries({ queryKey: queryKeys.session(created.session) });
      void client.invalidateQueries({ queryKey: queryKeys.sessions });
    },
  });
}

/** Založení nebo úprava boardu (jen předseda). */
export function useSaveSession() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, input }: { id?: number; input: SessionInput }) =>
      id ? mdtApi.updateSession(id, input) : mdtApi.createSession(input),
    onSuccess: (saved) => {
      void client.invalidateQueries({ queryKey: queryKeys.sessions });
      void client.invalidateQueries({ queryKey: queryKeys.session(saved.id) });
    },
  });
}

/** Po vygenerování podkladu se přenačte podklad i semafor případu. */
export function useInvalidateCase() {
  const client = useQueryClient();
  return React.useCallback(
    (caseId: number | string) => {
      void client.invalidateQueries({ queryKey: ['case', String(caseId)] });
    },
    [client],
  );
}

/** Česká zpráva k chybě přesunu (403 práva, 409 uzavřený board, síť). */
export function moveErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'Tento případ může přesunout jen předseda nebo zadávající lékař.';
    if (error.status === 409) return 'Cílový board je uzavřený.';
    if (error.status === 404) return 'Board nebo případ už neexistuje. Obnovte stránku.';
    return `Přesun se nepovedl (chyba ${error.status}). Zkuste to znovu.`;
  }
  return 'Server neodpovídá. Zkuste to znovu.';
}

/** Obecná česká chybová zpráva z API (backend vrací česky `detail`, jinak stav). */
export function apiErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'Na tuto akci nemáte oprávnění.';
    if (error.status >= 500) return 'Server vrátil chybu. Zkuste to za chvíli znovu.';
    return error.message && !/^HTTP Error/.test(error.message) ? error.message : fallback;
  }
  return error instanceof Error && error.message !== 'Failed to fetch' ? error.message : 'Server neodpovídá. Zkontrolujte připojení.';
}

export type { StoredBrief };
