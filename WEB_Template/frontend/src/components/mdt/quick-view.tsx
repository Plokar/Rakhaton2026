'use client';

import * as React from 'react';
import Link from 'next/link';
import { ChevronRight, TriangleAlert } from 'lucide-react';
import { Skeleton } from '@/components/shadcn/skeleton';
import { briefP03, intakeP03, observationsP03 } from '@/lib/fixtures';
import { mdtApi, type StoredBrief } from '@/lib/mdt-api';
import {
  useBriefQuery,
  useCompatibilityQuery,
  useIntakeQuery,
  useObservationsQuery,
  useSessionQuery,
  useTemplateQuery,
} from '@/lib/queries';
import { cn } from '@/lib/utils';
import type {
  CaseTemplate,
  IntakePrefill,
  IntakeWarning,
  MdtCase,
  MdtSessionDetail,
  ObservationSeries,
  ProcedureCompatibility,
} from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { CitationProvider, Citations, collectCitations } from './citations';
import { CompatibilityLight, LightIcon } from './CompatibilityLight';
import { dayLabel, timeLabel } from './dates';
import { FactIcon, FactLegend, FACT_META } from './FactIcon';
import { formatDate } from './format';
import { KbItemRow } from './KbItem';
import { buildKeyFacts, type KeyFact } from './key-facts';
import { SourceDrawer, type SourceLoader } from './SourceDrawer';

/**
 * 30s rychlý přehled případu (NAVRH_UI §2.2): stejné pořadí a zkratky v bočním panelu kalendáře,
 * v jednání komise, nahoře v detailu i v okně projektoru (T-512). Hlavička bez jména a RČ (D-018),
 * anamnéza od AI s citacemi, klíčové údaje s normalitou jen z rozmezí a pravidel, všechny postupy
 * se semaforem (D-015) a otázka pro MDT jako kotva diskuse.
 */

type Res<T> = { data: T | undefined; loading: boolean; failed: boolean };

export interface QuickViewSources {
  patientId: string;
  caseId: number | null;
  session: Res<MdtSessionDetail | null>;
  brief: Res<StoredBrief | null>;
  compatibility: Res<ProcedureCompatibility[]>;
  intake: Res<IntakePrefill>;
  observations: Res<ObservationSeries[]>;
  /** Doporučená šablona podle diagnózy (T-318); `null` = báze ji pro diagnózu nemá. */
  template: Res<CaseTemplate | null>;
  loadSource: SourceLoader;
}

const res = <T,>(q: { data: T | undefined; isLoading: boolean; isError: boolean }): Res<T> => ({
  data: q.data,
  loading: q.isLoading,
  failed: q.isError,
});

/** Data přehledu z API (TanStack Query): pět nezávislých zdrojů souběžně, sdílená cache s kalendářem. */
export function useQuickViewSources(target: { sessionId: number | null; caseId: number | null; patientId: string | null }): QuickViewSources {
  const session = useSessionQuery(target.sessionId);
  const brief = useBriefQuery(target.caseId);
  const compatibility = useCompatibilityQuery(target.caseId);
  const intake = useIntakeQuery(target.patientId);
  const observations = useObservationsQuery(target.patientId);
  const template = useTemplateQuery(target.caseId);
  return {
    patientId: target.patientId ?? '',
    caseId: target.caseId,
    session: res(session),
    brief: res(brief),
    compatibility: res(compatibility),
    intake: res(intake),
    observations: res(observations),
    template: res(template),
    loadSource: mdtApi.getEvidence,
  };
}

const done = <T,>(data: T): Res<T> => ({ data, loading: false, failed: false });

/** Demo případ P03 z fixtures (bez backendu, ARCH §7.3): semafor z B2 podkladu. */
export function fixtureQuickViewSources(loadSource: SourceLoader): QuickViewSources {
  return {
    patientId: 'P03',
    caseId: null,
    session: done(null),
    brief: done(briefP03 as StoredBrief),
    compatibility: done(
      (briefP03.decision_support?.treatment_options ?? []).map((o) => ({
        id: o.id,
        title: o.title,
        guideline_citations: o.guideline_citations,
        compatibility: o.compatibility,
      })),
    ),
    intake: done(intakeP03),
    observations: done(observationsP03),
    template: done(null),
    loadSource,
  };
}

