'use client';

import * as React from 'react';
import { CalendarClock, ChevronsDownUp, ChevronsUpDown, ShieldAlert, Type } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useApiData } from '@/lib/use-api-data';
import type { Brief, EvidenceId, SectionId } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { CaseHeader } from './CaseHeader';
import { CitationProvider, Citations, collectCitations } from './citations';
import { ClaimList } from './ClaimList';
import { BriefDataProvider, type BriefDataSource } from './data-source';
import { RedFlagCard } from './RedFlagCard';
import { RoleSection } from './RoleSection';
import { SourceDrawer } from './SourceDrawer';
import { Timeline } from './Timeline';
import { TreatmentOptions } from './TreatmentOptions';
import { TrialScreening } from './TrialScreening';

const TEXT_SECTION_TITLE: Partial<Record<SectionId, string>> = {
  summary: 'Souhrn případu (30 s)',
  timeline: 'Časová osa',
  anamnesis: 'Anamnéza',
  modalities: 'Léčebné metody a odborníci',
};

const NAV_LABELS: Partial<Record<SectionId, string>> = {
  summary: 'Souhrn',
  timeline: 'Časová osa',
  red_flags: 'Varovné signály',
  anamnesis: 'Anamnéza',
  role_views: 'Odbornosti',
  decision_support: 'Možnosti léčby',
  trials: 'Studie',
  questions: 'Otázky',
  mdt_question: 'Otázka MDT',
};

/**
 * Podklad pro komisi v jednom sloupci (ARCH §7.1, §7.3): hlavička a bloky v pořadí podle
 * konfigurace předsedy. Klik na citaci otevře zdroj; data bere z `dataSource` (API nebo fixtures).
 */
