import { CircleCheck, CircleQuestionMark, CircleX, FlaskConical } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Criterion, TrialScreening as Trial } from '@/types/mdt';
import { Citations } from './citations';

const OVERALL: Record<Trial['overall'], string> = {
  eligible: 'splňuje kritéria',
  potentially_eligible: 'potenciálně vhodný (chybí údaje)',
  not_eligible: 'nesplňuje kritéria',
};

/** Screening klinických studií RKT po kritériích s citací faktu pacienta (FR-D2). */
export function TrialScreening({ trials }: { trials: Trial[] }) {
  if (!trials.length) return <p className="text-sm text-muted-foreground">Žádná studie neodpovídá diagnóze.</p>;
  return (
    <ul className="space-y-3">
      {trials.map((t) => (
        <li key={t.study_id} className="rounded-lg border border-border bg-background p-3">
          <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-foreground">
            <FlaskConical className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
            <span className="font-mono">{t.study_id}</span>
            <span className="min-w-0 flex-1 font-normal">{t.title}</span>
          </p>
          <p
            className={cn(
              'mt-1 inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold',
              t.overall === 'not_eligible' ? 'border-border text-muted-foreground' : 'border-foreground/30 text-foreground',
            )}
          >
            {OVERALL[t.overall]}
          </p>
          <CriteriaGroup title="Kritéria zařazení" criteria={t.criteria.filter((c) => c.kind !== 'exclusion')} />
          <CriteriaGroup title="Kritéria vyřazení" criteria={t.criteria.filter((c) => c.kind === 'exclusion')} exclusion />
        </li>
      ))}
    </ul>
  );
}

function CriteriaGroup({ title, criteria, exclusion = false }: { title: string; criteria: Criterion[]; exclusion?: boolean }) {
  if (!criteria.length) return null;
  return (
    <div className="mt-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      <ul className="mt-1 space-y-1">
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
          criterion.status === 'unknown' ? 'text-muted-foreground' : good ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400',
        )}
        aria-hidden
      />
      <div className="min-w-0">
        <p className="text-foreground">
          {criterion.criterion_id && (
            <span className="mr-1 font-mono text-xs text-muted-foreground">{criterion.criterion_id.split('/')[1]}</span>
          )}
          {criterion.text}
          <Citations ids={[...(criterion.criterion_id ? [criterion.criterion_id] : []), ...criterion.citations]} />
        </p>
        <p className="text-[11px] text-muted-foreground">
          {label}
          {criterion.missing && <> · chybí: {criterion.missing}</>}
        </p>
      </div>
    </li>
  );
}
