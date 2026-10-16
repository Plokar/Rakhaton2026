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
    <span className={cn('inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold', meta.className)}>
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
}: {
  section: BriefSection;
  series: ObservationSeries[];
  hideUnverified: boolean;
  status: 'draft' | 'confirmed';
}) {
  const trends = section.role ? seriesForRole(section.role, series).map(withReadableLabel) : [];
  return (
    <AiBlock
      id={`role-${section.role}`}
      title={section.title}
      label={section.role && <RoleBadge role={section.role} />}
      status={status}
    >
      <ClaimList claims={section.items} hideUnverified={hideUnverified} />
      {trends.length > 0 && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {trends.map((s) => (
            <TrendChart key={s.code} series={s} />
          ))}
        </div>
      )}
      {section.assessment && <RoleAssessmentCard assessment={section.assessment} />}
    </AiBlock>
  );
}

const VERDICT_LABEL: Record<RoleAssessment['verdict'], string> = {
  candidate: 'Kandidát',
  conditional: 'Podmíněně',
  not_candidate: 'Není kandidát',
  insufficient_data: 'Nedostatek údajů',
};

const CRITERION_STATUS = {
  met: { label: 'splněno', icon: CircleCheck, className: 'text-emerald-600 dark:text-emerald-400' },
  not_met: { label: 'nesplněno', icon: CircleX, className: 'text-red-600 dark:text-red-400' },
  unknown: { label: 'neznámé', icon: CircleQuestionMark, className: 'text-muted-foreground' },
} as const;

/** Posouzení role (FR-B7): předběžný verdikt po kritériích s citacemi; podklad, rozhoduje lékař dané role. */
export function RoleAssessmentCard({ assessment }: { assessment: RoleAssessment }) {
  return (
    <div className="mt-3 rounded-lg border border-border bg-background p-3">
      <p className="text-sm font-semibold text-foreground">
        {assessment.question}{' '}
        <span className="ml-1 whitespace-nowrap rounded bg-muted px-1.5 py-0.5 text-xs">{VERDICT_LABEL[assessment.verdict]}</span>
      </p>
      <ul className="mt-2 space-y-1.5">
        {assessment.criteria.map((c) => (
          <CriterionRow key={c.text} criterion={c} />
        ))}
      </ul>
      <p className="mt-2 text-[11px] text-muted-foreground">{assessment.note}</p>
    </div>
  );
}

function CriterionRow({ criterion }: { criterion: Criterion }) {
  const status = CRITERION_STATUS[criterion.status];
  const Icon = status.icon;
  return (
    <li className="flex gap-2 text-sm">
      <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', status.className)} aria-hidden />
      <div className="min-w-0">
        <p>
          <span className="sr-only">{status.label}: </span>
          {criterion.text}
          <Citations ids={[...criterion.citations, ...(criterion.guideline ? [criterion.guideline] : [])]} />
        </p>
        <p className="text-[11px] text-muted-foreground">
          {status.label}
          {criterion.missing && <> · chybí: {criterion.missing}</>}
        </p>
      </div>
    </li>
  );
}
