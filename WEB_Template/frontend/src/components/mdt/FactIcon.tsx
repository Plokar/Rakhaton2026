import { CircleAlert, CircleCheck, CircleDashed, CircleDot, CircleMinus, Clock, OctagonAlert, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FactStatus } from './key-facts';

/**
 * Normalita údaje pacienta (T-512): barvu určuje jen referenční rozmezí z laboratoře nebo pravidlo
 * s citací, nikdy odhad. Tvar ikony nese význam i bez barvy (POZADAVKY §3.4).
 */
export const FACT_META: Record<FactStatus, { label: string; icon: LucideIcon; tone: string }> = {
  normal: { label: 'v normě', icon: CircleCheck, tone: 'text-emerald-700 dark:text-emerald-400' },
  abnormal: { label: 'mimo normu', icon: CircleAlert, tone: 'text-amber-700 dark:text-amber-400' },
  critical: { label: 'závažné', icon: OctagonAlert, tone: 'text-red-700 dark:text-red-400' },
  recorded: { label: 'bez hodnocení normality', icon: CircleDot, tone: 'text-muted-foreground' },
  missing: { label: 'chybí', icon: CircleDashed, tone: 'text-muted-foreground' },
  pending: { label: 'čeká se na výsledek', icon: Clock, tone: 'text-muted-foreground' },
  skipped: { label: 'přeskočeno lékařem', icon: CircleMinus, tone: 'text-muted-foreground' },
};

export function FactIcon({ status, className }: { status: FactStatus; className?: string }) {
  const meta = FACT_META[status];
  const Icon = meta.icon;
  return <Icon className={cn('size-4 shrink-0', meta.tone, className)} strokeWidth={2.25} aria-hidden />;
}

const LEGEND: FactStatus[] = ['normal', 'abnormal', 'critical', 'recorded', 'missing'];

/** Vysvětlivky normality (nápověda, NAVRH_UI heuristika 10). */
export function FactLegend({ className }: { className?: string }) {
  return (
    <ul className={cn('flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground', className)} aria-label="Vysvětlivky">
      {LEGEND.map((status) => (
        <li key={status} className="inline-flex items-center gap-1">
          <FactIcon status={status} className="size-3.5" />
          {FACT_META[status].label}
        </li>
      ))}
    </ul>
  );
}
