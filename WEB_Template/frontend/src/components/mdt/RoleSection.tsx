import { CircleCheck, CircleQuestionMark, CircleX } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefSection, Criterion, ObservationSeries, RoleAssessment, RoleId } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { Citations } from './citations';
import { ClaimList } from './ClaimList';
import { ROLE_META } from './roles';
import { seriesForRole, TrendChart, withReadableLabel } from './TrendChart';

export function RoleBadge({ role }: { role: RoleId }) {
  const meta = ROLE_META[role];
  return (
    <span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-bold', meta.className)}>
      {meta.label}
    </span>
  );
}

/**
 * Sekce odbornosti (FR-B1–B6, D-017): údaje pro jednu roli pod sebou se štítkem a barvou odbornosti,
 * posouzení role (FR-B7) a trendy, které daná role potřebuje (markery onkologovi, PROMs pacientovi).
 */
export function RoleSection({
  section,
  series,
  hideUnverified,
  status,
  defaultOpen = true,
}: {
  section: BriefSection;
  series: ObservationSeries[];
  hideUnverified: boolean;
  status: 'draft' | 'confirmed';
  defaultOpen?: boolean;
}) {
  const trends = section.role ? seriesForRole(section.role, series).map(withReadableLabel) : [];
  return (
    <AiBlock
      id={`role-${section.role}`}
      title={section.title}
      label={section.role && <RoleBadge role={section.role} />}
      status={status}
      defaultOpen={defaultOpen}
    >
      <ClaimList claims={section.items} hideUnverified={hideUnverified} />
      {trends.length > 0 && (
        <div className="mt-3.5 grid gap-2.5 sm:grid-cols-2">
          {trends.map((s) => (
            <TrendChart key={s.code} series={s} />
          ))}
        </div>
      )}
      {section.assessment && <RoleAssessmentCard assessment={section.assessment} />}
    </AiBlock>
  );
}

const VERDICT_META: Record<RoleAssessment['verdict'], { label: string; className: string }> = {
  candidate: {
    label: 'Kandidát',
    className: 'border-emerald-600/50 bg-emerald-50 text-emerald-900 dark:border-emerald-500/50 dark:bg-emerald-950/70 dark:text-emerald-200',
  },
  conditional: {
    label: 'Podmíněně',
    className: 'border-amber-600/60 bg-amber-50 text-amber-950 dark:border-amber-500/50 dark:bg-amber-950/70 dark:text-amber-200',
  },
  not_candidate: {
    label: 'Není kandidát',
    className: 'border-red-600/60 bg-red-50 text-red-950 dark:border-red-500/50 dark:bg-red-950/70 dark:text-red-200',
  },
  insufficient_data: {
    label: 'Nedostatek údajů',
    className: 'border-slate-400/70 bg-slate-100 text-slate-800 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200',
  },
};

const CRITERION_STATUS = {
  met: { label: 'splněno', icon: CircleCheck, className: 'text-emerald-700 dark:text-emerald-400' },
  not_met: { label: 'nesplněno', icon: CircleX, className: 'text-red-700 dark:text-red-400' },
  unknown: { label: 'neznámé', icon: CircleQuestionMark, className: 'text-amber-700 dark:text-amber-400' },
} as const;

/** Posouzení role (FR-B7): předběžný verdikt po kritériích s citacemi; podklad, rozhoduje lékař dané role. */
export function RoleAssessmentCard({ assessment }: { assessment: RoleAssessment }) {
  const verdict = VERDICT_META[assessment.verdict];
  return (
    <div className="mt-3.5 rounded-lg border border-border bg-muted/30 p-3.5">
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-border/70 pb-2.5">
        <p className="text-sm font-bold text-foreground">{assessment.question}</p>
        <span className={cn('inline-flex shrink-0 items-center rounded-md border px-2 py-0.5 text-xs font-bold', verdict.className)}>
          Předběžně: {verdict.label}
        </span>
      </div>
      <ul className="mt-2.5 space-y-2">
        {assessment.criteria.map((c) => (
          <CriterionRow key={c.text} criterion={c} />
        ))}
      </ul>
      <p className="mt-2.5 text-[11px] font-medium text-muted-foreground">{assessment.note}</p>
    </div>
  );
}

function CriterionRow({ criterion }: { criterion: Criterion }) {
  const status = CRITERION_STATUS[criterion.status];
  const Icon = status.icon;
  return (
    <li className="flex gap-2.5 text-sm">
      <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', status.className)} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="leading-snug text-foreground">
          <span className="sr-only">{status.label}: </span>
          {criterion.text}
          <Citations ids={[...criterion.citations, ...(criterion.guideline ? [criterion.guideline] : [])]} />
        </p>
        <p className="mt-0.5 text-xs font-medium text-muted-foreground">
          <span className={cn('font-semibold', status.className)}>{status.label}</span>
          {criterion.missing && <> · <span className="text-foreground">chybí: {criterion.missing}</span></>}
        </p>
      </div>
    </li>
  );
}

