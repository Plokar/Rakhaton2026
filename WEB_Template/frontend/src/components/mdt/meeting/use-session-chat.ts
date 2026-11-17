'use client';

import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { mdtApi } from '@/lib/mdt-api';
import { subscribeSessionStream, type StreamStatus } from '@/lib/session-stream';
import type { Me, SessionMessage } from '@/types/mdt';

/** Stav živého spojení: `live` = zprávy chodí hned, `offline` = čeká se na nový pokus. */
export type ChatConnection = StreamStatus;

const messagesKey = (sessionId: number) => ['session', String(sessionId), 'messages'] as const;
const SEEN_KEY = (sessionId: number) => `mdt-chat-seen-${sessionId}`;

function readNumber(key: string): number {
  try {
    return Number(localStorage.getItem(key)) || 0;
  } catch {
    return 0;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // bez úložiště platí do přenačtení
  }
}

/** Zprávy podle ID bez duplicit: stejná zpráva přijde z POST i ze streamu. */
function merge(prev: SessionMessage[] | undefined, incoming: SessionMessage[]): SessionMessage[] {
  const byId = new Map((prev ?? []).map((m) => [m.id, m]));
  for (const m of incoming) byId.set(m.id, m);
  return [...byId.values()].sort((a, b) => a.id - b.id);
}

/**
 * Chat lékařů u zasedání (T-334). Bez websocketů a bez pollingu: historie jedním GET, nové zprávy přes
 * Server-Sent Events. Po výpadku sítě se `EventSource` připojí sám a server doplní zmeškané podle
 * `Last-Event-ID`; když server spojení odmítne (vypršelé přihlášení), obnoví se přihlášení a připojí znovu (T-336).
 */
export function useSessionChat(sessionId: number, me: Me | null) {
  const client = useQueryClient();
  const key = messagesKey(sessionId);
  const query = useQuery({
    queryKey: key,
    queryFn: () => mdtApi.getSessionMessages(sessionId),
    staleTime: Infinity,          // čerstvost drží stream
    refetchOnWindowFocus: false,
  });
  const [connection, setConnection] = React.useState<ChatConnection>('connecting');
  const loaded = query.isSuccess;

  React.useEffect(() => {
    if (!loaded) return;
    const k = messagesKey(sessionId);
    const add = (incoming: SessionMessage[]) => client.setQueryData<SessionMessage[]>(k, (prev) => merge(prev, incoming));
    const lastId = () => client.getQueryData<SessionMessage[]>(k)?.at(-1)?.id ?? 0;
    // T-379: sdílený stream zasedání (jedno spojení i se živým zasedáním)
    return subscribeSessionStream(sessionId, {
      after: lastId,
      onMessage: (message) => add([message]),
      onStatus: setConnection,
      // připojení k už otevřenému streamu nebo obnovení po výpadku: doplnit, co mezitím přišlo
      onOpen: () => {
        void mdtApi.getSessionMessages(sessionId, lastId() || undefined).then(add).catch(() => undefined);
      },
    });
  }, [client, sessionId, loaded]);

  const send = useMutation({
    mutationFn: (input: { text: string; case_id?: number | null }) => mdtApi.postSessionMessage(sessionId, input),
    onSuccess: (message) => client.setQueryData<SessionMessage[]>(messagesKey(sessionId), (prev) => merge(prev, [message])),
  });

  const messages = React.useMemo(() => query.data ?? [], [query.data]);
  const lastId = messages.at(-1)?.id ?? 0;

  // Otevřený panel = všechno přečtené; „přečteno do“ se mění jen při otevření a zavření (bez setState v efektu).
  // Otevření se nepamatuje: na úzkém displeji by boční panel po načtení zakryl jednání.
  const [open, setOpenState] = React.useState(false);
  const [seen, setSeen] = React.useState(() => ({ sessionId, id: readNumber(SEEN_KEY(sessionId)) }));
  const seenId = seen.sessionId === sessionId ? seen.id : readNumber(SEEN_KEY(sessionId));
  const unread = open ? 0 : messages.filter((m) => m.id > seenId && m.author?.user_id !== me?.user_id).length;

  React.useEffect(() => {
    if (open && lastId) write(SEEN_KEY(sessionId), String(lastId));
  }, [open, lastId, sessionId]);

  const setOpen = React.useCallback(
    (next: boolean) => {
      setSeen({ sessionId, id: Math.max(lastId, readNumber(SEEN_KEY(sessionId))) });
      setOpenState(next);
    },
    [lastId, sessionId],
  );

  return { messages, query, connection, send, unread, open, setOpen };
}

export type SessionChatState = ReturnType<typeof useSessionChat>;
