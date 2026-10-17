import { CircleCheck, CircleHelp, CircleX } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefSection, Criterion, ObservationSeries, RoleAssessment, RoleId } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { Citations } from './citations';
import { ClaimList } from './ClaimList';
import { ROLE_META } from './roles';
import { seriesForRole, TrendChart, withReadableLabel } from './TrendChart';

export function RoleBadge({ role }: { role: RoleId }) {
  const meta = ROLE_META[role];
  return <span className={cn('inline-flex shrink-0 items-center rounded-md border px-1.5 py-0.5 text-xs font-medium', meta.className)}>{meta.label}</span>;
}

/**
 * Sekce odbornosti (FR-B1–B6, D-017): údaje pro jednu roli se štítkem a barvou odbornosti,
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
      label={section.role && section.role !== 'patient' && <RoleBadge role={section.role} />}
      status={status}
      defaultOpen={defaultOpen}
      headingLevel="h3"
    >
      <ClaimList claims={section.items} hideUnverified={hideUnverified} />
      {trends.length > 0 && (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
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
  candidate: { label: 'kandidát', className: 'text-emerald-800 dark:text-emerald-300' },
  conditional: { label: 'podmíněně', className: 'text-amber-800 dark:text-amber-300' },
  not_candidate: { label: 'není kandidát', className: 'text-red-800 dark:text-red-300' },
  insufficient_data: { label: 'nedostatek údajů', className: 'text-slate-700 dark:text-slate-300' },
};

const CRITERION_STATUS = {
  met: { label: 'splněno', icon: CircleCheck, className: 'text-emerald-700 dark:text-emerald-400' },
  not_met: { label: 'nesplněno', icon: CircleX, className: 'text-red-700 dark:text-red-400' },
  unknown: { label: 'neznámé', icon: CircleHelp, className: 'text-amber-700 dark:text-amber-400' },
} as const;

/** Posouzení role (FR-B7): předběžný verdikt po kritériích s citacemi; podklad, rozhoduje lékař dané role. */
export function RoleAssessmentCard({ assessment }: { assessment: RoleAssessment }) {
  const verdict = VERDICT_META[assessment.verdict];
  return (
    <div className="mt-4 rounded-lg bg-muted/60 p-3.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <p className="text-sm font-semibold">{assessment.question}</p>
        <p className="text-[13px]">
          Předběžně: <span className={cn('font-semibold', verdict.className)}>{verdict.label}</span>
        </p>
      </div>
      <ul className="mt-2.5 flex flex-col gap-2">
        {assessment.criteria.map((c) => (
          <CriterionRow key={c.text} criterion={c} />
        ))}
      </ul>
      <p className="mt-2.5 text-xs text-muted-foreground">{assessment.note}</p>
    </div>
  );
}

function CriterionRow({ criterion }: { criterion: Criterion }) {
  const status = CRITERION_STATUS[criterion.status];
  const Icon = status.icon;
  return (
    <li className="flex gap-2 text-sm">
      <Icon className={cn('mt-0.5 size-4 shrink-0', status.className)} strokeWidth={2.25} aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="leading-snug">
          <span className="sr-only">{status.label}: </span>
          {criterion.text}
          <Citations ids={[...criterion.citations, ...(criterion.guideline ? [criterion.guideline] : [])]} />
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {status.label}
          {criterion.missing && <> · chybí: <span className="text-foreground">{criterion.missing}</span></>}
        </p>
      </div>
    </li>
  );
}
