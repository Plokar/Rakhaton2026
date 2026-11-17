'use client';

import { refreshSession } from '@/lib/api';
import { mdtApi } from '@/lib/mdt-api';
import type { LiveState, SessionMessage } from '@/types/mdt';

/**
 * Jeden SSE stream na zasedání pro celou záložku (T-379): chat lékařů (T-334) i živé zasedání (T-357) poslouchají
 * stejné spojení `GET /api/mdt/sessions/{sid}/stream/`. Dřív měla stránka jednání dvě spojení na stejnou adresu;
 * prohlížeč jich na HTTP/1.1 drží jen 6 na doménu, takže pár záložek aplikaci zaseklo.
 *
 * Spojení se otevře s prvním odběratelem a zavře s posledním. Po výpadku sítě se `EventSource` připojí sám,
 * po odmítnutí (vypršelé přihlášení) se obnoví přihlášení a spojení se otevře znovu (T-336).
 */
export type StreamStatus = 'connecting' | 'live' | 'offline';

export interface StreamListener {
  onMessage?: (message: SessionMessage) => void;
  onLive?: (state: LiveState) => void;
  /** Spojení je otevřené (i po obnovení): odběratel si doplní, co mezitím mohl zmeškat. */
  onOpen?: () => void;
  onStatus?: (status: StreamStatus) => void;
  /** ID poslední zprávy chatu, kterou odběratel má: stream při připojení doplní novější. */
  after?: () => number | null;
}

interface Stream {
  listeners: Set<StreamListener>;
  source: EventSource | null;
  status: StreamStatus;
  timer?: ReturnType<typeof setTimeout>;
  attempt: number;
}

const streams = new Map<number, Stream>();

function setStatus(stream: Stream, status: StreamStatus) {
  stream.status = status;
  stream.listeners.forEach((l) => l.onStatus?.(status));
}

function connect(sessionId: number, stream: Stream) {
  const afters = [...stream.listeners].map((l) => l.after?.()).filter((v): v is number => typeof v === 'number');
  const source = new EventSource(mdtApi.sessionStreamUrl(sessionId, afters.length ? Math.max(...afters) : null), {
    withCredentials: true,
  });
  stream.source = source;
  source.onopen = () => {
    stream.attempt = 0;
    setStatus(stream, 'live');
    stream.listeners.forEach((l) => l.onOpen?.());
  };
  source.onmessage = (event: MessageEvent<string>) => {
    const message = JSON.parse(event.data) as SessionMessage;
    stream.listeners.forEach((l) => l.onMessage?.(message));
  };
  source.addEventListener('live', (event) => {
    const state = JSON.parse((event as MessageEvent<string>).data) as LiveState;
    stream.listeners.forEach((l) => l.onLive?.(state));
  });
  source.onerror = () => {
    if (source.readyState !== EventSource.CLOSED) {
      setStatus(stream, 'connecting');               // výpadek sítě: EventSource se připojí sám
      return;
    }
    source.close();
    setStatus(stream, 'offline');
    const delay = stream.attempt === 0 ? 0 : Math.min(30_000, 3_000 * 2 ** (stream.attempt - 1));
    stream.attempt += 1;
    stream.timer = setTimeout(() => {
      void refreshSession().then(() => {
        if (streams.get(sessionId) === stream && stream.listeners.size) connect(sessionId, stream);
      });
    }, delay);
  };
}

/** Přihlásí odběratele ke streamu zasedání; vrací odhlášení. */
export function subscribeSessionStream(sessionId: number, listener: StreamListener): () => void {
  let stream = streams.get(sessionId);
  if (!stream) {
    stream = { listeners: new Set(), source: null, status: 'connecting', attempt: 0 };
    streams.set(sessionId, stream);
  }
  stream.listeners.add(listener);
  listener.onStatus?.(stream.status);
  if (!stream.source) connect(sessionId, stream);
  else if (stream.status === 'live') listener.onOpen?.();     // připojil se k už otevřenému: ať si doplní zmeškané
  const current = stream;
  return () => {
    current.listeners.delete(listener);
    if (current.listeners.size) return;
    clearTimeout(current.timer);
    current.source?.close();
    streams.delete(sessionId);
  };
}
