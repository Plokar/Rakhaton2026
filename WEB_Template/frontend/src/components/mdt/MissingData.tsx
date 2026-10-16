import { CircleDashed } from 'lucide-react';
import type { EvidenceId } from '@/types/mdt';
import { Citations } from './citations';

/**
 * Chybějící údaj (FR-R3): AI ho nehádá, řekne, co chybí a kde by měl být.
 * `skipped` = lékař údaj při zařazení přeskočil (D-019), v podkladu zůstává.
 */
export function MissingData({
  text,
  expectedSource,
  citations = [],
  skipped = false,
}: {
  text: string;
  expectedSource?: string;
  citations?: EvidenceId[];
  skipped?: boolean;
}) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-dashed border-amber-500/60 bg-amber-50/60 px-3 py-2.5 text-sm dark:border-amber-500/40 dark:bg-amber-950/30">
      <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="leading-snug">
          <span className="mr-1.5 inline-flex items-center rounded-sm bg-amber-200/70 px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-amber-950 dark:bg-amber-900/60 dark:text-amber-200">
            {skipped ? 'Chybí (přeskočeno lékařem)' : 'Údaj chybí v podkladech'}
          </span>
          <span className="font-medium text-foreground">{text}</span>
          <Citations ids={citations} />
        </p>
        {expectedSource && (
          <p className="mt-1 text-xs font-medium text-muted-foreground">
            Kde doplnit: <span className="text-foreground">{expectedSource}</span>
          </p>
        )}
      </div>
    </div>
  );
}