const INTENT_LABEL: Record<'C' | 'P', string> = { C: 'kurativní', P: 'paliativní' };

/** Hlavička přehledu z agendy boardu, šablony údajů a podkladu (co je k dispozici dřív). */
export function quickHeader(sources: QuickViewSources, item: MdtCase | null) {
  const brief = sources.brief.data ?? null;
  const intake = sources.intake.data ?? null;
  const patient = item?.patient ?? null;
  const field = (id: string) => intake?.fields.find((f) => f.id === id);
  const physicianPs = item?.ecog ?? intake?.ecog_physician?.value ?? brief?.header.ecog.physician?.value ?? null;
  const patientPsText = field('ecog.patient')?.value;
  const patientPs = patientPsText && /^[0-4]$/.test(patientPsText) ? Number(patientPsText) : brief?.header.ecog.patient?.value ?? null;
  const intent = item?.intent ?? intake?.intent_prefill ?? brief?.header.intent?.letter ?? null;
  return {
    displayName: patient?.display_name ?? brief?.header.display_name ?? sources.patientId,
    diagnosis: patient?.diagnosis ?? (brief ? { text: brief.header.diagnosis.text, icd10: brief.header.diagnosis.icd10, citation: brief.header.diagnosis.citation } : null),
    tnm: field('staging.tnm')?.value ?? brief?.header.tnm?.text ?? null,
    physicianPs,
    patientPs,
    psDiffers: physicianPs !== null && patientPs !== null && Math.abs(physicianPs - patientPs) >= 1,
    intent,
    intentSource: item?.intent ? 'potvrzeno při zařazení' : intake?.intent_prefill ? 'předvyplněno z minulé MDT' : intent ? 'z podkladu' : 'zatím nezvoleno',
    question: item?.question ?? patient?.mdt_question ?? brief?.header.mdt_question.text ?? null,
    questionCitation: patient?.mdt_question_citation ?? brief?.header.mdt_question.citation ?? null,
    warnings: intake?.warnings ?? [],
  };
}

type Header = ReturnType<typeof quickHeader>;

interface QuickViewContextValue {
  sources: QuickViewSources;
  item: MdtCase | null;
  header: Header;
  facts: KeyFact[];
  ecogWarnings: IntakeWarning[];
}

const QuickViewContext = React.createContext<QuickViewContextValue | null>(null);

function useQuickView(): QuickViewContextValue {
  const ctx = React.useContext(QuickViewContext);
  if (!ctx) throw new Error('Část rychlého přehledu musí být uvnitř <QuickViewRoot>.');
  return ctx;
}

/** Kontext přehledu: odvozená hlavička, klíčové údaje, číslování citací a boční panel se zdrojem. */
export function QuickViewRoot({
  sources,
  caseId,
  children,
}: {
  sources: QuickViewSources;
  caseId: number | null;
  children: React.ReactNode;
}) {
  const [sourceId, setSourceId] = React.useState<string | null>(null);
  const item = sources.session.data?.cases.find((c) => c.id === caseId) ?? null;
  const { facts, ecogWarnings } = React.useMemo(
    () => buildKeyFacts(sources.intake.data, sources.observations.data),
    [sources.intake.data, sources.observations.data],
  );
  const anamnesis = sources.brief.data?.sections.find((s) => s.id === 'anamnesis') ?? null;
  const citationOrder = React.useMemo(
    () => collectCitations([anamnesis, facts, sources.compatibility.data, item?.patient]),
    [anamnesis, facts, sources.compatibility.data, item?.patient],
  );
  const value = { sources, item, header: quickHeader(sources, item), facts, ecogWarnings };
  const close = React.useCallback(() => setSourceId(null), []);
  return (
    <QuickViewContext.Provider value={value}>
      <CitationProvider order={citationOrder} activeId={sourceId} onOpen={setSourceId}>
        {children}
        <SourceDrawer evidenceId={sourceId} loadSource={sources.loadSource} onClose={close} />
      </CitationProvider>
    </QuickViewContext.Provider>
  );
}

// ── Hlavička ────────────────────────────────────────────────────────────────

