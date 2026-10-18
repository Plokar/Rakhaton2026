'use client';

import * as React from 'react';
import { Bot, CircleHelp, LoaderCircle, SendHorizontal, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Textarea } from '@/components/shadcn/textarea';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import type { ChatbotMessage, EvidenceId, MdtCase } from '@/types/mdt';
import { AiTag } from '../AiBlock';
import { CitationProvider, Citations, collectCitations } from '../citations';
import { ClaimItem } from '../ClaimList';
import { timeLabel } from '../dates';
import { SourceDrawer } from '../SourceDrawer';
import type { ChatbotState } from './use-chatbot';

const MAX_LENGTH = 2000;

/**
 * Chatbot u zasedání (T-344): lékař se ptá AI na pacienta na řadě (bez štítku jen guidelines a studie).
 * Každé tvrzení odpovědi má citaci, klik otevře zdroj v bočním panelu; neověřené tvrzení, chybějící údaj
 * a nejistota AI jsou označené. Rozhovor je soukromý, odpověď AI není oficiální záznam. Uzavřený board jen ke čtení.
 */
export function ChatbotPanel({
  bot,
  current,
  closed,
  onClose,
  onSelectCase,
  Title = 'h2',
}: {
  bot: ChatbotState;
  /** Pacient na řadě: dotaz se ptá na něj. */
  current: Pick<MdtCase, 'id' | 'patient_id'> | null;
  closed: boolean;
  /** Bez `onClose` panel nemá vlastní zavírací tlačítko (Sheet má svoje). */
  onClose?: () => void;
  onSelectCase?: (caseId: number) => void;
  Title?: React.ElementType;
}) {
  const { messages, query, send } = bot;
  const [text, setText] = React.useState('');
  const [tagged, setTagged] = React.useState(true);
  const [sourceId, setSourceId] = React.useState<EvidenceId | null>(null);
  const list = React.useRef<HTMLOListElement>(null);
  const citationOrder = React.useMemo(() => collectCitations(messages), [messages]);
  const pending = send.isPending ? send.variables : undefined;

  // Vlastní rozhovor: po dotazu i odpovědi vždy dolů.
  React.useEffect(() => {
    const el = list.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, send.isPending]);

  const tag = tagged && current ? current : null;
  const submit = () => {
    const body = text.trim();
    if (!body || send.isPending || closed) return;
    setText('');
    send.mutate(
      { text: body, case_id: tag?.id ?? null },
      {
        onError: (err) => {
          setText(body);
          toast.error(apiErrorMessage(err, 'Dotaz se nepodařilo odeslat.'));
        },
      },
    );
  };

  return (
    <section aria-labelledby="chatbot-title" className="flex h-full min-h-0 flex-col bg-card">
      <header className="flex shrink-0 items-center gap-2 border-b border-border px-4 py-3">
        <Bot className="size-4 text-ai" aria-hidden />
        <Title id="chatbot-title" className="text-sm font-semibold">Chatbot</Title>
        <span className="text-xs text-muted-foreground">odpovědi AI se zdroji</span>
        {onClose && (
          <Button variant="ghost" size="icon-sm" className="ml-auto" onClick={onClose} aria-label="Zavřít chatbot" title="Zavřít chatbot (A)">
            <X aria-hidden />
          </Button>
        )}
      </header>

      <CitationProvider order={citationOrder} activeId={sourceId} onOpen={setSourceId}>
        <ol
          ref={list}
          role="log"
          aria-label="Rozhovor s AI"
          aria-live="polite"
          aria-busy={send.isPending}
          className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-3"
        >
          {query.isLoading ? (
            <li className="text-sm text-muted-foreground">Načítám rozhovor…</li>
          ) : query.isError ? (
            <li role="alert" className="text-sm text-destructive">{apiErrorMessage(query.error, 'Rozhovor se nepodařilo načíst.')}</li>
          ) : messages.length === 0 && !pending ? (
            <li className="space-y-2 text-sm text-muted-foreground">
              <p>Zeptejte se AI na pacienta na řadě, třeba „Jak se vyvíjí CEA?“ nebo „Splňuje kritéria studie RKT-03?“.</p>
              <p>AI odpovídá jen z dokumentace v IRIS. Každé tvrzení má zdroj, kliknutím na číslo ho otevřete. Rozhovor vidíte jen vy.</p>
            </li>
          ) : (
            messages.map((m) =>
              m.role === 'user' ? (
                <Question key={m.id} text={m.text} label={m.case} createdAt={m.created_at} onSelectCase={onSelectCase} />
              ) : (
                <Answer key={m.id} message={m} />
              ),
            )
          )}
          {pending && (
            <>
              <Question
                text={pending.text}
                label={pending.case_id != null && current?.id === pending.case_id ? { id: pending.case_id, patient_id: current.patient_id } : null}
              />
              <li className="flex items-center gap-2 text-sm text-muted-foreground">
                <LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden />
                AI odpovídá…
              </li>
            </>
          )}
        </ol>
        <SourceDrawer evidenceId={sourceId} loadSource={mdtApi.getEvidence} onClose={() => setSourceId(null)} />
      </CitationProvider>

      <form
        className="shrink-0 space-y-2 border-t border-border px-4 py-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {closed ? (
          <p className="text-sm text-muted-foreground">Board je uzavřený, chatbot je jen ke čtení.</p>
        ) : (
          <>
            <div className="flex min-h-6 items-center gap-2 text-xs text-muted-foreground">
              {tag ? (
                <>
                  <span>Ptáte se na</span>
                  <span translate="no" className="inline-flex items-center gap-1 rounded-md bg-primary/10 py-0.5 pr-1 pl-1.5 font-medium text-foreground">
                    {tag.patient_id}
                    <button
                      type="button"
                      onClick={() => setTagged(false)}
                      className="rounded-sm p-0.5 hover:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                      aria-label={`Odebrat ${tag.patient_id}, ptát se jen na guidelines a studie`}
                    >
                      <X className="size-3" aria-hidden />
                    </button>
                  </span>
                </>
              ) : (
                <>
                  <span>Obecně: jen guidelines a studie</span>
                  {current && (
                    <button
                      type="button"
                      onClick={() => setTagged(true)}
                      className="rounded-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                      Ptát se na {current.patient_id}
                    </button>
                  )}
                </>
              )}
            </div>
            <div className="flex items-end gap-2">
              <label htmlFor="chatbot-input" className="sr-only">Dotaz pro AI</label>
              <Textarea
                id="chatbot-input"
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
                placeholder="Zeptejte se AI…"
                className="max-h-40 min-h-9 resize-none"
              />
              <Button type="submit" size="icon" disabled={!text.trim() || send.isPending} aria-label="Odeslat dotaz">
                <SendHorizontal aria-hidden />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Enter odešle, Shift+Enter nový řádek. Odpověď AI je návrh z dokumentace, ne oficiální záznam. Nepište jméno ani RČ pacienta.
            </p>
          </>
        )}
      </form>
    </section>
  );
}

