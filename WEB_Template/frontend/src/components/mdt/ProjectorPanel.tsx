'use client';

import * as React from 'react';
import {
  CircleAlert,
  CircleCheck,
  CircleDashed,
  CircleDot,
  CircleMinus,
  Clock,
  OctagonAlert,
  Stethoscope,
  type LucideIcon,
} from 'lucide-react';
import { AiBlock } from '@/components/mdt/AiBlock';
import { CitationProvider, Citations, collectCitations } from '@/components/mdt/citations';
import { CompatibilityLight } from '@/components/mdt/CompatibilityLight';
import { formatDate } from '@/components/mdt/format';
import { buildKeyFacts, type FactGroup, type FactStatus, type KeyFact } from '@/components/mdt/key-facts';
import type { ProjectorSelection } from '@/components/mdt/projector';
import { SourceDrawer } from '@/components/mdt/SourceDrawer';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi, type StoredBrief } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import { cn } from '@/lib/utils';
import type {
  IntakePrefill,
  IntakeWarning,
  MdtCase,
  MdtSessionDetail,
  ObservationSeries,
  ProcedureCompatibility,
} from '@/types/mdt';

// Stabilní fetchery pro useApiData; prázdný argument = nic nenačítat.
const loadSession = async (id: string): Promise<MdtSessionDetail | null> => (id ? mdtApi.getSession(id) : null);
const loadBrief = async (id: string): Promise<StoredBrief | null> => (id ? mdtApi.getBrief(id) : null);
const loadCompatibility = async (id: string): Promise<ProcedureCompatibility[] | null> =>
  id ? mdtApi.getCompatibility(Number(id)) : null;
const loadIntake = async (pid: string): Promise<IntakePrefill | null> => (pid ? mdtApi.getIntake(pid) : null);
const loadObservations = async (pid: string): Promise<ObservationSeries[] | null> =>
  pid ? mdtApi.getObservations(pid) : null;

const STATUS_META: Record<FactStatus, { label: string; icon: LucideIcon; className: string }> = {
  normal: { label: 'v normě', icon: CircleCheck, className: 'text-emerald-600 dark:text-emerald-400' },
  abnormal: { label: 'mimo normu', icon: CircleAlert, className: 'text-amber-600 dark:text-amber-400' },
  critical: { label: 'závažné', icon: OctagonAlert, className: 'text-red-600 dark:text-red-400' },
  recorded: { label: 'bez hodnocení normality', icon: CircleDot, className: 'text-muted-foreground' },
  missing: { label: 'chybí', icon: CircleDashed, className: 'text-muted-foreground' },
  pending: { label: 'čeká se na výsledek', icon: Clock, className: 'text-muted-foreground' },
  skipped: { label: 'přeskočeno lékařem', icon: CircleMinus, className: 'text-muted-foreground' },
};

const LEGEND: FactStatus[] = ['normal', 'abnormal', 'critical', 'recorded', 'missing'];

const GROUP_TITLE: Record<FactGroup, string> = {
  diagnosis: 'Podle diagnózy',
  lab: 'Laboratoř',
  general: 'Obecně',
  alert: 'Další upozornění',
};

const INTENT_LABEL: Record<'C' | 'P', string> = { C: 'kurativní', P: 'paliativní' };

