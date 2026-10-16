'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/contexts/AuthContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import {
  Radio,
  Send,
  Terminal,
  RefreshCw,
  Zap,
  Users,
  Clock,
  Activity,
  Trash2,
} from 'lucide-react';

interface LogMessage {
  id: string;
  type: string;
  user?: string;
  payload?: unknown;
  timestamp: string;
}

export default function RealtimePage() {
  const { user } = useAuth();
  const [room, setRoom] = React.useState('hackathon');
  const [wsUrl, setWsUrl] = React.useState('/ws/room/hackathon/');
  const [messages, setMessages] = React.useState<LogMessage[]>([]);
  const [inputMsg, setInputMsg] = React.useState('');
  const [pingLatency, setPingLatency] = React.useState<number | null>(null);
  const pingStartRef = React.useRef<number | null>(null);

  const { status, sendMessage, reconnect } = useWebSocket(wsUrl, {
    onMessage: (msg: unknown) => {
      const parsed = msg as Record<string, unknown>;

      // If this was a ping response
      if (parsed.type === 'pong' && pingStartRef.current) {
        const diff = Date.now() - pingStartRef.current;
        setPingLatency(diff);
        pingStartRef.current = null;
      }

      setMessages((prev) => [
        {
          id: Math.random().toString(36).substring(2, 9),
          type: String(parsed.type || 'message'),
          user: String(parsed.user || 'Systém'),
          payload: parsed.payload || parsed.data || parsed.message || parsed,
          timestamp: new Date().toLocaleTimeString('cs-CZ', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
          }),
        },
        ...prev.slice(0, 99),
      ]);
    },
    autoReconnect: true,
  });

  const handleSend = () => {
    if (!inputMsg.trim() || status !== 'connected') return;
    sendMessage({
      type: 'chat_message',
      payload: inputMsg.trim(),
    });
    setInputMsg('');
  };

  const handlePing = () => {
    if (status !== 'connected') return;
    pingStartRef.current = Date.now();
    sendMessage({ type: 'ping', payload: { client_time: Date.now() } });
  };

  const switchRoom = (targetRoom: string) => {
    setRoom(targetRoom);
    setWsUrl(targetRoom === 'echo' ? '/ws/echo/' : `/ws/room/${targetRoom}/`);
    setMessages([]);
  };

  const statusColors = {
    connected: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20',
    connecting: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
    disconnected: 'text-muted-foreground bg-muted border-border',
    error: 'text-destructive bg-destructive/10 border-destructive/20',
  };

  const statusLabels = {
    connected: 'Připojeno',
    connecting: 'Připojuji...',
    disconnected: 'Odpojeno',
    error: 'Chyba spojení',
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
                WebSocket Live Monitor
              </h1>
              <div
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
                  statusColors[status] || statusColors.disconnected
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    status === 'connected' ? 'bg-emerald-500 animate-pulse' : 'bg-current'
                  }`}
                />
                {statusLabels[status] || status}
              </div>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Django Channels s Redis Channel Layer. Testování obousměrné komunikace v reálném čase.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePing}
              disabled={status !== 'connected'}
              className="gap-1.5"
            >
              <Activity className="h-4 w-4 text-primary" />
              Změřit Ping {pingLatency !== null && `(${pingLatency} ms)`}
            </Button>
            <Button variant="outline" size="sm" onClick={reconnect} className="gap-1.5">
              <RefreshCw className="h-4 w-4" /> Reconnect
            </Button>
          </div>
        </div>

        {/* Channel Selector Pills */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Kanál:
          </span>
          {[
            { id: 'hackathon', label: '#hackathon (Broadcast)' },
            { id: 'general', label: '#general (Chat)' },
            { id: 'echo', label: 'Echo Test (/ws/echo/)' },
          ].map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => switchRoom(c.id)}
              className={`rounded-xl px-3 py-1.5 text-xs font-semibold border transition ${
                room === c.id
                  ? 'border-primary bg-primary/10 text-primary'
                  : 'border-border bg-card text-muted-foreground hover:text-foreground'
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Terminal / Live Message Stream */}
        <Card className="border-border shadow-md">
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/60">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-emerald-500" />
              <CardTitle className="text-sm font-semibold">
                Živý proud zpráv • {wsUrl}
              </CardTitle>
            </div>
            <button
              type="button"
              onClick={() => setMessages([])}
              className="text-xs text-muted-foreground hover:text-destructive transition flex items-center gap-1"
            >
              <Trash2 className="h-3.5 w-3.5" /> Vyčistit
            </button>
          </CardHeader>

          <CardContent className="p-0">
            <div className="h-80 overflow-y-auto p-4 font-mono text-xs space-y-2 bg-muted/20">
              {messages.length === 0 ? (
                <div className="flex h-full items-center justify-center text-muted-foreground/60">
                  Čekám na zprávy v kanálu...
                </div>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-start gap-2.5 rounded-lg bg-card/80 p-2.5 border border-border/60"
                  >
                    <span className="text-[10px] text-muted-foreground shrink-0">{m.timestamp}</span>
                    <span className="font-semibold text-primary shrink-0">[{m.type}]</span>
                    <span className="font-semibold text-foreground shrink-0">{m.user}:</span>
                    <span className="text-muted-foreground break-all">
                      {typeof m.payload === 'object'
                        ? JSON.stringify(m.payload)
                        : String(m.payload)}
                    </span>
                  </div>
                ))
              )}
            </div>

            {/* Input Bar */}
            <div className="p-3 border-t border-border flex gap-2 bg-card">
              <Input
                placeholder="Napište zprávu a stiskněte Enter..."
                value={inputMsg}
                onChange={(e) => setInputMsg(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                disabled={status !== 'connected'}
                className="text-xs"
              />
              <Button
                onClick={handleSend}
                disabled={status !== 'connected' || !inputMsg.trim()}
                className="gap-1.5 shrink-0"
              >
                <Send className="h-4 w-4" /> Odeslat
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Technical architecture hint */}
        <div className="rounded-2xl border border-border bg-card p-4 text-xs text-muted-foreground space-y-1">
          <p className="font-semibold text-foreground">💡 Jak používat WebSockety ve vašich komponentách:</p>
          <p className="font-mono text-[11px] text-primary">
            const &#123; status, sendMessage, lastMessage &#125; = useWebSocket(&apos;/ws/room/muj_kanal/&apos;);
          </p>
          <p>
            Spojení automaticky posílá váš přihlašovací JWT cookie token a udržuje spojení živé s auto-reconnectem.
          </p>
        </div>
      </div>
    </DashboardLayout>
  );
}
