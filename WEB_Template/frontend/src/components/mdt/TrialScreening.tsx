import { CircleCheck, CircleQuestionMark, CircleX, FlaskConical } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Criterion, TrialScreening as Trial } from '@/types/mdt';
import { Citations } from './citations';

const OVERALL: Record<Trial['overall'], string> = {
  eligible: 'splňuje kritéria',
  potentially_eligible: 'potenciálně vhodný (chybí údaje)',
  not_eligible: 'nesplňuje kritéria',
};

const OVERALL_STYLE: Record<Trial['overall'], string> = {
  eligible: 'border-emerald-700/45 bg-emerald-500/15 text-emerald-950 dark:border-emerald-400/50 dark:bg-emerald-500/20 dark:text-emerald-100',
  potentially_eligible: 'border-amber-600/50 bg-amber-500/15 text-amber-950 dark:border-amber-400/50 dark:bg-amber-500/20 dark:text-amber-100',
  not_eligible: 'border-slate-400/60 bg-slate-500/10 text-slate-700 dark:border-slate-500/50 dark:text-slate-300',
};

/** Screening klinických studií RKT po kritériích s citací faktu pacienta (FR-D2). */
export function TrialScreening({ trials }: { trials: Trial[] }) {
  if (!trials.length) return <p className="text-sm text-muted-foreground">Žádná studie neodpovídá diagnóze.</p>;
  return (
    <ul className="space-y-3">
      {trials.map((t) => (
        <li key={t.study_id} className="rounded-xl border border-border bg-background p-4 shadow-2xs">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="flex min-w-0 flex-1 flex-wrap items-center gap-2 text-sm font-bold text-foreground">
              <FlaskConical className="h-4 w-4 shrink-0 text-primary" aria-hidden />
              <span className="rounded border border-primary/25 bg-primary/10 px-1.5 py-0.5 font-mono text-xs font-bold text-primary">
                {t.study_id}
              </span>
              <span className="min-w-0 flex-1">{t.title}</span>
            </p>
            <span
              className={cn(
                'inline-flex shrink-0 rounded-md border px-2.5 py-0.5 text-xs font-bold',
                OVERALL_STYLE[t.overall],
              )}
            >
              {OVERALL[t.overall]}
            </span>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <CriteriaGroup title="Kritéria zařazení" criteria={t.criteria.filter((c) => c.kind !== 'exclusion')} />
            <CriteriaGroup title="Kritéria vyřazení" criteria={t.criteria.filter((c) => c.kind === 'exclusion')} exclusion />
          </div>
        </li>
      ))}
    </ul>
  );
}

function CriteriaGroup({ title, criteria, exclusion = false }: { title: string; criteria: Criterion[]; exclusion?: boolean }) {
  if (!criteria.length) return null;
  return (
    <div className="rounded-lg border border-border/80 bg-card/60 p-2.5">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{title}</p>
      <ul className="mt-1.5 space-y-1.5">
        {criteria.map((c) => (
          <CriterionLine key={c.criterion_id ?? c.text} criterion={c} exclusion={exclusion} />
        ))}
      </ul>
    </div>
  );
}

function CriterionLine({ criterion, exclusion }: { criterion: Criterion; exclusion: boolean }) {
  // U vylučujícího kritéria „met“ = vylučující okolnost platí (pacient je vyřazen), ARCH §8.1.
  const good = exclusion ? criterion.status === 'not_met' : criterion.status === 'met';
  const label =
    criterion.status === 'unknown'
      ? 'neznámé'
      : exclusion
        ? criterion.status === 'met'
          ? 'platí, vyřazuje'
          : 'neplatí'
        : criterion.status === 'met'
          ? 'splněno'
          : 'nesplněno';
  const Icon = criterion.status === 'unknown' ? CircleQuestionMark : good ? CircleCheck : CircleX;
  return (
    <li className="flex gap-2 text-sm">
      <Icon
        className={cn(
          'mt-0.5 h-4 w-4 shrink-0',
          criterion.status === 'unknown'
            ? 'text-amber-600 dark:text-amber-400'
            : good
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-red-600 dark:text-red-400',
        )}
        aria-hidden
      />
      <div className="min-w-0">
        <p className="leading-snug text-foreground">
          {criterion.criterion_id && (
            <span className="mr-1.5 rounded bg-muted px-1 py-0.5 font-mono text-[11px] font-bold text-muted-foreground">
              {criterion.criterion_id.split('/')[1]}
            </span>
          )}
          {criterion.text}
          <Citations ids={[...(criterion.criterion_id ? [criterion.criterion_id] : []), ...criterion.citations]} />
        </p>
        <p className="mt-0.5 text-[11px] font-medium text-muted-foreground">
          {label}
          {criterion.missing && <span className="font-semibold text-amber-800 dark:text-amber-300"> · chybí: {criterion.missing}</span>}
        </p>
      </div>
    </li>
  );
}