const MEETING_DATE = new Intl.DateTimeFormat('cs-CZ', { day: 'numeric', month: 'numeric', year: 'numeric', timeZone: 'Europe/Prague' });
const MEETING_TIME = new Intl.DateTimeFormat('cs-CZ', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Prague' });

/** Datum a čas zasedání v pražském čase ("2026-10-21T14:00:00+02:00" → „21. 10. 2026“, „14:00“). */
export const meetingDate = (iso: string) => MEETING_DATE.format(new Date(iso));
export const meetingTime = (iso: string) => MEETING_TIME.format(new Date(iso));

/**
 * Úzký panel pro projektor vedle snímku z PACS (T-512, FR-U2): hlavička bez jména a RČ (D-018),
 * anamnéza od AI s citacemi, klíčové údaje podle diagnózy s normalitou z pravidel a referenčních mezí,
 * všechny léčebné postupy se semaforem (D-015) a dole otázka pro MDT s MKN-10.
 */
export function ProjectorPanel({
  selection,
  className,
  titleAs = 'h1',
}: {
  selection: ProjectorSelection | null;
  className?: string;
  /** V samostatném okně h1, v náhledu uvnitř admin stránky h2. */
  titleAs?: 'h1' | 'h2';
}) {
  const caseKey = selection ? String(selection.caseId) : '';
  const patientId = selection?.patient ?? '';
  // Pět nezávislých zdrojů běží souběžně: board (hlavička, otázka), podklad, semafor, šablona, laboratoř.
  const session = useApiData(loadSession, selection ? String(selection.board) : '');
  const brief = useApiData(loadBrief, caseKey);
  const compatibility = useApiData(loadCompatibility, caseKey);
  const intake = useApiData(loadIntake, patientId);
  const observations = useApiData(loadObservations, patientId);
  const [sourceId, setSourceId] = React.useState<string | null>(null);

  const item = session.data?.cases.find((c) => c.id === selection?.caseId) ?? null;
  const keyFacts = React.useMemo(() => buildKeyFacts(intake.data, observations.data), [intake.data, observations.data]);
  const anamnesis = brief.data?.sections.find((s) => s.id === 'anamnesis') ?? null;
  const citationOrder = React.useMemo(
    () => collectCitations([anamnesis, keyFacts.facts, compatibility.data, item?.patient]),
    [anamnesis, keyFacts.facts, compatibility.data, item?.patient],
  );

  if (!selection) {
    return (
      <EmptyState
        className={cn('h-full rounded-none border-0 bg-transparent', className)}
        icon={<Stethoscope className="size-6" aria-hidden />}
        title="Vyberte případ"
        description="V seznamu boardů rozbalte board a klikněte na pacienta. Panel se přepne sám."
      />
    );
  }

  return (
    <CitationProvider order={citationOrder} activeId={sourceId} onOpen={setSourceId}>
      <article className={cn('flex h-full min-h-0 flex-col bg-background text-foreground', className)} aria-label="Klinický přehled pro projektor">
        <PanelHeader
          titleAs={titleAs}
          patientId={selection.patient}
          item={item}
          session={session.data ?? null}
          intake={intake.data ?? null}
          ecogWarnings={keyFacts.ecogWarnings}
          loading={session.loading}
          failed={Boolean(session.error)}
          missingCase={Boolean(session.data) && !item}
        />
        {/* relative: sr-only popisky (position: absolute) zůstanou v rolovací oblasti a nenatáhnou stránku */}
        <div className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <div className="flex flex-col gap-6 px-4 py-4">
            <AnamnesisSection brief={brief.data ?? null} loading={brief.loading} />
            <KeyFactsSection facts={keyFacts.facts} loading={intake.loading || observations.loading} failed={Boolean(intake.error)} />
            <TreatmentsSection options={compatibility.data ?? null} loading={compatibility.loading} failed={Boolean(compatibility.error)} />
          </div>
        </div>
        <QuestionStrip item={item} loading={session.loading} />
      </article>
      <SourceDrawer evidenceId={sourceId} loadSource={mdtApi.getEvidence} onClose={() => setSourceId(null)} />
    </CitationProvider>
  );
}

function PanelHeader({
  titleAs: Title,
  patientId,
  item,
  session,
  intake,
  ecogWarnings,
  loading,
  failed,
  missingCase,
}: {
  titleAs: 'h1' | 'h2';
  patientId: string;
  item: MdtCase | null;
  session: MdtSessionDetail | null;
  intake: IntakePrefill | null;
  ecogWarnings: IntakeWarning[];
  loading: boolean;
  failed: boolean;
  missingCase: boolean;
}) {
  const patient = item?.patient ?? null;
  const physicianPs = item?.ecog ?? intake?.ecog_physician?.value ?? null;
  const patientPsText = intake?.fields.find((f) => f.id === 'ecog.patient')?.value;
  const patientPs = patientPsText && /^[0-4]$/.test(patientPsText) ? Number(patientPsText) : null;
  const psDiffers = physicianPs !== null && patientPs !== null && Math.abs(physicianPs - patientPs) >= 1;
  const intent = item?.intent ?? intake?.intent_prefill ?? null;
  const intentSource = item?.intent ? 'potvrzeno při zařazení' : intake?.intent_prefill ? 'předvyplněno z minulé MDT' : 'zatím nezvoleno';
  const tnm = intake?.fields.find((f) => f.id === 'staging.tnm')?.value;
  const ecogTitle = ecogWarnings.map((w) => w.title).join(' · ');

  return (
    <header className="shrink-0 border-b border-border bg-card px-4 py-3">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <Title translate="no" className="text-base font-semibold leading-tight">{patient?.display_name ?? patientId}</Title>
          {loading ? (
            <Skeleton className="mt-2 h-4 w-40" />
          ) : failed ? (
            <p className="mt-1 text-sm text-destructive">Board se nepodařilo načíst. Zkuste případ vybrat znovu.</p>
          ) : missingCase ? (
            <p className="mt-1 text-sm text-destructive">Případ už v tomto boardu není. Vyberte ho znovu v admin okně.</p>
          ) : (
            <>
              <p className="mt-1 text-sm leading-snug text-muted-foreground">
                {patient?.diagnosis?.text ?? 'Diagnóza v záznamu chybí'}
                {tnm ? ` · ${tnm}` : ''}
              </p>
              {session && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {session.title} · {meetingDate(session.date)} {meetingTime(session.date)}
                </p>
              )}
            </>
          )}
        </div>
        <dl className="flex shrink-0 gap-1.5">
          <div className="flex min-w-14 flex-col items-center rounded-lg border border-border bg-background px-2 py-1.5" title="Performance status (ECOG) podle lékaře">
            <dt className="text-[11px] font-medium text-muted-foreground">PS</dt>
            <dd className="text-[28px] font-bold leading-none tabular-nums">{physicianPs ?? '–'}</dd>
            {patientPs !== null && (
              <dd
                className={cn(
                  'mt-1 inline-flex items-center gap-0.5 text-[11px] font-medium tabular-nums',
                  psDiffers ? 'text-amber-700 dark:text-amber-400' : 'text-muted-foreground',
                )}
                title={psDiffers ? ecogTitle || 'PS lékaře a pacienta se liší o 1 a víc (OBC-1.3)' : 'PS podle pacienta (PROMs)'}
              >
                {psDiffers && <CircleAlert className="size-3" aria-hidden />}
                pac. {patientPs}
                {psDiffers && <span className="sr-only">, liší se od lékaře</span>}
              </dd>
            )}
          </div>
          <div className="flex min-w-14 flex-col items-center rounded-lg border border-border bg-background px-2 py-1.5" title={`Léčebný záměr: ${intentSource}`}>
            <dt className="text-[11px] font-medium text-muted-foreground">C/P</dt>
            <dd className="text-[28px] font-bold leading-none">{intent ?? '–'}</dd>
            <dd className="mt-1 text-[11px] text-muted-foreground">{intent ? INTENT_LABEL[intent] : 'nezvoleno'}</dd>
          </div>
        </dl>
      </div>
    </header>
  );
}

