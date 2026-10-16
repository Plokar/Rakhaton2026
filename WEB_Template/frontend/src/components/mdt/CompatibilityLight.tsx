import { cn } from '@/lib/utils';
import type { Light } from '@/types/mdt';

/**
 * Semafor souladu postupu se stavem pacienta (FR-D4, D-015, §5.9). Barva není doporučení
 * a nikdy nenese informaci sama: vždy je u ní značka a text (POZADAVKY §3.4).
 */
export const LIGHT_META: Record<Light, { label: string; mark: string; className: string }> = {
  green: {
    label: 'nevylučuje',
    mark: '✓',
    className: 'border-emerald-500/50 bg-emerald-500/15 text-emerald-800 dark:text-emerald-300',
  },
  orange: {
    label: 'pozor',
    mark: '!',
    className: 'border-orange-500/50 bg-orange-500/15 text-orange-800 dark:text-orange-300',
  },
  red: { label: 'vylučuje', mark: '✕', className: 'border-red-500/50 bg-red-500/15 text-red-800 dark:text-red-300' },
  grey: { label: 'nelze posoudit', mark: '?', className: 'border-zinc-400/60 bg-zinc-500/15 text-zinc-700 dark:text-zinc-300' },
  skipped: {
    label: 'neposuzováno',
    mark: '–',
    className: 'border-dashed border-zinc-400/60 text-muted-foreground',
  },
};

export function CompatibilityLight({ light, className }: { light: Light; className?: string }) {
  const meta = LIGHT_META[light];
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold',
        meta.className,
        className,
      )}
    >
      <span aria-hidden className="font-bold">
        {meta.mark}
      </span>
      {meta.label}
    </span>
  );
}
