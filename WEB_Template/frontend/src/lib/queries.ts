'use client';

import * as React from 'react';
import { QueryClient, useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/lib/api';
import { mdtApi } from '@/lib/mdt-api';
import type { MdtCase, MdtSessionDetail, MdtSessionListItem } from '@/types/mdt';

/**
 * Serverová data pro UI v2 (docs/NAVRH_UI.md §10.3): jedna cache pro sidebar, kalendář i jednání,
 * optimistický přesun pacienta s návratem. Stávající stránky dál používají `useApiData`.
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
  sessions: ['sessions'] as const,
  session: (id: number | string) => ['session', String(id)] as const,
  tasks: ['tasks'] as const,
  patients: ['patients'] as const,
};

export function useSessionsQuery() {
  return useQuery({ queryKey: queryKeys.sessions, queryFn: () => mdtApi.getSessions() });
}

export function useSessionQuery(id: number | string | null | undefined) {
  return useQuery({
    queryKey: queryKeys.session(id ?? ''),
    queryFn: () => mdtApi.getSession(String(id)),
    enabled: id !== null && id !== undefined && id !== '',
  });
}

export function useTasksQuery() {
  return useQuery({ queryKey: queryKeys.tasks, queryFn: () => mdtApi.getTasks(), staleTime: 60_000 });
}

export function usePatientsQuery(enabled = true) {
  return useQuery({ queryKey: queryKeys.patients, queryFn: () => mdtApi.getPatients(), enabled, staleTime: 5 * 60_000 });
}

/**
 * Zasedání v rozsahu i s případy: seznam + detail každého boardu souběžně (bez waterfallu).
 * Až API umí `sessions?expand=cases` (NAVRH_UI §10.2), stačí jeden dotaz.
 */
export function useSessionsWithCases(filter: (session: MdtSessionListItem) => boolean) {
  const sessions = useSessionsQuery();
  const visible = React.useMemo(() => (sessions.data ?? []).filter(filter), [sessions.data, filter]);
  const details = useQueries({
    queries: visible.map((s) => ({ queryKey: queryKeys.session(s.id), queryFn: () => mdtApi.getSession(String(s.id)) })),
  });
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
