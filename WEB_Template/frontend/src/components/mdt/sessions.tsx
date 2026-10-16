'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  ArrowRightLeft,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  Clock,
  Eye,
  FileText,
  HelpCircle,
  LoaderCircle,
  NotebookPen,
  Scale,
  Stethoscope,
  UserRound,
} from 'lucide-react';
import { ApiError } from '@/lib/api';
import { briefP03 } from '@/lib/fixtures';
import { mdtApi, type StoredBrief } from '@/lib/mdt-api';
import { cn } from '@/lib/utils';
import type { EvidenceId, IntakePrefill, MdtCase, MdtSession, MdtSessionListItem } from '@/types/mdt';
import { BriefWindowLink } from './BriefWindowLink';
import { CitationProvider, Citations, collectCitations } from './citations';
import { ClaimList } from './ClaimList';
import { CompatibilityLight } from './CompatibilityLight';
import { apiDataSource, fixtureDataSource } from './data-source';
import { EcogDifference, EcogTiles } from './EcogCompare';
import { formatDate } from './format';
import { ReadinessBadge } from './ReadinessBadge';
import { SourceDrawer } from './SourceDrawer';

export const SESSION_STATUS: Record<MdtSession['status'], string> = {
  planned: 'Plánováno',
  in_progress: 'Probíhá',
  closed: 'Uzavřeno',
};

const SESSION_STATUS_BADGE: Record<MdtSession['status'], string> = {
  planned: 'border-teal-700/35 bg-teal-500/10 text-teal-900 dark:border-teal-400/40 dark:bg-teal-400/15 dark:text-teal-200',
  in_progress: 'border-emerald-700/40 bg-emerald-500/15 text-emerald-950 dark:border-emerald-400/40 dark:bg-emerald-500/20 dark:text-emerald-200',
  closed: 'border-slate-400/50 bg-slate-500/10 text-slate-700 dark:border-slate-500/50 dark:text-slate-300',
};

export const CASE_STATUS: Record<MdtCase['status'], string> = {
  nominated: 'Nominován',
  ready: 'Připraven',
  in_discussion: 'Projednává se',
  decided: 'Rozhodnuto',
  confirmed: 'Potvrzeno',
  returned: 'Vrácen k doplnění',
};

const CASE_STATUS_BADGE: Record<MdtCase['status'], string> = {
  nominated: 'border-slate-400/60 bg-slate-500/10 text-slate-800 dark:border-slate-500/50 dark:text-slate-200',
  ready: 'border-teal-700/40 bg-teal-500/10 text-teal-950 dark:border-teal-400/40 dark:bg-teal-400/15 dark:text-teal-200',
  in_discussion: 'border-amber-600/50 bg-amber-500/15 text-amber-950 dark:border-amber-400/50 dark:bg-amber-500/20 dark:text-amber-200',
  decided: 'border-sky-700/40 bg-sky-500/10 text-sky-950 dark:border-sky-400/40 dark:bg-sky-500/15 dark:text-sky-200',
  confirmed: 'border-emerald-700/45 bg-emerald-500/15 text-emerald-950 dark:border-emerald-400/45 dark:bg-emerald-500/20 dark:text-emerald-200',
  returned: 'border-red-600/60 bg-red-500/15 text-red-950 dark:border-red-400/60 dark:bg-red-500/20 dark:text-red-200',
};

/** Boardy seřazené od nejbližšího termínu. */
export function sortSessions<T extends MdtSession>(sessions: T[]): T[] {
  return [...sessions].sort((a, b) => a.date.localeCompare(b.date));
}