export function BriefView({ brief, dataSource }: { brief: Brief; dataSource: BriefDataSource }) {
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const [allExpanded, setAllExpanded] = React.useState(true);
  const [comfortLarge, setComfortLarge] = React.useState(false);

  const timeline = useApiData(dataSource.loadTimeline, brief.patient_id);
  const series = useApiData(dataSource.loadObservations, brief.patient_id);
  const order = React.useMemo(
    () => collectCitations([brief, timeline.data ?? [], series.data ?? []]),
    [brief, timeline.data, series.data],
  );
  const close = React.useCallback(() => setOpenId(null), []);
  const hideUnverified = brief.config.hide_unverified;
  const ds = brief.decision_support;

  const blocks = [...brief.config.sections]
    .filter((s) => s.enabled)
    .sort((a, b) => a.order - b.order)
    .map((s) => s.id);

  const firstRole = brief.sections.find((s) => s.id === 'role_views')?.role;

  const textSection = (id: SectionId) =>
    brief.sections
      .filter((s) => s.id === id)
      .map((s) => (
        <AiBlock
          key={`${id}-${s.title}-${allExpanded}`}
          id={id}
          title={s.title || TEXT_SECTION_TITLE[id] || id}
          status={brief.status}
          defaultOpen={id === 'summary' ? true : allExpanded}
        >
          <ClaimList claims={s.items} hideUnverified={hideUnverified} />
        </AiBlock>
      ));

  const renderBlock = (id: SectionId): React.ReactNode => {
    switch (id) {
      case 'timeline':
        return (
          <React.Fragment key={id}>
            {textSection(id)}
            {timeline.data && timeline.data.length > 0 && (
              <section id="timeline-events" className="scroll-mt-28 rounded-xl border border-border bg-card p-4 shadow-2xs">
                <h2 className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-border/70 pb-2.5 text-base font-bold text-foreground">
                  <span className="flex items-center gap-2">
                    <CalendarClock className="h-4 w-4 text-primary" aria-hidden /> Události z dokumentace
                  </span>
                  <span className="rounded-md border border-border bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
                    Přímá data z IRIS (mimo AI)
                  </span>
                </h2>
                <Timeline events={timeline.data} />
              </section>
            )}
          </React.Fragment>
        );
      case 'role_views':
        return (
          <div key={id} id="role_views" className="scroll-mt-28 space-y-3.5">
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
          <section key={id} id="red-flags" className="scroll-mt-28 rounded-xl border border-border bg-card p-4 shadow-2xs">
            <h2 className="flex items-center justify-between gap-2 border-b border-border/70 pb-2.5 text-base font-bold text-foreground">
              <span className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-destructive" aria-hidden /> Varovné signály ({brief.red_flags.length})
              </span>
              <span className="rounded-md border border-border bg-muted px-2 py-0.5 text-[11px] font-semibold text-muted-foreground">
                Deterministická pravidla + kontrola rozporů
              </span>
            </h2>
            {brief.red_flags.length === 0 ? (
              <p className="mt-3 text-sm text-muted-foreground">Pravidla nenašla žádný varovný signál.</p>
            ) : (
              <ul className="mt-3 space-y-2.5">
                {brief.red_flags.map((f) => (
                  <RedFlagCard key={f.id} flag={f} />
                ))}
              </ul>
            )}
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
            <ol className="list-decimal space-y-2 pl-5 text-sm font-medium leading-relaxed text-foreground">
              {ds.discussion_questions.map((q) => (
                <li key={q.text}>
                  {q.text}
                  <Citations ids={q.citations} />
                </li>
              ))}
            </ol>
            <p className="mt-3 border-t border-border/60 pt-2 text-xs text-muted-foreground">{ds.disclaimer}</p>
          </AiBlock>
        ) : null;
      case 'mdt_question':
        return (
          <section key={id} id="mdt_question" className="scroll-mt-28 rounded-xl border-2 border-primary/40 bg-card p-4 shadow-2xs">
            <h2 className="text-[11px] font-bold uppercase tracking-wider text-primary">Otázka pro rozhodnutí MDT</h2>
            <p className="mt-1.5 text-lg font-extrabold leading-snug text-foreground sm:text-xl">
              {brief.header.mdt_question.text}
              <Citations ids={[brief.header.mdt_question.citation]} />
            </p>
          </section>
        );
      default:
        return <React.Fragment key={id}>{textSection(id)}</React.Fragment>;
    }
  };

  return (
    <BriefDataProvider value={dataSource}>
      <CitationProvider order={order} activeId={openId} onOpen={setOpenId}>
        <div className={cn('space-y-4', comfortLarge && 'text-[106%] [&_p]:leading-relaxed')}>
          {/* 30-Second Patient Orientation Header */}
          <CaseHeader header={brief.header} redFlagCount={brief.red_flags.length} />

          {/* Sticky Quick-Jump & Reading Comfort Bar */}
          <nav
            aria-label="Rychlá navigace podkladem"
            className="sticky top-2 z-20 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-border bg-card/95 px-3 py-2 shadow-sm backdrop-blur-md"
          >
            <div className="flex flex-wrap items-center gap-1">
              {blocks.map((id) => {
                const label = NAV_LABELS[id];
                if (!label) return null;
                const href = id === 'red_flags' ? '#red-flags' : id === 'role_views' && firstRole ? `#role-${firstRole}` : `#${id}`;
                return (
                  <a
                    key={id}
                    href={href}
                    className={cn(
                      'inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold transition-colors',
                      id === 'red_flags' && brief.red_flags.length > 0
                        ? 'bg-red-50 text-red-900 hover:bg-red-100 dark:bg-red-950/70 dark:text-red-200'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                    )}
                  >
                    {label}
                    {id === 'red_flags' && brief.red_flags.length > 0 && (
                      <span className="rounded-xs bg-red-600 px-1 py-0.2 font-mono text-[10px] font-bold text-white dark:bg-red-500 dark:text-red-950">
                        {brief.red_flags.length}
                      </span>
                    )}
                  </a>
                );
              })}
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={() => setComfortLarge(!comfortLarge)}
                aria-pressed={comfortLarge}
                title="Zvětšit písmo pro projektor nebo pohodlnější čtení"
                className={cn(
                  'inline-flex h-7 items-center gap-1 rounded-md border px-2 text-xs font-semibold transition-colors',
                  comfortLarge
                    ? 'border-primary bg-primary text-primary-foreground'
                    : 'border-border bg-background text-foreground hover:bg-accent',
                )}
              >
                <Type className="h-3.5 w-3.5" aria-hidden />
                <span>A+</span>
              </button>
              <button
                type="button"
                onClick={() => setAllExpanded(!allExpanded)}
                title={allExpanded ? 'Sbalit podrobné sekce (ponechat 30s přehled)' : 'Rozbalit všechny sekce'}
                className="inline-flex h-7 items-center gap-1 rounded-md border border-border bg-background px-2 text-xs font-semibold text-foreground transition-colors hover:bg-accent"
              >
                {allExpanded ? (
                  <>
                    <ChevronsDownUp className="h-3.5 w-3.5" aria-hidden />
                    <span className="hidden sm:inline">Jen 30s přehled</span>
                  </>
                ) : (
                  <>
                    <ChevronsUpDown className="h-3.5 w-3.5" aria-hidden />
                    <span className="hidden sm:inline">Rozbalit vše</span>
                  </>
                )}
              </button>
            </div>
          </nav>

          {blocks.map(renderBlock)}

          {!ds && blocks.includes('decision_support') && (
            <p className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
              Možnosti léčby, studie a otázky k diskusi v tomto podkladu zatím nejsou.
            </p>
          )}

          <footer className="rounded-xl border border-border bg-card px-4 py-3 text-center text-xs text-muted-foreground">
            Podklad připravila AI (<span className="font-mono font-semibold text-foreground">{brief.model}</span>). Rozhoduje
            lékař, oficiálním záznamem se stane až po potvrzení. Tvrzení celkem:{' '}
            <strong className="text-foreground">{brief.stats.claims_total}</strong> · neověřených:{' '}
            <strong className="text-foreground">{brief.stats.claims_unverified}</strong> · chybějících údajů:{' '}
            <strong className="text-foreground">{brief.stats.missing_total}</strong>.
          </footer>
        </div>
        <SourceDrawer evidenceId={openId} loadSource={dataSource.loadSource} onClose={close} />
      </CitationProvider>
    </BriefDataProvider>
  );
}