function Metric({
  label,
  title,
  value,
  sub,
  warn = false,
}: {
  label: string;
  title: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  warn?: boolean;
}) {
  return (
    <div className="flex min-w-16 flex-col items-center rounded-xl border border-border bg-background px-2.5 py-1.5" title={title}>
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="text-[1.75rem] font-semibold leading-8 tabular-nums">{value}</dd>
      {sub && (
        <dd className={cn('inline-flex items-center gap-0.5 text-xs tabular-nums', warn ? 'font-medium text-amber-800 dark:text-amber-300' : 'text-muted-foreground')}>
          {sub}
        </dd>
      )}
    </div>
  );
}

/** PS lékař / pacient a záměr C/P (D-018). Rozdíl PS ≥ 1 oranžově s ikonou (OBC-1.3). */
export function QuickMetrics() {
  const { header, ecogWarnings } = useQuickView();
  const psTitle = header.psDiffers
    ? ecogWarnings.map((w) => w.title).join(' · ') || 'PS lékaře a pacienta se liší o 1 a víc (OBC-1.3)'
    : 'Performance status (ECOG) podle lékaře, pod ním podle pacienta (PROMs)';
  return (
    <dl className="flex shrink-0 gap-1.5">
      <Metric
        label="PS"
        title={psTitle}
        value={header.physicianPs ?? '–'}
        warn={header.psDiffers}
        sub={
          header.patientPs !== null ? (
            <>
              {header.psDiffers && <TriangleAlert className="size-3" aria-hidden />}
              pac. {header.patientPs}
              {header.psDiffers && <span className="sr-only">, liší se od lékaře</span>}
            </>
          ) : (
            'pac. –'
          )
        }
      />
      <Metric
        label="C/P"
        title={`Léčebný záměr: ${header.intentSource}`}
        value={header.intent ?? '–'}
        sub={header.intent ? INTENT_LABEL[header.intent] : 'nezvoleno'}
      />
    </dl>
  );
}

/** Identita, diagnóza + TNM, zasedání. `as` určuje úroveň nadpisu (h1 v samostatném okně). */
export function QuickIdentity({
  as: Title = 'h2',
  size = 'default',
  icd = true,
}: {
  as?: 'h1' | 'h2';
  size?: 'default' | 'large';
  /** MKN-10 u diagnózy; úzký panel ho má v pásu otázky. */
  icd?: boolean;
}) {
  const { header, sources } = useQuickView();
  const session = sources.session.data;
  return (
    <div className="min-w-0 flex-1">
      <Title translate="no" className={cn('font-semibold leading-tight tracking-tight', size === 'large' ? 'text-xl' : 'text-base')}>
        {header.displayName}
      </Title>
      {sources.session.loading && !header.diagnosis ? (
        <Skeleton className="mt-2 h-4 w-48" />
      ) : sources.session.failed && !header.diagnosis ? (
        <p className="mt-1 text-sm text-destructive">Board se nepodařilo načíst. Vyberte případ znovu.</p>
      ) : (
        <p className="mt-1 text-sm leading-snug text-muted-foreground">
          {header.diagnosis ? (
            <>
              {icd && <><span translate="no" className="font-medium text-foreground">{header.diagnosis.icd10}</span> </>}
              {header.diagnosis.text}
            </>
          ) : (
            'Diagnóza v záznamu chybí'
          )}
          {header.tnm && <> · <span translate="no">{header.tnm}</span></>}
        </p>
      )}
      {session && (
        <p className="mt-0.5 text-xs text-muted-foreground">
          {session.title}, {dayLabel(session.date)} {timeLabel(session.date)}
        </p>
      )}
    </div>
  );
}

