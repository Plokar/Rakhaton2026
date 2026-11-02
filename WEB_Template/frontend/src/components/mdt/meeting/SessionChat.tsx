'use client';

import * as React from 'react';
import { MessagesSquare, SendHorizontal, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Textarea } from '@/components/shadcn/textarea';
import { apiErrorMessage } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtCase, SessionMessage } from '@/types/mdt';
import { timeLabel } from '../dates';
import { useMe } from '../me';
import { ROLE_META } from '../roles';
import type { ChatConnection, SessionChatState } from './use-session-chat';

const MAX_LENGTH = 2000;

const CONNECTION_LABEL: Record<ChatConnection, string> = {
  live: 'živě',
  connecting: 'připojuji…',
  offline: 'bez spojení, zkouším znovu',
};

/**
 * Chat lékařů u zasedání (T-334): jedno vlákno na board, zpráva nese štítek pacienta, který byl na řadě.
 * V jednání panel vpravo, na úzkém displeji v bočním panelu. Uzavřený board je jen ke čtení.
 */
export function SessionChat({
  chat,
  current,
  closed,
  onClose,
  onSelectCase,
  Title = 'h2',
}: {
  chat: SessionChatState;
  /** Pacient na řadě: nová zpráva dostane jeho štítek. */
  current: Pick<MdtCase, 'id' | 'patient_id'> | null;
  closed: boolean;
  /** Bez `onClose` panel nemá vlastní zavírací tlačítko (Sheet má svoje). */
  onClose?: () => void;
  onSelectCase?: (caseId: number) => void;
  Title?: React.ElementType;
}) {
  const me = useMe();
  const { messages, query, connection, send } = chat;
  const [text, setText] = React.useState('');
  const [tagged, setTagged] = React.useState(true);
  const list = React.useRef<HTMLOListElement>(null);
  const atBottom = React.useRef(true);
  const lastId = messages.at(-1)?.id ?? 0;
  const lastOwn = messages.at(-1)?.author?.user_id === me?.user_id;

  // Nová zpráva: posunout dolů, jen když je lékař u poslední (nebo ji napsal sám), ať mu neuskočí čtení.
  React.useEffect(() => {
    const el = list.current;
    if (el && (atBottom.current || lastOwn)) el.scrollTop = el.scrollHeight;
  }, [lastId, lastOwn]);

  const tag = tagged && current ? current : null;
  const submit = () => {
    const body = text.trim();
    if (!body || send.isPending || closed) return;
    send.mutate(
      { text: body, case_id: tag?.id ?? null },
      {
        onSuccess: () => setText(''),
        onError: (err) => toast.error(apiErrorMessage(err, 'Zprávu se nepodařilo odeslat.')),
      },
    );
  };

  return (
    <section aria-labelledby="session-chat-title" className="flex h-full min-h-0 flex-col bg-card">
      <header className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-3">
        <MessagesSquare className="size-4 text-muted-foreground" aria-hidden />
        <Title id="session-chat-title" className="text-sm font-semibold">Chat lékařů</Title>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground" aria-live="polite">
          <span
            aria-hidden
            className={cn(
              'size-1.5 rounded-full',
              connection === 'live' ? 'bg-emerald-600 dark:bg-emerald-400' : connection === 'offline' ? 'bg-amber-600 dark:bg-amber-400' : 'bg-muted-foreground/50',
            )}
          />
          {CONNECTION_LABEL[connection]}
        </span>
        {onClose && (
          <Button variant="ghost" size="icon-sm" className="ml-auto" onClick={onClose} aria-label="Zavřít chat" title="Zavřít chat (C)">
            <X aria-hidden />
          </Button>
        )}
      </header>

      <ol
        ref={list}
        role="log"
        aria-label="Zprávy"
        aria-live="polite"
        onScroll={(e) => {
          const el = e.currentTarget;
          atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
        }}
        className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3"
      >
        {query.isLoading ? (
          <li className="text-sm text-muted-foreground">Načítám zprávy…</li>
        ) : query.isError ? (
          <li role="alert" className="text-sm text-destructive">{apiErrorMessage(query.error, 'Zprávy se nepodařilo načíst.')}</li>
        ) : messages.length === 0 ? (
          <li className="text-sm text-muted-foreground">
            Zatím tu nic není. Zprávu uvidí všichni lékaři tohoto zasedání hned, bez obnovení stránky.
          </li>
        ) : (
          messages.map((m) => <ChatMessage key={m.id} message={m} own={m.author?.user_id === me?.user_id} onSelectCase={onSelectCase} />)
        )}
      </ol>

      <form
        className="shrink-0 space-y-2 border-t border-border px-4 py-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {closed ? (
          <p className="text-sm text-muted-foreground">Board je uzavřený, chat je jen ke čtení.</p>
        ) : (
          <>
            <div className="flex min-h-6 items-center gap-2 text-xs text-muted-foreground">
              {tag ? (
                <>
                  <span>K pacientovi</span>
                  <span translate="no" className="inline-flex items-center gap-1 rounded-md bg-primary/10 py-0.5 pr-1 pl-1.5 font-medium text-foreground">
                    {tag.patient_id}
                    <button
                      type="button"
                      onClick={() => setTagged(false)}
                      className="rounded-sm p-0.5 hover:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label={`Odebrat štítek ${tag.patient_id}, zpráva k celému zasedání`}
                    >
                      <X className="size-3" aria-hidden />
                    </button>
                  </span>
                </>
              ) : (
                <>
                  <span>K celému zasedání</span>
                  {current && (
                    <button
                      type="button"
                      onClick={() => setTagged(true)}
                      className="rounded-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      Přidat štítek {current.patient_id}
                    </button>
                  )}
                </>
              )}
            </div>
            <div className="flex items-end gap-2">
              <label htmlFor="session-chat-input" className="sr-only">Zpráva pro lékaře zasedání</label>
              <Textarea
                id="session-chat-input"
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                    e.preventDefault();
                    submit();
                  }
                }}
                maxLength={MAX_LENGTH}
                rows={1}
                placeholder="Napište zprávu…"
                className="max-h-40 min-h-9 resize-none"
              />
              <Button type="submit" size="icon" disabled={!text.trim() || send.isPending} aria-label="Odeslat zprávu">
                <SendHorizontal aria-hidden />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">Enter odešle, Shift+Enter nový řádek. Nepište jméno ani RČ pacienta.</p>
          </>
        )}
      </form>
    </section>
  );
}

