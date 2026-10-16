'use client';

import * as React from 'react';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';

const fetchReadiness = (caseId: string) => mdtApi.getReadiness(Number(caseId));

/**
 * Připravenost případu v agendě (BON-1): skóre úplnosti podle OBC-1.1 a zastaralý staging (OBC-1.2).
 * Nevyřešené údaje (i přeskočené) jsou v `title`, nic se neztrácí (D-019). Mimo barvy semaforu, vždy text.
 */
export function ReadinessBadge({ caseId }: { caseId: number }) {
  const { data } = useApiData(fetchReadiness, String(caseId));
  if (!data) return null;
  const stale = data.stale_staging.map((s) => `${s.age_days} dní`).join(', ');
  const unresolved = data.unresolved.map((f) => `${f.label} (${f.status === 'skipped' ? 'přeskočeno' : 'chybí'})`);
  return (
    <span
      className="rounded-md border border-border bg-background px-2 py-0.5 text-[11px] font-semibold text-foreground"
      title={unresolved.length ? `Nevyřešeno: ${unresolved.join(', ')}` : 'Všechny povinné údaje jsou doplněné'}
    >
      Připravenost {data.score.present}/{data.score.total} ({data.score.percent} %)
      {data.status === 'ready' ? ' · kompletní' : ` · chybí ${data.unresolved.length}`}
      {stale && ` · staging ${stale}`}
    </span>
  );
}
