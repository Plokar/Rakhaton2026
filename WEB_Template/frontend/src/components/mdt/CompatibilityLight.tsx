import { CircleAlert, CircleCheck, CircleHelp, CircleMinus, CircleX, type LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Light } from '@/types/mdt';

/**
 * Semafor souladu postupu se stavem pacienta (FR-D4, D-015, §5.9). Barva není doporučení
 * a nikdy nenese informaci sama: vždy je u ní tvar ikony a text (POZADAVKY §3.4). Ikony jsou
 * ze stejné kruhové rodiny jako normalita hodnot (`FactIcon`), aby se lékař učil jeden jazyk.
 */
export const LIGHT_META: Record<Light, { label: string; icon: LucideIcon; tone: string; pill: string }> = {
  green: {
    label: 'dobrý',
    icon: CircleCheck,
    tone: 'text-emerald-700 dark:text-emerald-400',
    pill: 'bg-emerald-50 text-emerald-900 ring-emerald-700/20 dark:bg-emerald-400/10 dark:text-emerald-200 dark:ring-emerald-400/25',
  },
  orange: {
    label: 'pozor',
    icon: CircleAlert,
    tone: 'text-amber-700 dark:text-amber-400',
    pill: 'bg-amber-50 text-amber-950 ring-amber-700/25 dark:bg-amber-400/10 dark:text-amber-200 dark:ring-amber-400/25',
  },
  red: {
    label: 'vylučuje',
    icon: CircleX,
    tone: 'text-red-700 dark:text-red-400',
    pill: 'bg-red-50 text-red-950 ring-red-700/20 dark:bg-red-400/10 dark:text-red-200 dark:ring-red-400/25',
  },
  grey: {
    label: 'nelze posoudit',
    icon: CircleHelp,
    tone: 'text-slate-600 dark:text-slate-400',
    pill: 'bg-slate-100 text-slate-800 ring-slate-500/20 dark:bg-slate-400/10 dark:text-slate-300 dark:ring-slate-400/20',
  },
  skipped: {
    label: 'neposuzováno',
    icon: CircleMinus,
    tone: 'text-muted-foreground',
    pill: 'bg-transparent text-muted-foreground ring-border',
  },
};

export function CompatibilityLight({ light, className }: { light: Light; className?: string }) {
  const meta = LIGHT_META[light];
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-0.5 text-xs font-medium ring-1 ring-inset',
        meta.pill,
        className,
      )}
    >
      <Icon className={cn('size-3.5', meta.tone)} strokeWidth={2.25} aria-hidden />
      {meta.label}
    </span>
  );
}

/** Jen ikona semaforu s textem pro čtečky (kompaktní řádky „nelze posoudit“). */
export function LightIcon({ light, className }: { light: Light; className?: string }) {
  const meta = LIGHT_META[light];
  const Icon = meta.icon;
  return (
    <>
      <Icon className={cn('size-4 shrink-0', meta.tone, className)} strokeWidth={2.25} aria-hidden />
      <span className="sr-only">{meta.label}</span>
    </>
  );
}
