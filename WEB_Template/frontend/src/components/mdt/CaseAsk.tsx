'use client';

import * as React from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import type { CaseAnswer } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { ClaimList } from './ClaimList';

const EXAMPLES = ['Kdy byla poslední dávka oxaliplatiny a s jakou toxicitou?', 'Jaký je poslední CEA?', 'Jaké má pacient komorbidity?'];

/**
 * Otázka nad případem během zasedání (BONUS Q&A, T-332): odpověď jen z dat pacienta v IRIS, každá věta
 * s citací přes grounding validátor. Když odpověď v datech není, řekne to; nic nedomýšlí. Odpovědi se
 * nikam neukládají a nejsou součástí záznamu.
 */
export function CaseAsk({ caseId }: { caseId: number }) {
  const [question, setQuestion] = React.useState('');
  const [answers, setAnswers] = React.useState<CaseAnswer[]>([]);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const inputId = React.useId();

  const ask = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    try {
      const answer = await mdtApi.askCase(caseId, q);
      setAnswers((prev) => [answer, ...prev]);
      setQuestion('');
    } catch (err) {
      setError(apiErrorMessage(err, 'Odpověď se nepodařilo získat.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <label htmlFor={inputId} className="text-sm font-medium">Otázka k případu</label>
        <div className="flex gap-2">
          <Input
            id={inputId}
            value={question}
            maxLength={500}
            placeholder="Např. Kdy byla poslední dávka oxaliplatiny a s jakou toxicitou?"
            onChange={(e) => setQuestion(e.target.value)}
          />
          <Button type="submit" isLoading={busy} disabled={!question.trim()}>
            <Send aria-hidden /> Zeptat se
          </Button>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => void ask(example)}
              disabled={busy}
              className="rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
            >
              {example}
            </button>
          ))}
        </div>
      </form>
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {answers.map((answer) => (
        <AiBlock key={answer.answered_at + answer.question} title={answer.question} headingLevel="h3">
          <ClaimList claims={answer.items} />
          <p className="mt-3 text-xs text-muted-foreground">
            {answer.mode === 'ai'
              ? 'Odpověď AI jen z dat pacienta v IRIS, každá věta s citací. Neukládá se do záznamu.'
              : 'Bez AI: nalezené záznamy z dokumentace pacienta, doslova a s citací.'}
          </p>
        </AiBlock>
      ))}
    </div>
  );
}
