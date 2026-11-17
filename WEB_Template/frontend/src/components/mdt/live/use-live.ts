'use client';

import * as React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { mdtApi } from '@/lib/mdt-api';
import { subscribeSessionStream, type StreamStatus } from '@/lib/session-stream';
import type { MyLive } from '@/types/mdt';

/**
 * Živé zasedání (T-357): kde lékař má být, kde je a který pacient je právě na projektoru.
 * Stav projektoru chodí přes SSE stream boardu (`event: live`, stejné spojení jako chat lékařů, T-334),
 * přehled „moje zasedání“ se obnovuje po minutě (začátek dalšího zasedání), přítomnost se ohlašuje po 2 min.
 */
export const liveKeys = {
  mine: ['live', 'mine'] as const,
  session: (sessionId: number) => ['session', String(sessionId), 'live'] as const,
};

const PRESENCE_EVERY = 120_000;
const PUBLISH_DELAY = 400;
const HEARTBEAT_EVERY = 4 * 60_000;     // server považuje stav za starý po 15 min (live.LIVE_STALE_AFTER)

export function useMyLive(enabled = true) {
  return useQuery({
    queryKey: liveKeys.mine,
    queryFn: () => mdtApi.getMyLive(),
    enabled,
    refetchInterval: 60_000,
    staleTime: 20_000,
  });
}

/** Stav projektoru boardu: GET + živé změny ze streamu (bez pollingu). */
export function useLiveSession(sessionId: number | null) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: liveKeys.session(sessionId ?? 0),
    queryFn: () => mdtApi.getLive(sessionId!),
    enabled: sessionId != null,
    staleTime: Infinity,
  });
  const [status, setStatus] = React.useState<StreamStatus>('connecting');

  React.useEffect(() => {
    if (sessionId == null) return;
    // T-379: sdílený stream zasedání (stejné spojení jako chat lékařů)
    return subscribeSessionStream(sessionId, {
      onLive: (state) => {
        client.setQueryData(liveKeys.session(sessionId), state);
        client.setQueryData<MyLive>(liveKeys.mine, (prev) =>
          prev && { ...prev, sessions: prev.sessions.map((s) => (s.id === state.session ? { ...s, status: state.status, live: state } : s)) },
        );
        if (state.status === 'closed') void client.invalidateQueries({ queryKey: ['session', String(sessionId)], exact: true });
      },
      onStatus: setStatus,
      // co se změnilo, než se spojení otevřelo (nebo během výpadku)
      onOpen: () => void client.invalidateQueries({ queryKey: liveKeys.session(sessionId) }),
    });
  }, [client, sessionId]);
  const connected = status === 'live';

  return { live: query.data ?? null, query, connected };
}

/** „Jsem na zasedání“: ohlášení hned a pak každé 2 min, dokud je stránka vidět. */
export function usePresence(sessionId: number | null, enabled: boolean) {
  const client = useQueryClient();
  React.useEffect(() => {
    if (sessionId == null || !enabled) return;
    const ping = () => {
      if (document.visibilityState !== 'visible') return;
      mdtApi
        .joinSession(sessionId)
        .then((state) => {
          client.setQueryData(liveKeys.session(sessionId), state);
          void client.invalidateQueries({ queryKey: liveKeys.mine });
        })
        .catch(() => undefined);           // uzavřený board nebo výpadek: zkusí se příště
    };
    ping();
    const timer = setInterval(ping, PRESENCE_EVERY);
    document.addEventListener('visibilitychange', ping);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', ping);
    };
  }, [client, sessionId, enabled]);
}

/**
 * Jednání komise u předsedy: pacient na řadě a slide projektoru se zapíšou na server, aby je viděly mobily
 * ostatních lékařů. Krátké zpoždění sloučí rychlé přepínání (↑↓, ←→) do jednoho zápisu. Jen na zahájeném
 * zasedání (T-379); stejný stav se zopakuje každé 4 min, jinak by ho mobily ukázaly jako starý.
 */
export function usePublishLive(
  sessionId: number,
  enabled: boolean,
  caseId: number | null,
  slide: { index: number; total: number; label: string } | null,
) {
  const client = useQueryClient();
  const index = slide?.index;
  const total = slide?.total;
  const label = slide?.label;
  React.useEffect(() => {
    if (!enabled || caseId == null) return;
    const publish = () => {
      const next = total ? { index: index ?? 0, total, label: label ?? '' } : null;
      mdtApi
        .putLive(sessionId, { case_id: caseId, slide: next })
        .then((state) => client.setQueryData(liveKeys.session(sessionId), state))
        .catch(() => undefined);           // bez práva nebo uzavřený board: jednání funguje dál
    };
    const timer = setTimeout(publish, PUBLISH_DELAY);
    const heartbeat = setInterval(publish, HEARTBEAT_EVERY);
    return () => {
      clearTimeout(timer);
      clearInterval(heartbeat);
    };
  }, [client, sessionId, enabled, caseId, index, total, label]);
}
