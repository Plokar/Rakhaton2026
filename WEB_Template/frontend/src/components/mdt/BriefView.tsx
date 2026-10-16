'use client';

import * as React from 'react';
import { CalendarClock, ShieldAlert } from 'lucide-react';
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
  summary: 'Souhrn případu',
  timeline: 'Časová osa',
  anamnesis: 'Anamnéza',
  modalities: 'Léčebné metody a odborníci',
};

/**
 * Podklad pro komisi v jednom sloupci (ARCH §7.1, §7.3): hlavička a bloky v pořadí podle
 * konfigurace předsedy. Klik na citaci otevře zdroj; data bere z `dataSource` (API nebo fixtures).
 */
export function BriefView({ brief, dataSource }: { brief: Brief; dataSource: BriefDataSource }) {
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
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

  const textSection = (id: SectionId) =>
    brief.sections
      .filter((s) => s.id === id)
      .map((s) => (
        <AiBlock key={`${id}-${s.title}`} id={id} title={s.title || TEXT_SECTION_TITLE[id] || id} status={brief.status}>
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
              <section className="rounded-xl border border-border bg-card p-4">
                <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold text-foreground">
                  <CalendarClock className="h-4 w-4 text-muted-foreground" aria-hidden /> Události z dokumentace
                  <span className="text-[11px] font-normal text-muted-foreground">(data z IRIS, ne AI)</span>
                </h2>
                <Timeline events={timeline.data} />
              </section>
            )}
          </React.Fragment>
        );
      case 'role_views':
        return brief.sections
          .filter((s) => s.id === 'role_views')
          .map((s) => (
            <RoleSection
              key={`role-${s.role}`}
              section={s}
              series={series.data ?? []}
              hideUnverified={hideUnverified}
              status={brief.status}
            />
          ));
      case 'red_flags':
        return (
          <section key={id} id="red-flags" className="scroll-mt-24 rounded-xl border border-border bg-card p-4">
            <h2 className="flex items-center gap-2 text-sm font-semibold text-foreground">
              <ShieldAlert className="h-4 w-4 text-destructive" aria-hidden /> Varovné signály ({brief.red_flags.length})
            </h2>
            {brief.red_flags.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">Pravidla nenašla žádný varovný signál.</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {brief.red_flags.map((f) => (
                  <RedFlagCard key={f.id} flag={f} />
                ))}
              </ul>
            )}
          </section>
        );
      case 'decision_support':
        return ds ? (
          <AiBlock key={id} id={id} title="Možnosti léčby" status={brief.status}>
            <TreatmentOptions options={ds.treatment_options} />
          </AiBlock>
        ) : null;
      case 'trials':
        return ds ? (
          <AiBlock key={id} id={id} title="Klinické studie" status={brief.status}>
            <TrialScreening trials={ds.trials} />
          </AiBlock>
        ) : null;
      case 'questions':
        return ds ? (
          <AiBlock key={id} id={id} title="Otázky k diskusi" status={brief.status}>
            <ol className="list-decimal space-y-1.5 pl-5 text-sm text-foreground">
              {ds.discussion_questions.map((q) => (
                <li key={q.text}>
                  {q.text}
                  <Citations ids={q.citations} />
                </li>
              ))}
            </ol>
            <p className="mt-2 text-[11px] text-muted-foreground">{ds.disclaimer}</p>
          </AiBlock>
        ) : null;
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
      default:
        return <React.Fragment key={id}>{textSection(id)}</React.Fragment>;
    }
  };

  return (
    <BriefDataProvider value={dataSource}>
      <CitationProvider order={order} activeId={openId} onOpen={setOpenId}>
        <div className="space-y-4">
          <CaseHeader header={brief.header} redFlagCount={brief.red_flags.length} />
          {blocks.map(renderBlock)}
          {!ds && blocks.includes('decision_support') && (
            <p className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
              Možnosti léčby, studie a otázky k diskusi v tomto podkladu zatím nejsou.
            </p>
          )}
          <p className="text-center text-[11px] text-muted-foreground">
            Podklad připravila AI ({brief.model}). Rozhoduje lékař, oficiálním záznamem se stane až po potvrzení.
            {' '}Tvrzení: {brief.stats.claims_total}, neověřených: {brief.stats.claims_unverified}, chybějících údajů:{' '}
            {brief.stats.missing_total}.
          </p>
        </div>
        <SourceDrawer evidenceId={openId} loadSource={dataSource.loadSource} onClose={close} />
      </CitationProvider>
    </BriefDataProvider>
  );
}
