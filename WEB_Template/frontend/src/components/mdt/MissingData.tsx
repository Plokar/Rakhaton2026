import { CircleDashed, CircleMinus } from 'lucide-react';
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
  const Icon = skipped ? CircleMinus : CircleDashed;
  return (
    <div className="flex items-start gap-2 rounded-md border border-dashed border-amber-600/40 px-2.5 py-1.5 text-sm dark:border-amber-400/40">
      <Icon className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden />
      <div className="min-w-0 flex-1 leading-snug">
        <p>
          <span className="font-medium text-amber-900 dark:text-amber-200">{skipped ? 'Chybí (přeskočeno lékařem): ' : 'Chybí: '}</span>
          {text}
          <Citations ids={citations} />
        </p>
        {expectedSource && <p className="mt-0.5 text-xs text-muted-foreground">Kde doplnit: {expectedSource}</p>}
      </div>
    </div>
  );
}
