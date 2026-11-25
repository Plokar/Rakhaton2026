'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { RotateCcw } from 'lucide-react';
import { mdtApi } from '@/lib/mdt-api';
import { cn } from '@/lib/utils';
import { formatDate } from './format';

/**
 * Plánovaná re-MDT k naplánování (T-384): komise v závěru určila opětovné projednání a pacient zatím není na
 * žádném budoucím zasedání. Zařazuje lékař sám, nic se nezakládá automaticky.
 */
export function ReMdtCard({ className }: { className?: string }) {
  const { data } = useQuery({ queryKey: ['re-mdt'], queryFn: () => mdtApi.getReMdt(), staleTime: 60_000 });
  if (!data?.length) return null;
  return (
    <section aria-labelledby="remdt-nadpis" className={cn('rounded-xl border border-amber-300/70 bg-amber-50/60 p-4 dark:border-amber-400/30 dark:bg-amber-400/5', className)}>
      <h2 id="remdt-nadpis" className="flex items-center gap-2 text-sm font-semibold">
        <RotateCcw className="size-4" aria-hidden /> Re-MDT k naplánování ({data.length})
      </h2>
      <p className="mt-0.5 text-[13px] text-muted-foreground">Pacienta zařaďte na zasedání komise (Zasedání → board → Zařadit pacienta).</p>
      <ul className="mt-2 divide-y divide-border/70 text-sm">
        {data.map((item) => (
          <li key={item.case_id} className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5 py-1.5">
            <Link href={`/dashboard/patients/${item.patient_id}`} translate="no" className="font-semibold underline-offset-4 hover:underline">
              {item.patient_id}
            </Link>
            <span className={cn('tabular-nums', item.overdue && 'font-medium text-destructive')}>
              {item.overdue ? 'po termínu ' : ''}{formatDate(item.date)}
            </span>
            <span className="min-w-0 flex-1 text-muted-foreground">{item.reason || 'bez uvedeného důvodu'}</span>
            <span className="text-[13px] text-muted-foreground">{item.session.title}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
