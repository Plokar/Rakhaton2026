'use client';

import * as React from 'react';
import { CalendarClock } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { apiErrorMessage, useMoveCase, useSessionsQuery } from '@/lib/queries';
import type { MdtSessionDetail } from '@/types/mdt';
import { dayLabel, isOverdue, timeLabel } from '../dates';
import { isDiscussed } from '../patient';

/**
 * Zasedání po termínu, které nikdo neukončil (T-376). Jen předsedovi: přesunout neprojednané pacienty na
 * nejbližší další zasedání stejné komise, nebo board ukončit. Nic se neděje samo, vždy klik předsedy.
 */
export function OverdueBanner({ board, onClose }: { board: MdtSessionDetail; onClose: () => void }) {
  const sessions = useSessionsQuery();
  const move = useMoveCase();
  const [moving, setMoving] = React.useState(false);
  const [now] = React.useState(() => Date.now());      // čas otevření obrazovky; render zůstává čistý
  if (!isOverdue(board, new Date(now))) return null;

  const pending = board.cases.filter((c) => c.id != null && !isDiscussed(c));
  const sameCommittee = (s: { title: string; committee?: { id: number } | null }) =>
    board.committee?.id ? s.committee?.id === board.committee.id : s.title === board.title;
  const next = (sessions.data ?? [])
    .filter((s) => s.id !== board.id && s.status !== 'closed' && new Date(s.date).getTime() > now && sameCommittee(s))
    .toSorted((a, b) => a.date.localeCompare(b.date))[0];

  const moveAll = async () => {
    if (!next) return;
    setMoving(true);
    try {
      for (const item of pending) await move.mutateAsync({ caseId: item.id as number, from: board.id, to: next.id });
      toast.success(`Přesunuto na ${dayLabel(next.date)} ${timeLabel(next.date)}`, { description: pending.map((c) => c.patient_id).join(', ') });
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Přesun se nepodařil. Zkontrolujte agendu obou zasedání.'));
    } finally {
      setMoving(false);
    }
  };

  return (
    <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-amber-300/60 bg-amber-50 px-4 py-2 text-sm text-amber-950 sm:px-6 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-100">
      <CalendarClock className="size-4 shrink-0" aria-hidden />
      <span className="min-w-0 flex-1">
        <span className="font-medium">Zasedání proběhlo {dayLabel(board.date)} a není ukončené.</span>{' '}
        {pending.length > 0 ? (
          <>Neprojednaní pacienti: <span translate="no" className="font-medium">{pending.map((c) => c.patient_id).join(', ')}</span>.</>
        ) : (
          'Všichni pacienti jsou projednaní.'
        )}
      </span>
      {pending.length > 0 && next && (
        <Button variant="outline" size="sm" onClick={() => void moveAll()} disabled={moving}>
          Přesunout neprojednané na {dayLabel(next.date)}
        </Button>
      )}
      <Button size="sm" onClick={onClose} disabled={moving}>Ukončit board</Button>
    </div>
  );
}