/** Počet aktivních varování z kontroly úplnosti (POZADAVKY §2.2), odkaz na detail. */
export function QuickWarnings({ href }: { href?: string }) {
  const { header } = useQuickView();
  const count = header.warnings.length;
  if (!count) return null;
  const high = header.warnings.filter((w) => w.severity === 'high').length;
  const label = `${count} varování${high ? `, ${high} závažn${high === 1 ? 'é' : 'á'}` : ''}`;
  const content = (
    <>
      <TriangleAlert className={cn('size-4', high ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400')} aria-hidden />
      {label}
    </>
  );
  return href ? (
    <Link href={href} className="inline-flex items-center gap-1.5 text-sm font-medium underline-offset-4 hover:underline">
      {content}
    </Link>
  ) : (
    <span className="inline-flex items-center gap-1.5 text-sm font-medium">{content}</span>
  );
}

// ── Klíčové údaje ───────────────────────────────────────────────────────────

const ATTENTION = new Set(['critical', 'abnormal']);
const UNRESOLVED = new Set(['missing', 'pending', 'skipped']);

/** Pořadí pro 30 s: závažné a mimo normu, pak chybějící, pak zaznamenané; normální hodnoty sbalené. */
function orderFacts(facts: KeyFact[]) {
  const rank = (f: KeyFact) => (f.status === 'critical' ? 0 : f.status === 'abnormal' ? 1 : 2);
  return {
    attention: facts.filter((f) => ATTENTION.has(f.status)).toSorted((a, b) => rank(a) - rank(b)),
    unresolved: facts.filter((f) => UNRESOLVED.has(f.status)),
    recorded: facts.filter((f) => f.status === 'recorded'),
    normal: facts.filter((f) => f.status === 'normal'),
  };
}

function FactRow({ fact }: { fact: KeyFact }) {
  const meta = FACT_META[fact.status];
  const value = fact.value ?? meta.label;
  return (
    <li
      className="grid grid-cols-[1rem_6.5rem_minmax(0,1fr)] items-start gap-x-2 py-1.5"
      title={[fact.label, fact.reason].filter(Boolean).join(' · ')}
    >
      <FactIcon status={fact.status} className="mt-0.5" />
      <span className="line-clamp-2 text-[13px] font-semibold leading-5">
        {fact.abbr}
        <span className="sr-only">: {fact.label}, {meta.label}</span>
      </span>
      <span className="min-w-0 text-[13px] leading-5">
        <span className={cn('line-clamp-2', fact.status === 'missing' && 'text-muted-foreground')}>
          {value}
          {fact.date && <span className="tabular-nums text-muted-foreground"> · {formatDate(fact.date)}</span>}
          <Citations ids={fact.citations} />
        </span>
        {fact.reason && fact.status !== 'normal' && fact.status !== 'recorded' && (
          <span className="line-clamp-2 block text-xs leading-4 text-muted-foreground">{fact.reason}</span>
        )}
      </span>
    </li>
  );
}

/**
 * Údaj jako dlaždice úzkého panelu (projektor, boční panel): zkratka a krátká hodnota, ikona normality.
 * Důvod barvy je v tooltipu a pro čtečky; dlouhá hodnota nebo samostatné varování zabere oba sloupce.
 */
const PATIENT_FACT = /^P\d{2}(?:-|#|$)/;

function FactTile({ fact }: { fact: KeyFact }) {
  const meta = FACT_META[fact.status];
  const value = fact.value ?? meta.label;
  const wide = fact.group === 'alert';
  // V dlaždici jen fakta pacienta (nejvýš 2); pasáže pravidel a ostatní zdroje jsou v tooltipu a v detailu.
  const shown = fact.citations.filter((c) => PATIENT_FACT.test(c)).slice(0, 2);
  const detail = [fact.label, fact.date && formatDate(fact.date), fact.reason, fact.citations.join(', ')].filter(Boolean).join(' · ');
  return (
    <li className={cn('flex min-w-0 items-start gap-2', wide && 'col-span-2')} title={detail}>
      <FactIcon status={fact.status} className="mt-0.5 size-[1.125rem]" />
      <div className="min-w-0">
        <p className="text-sm font-semibold leading-5">
          {fact.abbr}
          <span className="sr-only">: {meta.label}{fact.reason ? `, ${fact.reason}` : ''}</span>
          <Citations ids={shown} className="ml-1.5" />
        </p>
        <p className={cn('line-clamp-2 text-sm leading-5', fact.status === 'missing' ? 'text-muted-foreground/80' : 'text-muted-foreground')}>{value}</p>
      </div>
    </li>
  );
}

export function KeyFactsList({ legend = true, layout = 'rows' }: { legend?: boolean; layout?: 'rows' | 'tiles' }) {
  const { facts, sources } = useQuickView();
  const [showNormal, setShowNormal] = React.useState(false);
  const groups = orderFacts(facts);
  const loading = sources.intake.loading || sources.observations.loading;
  const Item = layout === 'tiles' ? FactTile : FactRow;
  // Úzký panel: obecné údaje (histologie, TNM, komorbidity…) opakují hlavičku, sbalí se s hodnotami v normě.
  const tiles = layout === 'tiles';
  const primary = [...groups.attention, ...groups.unresolved, ...groups.recorded.filter((f) => !tiles || f.group !== 'general')];
  const folded = [...(tiles ? groups.recorded.filter((f) => f.group === 'general') : []), ...groups.normal];

  return (
    <section aria-labelledby="qv-facts">
      <h3 id="qv-facts" className={cn('text-sm font-semibold', layout === 'tiles' ? 'sr-only' : 'mb-1')}>Klíčové údaje</h3>
      {loading ? (
        <SkeletonRows rows={5} />
      ) : sources.intake.failed ? (
        <p role="alert" className="text-sm text-destructive">Údaje pacienta se nepodařilo načíst. Obnovte stránku (F5).</p>
      ) : facts.length === 0 ? (
        <p className="text-sm text-muted-foreground">Pro pacienta nejsou v IRIS žádné údaje šablony.</p>
      ) : (
        <>
          <ul className={layout === 'tiles' ? 'grid grid-cols-2 gap-x-4 gap-y-3 pt-1' : 'divide-y divide-border/60'}>
            {primary.map((fact) => (
              <Item key={fact.id} fact={fact} />
            ))}
            {showNormal && folded.map((fact) => <Item key={fact.id} fact={fact} />)}
          </ul>
          {folded.length > 0 && (
            <button
              type="button"
              onClick={() => setShowNormal(!showNormal)}
              aria-expanded={showNormal}
              className={cn(
                'flex max-w-full items-center gap-1.5 rounded-md py-1 text-left text-[13px] font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                layout === 'tiles' ? 'mt-2' : 'mt-1',
              )}
            >
              <ChevronRight className={cn('size-4 transition-transform motion-reduce:transition-none', showNormal && 'rotate-90')} aria-hidden />
              <span className="shrink-0 whitespace-nowrap">
                {showNormal
                  ? tiles ? 'Skrýt další údaje' : 'Skrýt hodnoty v normě'
                  : tiles ? `Další údaje (${folded.length})` : `V normě (${folded.length})`}
              </span>
              {!showNormal && (
                <span className="min-w-0 truncate font-normal" translate="no">
                  {folded.slice(0, 5).map((f) => f.abbr).join(', ')}
                  {folded.length > 5 ? '…' : ''}
                </span>
              )}
            </button>
          )}
          {legend && <FactLegend className="mt-3 border-t border-border/60 pt-2" />}
        </>
      )}
    </section>
  );
}

function SkeletonRows({ rows }: { rows: number }) {
  return (
    <div className="flex flex-col gap-2.5 py-1" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <Skeleton key={i} className={cn('h-4', i % 2 ? 'w-4/5' : 'w-full')} />
      ))}
    </div>
  );
}

