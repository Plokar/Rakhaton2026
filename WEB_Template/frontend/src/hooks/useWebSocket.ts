'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

type WsStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

interface WsMessage {
  type: string;
  [key: string]: unknown;
}

interface UseWebSocketOptions {
  /** Automaticky se znovu připojit po odpojení */
  autoReconnect?: boolean;
  /** Maximální počet pokusů o reconnect (0 = neomezeně) */
  maxReconnectAttempts?: number;
  /** Základ pro exponential backoff (ms) */
  reconnectInterval?: number;
  /** Callback při přijetí zprávy */
  onMessage?: (message: WsMessage) => void;
  /** Callback při připojení */
  onOpen?: () => void;
  /** Callback při odpojení */
  onClose?: (event: CloseEvent) => void;
  /** Callback při chybě */
  onError?: (event: Event) => void;
}

interface UseWebSocketReturn {
  status: WsStatus;
  lastMessage: WsMessage | null;
  sendMessage: (data: WsMessage) => void;
  disconnect: () => void;
  reconnect: () => void;
  reconnectAttempts: number;
}

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ||
  (typeof window !== 'undefined'
    ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    : 'ws://localhost:8000');

/**
 * useWebSocket – custom hook pro WebSocket spojení s auto-reconnect.
 *
 * @param path  WebSocket path (např. '/ws/echo/' nebo '/ws/room/hackathon/')
 * @param options  Konfigurační možnosti
 *
 * @example
 * const { status, lastMessage, sendMessage } = useWebSocket('/ws/room/test/');
 * sendMessage({ type: 'message', payload: 'Hello!' });
 */
export function useWebSocket(
  path: string,
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const {
    autoReconnect = true,
    maxReconnectAttempts = 5,
    reconnectInterval = 1000,
    onMessage,
    onOpen,
    onClose,
    onError,
  } = options;

  const [status, setStatus] = useState<WsStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<WsMessage | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnectRef = useRef(autoReconnect);
  const attemptsRef = useRef(0);

  const url = `${WS_BASE}${path}`;

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus('connected');
      attemptsRef.current = 0;
      setReconnectAttempts(0);
      onOpen?.();
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as WsMessage;
        setLastMessage(message);
        onMessage?.(message);
      } catch {
        console.warn('[WS] Failed to parse message:', event.data);
      }
    };

    ws.onclose = (event) => {
      setStatus('disconnected');
      wsRef.current = null;
      onClose?.(event);

      // Auto-reconnect s exponential backoff
      if (
        shouldReconnectRef.current &&
        (maxReconnectAttempts === 0 ||
          attemptsRef.current < maxReconnectAttempts)
      ) {
        const delay = Math.min(
          reconnectInterval * Math.pow(2, attemptsRef.current),
          30000, // max 30s
        );
        attemptsRef.current += 1;
        setReconnectAttempts(attemptsRef.current);

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      }
    };

    ws.onerror = (event) => {
      setStatus('error');
      onError?.(event);
    };
  }, [url, maxReconnectAttempts, reconnectInterval, onMessage, onOpen, onClose, onError]);

  // Připojit při mount
  useEffect(() => {
    shouldReconnectRef.current = autoReconnect;
    connect();

    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close(1000, 'Component unmounted');
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path]);

  const sendMessage = useCallback((data: WsMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WS] Cannot send – socket not connected');
    }
  }, []);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close(1000, 'Manual disconnect');
  }, []);

  const reconnect = useCallback(() => {
    shouldReconnectRef.current = autoReconnect;
    attemptsRef.current = 0;
    setReconnectAttempts(0);
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    wsRef.current?.close();
    connect();
  }, [autoReconnect, connect]);

  return { status, lastMessage, sendMessage, disconnect, reconnect, reconnectAttempts };
}