function SectionTitle({ id, children }: { id: string; children: React.ReactNode }) {
  return <h2 id={id} className="mb-2.5 text-sm font-semibold text-foreground">{children}</h2>;
}

function SectionSkeleton({ rows }: { rows: number }) {
  return (
    <div className="flex flex-col gap-2" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => <Skeleton key={i} className={cn('h-4', i % 2 ? 'w-4/5' : 'w-full')} />)}
    </div>
  );
}

function AnamnesisSection({ brief, loading }: { brief: StoredBrief | null; loading: boolean }) {
  const section = brief?.sections.find((s) => s.id === 'anamnesis');
  if (loading) {
    return (
      <section aria-labelledby="projector-anamnesis">
        <SectionTitle id="projector-anamnesis">Anamnéza</SectionTitle>
        <SectionSkeleton rows={3} />
      </section>
    );
  }
  if (!section?.items.length) {
    return (
      <section aria-labelledby="projector-anamnesis">
        <SectionTitle id="projector-anamnesis">Anamnéza</SectionTitle>
        <p className="text-sm leading-relaxed text-muted-foreground">
          {brief ? 'Podklad anamnézu neobsahuje.' : 'Zkrácená anamnéza se zobrazí, až vznikne podklad pro komisi.'}
        </p>
      </section>
    );
  }
  return (
    <AiBlock title="Anamnéza" status={brief?.status === 'confirmed' ? 'confirmed' : 'draft'}>
      <p className="text-[15px] leading-relaxed text-foreground">
        {section.items.map((claim) => (
          <React.Fragment key={claim.id}>
            {claim.kind === 'missing' ? <span className="text-muted-foreground">Chybí: {claim.text}</span> : claim.text}
            <Citations ids={claim.citations} />{' '}
          </React.Fragment>
        ))}
      </p>
    </AiBlock>
  );
}

