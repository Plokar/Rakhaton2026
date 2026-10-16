import { cn } from '@/lib/utils';
import type { Light } from '@/types/mdt';

/**
 * Semafor souladu postupu se stavem pacienta (FR-D4, D-015, §5.9). Barva není doporučení
 * a nikdy nenese informaci sama: vždy je u ní značka a text (POZADAVKY §3.4).
 */
export const LIGHT_META: Record<Light, { label: string; mark: string; className: string; dotClass: string }> = {
  green: {
    label: 'nevylučuje',
    mark: '✓',
    className: 'border-emerald-600/50 bg-emerald-50 text-emerald-900 dark:border-emerald-500/50 dark:bg-emerald-950/70 dark:text-emerald-200',
    dotClass: 'bg-emerald-600 text-white dark:bg-emerald-500 dark:text-emerald-950',
  },
  orange: {
    label: 'pozor',
    mark: '!',
    className: 'border-amber-600/60 bg-amber-50 text-amber-950 dark:border-amber-500/50 dark:bg-amber-950/70 dark:text-amber-200',
    dotClass: 'bg-amber-600 text-white dark:bg-amber-500 dark:text-amber-950',
  },
  red: {
    label: 'vylučuje',
    mark: '✕',
    className: 'border-red-600/60 bg-red-50 text-red-950 dark:border-red-500/50 dark:bg-red-950/70 dark:text-red-200',
    dotClass: 'bg-red-600 text-white dark:bg-red-500 dark:text-red-950',
  },
  grey: {
    label: 'nelze posoudit',
    mark: '?',
    className: 'border-slate-400/70 bg-slate-100 text-slate-800 dark:border-slate-600 dark:bg-slate-800/80 dark:text-slate-200',
    dotClass: 'bg-slate-600 text-white dark:bg-slate-500 dark:text-slate-950',
  },
  skipped: {
    label: 'neposuzováno',
    mark: '–',
    className: 'border-dashed border-slate-400 bg-transparent text-muted-foreground',
    dotClass: 'bg-slate-300 text-slate-800 dark:bg-slate-700 dark:text-slate-200',
  },
};

export function CompatibilityLight({ light, className }: { light: Light; className?: string }) {
  const meta = LIGHT_META[light];
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-semibold tracking-tight',
        meta.className,
        className,
      )}
    >
      <span
        aria-hidden
        className={cn('inline-flex h-4 w-4 items-center justify-center rounded-xs text-[10px] font-extrabold leading-none', meta.dotClass)}
      >
        {meta.mark}
      </span>
      {meta.label}
    </span>
  );
}

