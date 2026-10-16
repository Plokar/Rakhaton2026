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
    <div className="flex gap-2 rounded-lg border border-dashed border-border bg-muted/50 px-3 py-2 text-sm">
      <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
      <div className="min-w-0">
        <p>
          <span className="font-semibold text-muted-foreground">
            {skipped ? 'Chybí (přeskočeno lékařem):' : 'Údaj chybí v podkladech:'}
          </span>{' '}
          <span className="text-foreground">{text}</span>
          <Citations ids={citations} />
        </p>
        {expectedSource && <p className="mt-0.5 text-xs text-muted-foreground">Doplnit: {expectedSource}</p>}
      </div>
    </div>
  );
}