// ── Šablona podle diagnózy (T-318) ─────

/**
 * Úplnost podle šablony projektoru pro diagnózu (báze `data/onko`, bez AI): kolik údajů šablony je
 * v podkladech, co je jen zmínka, starší než limit nebo chybí. Vidět jsou jen nedořešené, zbytek na klik.
 */
export function TemplateSummary() {
  const { sources } = useQuickView();
  const [all, setAll] = React.useState(false);
  const template = sources.template.data;
  if (!template?.projector.length) return null;
  const items = template.projector.filter((i) => i.status !== 'not_applicable');
  const open = items.filter((i) => i.status !== 'present');
  const count = (status: string) => items.filter((i) => i.status === status).length;
  const parts = [
    `v podkladech ${count('present')} z ${items.length}`,
    count('mention') && `jen zmínka ${count('mention')}`,
    count('stale') && `starší než limit ${count('stale')}`,
    count('missing') && `chybí ${count('missing')}`,
  ].filter(Boolean);
  return (
    <section aria-labelledby="qv-template">
      <h3 id="qv-template" className="text-sm font-semibold">
        Šablona: <span className="font-normal">{template.name}</span>
        <Citations ids={template.sources} />
      </h3>
      <p className="mt-0.5 text-xs text-muted-foreground">{parts.join(' · ')}</p>
      <ul className="mt-1 divide-y divide-border/60">
        {(all ? items : open).map((item) => <KbItemRow key={item.id} item={item} />)}
      </ul>
      {open.length < items.length && (
        <button
          type="button"
          onClick={() => setAll(!all)}
          aria-expanded={all}
          className="mt-1 inline-flex items-center gap-1.5 rounded-md py-1 text-[13px] font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRight className={cn('size-4 transition-transform motion-reduce:transition-none', all && 'rotate-90')} aria-hidden />
          {all ? 'Jen nedořešené údaje' : `Všechny údaje šablony (${items.length})`}
        </button>
      )}
    </section>
  );
}

