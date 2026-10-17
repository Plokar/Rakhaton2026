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
  ProjectorLayout,
  ProjectorSection,
  CaseTemplate,
  IntakePrefill,
  IntakeWarning,
  Light,
  MdtCase,
  MdtSessionDetail,
  ObservationSeries,
  ProcedureCompatibility,
} from '@/types/mdt';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/shadcn/tooltip';
import { AiBlock } from './AiBlock';
import { CitationProvider, Citations, collectCitations, useCitationOpen } from './citations';
import { CompatibilityLight, LightIcon, LIGHT_META } from './CompatibilityLight';
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
    <div className="flex min-w-15 flex-col items-center rounded-xl border border-border bg-background px-2.5 py-1.5" title={title}>
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

/**
 * Kompaktní identita pro okno projektoru (T-327): kód + TNM na jeden řádek, název diagnózy a board zkrácené
 * na řádek (celé v `title`), počet varování. Pořád D-018: bez jména a RČ, diagnóza + TNM.
 */
function QuickIdentityCompact({ as: Title }: { as: 'h1' | 'h2' }) {
  const { header, sources } = useQuickView();
  const session = sources.session.data;
  const high = header.warnings.filter((w) => w.severity === 'high').length;
  return (
    <div className="min-w-0 flex-1">
      <Title translate="no" className="text-base font-semibold leading-tight tracking-tight">{header.displayName}</Title>
      {sources.session.loading && !header.diagnosis ? (
        <Skeleton className="mt-1.5 h-4 w-40" />
      ) : (
        <>
          <p className="mt-0.5 text-sm leading-snug">
            {header.diagnosis ? <span translate="no" className="font-semibold">{header.diagnosis.icd10}</span> : 'Diagnóza v záznamu chybí'}
            {header.tnm && (
              <>
                {' · '}
                {/* „(TNM 8. vyd.)“ jen v title, aby se TNM vešlo na řádek */}
                <span translate="no" title={header.tnm}>{header.tnm.replace(/\s*\(TNM[^)]*\)\s*$/, '')}</span>
              </>
            )}
          </p>
          {header.diagnosis && (
            <p className="truncate text-xs text-muted-foreground" title={header.diagnosis.text}>{header.diagnosis.text}</p>
          )}
        </>
      )}
      <p className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
        {header.warnings.length > 0 && (
          <span className="inline-flex shrink-0 items-center gap-1 font-medium text-foreground">
            <TriangleAlert className={cn('size-3.5', high ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400')} aria-hidden />
            {header.warnings.length} varování{high ? ` (${high} závažn${high === 1 ? 'é' : 'á'})` : ''}
          </span>
        )}
        {session && (
          <span className="truncate" title={session.title}>
            {header.warnings.length > 0 && '· '}
            {session.title}, {dayLabel(session.date)} {timeLabel(session.date)}
          </span>
        )}
      </p>
    </div>
  );
}

/** Identita, diagnóza + TNM, zasedání. `as` určuje úroveň nadpisu (h1 v samostatném okně). */
export function QuickIdentity({ as: Title = 'h2', size = 'default' }: { as?: 'h1' | 'h2'; size?: 'default' | 'large' | 'compact' }) {
  const { header, sources } = useQuickView();
  const session = sources.session.data;
  if (size === 'compact') return <QuickIdentityCompact as={Title} />;
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
              <span translate="no" className="font-medium text-foreground">{header.diagnosis.icd10}</span> {header.diagnosis.text}
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

export function KeyFactsList({ legend = true }: { legend?: boolean }) {
  const { facts, sources } = useQuickView();
  const [showNormal, setShowNormal] = React.useState(false);
  const groups = orderFacts(facts);
  const loading = sources.intake.loading || sources.observations.loading;

  return (
    <section aria-labelledby="qv-facts">
      <h3 id="qv-facts" className="mb-1 text-sm font-semibold">Klíčové údaje</h3>
      {loading ? (
        <SkeletonRows rows={5} />
      ) : sources.intake.failed ? (
        <p role="alert" className="text-sm text-destructive">Údaje pacienta se nepodařilo načíst. Obnovte stránku (F5).</p>
      ) : facts.length === 0 ? (
        <p className="text-sm text-muted-foreground">Pro pacienta nejsou v IRIS žádné údaje šablony.</p>
      ) : (
        <>
          <ul className="divide-y divide-border/60">
            {[...groups.attention, ...groups.unresolved, ...groups.recorded].map((fact) => (
              <FactRow key={fact.id} fact={fact} />
            ))}
            {showNormal && groups.normal.map((fact) => <FactRow key={fact.id} fact={fact} />)}
          </ul>
          {groups.normal.length > 0 && (
            <button
              type="button"
              onClick={() => setShowNormal(!showNormal)}
              aria-expanded={showNormal}
              className="mt-1 inline-flex items-center gap-1.5 rounded-md py-1 text-[13px] font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <ChevronRight className={cn('size-4 transition-transform motion-reduce:transition-none', showNormal && 'rotate-90')} aria-hidden />
              {showNormal ? 'Skrýt hodnoty v normě' : `V normě (${groups.normal.length})`}
              {!showNormal && (
                <span className="font-normal" translate="no">
                  {groups.normal.slice(0, 5).map((f) => f.abbr).join(', ')}
                  {groups.normal.length > 5 ? '…' : ''}
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

/** Text buňky: „Chybí“ + „Chybí: Deficit DPD“ → stačí „Deficit DPD“ (celé znění zůstává v bublině). */
function factCell(fact: KeyFact) {
  const value = fact.value ?? FACT_META[fact.status].label;
  const cell = value.startsWith(`${fact.abbr}: `) ? value.slice(fact.abbr.length + 2) : value;
  const length = fact.abbr.length + 1 + cell.length;
  // šířka v šestinách řádku (okno projektoru 420 px): třetina, polovina, dvě třetiny, nebo celý řádek
  const units: CellUnits = length <= 13 ? 2 : length <= 22 ? 3 : length <= 32 ? 4 : 6;
  return { value, cell, units };
}

type CellUnits = 2 | 3 | 4 | 6;

const CELL_BASIS: Record<CellUnits, string> = {
  2: 'basis-[calc(50%-1px)] @[22rem]:basis-[calc(33.333%-1px)] @[40rem]:basis-[calc(25%-1px)]',
  3: 'basis-[calc(50%-1px)] @[40rem]:basis-[calc(33.333%-1px)]',
  4: 'basis-full @[22rem]:basis-[calc(66.666%-1px)] @[40rem]:basis-[calc(50%-1px)]',
  6: 'basis-full',
};

/**
 * Seřadí skupinu do řádků po 6 dílech (first-fit), aby krátké hodnoty vyplnily místo vedle delších
 * a v mřížce nezůstaly díry. Balí se jen uvnitř skupiny, takže pořadí podle závažnosti platí dál.
 */
function packFacts(group: KeyFact[], unitsOf: (fact: KeyFact) => CellUnits = (fact) => factCell(fact).units): KeyFact[] {
  const rows: { used: number; facts: KeyFact[] }[] = [];
  for (const fact of group) {
    const units = unitsOf(fact);
    const row = rows.find((r) => r.used + units <= 6);
    if (row) {
      row.facts.push(fact);
      row.used += units;
    } else {
      rows.push({ used: units, facts: [fact] });
    }
  }
  return rows.flatMap((r) => r.facts);
}

/**
 * Pořadí údajů na projektoru (T-332): připnuté v pořadí z `projector_layout.facts`, ostatní za nimi
 * výchozím pořadím (závažné, mimo normu, chybějící, zaznamenané, v normě; balené do řádků).
 */
export function projectorFactOrder(facts: KeyFact[], layout: ProjectorLayout | null | undefined): KeyFact[] {
  const byId = new Map(facts.map((f) => [f.id, f]));
  const pinned = (layout?.facts ?? []).map((id) => byId.get(id)).filter((f): f is KeyFact => Boolean(f));
  const pinnedIds = new Set(pinned.map((f) => f.id));
  const groups = orderFacts(facts.filter((f) => !pinnedIds.has(f.id)));
  return [...pinned, ...[groups.attention, groups.unresolved, groups.recorded, groups.normal].flatMap((group) => packFacts(group))];
}

export const PROJECTOR_BLOCKS: Record<ProjectorSection, string> = {
  anamnesis: 'Anamnéza',
  facts: 'Klíčové údaje',
  template: 'Šablona (úplnost podle diagnózy)',
  treatments: 'Léčebné postupy',
};
const DEFAULT_BLOCKS: ProjectorSection[] = ['anamnesis', 'facts', 'template', 'treatments'];

/** Bloky v okně projektoru (T-330: šablona je jen v rychlém přehledu, na projektoru ne). */
export const PROJECTOR_WINDOW_BLOCKS: ProjectorSection[] = ['anamnesis', 'facts', 'treatments'];

/**
 * Bloky v pořadí z `projector_layout.sections`, chybějící výchozím pořadím za nimi. Šablona, kterou okno
 * projektoru nemá (a dialog ji proto neřadí), zůstává v rychlém přehledu hned za klíčovými údaji.
 */
export function projectorBlockOrder(layout: ProjectorLayout | null | undefined): ProjectorSection[] {
  const order = [...new Set([...(layout?.sections ?? []), ...DEFAULT_BLOCKS.filter((b) => b !== 'template')])];
  if (!order.includes('template')) order.splice(order.indexOf('facts') + 1, 0, 'template');
  return order;
}

/**
 * Hustá mřížka pro projektor (T-326, T-327): buňka = jeden řádek se zkratkou, hodnotou a ikonou stavu. Důvod
 * barvy, datum a plný název jsou v bublině po najetí nebo fokusu; klik otevře zdroj (dohledatelnost, zadání §3.3).
 * Pořadí: závažné, mimo normu, chybějící, zaznamenané, v normě; poslední buňka řádku se roztáhne (žádné díry).
 */
export function KeyFactsGrid() {
  const { facts, sources, item } = useQuickView();
  const open = useCitationOpen();
  const ordered = projectorFactOrder(facts, item?.projector_layout);
  const loading = sources.intake.loading || sources.observations.loading;

  return (
    <section aria-labelledby="qv-facts-grid" className="@container">
      <h3 id="qv-facts-grid" className="mb-1.5 text-sm font-semibold">Klíčové údaje</h3>
      {loading ? (
        <SkeletonRows rows={4} />
      ) : sources.intake.failed ? (
        <p role="alert" className="text-sm text-destructive">Údaje pacienta se nepodařilo načíst. Obnovte okno (F5).</p>
      ) : ordered.length === 0 ? (
        <p className="text-sm text-muted-foreground">Pro pacienta nejsou v IRIS žádné údaje šablony.</p>
      ) : (
        <>
          <ul className="flex flex-wrap gap-px overflow-hidden rounded-lg border border-border bg-border">
            {ordered.map((fact) => {
              const meta = FACT_META[fact.status];
              const { value, cell, units } = factCell(fact);
              const tip = [
                `${fact.label}: ${value}`,
                fact.date ? `ze dne ${formatDate(fact.date)}` : null,
                fact.status !== 'recorded' && fact.status !== 'normal' ? meta.label : null,
                fact.reason,
              ].filter(Boolean).join(' · ');
              const source = fact.citations.find((c) => /^P\d{2}/.test(c)) ?? fact.citations[0];
              return (
                <li key={fact.id} className={cn('min-w-0 grow bg-card', CELL_BASIS[units])}>
                  <Tooltip>
                    <TooltipTrigger
                      render={
                        <button
                          type="button"
                          onClick={() => source && open?.(source)}
                          aria-label={`${fact.label}: ${value}, ${meta.label}${fact.reason ? `. ${fact.reason}` : ''}${source ? '. Otevřít zdroj' : ''}`}
                          className={cn(
                            'flex h-full w-full min-w-0 items-center gap-1.5 px-2 py-1 text-left text-[13px] leading-5 transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                            fact.status === 'critical' && 'bg-red-50/70 dark:bg-red-950/30',
                            fact.status === 'abnormal' && 'bg-amber-50/60 dark:bg-amber-950/25',
                          )}
                        />
                      }
                    >
                      <FactIcon status={fact.status} className="size-3.5 shrink-0" />
                      <span translate="no" className="shrink-0 font-semibold">{fact.abbr}</span>
                      <span className={cn('min-w-0 truncate tabular-nums', fact.status === 'missing' || fact.status === 'pending' ? 'text-muted-foreground' : 'text-foreground')}>
                        {cell}
                      </span>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs text-left leading-snug">{tip}</TooltipContent>
                  </Tooltip>
                </li>
              );
            })}
          </ul>
          <FactLegend className="mt-2" />
        </>
      )}
    </section>
  );
}

/** Jedna věta k semaforu: rozhodující pravidlo zkrácené na ~140 znaků + počet dalších. */
function lightSummary(option: ProcedureCompatibility): string {
  const { compatibility } = option;
  const decisive = compatibility.rules.filter((rule) => rule.status === compatibility.overall);
  const head = decisive[0]?.text ?? compatibility.rules[0]?.text ?? 'Pravidla k tomuto postupu nic nenašla.';
  const short = head.length > 140 ? `${head.slice(0, 137).trimEnd()}…` : head;
  const more = decisive.length > 1 ? ` (+ ${decisive.length - 1} další)` : '';
  return `${LIGHT_META[compatibility.overall].label}: ${short}${more}`;
}

function TreatmentRowCompact({ option }: { option: ProcedureCompatibility }) {
  const open = useCitationOpen();
  const { compatibility } = option;
  const decisive = compatibility.rules.find((rule) => rule.status === compatibility.overall) ?? compatibility.rules[0];
  const source = decisive?.patient_citations[0] ?? decisive?.rule_citation;
  const summary = lightSummary(option);
  const muted = compatibility.overall === 'grey' || compatibility.overall === 'skipped';
  return (
    <li className="flex items-center gap-2 py-1">
      <p className={cn('min-w-0 flex-1 truncate text-[13px] leading-5', muted ? 'text-muted-foreground' : 'font-medium')} title={option.title}>
        {option.title}
      </p>
      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={() => source && open?.(source)}
              aria-label={`${summary}${source ? '. Otevřít zdroj' : ''}`}
              className="shrink-0 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          }
        >
          <CompatibilityLight light={compatibility.overall} />
        </TooltipTrigger>
        <TooltipContent side="left" className="max-w-xs text-left leading-snug">
          <div className="flex flex-col gap-1">
            <p>{summary}</p>
            {decisive && (
              <p className="text-[11px] opacity-80">
                Pravidlo {decisive.rule_citation}{source ? ' · kliknutím otevřete zdroj' : ''}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </li>
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

function TreatmentRow({ option }: { option: ProcedureCompatibility }) {
  const [open, setOpen] = React.useState(false);
  const { compatibility } = option;
  const compact = compatibility.overall === 'grey' || compatibility.overall === 'skipped';
  const decisive = compact ? [] : compatibility.rules.filter((rule) => rule.status === compatibility.overall).slice(0, 2);
  const rest = compatibility.rules.filter((rule) => !decisive.includes(rule));
  return (
    <li className={cn(compact ? 'py-1.5' : 'py-2.5')}>
      <div className="flex items-start gap-2">
        <p className={cn('min-w-0 flex-1 leading-snug', compact ? 'text-[13px] text-muted-foreground' : 'text-sm font-medium')}>
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
        <>
          <button
            type="button"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            className="mt-0.5 inline-flex items-center gap-1 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ChevronRight className={cn('size-3.5 transition-transform motion-reduce:transition-none', open && 'rotate-90')} aria-hidden />
            {compact ? `Proč (${rest.length})` : `Další pravidla (${rest.length})`}
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

/**
 * Všechny postupy v pořadí katalogu (ne podle barvy, aby řazení nepůsobilo jako doporučení).
 * `compact` (projektor): řádek = název + semafor, důvod jen v bublině po najetí na barvu.
 */
export function TreatmentList({ compact = false }: { compact?: boolean }) {
  const { sources } = useQuickView();
  const options = sources.compatibility.data;
  return (
    <section aria-labelledby="qv-treatments">
      <h3 id="qv-treatments" className="mb-1 text-sm font-semibold">
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
            {options.map((option) =>
              compact ? <TreatmentRowCompact key={option.id} option={option} /> : <TreatmentRow key={option.id} option={option} />)}
          </ul>
          <p className={cn('text-xs text-muted-foreground', compact ? 'mt-1' : 'mt-2 leading-relaxed')}>
            {compact
              ? 'Barvu počítají pravidla z guidelines, ne AI; nejde o doporučení.'
              : 'Barvu počítají pravidla z doporučených postupů, ne AI. Ukazuje soulad se stavem pacienta, nejde o doporučení. Rozhoduje komise.'}
          </p>
        </>
      )}
    </section>
  );
}

// ── Anamnéza a otázka ───────────────────────────────────────────────────────

export function AnamnesisPanel({
  defaultOpen = true,
  empty,
  compact = false,
}: {
  defaultOpen?: boolean;
  empty?: React.ReactNode;
  /** Okno projektoru (T-327): bez podkladu jen jeden řádek místo bloku. */
  compact?: boolean;
}) {
  const { sources } = useQuickView();
  const brief = sources.brief.data ?? null;
  const section = brief?.sections.find((s) => s.id === 'anamnesis');
  if (compact && !sources.brief.loading && !section?.items.length) {
    return (
      <p className="text-[13px] text-muted-foreground">
        <span className="font-semibold text-foreground">Anamnéza</span> · {brief ? 'podklad ji neobsahuje' : 'zatím bez podkladu pro komisi'}
      </p>
    );
  }
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
 * Úzký přehled (okno projektoru 420 px, boční panel kalendáře): jeden sloupec, anamnéza nahoře,
 * otázka přilepená dole. Rodič určuje výšku (flex).
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
        <header className="flex shrink-0 items-start gap-3 border-b border-border bg-card px-3 py-2">
          <QuickIdentity as={titleAs} size="compact" />
          <QuickMetrics />
        </header>
        <div className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain">
          <div className="flex flex-col gap-3.5 px-3 py-3">
            <NarrowBlocks />
          </div>
        </div>
        <QuestionStrip className="shrink-0 border-t-2 border-t-primary/40 px-3 py-2" clampLines={2} />
        {footer}
      </article>
    </QuickViewRoot>
  );
}

/** Bloky úzkého panelu v pořadí, které nastavil zadávající lékař nebo předseda (T-332). */
function NarrowBlocks() {
  const { item } = useQuickView();
  const blocks: Record<ProjectorSection, React.ReactNode> = {
    anamnesis: <AnamnesisPanel compact />,
    facts: <KeyFactsGrid />,
    template: <TemplateSummary />,
    treatments: <TreatmentList compact />,
  };
  return (
    <>
      {projectorBlockOrder(item?.projector_layout).map((id) => (
        <React.Fragment key={id}>{blocks[id]}</React.Fragment>
      ))}
    </>
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

// ── Okno pro projektor (T-330, schválený náhled) ────────────────────────────

/** Akcent značky (korálová) jen pro kód MKN-10 v okně projektoru; semafor a závažnost mají vlastní barvy (D-017). */
const PJ_ACCENT = 'bg-[#C84646]/10 text-[#C84646] dark:bg-[#F28B82]/15 dark:text-[#F28B82]';
const PJ_CARD = 'rounded-[20px] bg-card p-4';

/** Štítek semaforu: text nese význam sám, barva ho jen zvýrazní (POZADAVKY §3.4). */
const PJ_PILL: Record<Light, string> = {
  green: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-400/15 dark:text-emerald-200',
  orange: 'bg-amber-100 text-amber-900 dark:bg-amber-400/15 dark:text-amber-200',
  red: 'bg-red-700 text-white dark:bg-red-500',
  grey: 'bg-muted text-slate-700 dark:text-slate-300',
  skipped: 'text-muted-foreground ring-1 ring-inset ring-border',
};

const PJ_GROUPS = [
  { key: 'attention', title: 'Pozornost' },
  { key: 'unresolved', title: 'Chybí nebo je staré' },
  { key: 'recorded', title: 'Zaznamenáno' },
  { key: 'normal', title: 'V normě' },
] as const;

/**
 * Šířka buňky v okně projektoru: závažný údaj má celý řádek (podbarvení přes celou šířku); buňky mají větší
 * odsazení než v mřížce úzkého přehledu, proto se na třetinu řádku vejde jen kratší text („Leu 5,2 10⁹/l“ už ne).
 */
function pjUnits(fact: KeyFact): CellUnits {
  if (fact.status === 'critical') return 6;
  const { cell } = factCell(fact);
  const length = fact.abbr.length + 1 + cell.length;
  return length <= 11 ? 2 : length <= 22 ? 3 : length <= 32 ? 4 : 6;
}

function ProjectorFactCell({ fact }: { fact: KeyFact }) {
  const open = useCitationOpen();
  const meta = FACT_META[fact.status];
  const { value, cell } = factCell(fact);
  const critical = fact.status === 'critical';
  const shown = critical && fact.reason ? `${cell} · ${fact.reason}` : cell;
  const tip = [
    `${fact.label}: ${value}`,
    fact.date ? `ze dne ${formatDate(fact.date)}` : null,
    fact.status !== 'recorded' && fact.status !== 'normal' ? meta.label : null,
    fact.reason,
  ].filter(Boolean).join(' · ');
  const source = fact.citations.find((c) => /^P\d{2}/.test(c)) ?? fact.citations[0];
  return (
    <li className={cn('min-w-0 grow bg-card', CELL_BASIS[pjUnits(fact)])}>
      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={() => source && open?.(source)}
              aria-label={`${fact.label}: ${value}, ${meta.label}${fact.reason ? `. ${fact.reason}` : ''}${source ? '. Otevřít zdroj' : ''}`}
              className={cn(
                'flex h-full w-full min-w-0 items-center gap-1.5 px-2.5 py-1.5 text-left text-[13px] leading-5 transition-colors hover:bg-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                critical && 'bg-red-100/80 text-red-950 hover:bg-red-100 dark:bg-red-950/50 dark:text-red-100',
                fact.status === 'abnormal' && 'bg-amber-50 dark:bg-amber-950/30',
              )}
            />
          }
        >
          <FactIcon status={fact.status} className="size-3.5 shrink-0" />
          <span translate="no" className="shrink-0 font-semibold">{fact.abbr}</span>
          <span className={cn('min-w-0 truncate tabular-nums', (fact.status === 'missing' || fact.status === 'pending') && 'text-muted-foreground')}>
            {shown}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-left leading-snug">{tip}</TooltipContent>
      </Tooltip>
    </li>
  );
}

function ProjectorHeader({ as: Title }: { as: 'h1' | 'h2' }) {
  const { header, sources, ecogWarnings } = useQuickView();
  const high = header.warnings.filter((w) => w.severity === 'high').length;
  const psTitle = header.psDiffers
    ? ecogWarnings.map((w) => w.title).join(' · ') || 'PS lékaře a pacienta se liší o 1 a víc (OBC-1.3)'
    : 'Performance status (ECOG) podle lékaře, pod ním podle pacienta (PROMs)';
  return (
    <header className={cn(PJ_CARD, 'flex shrink-0 items-start gap-3')}>
      <div className="min-w-0 flex-1">
        <Title translate="no" className="text-[19px] font-semibold leading-tight tracking-tight">{header.displayName}</Title>
        {sources.session.loading && !header.diagnosis ? (
          <Skeleton className="mt-2 h-4 w-40" />
        ) : (
          <>
            <p className="mt-1 text-sm leading-snug">
              {header.diagnosis ? <span translate="no" className="font-semibold">{header.diagnosis.icd10}</span> : 'Diagnóza v záznamu chybí'}
              {header.tnm && (
                <>
                  {' · '}
                  <span translate="no" title={header.tnm}>{header.tnm.replace(/\s*\(TNM[^)]*\)\s*$/, '')}</span>
                </>
              )}
            </p>
            {header.diagnosis && (
              <p className="mt-0.5 truncate text-xs text-muted-foreground" title={header.diagnosis.text}>{header.diagnosis.text}</p>
            )}
          </>
        )}
        {header.warnings.length > 0 && (
          <p className={cn('mt-2 flex items-center gap-1.5 text-[13px] font-semibold', high ? 'text-red-700 dark:text-red-400' : 'text-amber-800 dark:text-amber-300')}>
            <TriangleAlert className="size-3.5 shrink-0" aria-hidden />
            {header.warnings.length} varování{high ? `, ${high} závažn${high === 1 ? 'é' : 'á'}` : ''}
          </p>
        )}
      </div>
      <dl className="flex shrink-0 gap-1.5">
        <div className="w-16 rounded-[14px] bg-muted/70 py-1.5 text-center" title={psTitle}>
          <dt className="text-[11px] font-semibold text-muted-foreground">PS</dt>
          <dd className="text-[28px] font-medium leading-8 tabular-nums">{header.physicianPs ?? '–'}</dd>
          <dd className={cn('text-[11px] tabular-nums', header.psDiffers ? 'font-semibold text-amber-800 dark:text-amber-300' : 'text-muted-foreground')}>
            pac. {header.patientPs ?? '–'}
            {header.psDiffers && <span className="sr-only">, liší se od lékaře</span>}
          </dd>
        </div>
        <div className="w-16 rounded-[14px] bg-muted/70 py-1.5 text-center" title={`Léčebný záměr: ${header.intentSource}`}>
          <dt className="text-[11px] font-semibold text-muted-foreground">C/P</dt>
          <dd className="text-[28px] font-medium leading-8">{header.intent ?? '–'}</dd>
          <dd className="text-[11px] text-muted-foreground">{header.intent ? INTENT_LABEL[header.intent] : 'nezvoleno'}</dd>
        </div>
      </dl>
    </header>
  );
}

function ProjectorFacts() {
  const { facts, sources, item } = useQuickView();
  // T-332: údaje v pořadí lékaře jsou nahoře jako vlastní skupina, ostatní ve výchozích skupinách
  const byId = new Map(facts.map((f) => [f.id, f]));
  const pinned = (item?.projector_layout?.facts ?? []).map((id) => byId.get(id)).filter((f): f is KeyFact => Boolean(f));
  const pinnedIds = new Set(pinned.map((f) => f.id));
  const groups = { pinned, ...orderFacts(facts.filter((f) => !pinnedIds.has(f.id))) };
  const loading = sources.intake.loading || sources.observations.loading;
  return (
    <section aria-labelledby="pj-facts" className={cn(PJ_CARD, '@container flex flex-col gap-2')}>
      <h2 id="pj-facts" className="mb-1 text-base font-semibold">Klíčové údaje</h2>
      {loading ? (
        <SkeletonRows rows={5} />
      ) : sources.intake.failed ? (
        <p role="alert" className="text-sm text-destructive">Údaje pacienta se nepodařilo načíst. Obnovte okno (F5).</p>
      ) : facts.length === 0 ? (
        <p className="text-sm text-muted-foreground">Pro pacienta nejsou v IRIS žádné údaje šablony.</p>
      ) : (
        [{ key: 'pinned' as const, title: 'Pořadí lékaře' }, ...PJ_GROUPS].map(({ key, title }) =>
          groups[key].length ? (
            <div key={key}>
              <h3 className="mx-0.5 mb-1.5 flex justify-between text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                <span>{title}</span>
                <span className="tabular-nums">{groups[key].length}</span>
              </h3>
              <ul className="flex flex-wrap gap-px overflow-hidden rounded-xl border border-border bg-border">
                {(key === 'pinned' ? groups.pinned : packFacts(groups[key], pjUnits)).map((fact) => <ProjectorFactCell key={fact.id} fact={fact} />)}
              </ul>
            </div>
          ) : null,
        )
      )}
    </section>
  );
}

function ProjectorTreatmentRow({ option }: { option: ProcedureCompatibility }) {
  const open = useCitationOpen();
  const light = option.compatibility.overall;
  const decisive = option.compatibility.rules.find((rule) => rule.status === light) ?? option.compatibility.rules[0];
  const source = decisive?.patient_citations[0] ?? decisive?.rule_citation;
  const summary = lightSummary(option);
  const muted = light === 'grey' || light === 'skipped';
  return (
    <li className={cn('flex items-center gap-2.5 rounded-xl px-2.5 py-2', light === 'red' && 'bg-red-100/80 dark:bg-red-950/50')}>
      <p
        className={cn(
          'min-w-0 flex-1 truncate text-[13px] font-medium',
          muted && 'text-muted-foreground',
          light === 'red' && 'text-red-900 dark:text-red-100',
        )}
        title={option.title}
      >
        {option.title}
      </p>
      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={() => source && open?.(source)}
              aria-label={`${summary}${source ? '. Otevřít zdroj' : ''}`}
              className={cn(
                'shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                PJ_PILL[light],
              )}
            />
          }
        >
          {LIGHT_META[light].label}
        </TooltipTrigger>
        <TooltipContent side="left" className="max-w-xs text-left leading-snug">
          <div className="flex flex-col gap-1">
            <p>{summary}</p>
            {decisive && (
              <p className="text-[11px] opacity-80">
                Pravidlo {decisive.rule_citation}{source ? ' · kliknutím otevřete zdroj' : ''}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </li>
  );
}

function ProjectorTreatments() {
  const { sources } = useQuickView();
  const options = sources.compatibility.data;
  return (
    <section aria-labelledby="pj-treatments" className={cn(PJ_CARD, 'flex flex-col')}>
      <h2 id="pj-treatments" className="mb-2 text-base font-semibold">
        Léčebné postupy{options?.length ? <span className="font-normal text-muted-foreground"> ({options.length})</span> : null}
      </h2>
      {sources.compatibility.loading ? (
        <SkeletonRows rows={4} />
      ) : sources.compatibility.failed ? (
        <p role="alert" className="text-sm text-destructive">Soulad postupů se nepodařilo načíst. Obnovte okno (F5).</p>
      ) : !options?.length ? (
        <p className="text-sm text-muted-foreground">Pro diagnózu nejsou v katalogu žádné postupy.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-0.5">
            {options.map((option) => <ProjectorTreatmentRow key={option.id} option={option} />)}
          </ul>
          <p className="mx-0.5 mt-2 text-[11px] text-muted-foreground">
            Barvu počítají pravidla z guidelines, ne AI. Důvod se ukáže po najetí na barvu.
          </p>
        </>
      )}
    </section>
  );
}

function ProjectorQuestion() {
  const { header, sources } = useQuickView();
  const [expanded, setExpanded] = React.useState(false);
  return (
    <footer className={cn(PJ_CARD, 'flex shrink-0 items-start gap-3')}>
      <div className="min-w-0 flex-1">
        <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Otázka pro MDT</h2>
        {sources.session.loading && !header.question ? (
          <Skeleton className="h-5 w-full" />
        ) : (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
            title={expanded ? 'Zkrátit otázku' : 'Celá otázka'}
            className="block w-full rounded-sm text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className={cn('block text-base font-semibold leading-snug text-balance', !expanded && 'line-clamp-2')}>
              {header.question ?? 'Otázka pro MDT v záznamu chybí.'}
            </span>
          </button>
        )}
        {header.questionCitation && <Citations ids={[header.questionCitation]} className="mt-1" />}
      </div>
      {header.diagnosis && (
        <div className={cn('shrink-0 rounded-[14px] px-2.5 py-1.5 text-center', PJ_ACCENT)} title={header.diagnosis.text}>
          <p className="text-[11px] font-semibold text-muted-foreground">MKN-10</p>
          <p translate="no" className="text-base font-bold tabular-nums">{header.diagnosis.icd10}</p>
        </div>
      )}
    </footer>
  );
}

/** Anamnéza jen když ji podklad má; prázdný blok okno pro projektor nezabírá. */
function ProjectorAnamnesis() {
  const { sources } = useQuickView();
  const section = sources.brief.data?.sections.find((s) => s.id === 'anamnesis');
  if (!section?.items.length) return null;
  return (
    <div className={PJ_CARD}>
      <AnamnesisPanel defaultOpen={false} />
    </div>
  );
}

/** Bloky okna projektoru v pořadí, které nastavil zadávající lékař nebo předseda (T-332). */
function ProjectorBlocks() {
  const { item } = useQuickView();
  const blocks: Partial<Record<ProjectorSection, React.ReactNode>> = {
    anamnesis: <ProjectorAnamnesis />,
    facts: <ProjectorFacts />,
    treatments: <ProjectorTreatments />,
  };
  return (
    <div className="flex flex-col gap-3">
      {projectorBlockOrder(item?.projector_layout).map((id) => (
        <React.Fragment key={id}>{blocks[id]}</React.Fragment>
      ))}
    </div>
  );
}

/**
 * Okno pro projektor (T-330, podle schváleného náhledu): šedé pozadí s bílými kartami, hlavička a otázka
 * pro MDT vždy vidět, mezi nimi anamnéza (když je), klíčové údaje ve skupinách a postupy se semaforem.
 * Závažný údaj a postup „vylučuje“ jsou podbarvené přes celý řádek.
 */
export function CaseQuickViewProjector({
  sources,
  caseId,
  titleAs = 'h1',
  className,
}: {
  sources: QuickViewSources;
  caseId: number | null;
  titleAs?: 'h1' | 'h2';
  className?: string;
}) {
  return (
    <QuickViewRoot sources={sources} caseId={caseId}>
      <article className={cn('flex h-full min-h-0 flex-col gap-3 bg-muted p-3', className)} aria-label="Přehled případu pro projektor">
        <ProjectorHeader as={titleAs} />
        <div className="relative -mx-3 min-h-0 flex-1 overflow-y-auto overscroll-contain px-3">
          <ProjectorBlocks />
        </div>
        <ProjectorQuestion />
      </article>
    </QuickViewRoot>
  );
}