function KeyFactsSection({ facts, loading, failed }: { facts: KeyFact[]; loading: boolean; failed: boolean }) {
  const groups = (Object.keys(GROUP_TITLE) as FactGroup[])
    .map((group) => ({ group, items: facts.filter((f) => f.group === group) }))
    .filter((g) => g.items.length > 0);
  return (
    <section aria-labelledby="projector-facts">
      <SectionTitle id="projector-facts">Klíčové údaje</SectionTitle>
      {loading ? (
        <SectionSkeleton rows={4} />
      ) : failed ? (
        <p role="alert" className="text-sm text-destructive">Údaje pacienta se nepodařilo načíst. Obnovte okno (F5).</p>
      ) : groups.length === 0 ? (
        <p className="text-sm text-muted-foreground">Pro pacienta nejsou v IRIS žádné údaje šablony.</p>
      ) : (
        <div className="flex flex-col gap-4">
          {groups.map(({ group, items }) => (
            <div key={group}>
              <h3 className="mb-1.5 text-xs font-medium text-muted-foreground">{GROUP_TITLE[group]}</h3>
              <ul className="grid grid-cols-2 gap-x-3 gap-y-2.5">
                {items.map((fact) => <FactItem key={fact.id} fact={fact} />)}
              </ul>
            </div>
          ))}
          <FactLegend />
        </div>
      )}
    </section>
  );
}

function FactItem({ fact }: { fact: KeyFact }) {
  const meta = STATUS_META[fact.status];
  const Icon = meta.icon;
  const value = fact.value ?? meta.label;
  const wide = fact.group === 'alert' || value.length > 26;
  return (
    <li className={cn('flex min-w-0 items-start gap-2', wide && 'col-span-2')} title={[fact.label, fact.reason].filter(Boolean).join(' — ')}>
      <Icon className={cn('mt-0.5 size-4 shrink-0', meta.className)} strokeWidth={2.25} aria-hidden />
      <div className="min-w-0">
        <p className="text-[13px] font-semibold leading-snug">
          {fact.abbr}
          <span className="sr-only">: {fact.label}, {meta.label}</span>
          <Citations ids={fact.citations} />
        </p>
        <p className="line-clamp-2 text-[13px] leading-snug text-muted-foreground">
          {value}
          {fact.date && <span className="tabular-nums"> · {formatDate(fact.date)}</span>}
        </p>
        {fact.reason && fact.status !== 'normal' && fact.status !== 'recorded' && (
          <p className={cn('line-clamp-2 text-xs leading-snug', meta.className)}>{fact.reason}</p>
        )}
      </div>
    </li>
  );
}

function FactLegend() {
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1 border-t border-border pt-2.5 text-xs text-muted-foreground" aria-label="Vysvětlivky">
      {LEGEND.map((status) => {
        const { icon: Icon, label, className } = STATUS_META[status];
        return (
          <li key={status} className="inline-flex items-center gap-1">
            <Icon className={cn('size-3.5', className)} strokeWidth={2.25} aria-hidden />
            {label}
          </li>
        );
      })}
      <li className="basis-full">Barvu určuje jen referenční rozmezí z laboratoře nebo pravidlo s citací.</li>
    </ul>
  );
}

