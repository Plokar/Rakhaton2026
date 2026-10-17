'use client';

import { CircleAlert } from 'lucide-react';
import { useReadinessQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { Readiness } from '@/types/mdt';

/** Popis připravenosti pro tooltip a čtečky: nevyřešené údaje i přeskočené zůstávají vidět (D-019). */
export function readinessTitle(data: Readiness): string {
  const unresolved = data.unresolved.map((f) => `${f.label} (${f.status === 'skipped' ? 'přeskočeno' : 'chybí'})`);
  const stale = data.stale_staging.map((s) => `staging ${s.age_days} dní`);
  const base = `Připravenost podkladů ${data.score.present}/${data.score.total} (${data.score.percent} %)`;
  const rest = [...unresolved, ...stale];
  return rest.length ? `${base}. Nevyřešeno: ${rest.join(', ')}` : `${base}. Všechny povinné údaje jsou doplněné.`;
}

/**
 * Připravenost případu (BON-1, OBC-1.1 / OBC-1.2) jako číslo: pod 70 % oranžově s ikonou.
 * Mimo barvy semaforu, vždy text (NAVRH_UI §6.2).
 */
export function ReadinessMark({ caseId, className }: { caseId: number; className?: string }) {
  const { data } = useReadinessQuery(caseId);
  if (!data) return <span className={cn('inline-block w-9', className)} aria-hidden />;
  const low = data.score.percent < 70;
  const title = readinessTitle(data);
  return (
    <span
      title={title}
      className={cn(
        'inline-flex shrink-0 items-center justify-end gap-0.5 text-xs tabular-nums',
        low ? 'font-medium text-amber-800 dark:text-amber-300' : 'text-muted-foreground',
        className,
      )}
    >
      {low && <CircleAlert className="size-3.5" aria-hidden />}
      {data.score.percent} %<span className="sr-only">. {title}</span>
    </span>
  );
}
