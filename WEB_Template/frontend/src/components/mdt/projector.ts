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
  return Number.isInteger(board) && board > 0 && Number.isInteger(caseId) && caseId > 0 && patient && /^P\d{2,3}$/.test(patient)
    ? { board, caseId, patient }
    : null;
}

/** Pošle výběr do otevřeného okna projektoru (když žádné není, nic se nestane). */
export function publishSelection(selection: ProjectorSelection) {
  post(selection);
}

/** Okno projektoru je jiná záložka s vlastní cache: po změně případu (pořadí údajů, T-332) si board načte znovu. */
export function publishRefresh(board: number) {
  post({ type: 'refresh', board });
}

// ── Slidy (T-348): jednání přepíná slidy projektoru, projektor hlásí, na kterém je ─────────────────────────

export interface SlideState {
  board: number;
  caseId: number;
  index: number;
  total: number;
  /** Bloky na aktuálním slidu („Klíčové údaje · Léčebné postupy“). */
  label: string;
}

type SlideCommand = { type: 'slide'; board: number; caseId: number; delta?: number; to?: number };
type Message = ProjectorSelection | { type: 'refresh'; board: number } | SlideCommand | ({ type: 'slides' } & SlideState);

function post(message: Message) {
  if (typeof BroadcastChannel === 'undefined') return;
  const channel = new BroadcastChannel(CHANNEL);
  channel.postMessage(message);
  channel.close();
}

/** Okno jednání: další / předchozí slide (`delta`) nebo konkrétní (`to`) u pacienta na projektoru. */
export function publishSlide(board: number, caseId: number, move: { delta: number } | { to: number }) {
  post({ type: 'slide', board, caseId, ...move });
}

/** Okno projektoru: příkazy z jednání pro tohoto pacienta + hlášení stavu zpět. */
export function useSlideRemote(
  target: { board: number; caseId: number } | null,
  state: { index: number; total: number; label: string },
  onCommand: (move: { delta?: number; to?: number }) => void,
) {
  const command = React.useRef(onCommand);
  const latest = React.useRef(state);
  React.useEffect(() => {
    command.current = onCommand;
    latest.current = state;
  });
  const board = target?.board;
  const caseId = target?.caseId;
  React.useEffect(() => {
    if (board == null || caseId == null || typeof BroadcastChannel === 'undefined') return;
    const channel = new BroadcastChannel(CHANNEL);
    channel.onmessage = (event: MessageEvent<Message>) => {
      const data = event.data;
      if (!data || !('type' in data) || data.type !== 'slide' || data.board !== board || data.caseId !== caseId) return;
      command.current({ delta: data.delta, to: data.to });
      // i příkaz bez změny (`delta: 0` z nově otevřeného jednání) dostane odpověď, kde projektor je
      post({ type: 'slides', board, caseId, ...latest.current });
    };
    return () => channel.close();
  }, [board, caseId]);
  const { index, total, label } = state;
  React.useEffect(() => {
    if (board != null && caseId != null) post({ type: 'slides', board, caseId, index, total, label });
  }, [board, caseId, index, total, label]);
}

/** Okno jednání: na kterém slidu je projektor u tohoto pacienta (null = projektor neběží nebo ukazuje jiného). */
export function useProjectorSlides(board: number, caseId: number | null): SlideState | null {
  const [state, setState] = React.useState<SlideState | null>(null);
  React.useEffect(() => {
    if (typeof BroadcastChannel === 'undefined') return;
    const channel = new BroadcastChannel(CHANNEL);
    channel.onmessage = (event: MessageEvent<Message>) => {
      const data = event.data;
      if (data && 'type' in data && data.type === 'slides') {
        const { board: b, caseId: c, index, total, label } = data;
        setState({ board: b, caseId: c, index, total, label });
      }
    };
    return () => channel.close();
  }, []);
  React.useEffect(() => {
    if (caseId != null) publishSlide(board, caseId, { delta: 0 });       // projektor už běží: ať řekne, kde je
  }, [board, caseId]);
  return state && state.board === board && state.caseId === caseId ? state : null;
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
    channel.onmessage = (event: MessageEvent<Message>) => {
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