function Question({
  text,
  label,
  createdAt,
  onSelectCase,
}: {
  text: string;
  label: { id: number; patient_id: string } | null;
  createdAt?: string;
  onSelectCase?: (caseId: number) => void;
}) {
  return (
    <li className="flex flex-col items-end gap-1 pl-8">
      <p className="flex flex-wrap items-baseline gap-x-1.5 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Vy</span>
        {createdAt && <time dateTime={createdAt} className="tabular-nums">{timeLabel(createdAt)}</time>}
        {label &&
          (onSelectCase ? (
            <button
              type="button"
              translate="no"
              onClick={() => onSelectCase(label.id)}
              title={`Zobrazit ${label.patient_id}`}
              className="rounded-md bg-muted px-1.5 py-px font-medium text-foreground hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {label.patient_id}
            </button>
          ) : (
            <span translate="no" className="rounded-md bg-muted px-1.5 py-px font-medium text-foreground">{label.patient_id}</span>
          ))}
      </p>
      <p className="max-w-full rounded-lg bg-primary/10 px-3 py-2 text-sm whitespace-pre-wrap break-words text-foreground">{text}</p>
    </li>
  );
}

/** Odpověď AI: fialový pruh vlevo (D-017) a štítek „AI návrh“, tvrzení s citacemi jako v podkladu. */
function Answer({ message }: { message: ChatbotMessage }) {
  const empty = !message.text && message.claims.length === 0 && message.uncertain.length === 0;
  return (
    <li className="flex flex-col items-start gap-1 pr-4">
      <p className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
        <AiTag />
        {message.case && <span translate="no" className="font-medium text-foreground">{message.case.patient_id}</span>}
        <time dateTime={message.created_at} className="tabular-nums">{timeLabel(message.created_at)}</time>
      </p>
      <div className="w-full space-y-2 border-l-2 border-ai/50 pl-3">
        {message.text && <p className="text-sm text-muted-foreground">{message.text}</p>}
        {empty && <p className="text-sm text-muted-foreground">AI neodpověděla.</p>}
        {message.claims.length > 0 && (
          <ul className="flex flex-col gap-2">
            {message.claims.map((claim) => (
              <li key={claim.id}>
                <ClaimItem claim={claim} />
              </li>
            ))}
          </ul>
        )}
        {message.uncertain.map((u, i) => (
          <p key={i} className="rounded-md bg-amber-50 px-2.5 py-1.5 text-sm leading-relaxed dark:bg-amber-400/10">
            <span className="mr-1.5 inline-flex items-center gap-1 align-baseline text-xs font-medium text-amber-800 dark:text-amber-300">
              <CircleHelp className="size-3.5 self-center" aria-hidden /> Nejistota AI
            </span>
            {u.text}
            <Citations ids={u.citations} />
          </p>
        ))}
      </div>
    </li>
  );
}
