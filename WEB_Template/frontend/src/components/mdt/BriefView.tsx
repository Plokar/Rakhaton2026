'use client';

import * as React from 'react';
import { ChevronsDownUp, ChevronsUpDown, Type } from 'lucide-react';
import { Button } from '@/components/shadcn/button';
import { useQuery } from '@tanstack/react-query';
import { cn } from '@/lib/utils';
import type { Brief, EvidenceId, SectionId } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { CaseHeader } from './CaseHeader';
import { CitationProvider, Citations, collectCitations } from './citations';
import { SectionClaims } from './ClaimList';
import { FeedbackNote } from './GenerateBrief';
import { BriefDataProvider, type BriefDataSource } from './data-source';
import { RedFlagList } from './RedFlagList';
import { RoleSection } from './RoleSection';
import { SourceDrawer } from './SourceDrawer';
import { Timeline } from './Timeline';
import { TreatmentOptions } from './TreatmentOptions';
import { TrialScreening } from './TrialScreening';
import { VerifierPanel } from './VerifierPanel';

const TEXT_SECTION_TITLE: Partial<Record<SectionId, string>> = {
  summary: 'Souhrn případu',
  timeline: 'Časová osa',
  anamnesis: 'Anamnéza',
  modalities: 'Léčebné metody a odborníci',
};

const NAV_LABELS: Partial<Record<SectionId, string>> = {
  summary: 'Souhrn',
  timeline: 'Osa',
  red_flags: 'Varování',
  anamnesis: 'Anamnéza',
  role_views: 'Odbornosti',
  decision_support: 'Léčba',
  trials: 'Studie',
  questions: 'Otázky',
};

const anchor = (id: SectionId) => (id === 'red_flags' ? 'varovani' : id);

/**
 * Podklad pro komisi v jednom sloupci, úzké okno vedle PACS (ARCH §7.1, FR-U2): hlavička a bloky
 * v pořadí podle konfigurace předsedy. Klik na citaci otevře zdroj; data bere z `dataSource`.
 */