/** Board = zasedání MDT (FR-P1): termín, komise, předseda a zařazení pacienti. */
export function SessionCard({ session }: { session: MdtSessionListItem }) {
  return (
    <Link
      href={`/dashboard/mdt/${session.id}`}
      className="group flex items-start gap-4 rounded-xl border border-border bg-card p-4 shadow-xs transition hover:border-primary/60 hover:bg-muted/30"
    >
      <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
        <CalendarDays className="h-5 w-5" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="text-base font-bold tracking-tight text-foreground group-hover:text-primary transition-colors">
            {session.title}
          </p>
          <span
            className={cn(
              'rounded-md border px-2 py-0.5 text-[11px] font-bold tracking-wide',
              SESSION_STATUS_BADGE[session.status],
            )}
          >
            {SESSION_STATUS[session.status]}
          </span>
        </div>
        <p className="mt-1 text-xs font-medium text-muted-foreground">
          <span className="font-semibold text-foreground">{formatDate(session.date)}</span>
          {session.chair && <> · předseda {session.chair.name}</>}
        </p>
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          {session.patients.length === 0 ? (
            <span className="text-xs text-muted-foreground">Zatím bez zařazených pacientů</span>
          ) : (
            <>
              <span className="text-[11px] font-semibold text-muted-foreground mr-0.5">
                Pacienti ({session.patients.length}):
              </span>
              {session.patients.map((pid) => (
                <span
                  key={pid}
                  className="rounded-md border border-border bg-background px-2 py-0.5 font-mono text-xs font-bold text-foreground shadow-2xs"
                >
                  {pid}
                </span>
              ))}
            </>
          )}
        </div>
      </div>
      <ChevronRight
        className="mt-3 h-5 w-5 shrink-0 text-muted-foreground transition group-hover:translate-x-0.5 group-hover:text-primary"
        aria-hidden
      />
    </Link>
  );
}

/**
 * Případ v agendě zasedání: 30s klinický přehled přímo na kartě pacienta na boardu (diagnóza, MKN-10,
 * ECOG, záměr C/P, celá otázka pro MDT) + rozbalovací 30s Rychlý náhled podkladu přímo v agendě.
 */