function TreatmentsSection({ options, loading, failed }: { options: ProcedureCompatibility[] | null; loading: boolean; failed: boolean }) {
  return (
    <section aria-labelledby="projector-treatments">
      <SectionTitle id="projector-treatments">Léčebné postupy</SectionTitle>
      {loading ? (
        <SectionSkeleton rows={3} />
      ) : failed ? (
        <p role="alert" className="text-sm text-destructive">Soulad postupů se nepodařilo načíst. Obnovte okno (F5).</p>
      ) : !options?.length ? (
        <p className="text-sm text-muted-foreground">Pro diagnózu nejsou v katalogu žádné postupy.</p>
      ) : (
        <>
          <ul className="flex flex-col divide-y divide-border">
            {options.map((option) => <TreatmentItem key={option.id} option={option} />)}
          </ul>
          <p className="mt-2.5 text-xs leading-relaxed text-muted-foreground">
            Barva ukazuje soulad postupu se stavem pacienta podle pravidel, nejde o doporučení. Rozhoduje komise.
          </p>
        </>
      )}
    </section>
  );
}

function TreatmentItem({ option }: { option: ProcedureCompatibility }) {
  const { compatibility } = option;
  const decisive = compatibility.rules.filter((rule) => rule.status === compatibility.overall).slice(0, 2);
  const rest = compatibility.rules.filter((rule) => !decisive.includes(rule));
  return (
    <li className="py-2.5 first:pt-0 last:pb-0">
      <div className="flex items-start justify-between gap-2">
        <p className="min-w-0 text-sm font-semibold leading-snug">
          {option.title}
          <Citations ids={option.guideline_citations} />
        </p>
        <CompatibilityLight light={compatibility.overall} />
      </div>
      {decisive.map((rule) => (
        <p key={rule.rule_id} className="mt-1 text-[13px] leading-snug text-muted-foreground">
          {rule.text}
          <Citations ids={[...rule.patient_citations, rule.rule_citation]} />
        </p>
      ))}
      {rest.length > 0 && (
        <details className="mt-1 text-[13px] text-muted-foreground">
          <summary className="cursor-pointer select-none text-xs font-medium hover:text-foreground">
            Další pravidla ({rest.length})
          </summary>
          <ul className="mt-1 flex flex-col gap-1">
            {rest.map((rule) => (
              <li key={rule.rule_id} className="flex items-start gap-2 leading-snug">
                <CompatibilityLight light={rule.status} className="px-1 py-0 text-[11px]" />
                <span className="min-w-0">
                  {rule.text}
                  <Citations ids={[...rule.patient_citations, rule.rule_citation]} />
                </span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </li>
  );
}

function QuestionStrip({ item, loading }: { item: MdtCase | null; loading: boolean }) {
  const patient = item?.patient ?? null;
  const question = item?.question ?? patient?.mdt_question ?? null;
  return (
    <footer className="shrink-0 border-t-2 border-primary/40 bg-card px-4 py-3">
      <h2 className="sr-only">Otázka pro MDT</h2>
      <div className="flex items-start gap-3">
        {loading ? (
          <Skeleton className="h-6 flex-1" />
        ) : (
          <p className="min-w-0 flex-1 text-lg font-bold leading-snug text-balance">
            {question ?? 'Otázka pro MDT v záznamu chybí.'}
            {patient?.mdt_question_citation && <Citations ids={[patient.mdt_question_citation]} />}
          </p>
        )}
        {patient?.diagnosis && (
          <div className="shrink-0 text-right" title={patient.diagnosis.text}>
            <p className="text-[11px] font-medium text-muted-foreground">MKN-10</p>
            <p translate="no" className="text-base font-bold tabular-nums">{patient.diagnosis.icd10}</p>
          </div>
        )}
      </div>
    </footer>
  );
}
