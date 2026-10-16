'use client';

import * as React from 'react';
import { CircleCheck, CircleQuestionMark, CircleX, ShieldAlert, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Brief, BriefSection, Criterion, EvidenceId, RedFlag, RoleAssessment, SectionId } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { CaseHeader } from './CaseHeader';
import { CitationProvider, Citations, collectCitations } from './citations';
import { ClaimList } from './ClaimList';
import { ROLE_META } from './roles';
import { SourceDrawer, type SourceLoader } from './SourceDrawer';

const TEXT_SECTION_TITLE: Partial<Record<SectionId, string>> = {
  summary: 'Souhrn případu',
  timeline: 'Časová osa',
  anamnesis: 'Anamnéza',
  modalities: 'Léčebné metody a odborníci',
};

/**
 * Podklad pro komisi v jednom sloupci (ARCH §7.1, §7.3): hlavička a bloky v pořadí podle
 * konfigurace předsedy. Klik na citaci otevře zdroj (`loadSource`: API nebo fixture).
 */
export function BriefView({ brief, loadSource }: { brief: Brief; loadSource: SourceLoader }) {
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const order = React.useMemo(() => collectCitations(brief), [brief]);
  const close = React.useCallback(() => setOpenId(null), []);
  const hideUnverified = brief.config.hide_unverified;

  const blocks = [...brief.config.sections]
    .filter((s) => s.enabled)
    .sort((a, b) => a.order - b.order)
    .map((s) => s.id);

  const renderBlock = (id: SectionId) => {
    switch (id) {
      case 'role_views':
        return brief.sections
          .filter((s) => s.id === 'role_views')
          .map((s) => <RoleSection key={`role-${s.role}`} section={s} hideUnverified={hideUnverified} />);
      case 'red_flags':
        return <RedFlagList key={id} flags={brief.red_flags} />;
      case 'mdt_question':
        return (
          <section key={id} className="rounded-xl border border-border bg-card p-4">
            <h2 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Otázka pro MDT</h2>
            <p className="mt-1 text-lg font-semibold leading-snug text-foreground">
              {brief.header.mdt_question.text}
              <Citations ids={[brief.header.mdt_question.citation]} />
            </p>
          </section>
        );
      default: {
        const sections = brief.sections.filter((s) => s.id === id);
        return sections.map((s) => (
          <AiBlock key={`${id}-${s.title}`} id={id} title={s.title || TEXT_SECTION_TITLE[id] || id} status={brief.status}>
            <ClaimList claims={s.items} hideUnverified={hideUnverified} />
          </AiBlock>
        ));
      }
    }
  };

  return (
    <CitationProvider order={order} activeId={openId} onOpen={setOpenId}>
      <div className="space-y-4">
        <CaseHeader header={brief.header} redFlagCount={brief.red_flags.length} />
        {blocks.map(renderBlock)}
        <p className="text-center text-[11px] text-muted-foreground">
          Podklad připravila AI ({brief.model}). Rozhoduje lékař, oficiálním záznamem se stane až po potvrzení.
          {' '}Tvrzení: {brief.stats.claims_total}, neověřených: {brief.stats.claims_unverified}, chybějících údajů:{' '}
          {brief.stats.missing_total}.
        </p>
      </div>
      <SourceDrawer evidenceId={openId} loadSource={loadSource} onClose={close} />
    </CitationProvider>
  );
}

function RoleBadge({ role }: { role: NonNullable<BriefSection['role']> }) {
  const meta = ROLE_META[role];
  return (
    <span className={cn('inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold', meta.className)}>
      {meta.label}
    </span>
  );
}

function RoleSection({ section, hideUnverified }: { section: BriefSection; hideUnverified: boolean }) {
  return (
    <AiBlock id={`role-${section.role}`} title={section.title} label={section.role && <RoleBadge role={section.role} />}>
      <ClaimList claims={section.items} hideUnverified={hideUnverified} />
      {section.assessment && <AssessmentSummary assessment={section.assessment} />}
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

/** Posouzení role (FR-B7): podklad pro diskusi po kritériích s citacemi, rozhoduje lékař. */
function AssessmentSummary({ assessment }: { assessment: RoleAssessment }) {
  return (
    <div className="mt-3 rounded-lg border border-border bg-background p-3">
      <p className="text-sm font-semibold text-foreground">
        {assessment.question} <span className="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs">{VERDICT_LABEL[assessment.verdict]}</span>
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

const SEVERITY = {
  high: { label: 'vysoká závažnost', className: 'border-l-red-500' },
  moderate: { label: 'střední závažnost', className: 'border-l-orange-500' },
  low: { label: 'nízká závažnost', className: 'border-l-slate-400' },
} as const;

/** Varovné signály (FR-R2): závažnost, popis, oba zdroje a pasáž guidelines. */
function RedFlagList({ flags }: { flags: RedFlag[] }) {
  return (
    <section id="red-flags" className="scroll-mt-24 rounded-xl border border-border bg-card p-4">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
        <ShieldAlert className="h-4 w-4 text-destructive" aria-hidden /> Varovné signály ({flags.length})
      </h2>
      {flags.length === 0 ? (
        <p className="mt-2 text-sm text-muted-foreground">Pravidla nenašla žádný varovný signál.</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {flags.map((f) => (
            <li key={f.id} className={cn('rounded-lg border border-border border-l-4 bg-background px-3 py-2', SEVERITY[f.severity].className)}>
              <p className="text-sm font-semibold text-foreground">
                {f.title}
                {f.rule === 'RF-LLM' && (
                  <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-purple-500/15 px-1.5 py-0.5 align-middle text-[10px] font-semibold text-purple-700 dark:text-purple-300">
                    <Sparkles className="h-3 w-3" aria-hidden /> AI návrh
                  </span>
                )}
              </p>
              <p className="text-[11px] text-muted-foreground">
                {SEVERITY[f.severity].label} · {f.rule}
              </p>
              <p className="mt-1 text-sm text-foreground">
                {f.description}
                <Citations ids={[...f.citations, ...(f.guideline ? [f.guideline] : [])]} />
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
