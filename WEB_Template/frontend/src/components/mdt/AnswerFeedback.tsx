'use client';

import * as React from 'react';
import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Input } from '@/components/shadcn/input';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { cn } from '@/lib/utils';

type Target =
  | { message_id: number }
  | { patient_id: string; question: string; answer: unknown };

/**
 * Hodnocení odpovědi AI (T-382): 👍 / 👎 a u špatné odpovědi krátký důvod. Ukládá se pro vyhodnocení a ladění
 * promptů (`export_ai_feedback`); nic se nemění v podkladu ani v záznamu.
 */
export function AnswerFeedback({ target, className }: { target: Target; className?: string }) {
  const [rating, setRating] = React.useState<'up' | 'down' | null>(null);
  const [asking, setAsking] = React.useState(false);
  const [comment, setComment] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const send = (value: 'up' | 'down', text = '') => {
    setBusy(true);
    mdtApi
      .postAiFeedback({ ...target, rating: value, ...(text ? { comment: text } : {}) })
      .then(() => {
        setRating(value);
        setAsking(false);
        toast(value === 'up' ? 'Díky, odpověď označena jako dobrá.' : 'Díky, špatnou odpověď použijeme při ladění AI.', { duration: 2000 });
      })
      .catch((err: unknown) => toast.error(apiErrorMessage(err, 'Hodnocení se nepodařilo uložit.')))
      .finally(() => setBusy(false));
  };
  return (
    <div className={cn('flex flex-wrap items-center gap-1 pl-3 text-xs text-muted-foreground', className)}>
      <span className="mr-1">Odpověď byla</span>
      <Button variant={rating === 'up' ? 'secondary' : 'ghost'} size="icon-sm" disabled={busy} aria-pressed={rating === 'up'}
        aria-label="Dobrá odpověď" title="Dobrá odpověď" onClick={() => send('up')}>
        <ThumbsUp aria-hidden />
      </Button>
      <Button variant={rating === 'down' ? 'secondary' : 'ghost'} size="icon-sm" disabled={busy} aria-pressed={rating === 'down'}
        aria-label="Špatná odpověď" title="Špatná odpověď" onClick={() => setAsking(true)}>
        <ThumbsDown aria-hidden />
      </Button>
      {asking && (
        <form
          className="flex w-full items-center gap-1.5 pt-1"
          onSubmit={(e) => {
            e.preventDefault();
            send('down', comment.trim());
          }}
        >
          <Input value={comment} onChange={(e) => setComment(e.target.value)} maxLength={1000} placeholder="Co bylo špatně? (nepovinné)"
            aria-label="Co bylo na odpovědi špatně" className="h-8 text-xs" />
          <Button type="submit" size="sm" disabled={busy}>Odeslat</Button>
        </form>
      )}
    </div>
  );
}
