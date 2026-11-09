'use client';

import * as React from 'react';
import { useMutation } from '@tanstack/react-query';
import { Bot, LoaderCircle, SendHorizontal } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/shadcn/dialog';
import { Textarea } from '@/components/shadcn/textarea';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { ChatbotMessage, Claim, EvidenceId, ProjectorExtra } from '@/types/mdt';
import { ChatAnswer, ChatQuestion, type ChatAnswerData } from './ChatbotAnswer';
import { CitationProvider, collectCitations } from './citations';
import { SourceDrawer } from './SourceDrawer';

const MAX_LENGTH = 2000;
const HISTORY = 6;                  // předchozích zpráv do kontextu AI (jako chatbot u zasedání)
export const MAX_EXTRA = 12;        // údajů doplněných do okna pro projektor (stejně hlídá server)
const EXAMPLES = ['Jaká je hodnota FEV1?', 'Jaká je poslední hodnota CEA?', 'Kdy bylo poslední CT a co ukázalo?'];

type Turn = { id: number; question: string; askedAt: string; answer: ChatAnswerData | null };

/** Stejné tvrzení se stejnými zdroji je v okně jen jednou. */
const extraKey = (x: Pick<ProjectorExtra, 'text' | 'citations'>) => `${x.text.trim()}|${x.citations.join(',')}`;

/** Stabilní krátké ID údaje z jeho klíče (ID tvrzení `bot-01` se v každé odpovědi opakují). */
function extraId(key: string): string {
  let hash = 5381;
  for (let i = 0; i < key.length; i += 1) hash = (hash * 33) ^ key.charCodeAt(i);
  return `z-${(hash >>> 0).toString(36)}-${key.length.toString(36)}`;
}

/**
 * Chat vedle formuláře zařazení (T-345): „+ Doplnit z karty“ v editoru okna skočí do něj. Vrací false, když chat
 * vidět není (úzký displej); editor pak otevře chatbot v dialogu uprostřed.
 */
export const PatientChatFocus = React.createContext<(() => boolean) | null>(null);

type PanelProps = {
  patientId: string;
  /** Co už v okně je: u tvrzení se místo tlačítka ukáže „V okně pro projektor“. */
  extra?: ProjectorExtra[];
  onAdd?: (item: ProjectorExtra) => void;
};

/**
 * Chatbot nad kartou pacienta (T-345): lékař, který pacienta zařazuje, se doptává na dokumentaci v IRIS. Odpověď je
 * krátce údaj a hodnota, pod ní datum, doslovný text ze zdroje a proklik na zdroj; tvrzení se zdrojem jde jedním
 * klikem do okna pro projektor. Odpověď AI je návrh, nic se neukládá do záznamu; rozhovor drží jen tato stránka.
 */