// ── Léčebné postupy ─────────────────────────────────────────────────────────

function TreatmentRow({ option, dense = false }: { option: ProcedureCompatibility; dense?: boolean }) {
  const [open, setOpen] = React.useState(false);
  const { compatibility } = option;
  const muted = !dense && (compatibility.overall === 'grey' || compatibility.overall === 'skipped');
  // Úzký panel: jeden rozhodující důvod u každého postupu (i „nelze posoudit“), zbytek na klik.
  const decisive = compatibility.rules.filter((rule) => rule.status === compatibility.overall).slice(0, dense ? 1 : muted ? 0 : 2);
  const rest = compatibility.rules.filter((rule) => !decisive.includes(rule));
  return (
    <li className={cn(muted ? 'py-1.5' : dense ? 'py-3' : 'py-2.5')}>
      <div className="flex items-start gap-3">
        <p className={cn('min-w-0 flex-1 leading-snug', muted ? 'text-[13px] text-muted-foreground' : dense ? 'text-sm font-semibold' : 'text-sm font-medium')}>
          {option.title}
          {!dense && <Citations ids={option.guideline_citations} />}
        </p>
        <CompatibilityLight light={compatibility.overall} />
      </div>
      {decisive.map((rule) => (
        <p key={rule.rule_id} className={cn('text-muted-foreground', dense ? 'mt-0.5 text-sm leading-5' : 'mt-1 text-[13px] leading-snug')}>
          {rule.text}
          <Citations ids={[...rule.patient_citations, rule.rule_citation]} />
        </p>
      ))}
      {rest.length > 0 && (
        <>
          <button
            type="button"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            className="mt-0.5 inline-flex items-center gap-1 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ChevronRight className={cn('size-3.5 transition-transform motion-reduce:transition-none', open && 'rotate-90')} aria-hidden />
            {muted ? `Proč (${rest.length})` : `Další pravidla (${rest.length})`}
          </button>
          {open && (
            <ul className="mt-1 flex flex-col gap-1 pl-1">
              {rest.map((rule) => (
                <li key={rule.rule_id} className="flex items-start gap-2 text-[13px] leading-snug text-muted-foreground">
                  <span className="mt-0.5"><LightIcon light={rule.status} className="size-3.5" /></span>
                  <span className="min-w-0">
                    {rule.text}
                    <Citations ids={[...rule.patient_citations, rule.rule_citation]} />
                  </span>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </li>
  );
}

/** Všechny postupy v pořadí katalogu (ne podle barvy, aby řazení nepůsobilo jako doporučení). */
export function TreatmentList({ dense = false }: { dense?: boolean }) {
  const { sources } = useQuickView();
  const options = sources.compatibility.data;
  return (
    <section aria-labelledby="qv-treatments">
      <h3 id="qv-treatments" className={cn('text-sm font-semibold', dense ? 'sr-only' : 'mb-1')}>
        Léčebné postupy{options?.length ? <span className="font-normal text-muted-foreground"> ({options.length})</span> : null}
      </h3>
      {sources.compatibility.loading ? (
        <SkeletonRows rows={4} />
      ) : sources.compatibility.failed ? (
        <p role="alert" className="text-sm text-destructive">Soulad postupů se nepodařilo načíst. Obnovte stránku (F5).</p>
      ) : !options?.length ? (
        <p className="text-sm text-muted-foreground">Pro diagnózu nejsou v katalogu žádné postupy.</p>
      ) : (
        <>
          <ul className="divide-y divide-border/60">
            {options.map((option) => <TreatmentRow key={option.id} option={option} dense={dense} />)}
          </ul>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
            Barvu počítají pravidla z doporučených postupů, ne AI. Ukazuje soulad se stavem pacienta, nejde o doporučení. Rozhoduje komise.
          </p>
        </>
      )}
    </section>
  );
}

// ── Anamnéza a otázka ───────────────────────────────────────────────────────

export function AnamnesisPanel({ defaultOpen = true, empty }: { defaultOpen?: boolean; empty?: React.ReactNode }) {
  const { sources } = useQuickView();
  const brief = sources.brief.data ?? null;
  const section = brief?.sections.find((s) => s.id === 'anamnesis');
  if (sources.brief.loading) {
    return (
      <section aria-labelledby="qv-anamnesis">
        <h3 id="qv-anamnesis" className="mb-1 text-sm font-semibold">Anamnéza</h3>
        <SkeletonRows rows={3} />
      </section>
    );
  }
  if (!section?.items.length) {
    return (
      <section aria-labelledby="qv-anamnesis">
        <h3 id="qv-anamnesis" className="mb-1 text-sm font-semibold">Anamnéza</h3>
        {empty ?? (
          <p className="text-sm text-muted-foreground">
            {brief ? 'Podklad anamnézu neobsahuje.' : 'Zkrácená anamnéza se zobrazí, až vznikne podklad pro komisi.'}
          </p>
        )}
      </section>
    );
  }
  return (
    <AiBlock title="Anamnéza" status={brief?.status === 'confirmed' ? 'confirmed' : 'draft'} defaultOpen={defaultOpen} headingLevel="h3">
      <p className="text-[15px] leading-relaxed">
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

/**
 * Otázka pro MDT: kotva celé diskuse, proto vždy vidět (dole přilepená). V úzkém panelu se dlouhá
 * otázka zkrátí na 3 řádky a rozbalí klikem, aby nezakryla údaje.
 */
export function QuestionStrip({
  className,
  size = 'default',
  clampLines = size === 'default' ? 3 : 0,
}: {
  className?: string;
  size?: 'default' | 'large';
  /** Kolik řádků ukázat, než se otázka rozbalí (0 = celá). */
  clampLines?: 0 | 2 | 3;
}) {
  const { header, sources } = useQuickView();
  const [expanded, setExpanded] = React.useState(false);
  const clamp = clampLines > 0;
  const long = (header.question?.length ?? 0) > (clampLines === 2 ? 110 : 140);
  return (
    <footer className={cn('border-t border-border bg-card px-4 py-3', className)}>
      <h2 className="sr-only">Otázka pro MDT</h2>
      <div className="flex items-start gap-4">
        {sources.session.loading && !header.question ? (
          <Skeleton className="h-6 flex-1" />
        ) : (
          <div className="min-w-0 flex-1">
            <p
              className={cn(
                'font-semibold leading-snug text-balance',
                size === 'large' ? 'text-xl' : 'text-base',
                clamp && long && !expanded && (clampLines === 2 ? 'line-clamp-2' : 'line-clamp-3'),
              )}
            >
              {header.question ?? 'Otázka pro MDT v záznamu chybí.'}
              {header.questionCitation && <Citations ids={[header.questionCitation]} />}
            </p>
            {clamp && long && (
              <button
                type="button"
                onClick={() => setExpanded(!expanded)}
                aria-expanded={expanded}
                className="mt-0.5 rounded-sm text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {expanded ? 'Zkrátit otázku' : 'Celá otázka'}
              </button>
            )}
          </div>
        )}
        {header.diagnosis && (
          <div className="shrink-0 text-right" title={header.diagnosis.text}>
            <p className="text-xs text-muted-foreground">MKN-10</p>
            <p translate="no" className="text-base font-semibold tabular-nums">{header.diagnosis.icd10}</p>
          </div>
        )}
      </div>
    </footer>
  );
}

// ── Kompozice ───────────────────────────────────────────────────────────────

/**
 * Úzký přehled (okno projektoru 420 px, boční panel kalendáře) jako na ukázce z přihlášení (T-514):
 * klíčové údaje ve dvou sloupcích, postupy s jedním rozhodujícím důvodem, pak sbalená anamnéza
 * a šablona; otázka přilepená dole. Rodič určuje výšku (flex).
 */
export function CaseQuickViewNarrow({
  sources,
  caseId,
  titleAs = 'h2',
  className,
  footer,
}: {
  sources: QuickViewSources;
  caseId: number | null;
  titleAs?: 'h1' | 'h2';
  className?: string;
  footer?: React.ReactNode;
}) {
  return (
    <QuickViewRoot sources={sources} caseId={caseId}>
      <article className={cn('flex h-full min-h-0 flex-col bg-background', className)} aria-label="Rychlý přehled případu">
        <header className="flex shrink-0 items-start gap-3 border-b border-border bg-card px-4 py-3.5">
          <QuickIdentity as={titleAs} size="large" icd={false} />
          <QuickMetrics />
        </header>
        <div className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain bg-muted/40">
          <div className="flex flex-col px-4">
            <div className="border-b border-border py-4">
              <KeyFactsList layout="tiles" legend={false} />
            </div>
            <div className="border-b border-border py-1">
              <TreatmentList dense />
            </div>
            <div className="flex flex-col gap-5 py-4">
              <AnamnesisPanel defaultOpen={false} />
              <TemplateSummary />
              <FactLegend />
            </div>
          </div>
        </div>
        <QuestionStrip className="shrink-0 border-t-2 border-t-primary/40" />
        {footer}
      </article>
    </QuickViewRoot>
  );
}

/**
 * Široký přehled (jednání komise, nahoře v detailu): hlavička přes celou šířku, vlevo klíčové údaje
 * a sbalená anamnéza, vpravo všechny postupy. `toolbar` = akce pro pacienta pod hlavičkou.
 */
export function CaseQuickViewWide({
  sources,
  caseId,
  toolbar,
  warningsHref,
  anamnesisEmpty,
  stickyQuestion = true,
  className,
}: {
  sources: QuickViewSources;
  caseId: number | null;
  toolbar?: React.ReactNode;
  warningsHref?: string;
  anamnesisEmpty?: React.ReactNode;
  stickyQuestion?: boolean;
  className?: string;
}) {
  return (
    <QuickViewRoot sources={sources} caseId={caseId}>
      <article className={cn('@container flex min-h-0 flex-col', className)} aria-label="Rychlý přehled případu">
        <header className="flex flex-wrap items-start gap-x-6 gap-y-3 px-1 pb-4">
          <div className="flex min-w-[min(100%,18rem)] flex-1">
            <QuickIdentity size="large" />
          </div>
          <div className="flex items-center gap-5">
            <QuickWarnings href={warningsHref} />
            <QuickMetrics />
          </div>
        </header>
        {toolbar}
        <div className="grid gap-x-10 gap-y-8 py-5 @3xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
          <div className="flex min-w-0 flex-col gap-6">
            <KeyFactsList />
            <TemplateSummary />
            <AnamnesisPanel defaultOpen={false} empty={anamnesisEmpty} />
          </div>
          <div className="min-w-0">
            <TreatmentList />
          </div>
        </div>
        <QuestionStrip
          size="large"
          clampLines={stickyQuestion ? 2 : 0}
          className={cn('rounded-lg border', stickyQuestion && 'lg:sticky lg:bottom-0 lg:z-10 lg:shadow-[0_-12px_24px_-16px_rgb(15_23_42/0.25)]')}
        />
      </article>
    </QuickViewRoot>
  );
}

/**
 * Tělo přehledu bez hlavičky (detail pacienta má vlastní přilepenou hlavičku, NAVRH_UI §8):
 * klíčové údaje a anamnéza vlevo, postupy vpravo, otázka pro MDT dole.
 */
export function CaseQuickViewBody({
  sources,
  caseId,
  anamnesisEmpty,
}: {
  sources: QuickViewSources;
  caseId: number | null;
  anamnesisEmpty?: React.ReactNode;
}) {
  return (
    <QuickViewRoot sources={sources} caseId={caseId}>
      <div className="@container flex flex-col gap-5">
        <QuestionStrip size="large" className="rounded-lg border" />
        <div className="grid gap-x-10 gap-y-8 @3xl:grid-cols-[minmax(0,5fr)_minmax(0,6fr)]">
          <div className="flex min-w-0 flex-col gap-6">
            <KeyFactsList />
            <TemplateSummary />
            <AnamnesisPanel defaultOpen={false} empty={anamnesisEmpty} />
          </div>
          <div className="min-w-0">
            <TreatmentList />
          </div>
        </div>
      </div>
    </QuickViewRoot>
  );
}
