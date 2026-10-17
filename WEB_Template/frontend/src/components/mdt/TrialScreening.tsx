import { CircleCheck, CircleHelp, CircleX } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Criterion, TrialScreening as Trial } from '@/types/mdt';
import { Citations } from './citations';

const OVERALL: Record<Trial['overall'], { label: string; className: string }> = {
  eligible: { label: 'splňuje kritéria', className: 'text-emerald-800 dark:text-emerald-300' },
  potentially_eligible: { label: 'potenciálně vhodný, chybí údaje', className: 'text-amber-800 dark:text-amber-300' },
  not_eligible: { label: 'nesplňuje kritéria', className: 'text-muted-foreground' },
};

/** Screening klinických studií RKT po kritériích s citací faktu pacienta (FR-D2). */
export function TrialScreening({ trials }: { trials: Trial[] }) {
  if (!trials.length) return <p className="text-sm text-muted-foreground">Žádná studie neodpovídá diagnóze.</p>;
  return (
    <ul className="flex flex-col divide-y divide-border">
      {trials.map((t) => (
        <li key={t.study_id} className="py-3 first:pt-0 last:pb-0">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
            <p className="text-sm font-semibold">
              <span translate="no" className="mr-1.5 text-muted-foreground">{t.study_id}</span>
              {t.title}
            </p>
            <p className={cn('text-[13px] font-medium', OVERALL[t.overall].className)}>{OVERALL[t.overall].label}</p>
          </div>
          <div className="mt-2 grid gap-x-6 gap-y-3 sm:grid-cols-2">
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
    <div>
      <p className="mb-1 text-xs font-medium text-muted-foreground">{title}</p>
      <ul className="flex flex-col gap-1.5">
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
  const Icon = criterion.status === 'unknown' ? CircleHelp : good ? CircleCheck : CircleX;
  return (
    <li className="flex gap-2 text-[13px]">
      <Icon
        className={cn(
          'mt-0.5 size-4 shrink-0',
          criterion.status === 'unknown' ? 'text-amber-700 dark:text-amber-400' : good ? 'text-emerald-700 dark:text-emerald-400' : 'text-red-700 dark:text-red-400',
        )}
        strokeWidth={2.25}
        aria-hidden
      />
      <div className="min-w-0">
        <p className="leading-snug">
          {criterion.criterion_id && <span translate="no" className="mr-1 text-muted-foreground">{criterion.criterion_id.split('/')[1]}</span>}
          {criterion.text}
          <Citations ids={[...(criterion.criterion_id ? [criterion.criterion_id] : []), ...criterion.citations]} />
        </p>
        <p className="text-xs text-muted-foreground">
          {label}
          {criterion.missing && <span className="text-amber-800 dark:text-amber-300"> · chybí: {criterion.missing}</span>}
        </p>
      </div>
    </li>
  );
}
