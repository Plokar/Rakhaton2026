import { TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefHeader } from '@/types/mdt';
import { Citations } from './citations';
import { formatDate } from './format';

type Ecog = BriefHeader['ecog'];

export function ecogDifference(ecog: Ecog): number | null {
  return ecog.physician && ecog.patient ? Math.abs(ecog.physician.value - ecog.patient.value) : null;
}

/**
 * ECOG lékaře (velká číslice) a ECOG podle pacienta (PROMs `samostatnost`) vedle sebe (FR-A2, D-018).
 * Rozdíl ≥ 1 je varovný signál (OBC-1.3): oranžový rámeček a text, ne jen barva.
 */
export function EcogTiles({ ecog }: { ecog: Ecog }) {
  const warn = (ecogDifference(ecog) ?? 0) >= 1;
  return (
    <>
      <div className="rounded-lg border border-border bg-background p-2 text-center">
        <p className="text-[11px] font-medium text-muted-foreground">ECOG lékař</p>
        {ecog.physician ? (
          <>
            <p className="text-4xl font-extrabold leading-tight text-foreground">{ecog.physician.value}</p>
            <p className="text-[10px] text-muted-foreground">
              {formatDate(ecog.physician.date)}
              <Citations ids={[ecog.physician.citation]} />
            </p>
          </>
        ) : (
          <p className="py-2 text-xs text-muted-foreground">Údaj chybí</p>
        )}
      </div>
      <div className={cn('rounded-lg border p-2 text-center', warn ? 'border-orange-500/60 bg-orange-500/10' : 'border-border bg-background')}>
        <p className="text-[11px] font-medium text-muted-foreground">ECOG pacient</p>
        {ecog.patient ? (
          <>
            <p className="text-2xl font-bold leading-tight text-foreground">{ecog.patient.value}</p>
            <p className="text-[10px] text-muted-foreground">
              {formatDate(ecog.patient.date)}
              <Citations ids={[ecog.patient.citation]} />
            </p>
          </>
        ) : (
          <p className="py-2 text-xs text-muted-foreground">Údaj chybí</p>
        )}
      </div>
    </>
  );
}

export function EcogDifference({ ecog }: { ecog: Ecog }) {
  const diff = ecogDifference(ecog);
  if (diff === null || diff < 1) return null;
  return (
    <p className="flex items-start gap-1.5 text-xs font-medium text-orange-700 dark:text-orange-300">
      <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      ECOG lékaře a pacienta se liší o {diff} (varovný signál, OBC-1.3). Pacient: „{ecog.patient?.answer_text}“
    </p>
  );
}
