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
 * Rozdíl ≥ 1 je varovný signál (OBC-1.3): výrazný jantarový/oranžový stav a text, ne jen barva.
 */
export function EcogTiles({ ecog }: { ecog: Ecog }) {
  const diff = ecogDifference(ecog);
  const warn = (diff ?? 0) >= 1;
  return (
    <>
      <div className="flex flex-col justify-between rounded-lg border border-border bg-background px-3 py-2.5 text-center shadow-2xs">
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">ECOG lékař</p>
        {ecog.physician ? (
          <>
            <p className="my-0.5 font-mono text-3xl font-extrabold leading-none tabular-nums text-foreground sm:text-4xl">
              {ecog.physician.value}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {formatDate(ecog.physician.date)}
              <Citations ids={[ecog.physician.citation]} />
            </p>
          </>
        ) : (
          <p className="py-2 text-xs font-medium text-muted-foreground">Údaj chybí</p>
        )}
      </div>
      <div
        className={cn(
          'flex flex-col justify-between rounded-lg border px-3 py-2.5 text-center shadow-2xs',
          warn
            ? 'border-amber-600/70 bg-amber-50/90 dark:border-amber-500/60 dark:bg-amber-950/60'
            : 'border-border bg-background',
        )}
      >
        <p className="flex items-center justify-center gap-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
          <span>ECOG pacient</span>
          {warn && (
            <span className="inline-flex items-center rounded-xs bg-amber-600 px-1 py-0.2 text-[9px] font-extrabold text-white dark:bg-amber-500 dark:text-amber-950">
              ! Δ{diff}
            </span>
          )}
        </p>
        {ecog.patient ? (
          <>
            <p
              className={cn(
                'my-0.5 font-mono text-3xl font-extrabold leading-none tabular-nums sm:text-4xl',
                warn ? 'text-amber-900 dark:text-amber-200' : 'text-foreground',
              )}
            >
              {ecog.patient.value}
            </p>
            <p className="text-[11px] text-muted-foreground">
              {formatDate(ecog.patient.date)}
              <Citations ids={[ecog.patient.citation]} />
            </p>
          </>
        ) : (
          <p className="py-2 text-xs font-medium text-muted-foreground">Údaj chybí</p>
        )}
      </div>
    </>
  );
}

export function EcogDifference({ ecog }: { ecog: Ecog }) {
  const diff = ecogDifference(ecog);
  if (diff === null || diff < 1) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg border border-amber-600/50 bg-amber-50/90 px-3 py-2 text-xs text-amber-950 dark:border-amber-500/40 dark:bg-amber-950/50 dark:text-amber-200">
      <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden />
      <p className="leading-snug">
        <span className="font-bold">Varovný signál (OBC-1.3):</span> ECOG lékaře ({ecog.physician?.value}) a pacienta (
        {ecog.patient?.value}) se liší o {diff}.{' '}
        {ecog.patient?.answer_text && (
          <span className="font-medium">Pacient uvádí: „{ecog.patient.answer_text}“</span>
        )}
      </p>
    </div>
  );
}