function ChatMessage({
  message,
  own,
  onSelectCase,
}: {
  message: SessionMessage;
  own: boolean;
  onSelectCase?: (caseId: number) => void;
}) {
  const name = own ? 'Vy' : message.author?.name ?? 'Smazaný účet';
  const label = message.specialty ? ROLE_META[message.specialty]?.label : null;
  // demo účty se jmenují podle odbornosti („Chirurg“), ať to není dvakrát
  const specialty = label && label.toLowerCase() !== message.author?.name.toLowerCase() ? label : null;
  const c = message.case;
  return (
    <li className={cn('flex flex-col gap-1', own ? 'items-end pl-8' : 'items-start pr-8')}>
      <p className="flex flex-wrap items-baseline gap-x-1.5 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{name}</span>
        {specialty && <span>{specialty}</span>}
        <time dateTime={message.created_at} className="tabular-nums">{timeLabel(message.created_at)}</time>
        {c &&
          (onSelectCase ? (
            <button
              type="button"
              translate="no"
              onClick={() => onSelectCase(c.id)}
              title={`Zobrazit ${c.patient_id}`}
              className="rounded-md bg-muted px-1.5 py-px font-medium text-foreground hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {c.patient_id}
            </button>
          ) : (
            <span translate="no" className="rounded-md bg-muted px-1.5 py-px font-medium text-foreground">{c.patient_id}</span>
          ))}
      </p>
      <p
        className={cn(
          'max-w-full rounded-lg px-3 py-2 text-sm whitespace-pre-wrap break-words',
          own ? 'bg-primary/10 text-foreground' : 'bg-muted text-foreground',
        )}
      >
        {message.text}
      </p>
    </li>
  );
}