export function AgendaItem({
  item,
  moveTargets = [],
  onMove,
}: {
  item: MdtCase;
  moveTargets?: MdtSession[];
  onMove?: (targetSessionId: number) => Promise<void>;
}) {
  const patient = item.patient;
  const [previewOpen, setPreviewOpen] = React.useState(false);
  const questionText = item.question ?? patient?.mdt_question;

  return (
    <li className="overflow-hidden rounded-xl border border-border bg-card shadow-xs transition hover:border-border/90">
      {/* Horní identifikační lišta případu */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/40 px-4 py-2.5">
        <div className="flex flex-wrap items-center gap-2.5">
          <span
            className="flex h-7 min-w-7 items-center justify-center rounded-md border border-border bg-background px-2 font-mono text-xs font-extrabold text-foreground shadow-2xs"
            title="Pořadí v agendě"
          >
            #{item.order ?? '–'}
          </span>
          <h3 className="text-base font-extrabold tracking-tight text-foreground sm:text-lg">
            {patient?.display_name ?? item.patient_id}
          </h3>
          <span
            className={cn(
              'rounded-md border px-2.5 py-0.5 text-xs font-bold tracking-wide',
              CASE_STATUS_BADGE[item.status],
            )}
          >
            {CASE_STATUS[item.status]}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {item.id != null && <ReadinessBadge caseId={item.id} />}
          {item.imaging_recent_checked && (
            <span className="rounded-md border border-emerald-600/30 bg-emerald-500/10 px-2 py-0.5 text-[11px] font-semibold text-emerald-900 dark:text-emerald-200">
              Snímek &lt; 3 měs.
            </span>
          )}
          {item.skipped_fields.length > 0 && (
            <span className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-[11px] font-semibold text-amber-900 dark:text-amber-200">
              Přeskočeno: {item.skipped_fields.length}
            </span>
          )}
          {item.created_by && (
            <span className="inline-flex items-center gap-1 font-medium">
              <UserRound className="h-3.5 w-3.5" aria-hidden /> zařadil {item.created_by.name}
            </span>
          )}
        </div>
      </div>

      {/* 30s klinické jádro na boardu: Diagnóza + ECOG + Záměr + Otázka pro MDT */}
      <div className="space-y-3 p-4">
        <div className="grid gap-2.5 sm:grid-cols-12">
          {/* Hlavní diagnóza */}
          <div className="flex flex-col justify-between rounded-lg border border-border bg-background/70 px-3.5 py-2.5 sm:col-span-7">
            <span className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              <Stethoscope className="h-3.5 w-3.5 text-primary" aria-hidden /> Hlavní diagnóza
            </span>
            {patient?.diagnosis ? (
              <div className="mt-1 flex flex-wrap items-baseline gap-2">
                <span className="text-sm font-bold text-foreground sm:text-base">{patient.diagnosis.text}</span>
                <span className="rounded border border-primary/30 bg-primary/10 px-1.5 py-0.5 font-mono text-xs font-bold text-primary">
                  {patient.diagnosis.icd10}
                </span>
              </div>
            ) : (
              <span className="mt-1 text-sm text-muted-foreground">Diagnóza v přehledu neuvedena</span>
            )}
          </div>

          {/* ECOG stav */}
          <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-background/70 px-3.5 py-2.5 sm:col-span-2 sm:flex-col sm:items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">ECOG</span>
            <div className="flex items-baseline gap-1.5">
              <span className="font-mono text-2xl font-black leading-none text-foreground tabular-nums">
                {item.ecog !== null ? item.ecog : '–'}
              </span>
              <span className="text-[11px] font-medium text-muted-foreground">lékař</span>
            </div>
          </div>

          {/* Záměr léčby */}
          <div className="flex items-center justify-between gap-2 rounded-lg border border-border bg-background/70 px-3.5 py-2.5 sm:col-span-3 sm:flex-col sm:items-start">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Záměr léčby</span>
            {item.intent ? (
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-2xl font-black leading-none text-primary">{item.intent}</span>
                <span className="text-xs font-bold text-foreground">
                  {item.intent === 'C' ? 'Kurativní' : 'Paliativní'}
                </span>
              </div>
            ) : (
              <span className="text-xs font-semibold text-muted-foreground">Neurčen</span>
            )}
          </div>
        </div>

        {/* Otázka pro MDT — celá, bez oříznutí */}
        {questionText && (
          <div className="rounded-lg border border-primary/25 border-l-4 border-l-primary bg-primary/[0.05] px-3.5 py-2.5">
            <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-primary">
              <HelpCircle className="h-3.5 w-3.5" aria-hidden /> Otázka pro MDT komisi
            </p>
            <p className="mt-1 text-sm font-semibold leading-snug text-foreground sm:text-base">{questionText}</p>
          </div>
        )}

        {/* Akční lišta případu na boardu */}
        {item.id !== undefined && (
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => setPreviewOpen((v) => !v)}
                aria-expanded={previewOpen}
                className={cn(
                  'inline-flex h-9 items-center gap-1.5 rounded-lg border px-3 text-xs font-bold transition shadow-2xs',
                  previewOpen
                    ? 'border-primary bg-primary/15 text-primary'
                    : 'border-primary/40 bg-primary/5 text-primary hover:bg-primary/15',
                )}
              >
                <Eye className="h-3.5 w-3.5" aria-hidden />
                30s Rychlý náhled
                <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', previewOpen && 'rotate-180')} aria-hidden />
              </button>

              <Link
                href={`/dashboard/cases/${item.id}`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground shadow-2xs hover:bg-primary/90"
              >
                <FileText className="h-3.5 w-3.5" aria-hidden /> Otevřít podklad
              </Link>

              <BriefWindowLink
                caseId={item.id}
                className="h-9 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground hover:bg-accent"
              />

              <Link
                href={`/dashboard/cases/${item.id}/record`}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground hover:bg-accent"
              >
                <NotebookPen className="h-3.5 w-3.5" aria-hidden /> Závěr komise
              </Link>
            </div>

            {onMove && moveTargets.length > 0 && <MoveCase targets={moveTargets} onMove={onMove} />}
          </div>
        )}
      </div>

      {/* Rozbalovací 30s Rychlý náhled pacienta přímo na boardu */}
      {previewOpen && item.id !== undefined && (
        <BoardCasePreview caseId={String(item.id)} patientId={item.patient_id} />
      )}
    </li>
  );
}

type PreviewLoaded = {
  key: string;
  brief?: StoredBrief;
  intake?: IntakePrefill;
  usedFixture?: boolean;
  error?: string;
};

/**
 * 30s Rychlý náhled pacienta přímo v agendě boardu:
 * Načte vygenerovaný podklad (nebo živá data z IRIS přes intake / fixture P03) a ukáže
 * TNM + stádium, srovnání ECOG lékař vs. pacient, varovné signály, 3–5 bodů souhrnu a semafor léčby.
 */
function BoardCasePreview({ caseId, patientId }: { caseId: string; patientId: string }) {
  const key = `${caseId}:${patientId}`;
  const [loaded, setLoaded] = React.useState<PreviewLoaded | null>(null);
  const [openCitationId, setOpenCitationId] = React.useState<EvidenceId | null>(null);
  const closeDrawer = React.useCallback(() => setOpenCitationId(null), []);

  React.useEffect(() => {
    let cancelled = false;

    mdtApi
      .getBrief(caseId)
      .then((b) => {
        if (!cancelled) {
          setLoaded({ key, brief: b });
        }
      })
      .catch(async (err: unknown) => {
        if (cancelled) return;
        // Pokud podklad ještě není vygenerován (404), načteme živá 30s data pacienta z IRIS přes getIntake
        if (err instanceof ApiError && err.status === 404) {
          try {
            const prefill = await mdtApi.getIntake(patientId);
            if (!cancelled) {
              setLoaded({ key, intake: prefill });
            }
            return;
          } catch {
            // Pokračujeme na fallback níže
          }
        }
        // Fallback na P03 fixture při demo / offline režimu
        if (patientId === 'P03') {
          setLoaded({ key, brief: briefP03, usedFixture: true });
          return;
        }
        setLoaded({
          key,
          error: err instanceof Error ? err.message : 'Rychlý náhled se nepodařilo načíst.',
        });
      });

    return () => {
      cancelled = true;
    };
  }, [caseId, key, patientId]);

  const current = loaded?.key === key ? loaded : null;
  const brief = current?.brief ?? null;
  const intake = current?.intake ?? null;
  const citationOrder = React.useMemo(() => (brief ? collectCitations(brief) : []), [brief]);
  const dataSource = current?.usedFixture ? fixtureDataSource : apiDataSource;
  const summarySection = brief?.sections.find((s) => s.id === 'summary');
  const treatmentOptions = brief?.decision_support?.treatment_options ?? [];

  return (
    <div className="border-t border-border bg-muted/25 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <span className="inline-flex items-center gap-1.5 text-xs font-extrabold uppercase tracking-wider text-primary">
          <Clock className="h-3.5 w-3.5" aria-hidden /> 30s přehled pacienta na boardu
        </span>
        <span className="text-[11px] text-muted-foreground">
          Kliknutím na citaci <span className="font-mono font-bold text-primary">[1]</span> zobrazíte zdrojový záznam
        </span>
      </div>

      {!current && (
        <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
          <LoaderCircle className="h-4 w-4 animate-spin text-primary" aria-hidden />
          Načítám 30s klinický přehled pacienta…
        </div>
      )}

      {current?.error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
          {current.error}
        </p>
      )}

      {/* Varianta A: Plný vygenerovaný podklad (Brief) */}
      {brief && (
        <CitationProvider order={citationOrder} activeId={openCitationId} onOpen={setOpenCitationId}>
          <div className="space-y-3">
            {/* 1. TNM + Stage + ECOG Lékař vs. Pacient */}
            <div className="grid gap-3 lg:grid-cols-12">
              <div className="space-y-2 rounded-lg border border-border bg-card p-3 lg:col-span-6">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  TNM klasifikace, stádium a komorbidity
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {brief.header.tnm?.stage && (
                    <span className="rounded-md border border-primary/30 bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">
                      Stádium {brief.header.tnm.stage}
                    </span>
                  )}
                  {brief.header.tnm ? (
                    <span className="rounded-md border border-border bg-muted px-2 py-0.5 font-mono text-xs font-bold text-foreground">
                      {brief.header.tnm.text}
                      <Citations ids={[brief.header.tnm.citation]} />
                    </span>
                  ) : (
                    <span className="rounded-md border border-amber-500/40 bg-amber-500/10 px-2 py-0.5 text-xs font-semibold text-amber-900 dark:text-amber-200">
                      TNM v dokumentaci chybí
                    </span>
                  )}
                </div>
                {brief.header.comorbidities.length > 0 && (
                  <p className="text-xs leading-relaxed text-muted-foreground">
                    <span className="font-semibold text-foreground">Komorbidity: </span>
                    {brief.header.comorbidities.map((c, idx) => (
                      <React.Fragment key={`${c.citation}-${c.text}`}>
                        {idx > 0 && ' · '}
                        <span>{c.text}</span>
                        <Citations ids={[c.citation]} />
                      </React.Fragment>
                    ))}
                  </p>
                )}
              </div>

              <div className="space-y-2 lg:col-span-6">
                <div className="grid grid-cols-2 gap-2.5">
                  <EcogTiles ecog={brief.header.ecog} />
                </div>
                <EcogDifference ecog={brief.header.ecog} />
              </div>
            </div>

            {/* 2. Varovné signály (Red Flags) a upozornění */}
            {(brief.red_flags.length > 0 || brief.header.alerts.length > 0) && (
              <div className="rounded-lg border border-amber-500/40 bg-amber-500/[0.06] p-3">
                <p className="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-amber-900 dark:text-amber-200">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" aria-hidden />
                  Varovné signály a rizika ({brief.red_flags.length + brief.header.alerts.length})
                </p>
                <ul className="grid gap-1.5 sm:grid-cols-2">
                  {brief.header.alerts.map((a) => (
                    <li
                      key={a.id}
                      className="rounded-md border border-border bg-card px-2.5 py-1.5 text-xs text-foreground"
                    >
                      <span>{a.text}</span>
                      <Citations ids={a.citations} />
                    </li>
                  ))}
                  {brief.red_flags.map((rf) => (
                    <li
                      key={rf.id}
                      className={cn(
                        'rounded-md border border-border border-l-4 bg-card px-2.5 py-1.5 text-xs text-foreground',
                        rf.severity === 'high'
                          ? 'border-l-red-600'
                          : rf.severity === 'moderate'
                            ? 'border-l-amber-500'
                            : 'border-l-slate-400',
                      )}
                    >
                      <span className="font-bold">{rf.title}: </span>
                      <span>{rf.description}</span>
                      <Citations ids={rf.citations} />
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* 3. Souhrn případu (3–5 vět) + Semafor možností léčby vedle sebe */}
            <div className="grid gap-3 lg:grid-cols-12">
              <div className="rounded-lg border border-border bg-card p-3 lg:col-span-7">
                <p className="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  <Activity className="h-3.5 w-3.5 text-primary" aria-hidden /> Souhrn případu ({summarySection?.items.length ?? 0} bodů)
                </p>
                {summarySection ? (
                  <ClaimList claims={summarySection.items} hideUnverified={brief.config.hide_unverified} />
                ) : (
                  <p className="text-xs text-muted-foreground">Souhrn není v konfiguraci zapnutý.</p>
                )}
              </div>

              <div className="rounded-lg border border-border bg-card p-3 lg:col-span-5">
                <p className="mb-2 flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  <Scale className="h-3.5 w-3.5 text-primary" aria-hidden /> Možnosti léčby (semafor souladu)
                </p>
                {treatmentOptions.length > 0 ? (
                  <ul className="space-y-2">
                    {treatmentOptions.map((opt) => (
                      <li
                        key={opt.id}
                        className="flex flex-col justify-between gap-1.5 rounded-md border border-border bg-background/60 p-2 text-xs"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="font-semibold text-foreground">
                            {opt.title}
                            <Citations ids={opt.guideline_citations} />
                          </span>
                          <CompatibilityLight light={opt.compatibility.overall} className="shrink-0" />
                        </div>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-muted-foreground">Možnosti léčby nejsou vyhodnoceny.</p>
                )}
              </div>
            </div>
          </div>

          <SourceDrawer evidenceId={openCitationId} loadSource={dataSource.loadSource} onClose={closeDrawer} />
        </CitationProvider>
      )}

      {/* Varianta B: Podklad ještě nebyl vygenerován -> živé údaje z IRIS přes intake */}
      {!brief && intake && (
        <CitationProvider order={[]} activeId={openCitationId} onOpen={setOpenCitationId}>
          <div className="space-y-3">
            <div className="rounded-lg border border-border bg-card p-3">
              <p className="mb-2 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Klíčové parametry pacienta z IRIS ({intake.fields.length})
              </p>
              <ul className="grid gap-1.5 sm:grid-cols-2">
                {intake.fields.map((f) => (
                  <li key={f.id} className="rounded-md border border-border bg-background/60 px-2.5 py-1.5 text-xs">
                    <span className="font-bold text-foreground">{f.label}: </span>
                    <span className={cn(f.status === 'missing' ? 'font-semibold text-amber-800 dark:text-amber-300' : 'text-muted-foreground')}>
                      {f.status === 'missing' ? 'CHYBÍ' : f.value ?? f.status}
                    </span>
                    {f.citation && <Citations ids={[f.citation]} />}
                  </li>
                ))}
              </ul>
            </div>
            <p className="text-xs text-muted-foreground">
              AI podklad pro tento případ ještě nebyl vygenerován. Otevřete kartu <strong>Otevřít podklad</strong> pro vygenerování souhrnu a semaforu léčby.
            </p>
          </div>
          <SourceDrawer evidenceId={openCitationId} loadSource={apiDataSource.loadSource} onClose={closeDrawer} />
        </CitationProvider>
      )}
    </div>
  );
}

function MoveCase({ targets, onMove }: { targets: MdtSession[]; onMove: (target: number) => Promise<void> }) {
  const [target, setTarget] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const selectId = React.useId();

  const move = async () => {
    if (!target) return;
    setBusy(true);
    setError(null);
    try {
      await onMove(Number(target));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Přesun se nepodařil.');
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <label htmlFor={selectId} className="sr-only">
        Přesunout na jiný board
      </label>
      <select
        id={selectId}
        value={target}
        onChange={(e) => setTarget(e.target.value)}
        className="h-9 max-w-[14rem] rounded-lg border border-input bg-background px-2.5 text-xs font-medium text-foreground"
      >
        <option value="">Přesunout na board…</option>
        {targets.map((s) => (
          <option key={s.id} value={s.id}>
            {formatDate(s.date)} · {s.title}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={move}
        disabled={!target || busy}
        className="inline-flex h-9 items-center gap-1 rounded-lg border border-border bg-background px-3 text-xs font-semibold text-foreground hover:bg-accent disabled:opacity-50"
      >
        <ArrowRightLeft className="h-3.5 w-3.5" aria-hidden /> Přesunout
      </button>
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}