export function PatientChatPanel({
  patientId,
  extra = [],
  onAdd,
  inputRef,
  className,
  Title = 'h2',
  Description = 'p',
}: PanelProps & {
  inputRef?: React.Ref<HTMLTextAreaElement>;
  className?: string;
  Title?: React.ElementType;
  Description?: React.ElementType;
}) {
  const [turns, setTurns] = React.useState<Turn[]>([]);
  const [text, setText] = React.useState('');
  const [sourceId, setSourceId] = React.useState<EvidenceId | null>(null);
  const list = React.useRef<HTMLOListElement>(null);
  const nextTurn = React.useRef(0);
  const inputId = React.useId();
  const titleId = React.useId();
  const citationOrder = React.useMemo(() => collectCitations(turns.map((t) => t.answer)), [turns]);
  const added = React.useMemo(() => new Set(extra.map(extraKey)), [extra]);
  const full = extra.length >= MAX_EXTRA;

  const ask = useMutation({
    mutationFn: (input: { text: string; history: Pick<ChatbotMessage, 'role' | 'text' | 'claims'>[] }) =>
      mdtApi.askPatientChatbot(patientId, input),
  });

  // Po dotazu i odpovědi vždy dolů.
  React.useEffect(() => {
    const el = list.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [turns]);

  const send = (value: string) => {
    const question = value.trim();
    if (!question || ask.isPending) return;
    const history = turns
      .filter((t) => t.answer)
      .flatMap((t) => [
        { role: 'user' as const, text: t.question, claims: [] },
        { role: 'ai' as const, text: t.answer!.text, claims: t.answer!.claims },
      ])
      .slice(-HISTORY);
    const id = (nextTurn.current += 1);
    setTurns((prev) => [...prev, { id, question, askedAt: new Date().toISOString(), answer: null }]);
    setText('');
    ask.mutate(
      { text: question, history },
      {
        onSuccess: (answer) =>
          setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, answer: { ...answer, created_at: new Date().toISOString() } } : t))),
        onError: (err) => {
          setTurns((prev) => prev.filter((t) => t.id !== id));
          setText(question);
          toast.error(apiErrorMessage(err, 'Dotaz se nepodařilo odeslat.'));
        },
      },
    );
  };

  const add = (claim: Claim, ai: boolean) => {
    const item = { text: claim.text.trim().slice(0, 500), citations: claim.citations, ai };
    onAdd?.({ id: extraId(extraKey(item)), ...item });
  };

  return (
    <section aria-labelledby={titleId} className={cn('flex min-h-0 flex-col bg-card', className)}>
      <header className="flex shrink-0 items-baseline gap-2 border-b border-border px-4 py-3 in-data-[slot=dialog-content]:pr-12">
        <Bot className="size-4 translate-y-0.5 self-start text-ai" aria-hidden />
        <Title id={titleId} className="text-sm font-semibold">Chatbot</Title>
        <Description className="text-xs text-muted-foreground">
          karta pacienta <span translate="no" className="font-medium text-foreground">{patientId}</span>, odpovědi AI se zdroji
        </Description>
      </header>

      <CitationProvider order={citationOrder} activeId={sourceId} onOpen={setSourceId}>
        <ol
          ref={list}
          role="log"
          aria-label="Rozhovor s AI nad kartou pacienta"
          aria-live="polite"
          aria-busy={ask.isPending}
          className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-3"
        >
          {turns.length === 0 ? (
            <li className="flex flex-col gap-3 text-sm text-muted-foreground">
              <p className="max-w-prose">
                Doptejte se na cokoli z dokumentace pacienta v IRIS. Odpověď je údaj a hodnota, pod ní datum, doslovný text
                ze zdroje a proklik na zdroj{onAdd ? '. Údaj se zdrojem jde jedním klikem doplnit do okna pro projektor' : ''}.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {EXAMPLES.map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => send(example)}
                    className="rounded-lg border border-border px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {example}
                  </button>
                ))}
              </div>
            </li>
          ) : (
            turns.map((turn) => (
              <React.Fragment key={turn.id}>
                <ChatQuestion
                  text={turn.question}
                  createdAt={turn.askedAt}
                  tag={<span translate="no" className="rounded-md bg-muted px-1.5 py-px font-medium text-foreground">{patientId}</span>}
                />
                {turn.answer ? (
                  <ChatAnswer
                    message={turn.answer}
                    patientId={patientId}
                    onAdd={onAdd && !full ? add : undefined}
                    isAdded={(claim) => added.has(extraKey(claim))}
                  />
                ) : (
                  <li className="flex items-center gap-2 text-sm text-muted-foreground">
                    <LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden />
                    AI hledá v kartě pacienta…
                  </li>
                )}
              </React.Fragment>
            ))
          )}
        </ol>
        <SourceDrawer evidenceId={sourceId} loadSource={mdtApi.getEvidence} onClose={() => setSourceId(null)} />
      </CitationProvider>

      <form
        className="shrink-0 space-y-2 border-t border-border px-4 py-3"
        onSubmit={(e) => {
          e.preventDefault();
          e.stopPropagation();              // portál dialogu: odeslání nesmí probublat do formuláře zařazení
          send(text);
        }}
      >
        {onAdd && full && (
          <p className="text-xs text-muted-foreground">Okno pro projektor má už {MAX_EXTRA} doplněných údajů. Další přidáte, až nějaký odeberete.</p>
        )}
        <div className="flex items-end gap-2">
          <label htmlFor={inputId} className="sr-only">Dotaz pro AI na kartu pacienta</label>
          <Textarea
            ref={inputRef}
            id={inputId}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                send(text);
              }
            }}
            maxLength={MAX_LENGTH}
            rows={1}
            placeholder={`Doptat se na kartu ${patientId}…`}
            className="max-h-40 min-h-9 resize-none"
          />
          <Button type="submit" size="icon" disabled={!text.trim() || ask.isPending} aria-label="Odeslat dotaz">
            <SendHorizontal aria-hidden />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Enter odešle, Shift+Enter nový řádek. Odpověď AI je návrh z dokumentace, ne oficiální záznam. Nepište jméno ani RČ pacienta.
        </p>
      </form>
    </section>
  );
}

/** Chatbot nad kartou v dialogu uprostřed: z editoru okna u případu, nebo při zařazení na užším displeji. */
export function PatientChatDialog({
  open,
  onOpenChange,
  ...panel
}: PanelProps & { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[min(44rem,calc(100dvh-4rem))] flex-col gap-0 overflow-hidden p-0 shadow-[0_24px_48px_-12px_rgb(15_23_42/0.35)] sm:max-w-2xl">
        <PatientChatPanel {...panel} Title={DialogTitle} Description={DialogDescription} className="flex-1" />
      </DialogContent>
    </Dialog>
  );
}
