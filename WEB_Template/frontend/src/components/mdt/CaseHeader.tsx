import { CalendarDays, Cpu, HelpCircle, ShieldAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefHeader } from '@/types/mdt';
import { Citations } from './citations';
import { ClaimItem } from './ClaimList';
import { EcogDifference, EcogTiles } from './EcogCompare';
import { formatDate } from './format';

const INTENT_LABEL = { kurativni: 'Kurativní', paliativni: 'Paliativní' } as const;
const INTENT_SOURCE = {
  previous_mdt: 'z předchozí MDT',
  physician: 'zadal lékař',
  mdt_decision: 'rozhodnutí MDT',
} as const;

/**
 * Hlavička podkladu (D-018, FR-A1, FR-A2, FR-A4): orientace do 30 s.
 * Místo jména a RČ `P03 · muž · 67 let`; ECOG lékaře velký, vedle něj ECOG pacienta, záměr C/P.
 */
export function CaseHeader({
  header,
  redFlagCount,
  redFlagsHref = '#red-flags',
}: {
  header: BriefHeader;
  redFlagCount: number;
  redFlagsHref?: string;
}) {
  const { ecog } = header;

  return (
    <header className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
      {/* Top Identity & Status Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border bg-muted/50 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-md bg-primary px-2 py-0.5 font-mono text-xs font-extrabold text-primary-foreground">
            {header.display_name.split('·')[0]?.trim() || 'PACIENT'}
          </span>
          <h1 className="text-base font-extrabold tracking-tight text-foreground sm:text-lg">
            {header.display_name}
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 font-medium text-foreground">
            <CalendarDays className="h-3.5 w-3.5 text-primary" aria-hidden /> MDT {formatDate(header.mdt_date)}
          </span>
          {redFlagCount > 0 && (
            <a
              href={redFlagsHref}
              className="inline-flex items-center gap-1.5 rounded-md border border-red-600/50 bg-red-50 px-2.5 py-1 font-bold text-red-900 transition-colors hover:bg-red-100 dark:border-red-500/50 dark:bg-red-950/80 dark:text-red-200 dark:hover:bg-red-900/60"
            >
              <ShieldAlert className="h-3.5 w-3.5 text-red-600 dark:text-red-400" aria-hidden />
              Varovné signály: {redFlagCount}
            </a>
          )}
        </div>
      </div>

      <div className="space-y-3.5 p-4">
        {/* Primary Diagnosis & TNM Staging */}
        <div className="rounded-lg border border-border/80 bg-muted/25 p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Hlavní diagnóza a staging</p>
            <span className="rounded-sm border border-border bg-card px-1.5 py-0.5 font-mono text-xs font-bold text-foreground">
              MKN-10: {header.diagnosis.icd10}
            </span>
          </div>
          <p className="mt-1 text-base font-extrabold leading-snug text-foreground sm:text-lg">
            {header.diagnosis.text}
            <Citations ids={[header.diagnosis.citation]} />
          </p>
          {header.tnm && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center rounded-md border border-primary/30 bg-primary/10 px-2.5 py-0.5 font-mono text-xs font-bold text-primary">
                TNM: {header.tnm.text}
              </span>
              {header.tnm.stage && (
                <span className="inline-flex items-center rounded-md border border-border bg-card px-2.5 py-0.5 text-xs font-bold text-foreground">
                  Stadium {header.tnm.stage}
                </span>
              )}
              <Citations ids={[header.tnm.citation]} />
            </div>
          )}
        </div>

        {/* 3 Key Clinical Indicators: ECOG Lékař · ECOG Pacient · Záměr C/P */}
        <div className="grid grid-cols-3 gap-2.5">
          <EcogTiles ecog={ecog} />
          <div
            className={cn(
              'flex flex-col justify-between rounded-lg border px-3 py-2.5 text-center shadow-2xs',
              header.intent?.letter === 'C'
                ? 'border-teal-600/40 bg-teal-50/50 dark:border-teal-500/40 dark:bg-teal-950/30'
                : 'border-border bg-background',
            )}
          >
            <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Záměr léčby</p>
            {header.intent ? (
              <>
                <p className="my-0.5 font-mono text-3xl font-extrabold leading-none text-foreground sm:text-4xl">
                  {header.intent.letter}
                </p>
                <p className="text-[11px] font-semibold text-foreground">
                  {INTENT_LABEL[header.intent.code]}{' '}
                  <span className="block text-[10px] font-normal text-muted-foreground">
                    {INTENT_SOURCE[header.intent.source]}
                  </span>
                </p>
              </>
            ) : (
              <p className="py-2 text-xs font-medium text-muted-foreground">Nezadán</p>
            )}
          </div>
        </div>
        <EcogDifference ecog={ecog} />

        {/* Core MDT Question — Never truncated so 30s orientation is complete */}
        <div className="rounded-lg border border-border border-l-4 border-l-primary bg-muted/40 px-3.5 py-3">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-primary">
            <HelpCircle className="h-3.5 w-3.5" aria-hidden /> Otázka pro komisi (MDT)
          </p>
          <p className="mt-1 text-sm font-semibold leading-relaxed text-foreground sm:text-base">
            {header.mdt_question.text}
            <Citations ids={[header.mdt_question.citation]} />
          </p>
        </div>

        {/* Comorbidities & Clinical Alerts */}
        {(header.comorbidities.length > 0 || header.alerts.length > 0) && (
          <div className="grid gap-3 pt-1 sm:grid-cols-2">
            {header.comorbidities.length > 0 && (
              <div className="rounded-lg border border-border bg-background p-3">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  Komorbidity ({header.comorbidities.length})
                </p>
                <ul className="mt-2 flex flex-wrap gap-1.5">
                  {header.comorbidities.map((c) => (
                    <li
                      key={c.citation}
                      className="inline-flex items-center gap-1 rounded-md border border-border bg-muted/50 px-2 py-1 text-xs font-medium text-foreground"
                    >
                      <span>{c.text}</span>
                      {c.icd10 && <span className="font-mono text-[11px] text-muted-foreground">({c.icd10})</span>}
                      <Citations ids={[c.citation]} />
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {header.alerts.length > 0 && (
              <div className="rounded-lg border border-border border-l-4 border-l-teal-700 bg-background p-3 dark:border-l-teal-400">
                <p className="flex flex-wrap items-center justify-between gap-1 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                  <span>Alergie, implantáty a výkony</span>
                  <span className="inline-flex items-center gap-1 rounded-sm border border-teal-700/30 bg-teal-50 px-1.5 py-0.5 font-mono text-[10px] font-semibold normal-case tracking-normal text-teal-900 dark:border-teal-400/30 dark:bg-teal-950/70 dark:text-teal-200">
                    <Cpu className="h-2.5 w-2.5" aria-hidden /> AI návrh
                  </span>
                </p>
                <ul className="mt-2 space-y-1.5">
                  {header.alerts.map((a) => (
                    <li key={a.id}>
                      <ClaimItem claim={a} />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

