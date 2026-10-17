'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queries';

/**
 * Druhé okno pro projektor (T-512): úzký panel vedle snímku z PACS. Admin okno posílá vybraný případ
 * přes BroadcastChannel (stejný prohlížeč, bez reloadu) a URL nese výběr pro obnovení stránky.
 */
export interface ProjectorSelection {
  board: number;
  caseId: number;
  /** "P03": intake a laboratoř se načítají souběžně s boardem, bez čekání na agendu. */
  patient: string;
}

const CHANNEL = 'mdt-projector';
const WINDOW_NAME = 'mdt-projector';

export const projectorHref = (selection: ProjectorSelection | null) =>
  selection
    ? `/projector?${new URLSearchParams({ board: String(selection.board), case: String(selection.caseId), patient: selection.patient })}`
    : '/projector';

export function parseSelection(params: Record<string, string | string[] | undefined>): ProjectorSelection | null {
  const first = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value);
  const board = Number(first(params.board));
  const caseId = Number(first(params.case));
  const patient = first(params.patient);
  return Number.isInteger(board) && board > 0 && Number.isInteger(caseId) && caseId > 0 && patient && /^P\d{2}$/.test(patient)
    ? { board, caseId, patient }
    : null;
}

/** Pošle výběr do otevřeného okna projektoru (když žádné není, nic se nestane). */
export function publishSelection(selection: ProjectorSelection) {
  if (typeof BroadcastChannel === 'undefined') return;
  const channel = new BroadcastChannel(CHANNEL);
  channel.postMessage(selection);
  channel.close();
}

/** Okno projektoru je jiná záložka s vlastní cache: po změně případu (pořadí údajů, T-332) si board načte znovu. */
export function publishRefresh(board: number) {
  if (typeof BroadcastChannel === 'undefined') return;
  const channel = new BroadcastChannel(CHANNEL);
  channel.postMessage({ type: 'refresh', board });
  channel.close();
}

/** Otevře (nebo přepne) pojmenované úzké okno; blokované popupy vrátí false a odkaz se otevře v záložce. */
export function openProjectorWindow(selection: ProjectorSelection | null): boolean {
  const win = window.open(projectorHref(selection), WINDOW_NAME, 'popup,width=420,height=1000');
  win?.focus();
  return Boolean(win);
}

/** Okno projektoru: výběr z URL, pak každá zpráva z admin okna (stav se mění jen v callbacku). */
export function useProjectorSelection(initial: ProjectorSelection | null) {
  const [selection, setSelection] = React.useState(initial);
  const client = useQueryClient();
  React.useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return;
    const channel = new BroadcastChannel(CHANNEL);
    channel.onmessage = (event: MessageEvent<ProjectorSelection | { type: 'refresh'; board: number }>) => {
      if (event.data && 'type' in event.data) {
        if (event.data.type === 'refresh') void client.invalidateQueries({ queryKey: queryKeys.session(event.data.board) });
        return;
      }
      const next = parseSelection({ board: String(event.data?.board), case: String(event.data?.caseId), patient: event.data?.patient });
      if (!next) return;
      setSelection(next);
      window.history.replaceState(null, '', projectorHref(next));
    };
    return () => channel.close();
  }, [client]);
  return selection;
}