export function BriefView({ brief, dataSource }: { brief: Brief; dataSource: BriefDataSource }) {
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const [allExpanded, setAllExpanded] = React.useState(true);
  const [large, setLarge] = React.useState(false);

  const timeline = useQuery({ queryKey: ['patient', brief.patient_id, 'timeline'], queryFn: () => dataSource.loadTimeline(brief.patient_id) });
  const series = useQuery({ queryKey: ['patient', brief.patient_id, 'observations'], queryFn: () => dataSource.loadObservations(brief.patient_id) });
  const order = React.useMemo(
    () => collectCitations([brief, timeline.data ?? [], series.data ?? []]),
    [brief, timeline.data, series.data],
  );
  const close = React.useCallback(() => setOpenId(null), []);
  const hideUnverified = brief.config.hide_unverified;
  const ds = brief.decision_support;

  const blocks = [...brief.config.sections]
    .filter((s) => s.enabled && s.id !== 'mdt_question')
    .sort((a, b) => a.order - b.order)
    .map((s) => s.id);

  const textSection = (id: SectionId) =>
    brief.sections
      .filter((s) => s.id === id)
      .map((s) => (
        <AiBlock
          key={`${id}-${s.title}-${allExpanded}`}
          id={anchor(id)}
          title={s.title || TEXT_SECTION_TITLE[id] || id}
          status={brief.status}
          defaultOpen={id === 'summary' ? true : allExpanded}
        >
          <SectionClaims section={s} hideUnverified={hideUnverified} />
        </AiBlock>
      ));

  const renderBlock = (id: SectionId): React.ReactNode => {
    switch (id) {
      case 'timeline':
        return (
          <React.Fragment key={id}>
            {textSection(id)}
            {timeline.data && timeline.data.length > 0 && (
              <section aria-labelledby="osa-iris" className="scroll-mt-24">
                <h2 id="osa-iris" className="mb-1 text-[15px] font-semibold">Události z dokumentace</h2>
                <p className="mb-3 text-xs text-muted-foreground">Přímo z IRIS, bez AI.</p>
                <Timeline events={timeline.data} />
              </section>
            )}
          </React.Fragment>
        );
      case 'role_views':
        return (
          <div key={id} id="role_views" className="flex scroll-mt-24 flex-col gap-5">
            {brief.sections
              .filter((s) => s.id === 'role_views')
              .map((s) => (
                <RoleSection
                  key={`role-${s.role}-${allExpanded}`}
                  section={s}
                  series={series.data ?? []}
                  hideUnverified={hideUnverified}
                  status={brief.status}
                  defaultOpen={allExpanded}
                />
              ))}
          </div>
        );
      case 'red_flags':
        return (
          <section key={id} id="varovani" aria-labelledby="varovani-nadpis" className="scroll-mt-24">
            <h2 id="varovani-nadpis" className="mb-3 text-[15px] font-semibold">
              Varovné signály <span className="font-normal text-muted-foreground">({brief.red_flags.length})</span>
            </h2>
            <RedFlagList flags={brief.red_flags} />
          </section>
        );
      case 'decision_support':
        return ds ? (
          <AiBlock key={`${id}-${allExpanded}`} id={id} title="Možnosti léčby a soulad se stavem pacienta" status={brief.status} defaultOpen={allExpanded}>
            <TreatmentOptions options={ds.treatment_options} />
          </AiBlock>
        ) : null;
      case 'trials':
        return ds ? (
          <AiBlock key={`${id}-${allExpanded}`} id={id} title="Klinické studie (screening RKT)" status={brief.status} defaultOpen={allExpanded}>
            <TrialScreening trials={ds.trials} />
          </AiBlock>
        ) : null;
      case 'questions':
        return ds ? (
          <AiBlock key={`${id}-${allExpanded}`} id={id} title="Otázky k diskusi komise" status={brief.status} defaultOpen={allExpanded}>
            <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm leading-relaxed">
              {ds.discussion_questions.map((q) => (
                <li key={q.text}>
                  {q.text}
                  <Citations ids={q.citations} />
                </li>
              ))}
            </ol>
            <p className="mt-3 text-xs text-muted-foreground">{ds.disclaimer}</p>
          </AiBlock>
        ) : null;
      default:
        return <React.Fragment key={id}>{textSection(id)}</React.Fragment>;
    }
  };

  return (
    <BriefDataProvider value={dataSource}>
      <CitationProvider order={order} activeId={openId} onOpen={setOpenId}>
        <div className={cn('flex flex-col gap-6', large && 'text-[106%] [&_p]:leading-relaxed')}>
          <CaseHeader header={brief.header} redFlagCount={brief.red_flags.length} status={brief.status} />

          <nav
            aria-label="Sekce podkladu"
            className="sticky top-0 z-20 -mx-4 flex items-center gap-1 overflow-x-auto border-y border-border bg-background/95 px-4 py-1.5 backdrop-blur-none"
          >
            {blocks.map((id) =>
              NAV_LABELS[id] ? (
                <a
                  key={id}
                  href={`#${anchor(id)}`}
                  className="shrink-0 rounded-md px-2 py-1 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                >
                  {NAV_LABELS[id]}
                  {id === 'red_flags' && brief.red_flags.length > 0 && <span className="ml-1 tabular-nums">{brief.red_flags.length}</span>}
                </a>
              ) : null,
            )}
            <span className="ml-auto flex shrink-0 items-center gap-0.5">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setLarge(!large)}
                aria-pressed={large}
                aria-label="Větší písmo pro projektor"
                title="Větší písmo pro projektor"
              >
                <Type aria-hidden />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setAllExpanded(!allExpanded)}
                aria-label={allExpanded ? 'Sbalit podrobné sekce' : 'Rozbalit všechny sekce'}
                title={allExpanded ? 'Sbalit podrobné sekce' : 'Rozbalit všechny sekce'}
              >
                {allExpanded ? <ChevronsDownUp aria-hidden /> : <ChevronsUpDown aria-hidden />}
              </Button>
            </span>
          </nav>

          {blocks.map(renderBlock)}

          {!ds && blocks.includes('decision_support') && (
            <p className="text-sm text-muted-foreground">Možnosti léčby, studie a otázky k diskusi v tomto podkladu zatím nejsou.</p>
          )}

          <VerifierPanel verifier={brief.verifier} />

          {brief.feedback && <FeedbackNote feedback={brief.feedback} />}
          <p className="border-t border-border pt-4 text-xs text-muted-foreground">
            Podklad připravila AI ({brief.model}). Rozhoduje lékař, oficiálním záznamem se stane až po potvrzení. Tvrzení{' '}
            <span className="tabular-nums">{brief.stats.claims_total}</span>, neověřených <span className="tabular-nums">{brief.stats.claims_unverified}</span>,
            chybějících údajů <span className="tabular-nums">{brief.stats.missing_total}</span>.
          </p>
        </div>
        <SourceDrawer evidenceId={openId} loadSource={dataSource.loadSource} onClose={close} />
      </CitationProvider>
    </BriefDataProvider>
  );
}
