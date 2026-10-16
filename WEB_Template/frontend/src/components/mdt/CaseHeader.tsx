import { CalendarDays, ShieldAlert, TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefHeader } from '@/types/mdt';
import { Citations } from './citations';
import { ClaimItem } from './ClaimList';
import { formatDate } from './format';

const INTENT_LABEL = { kurativni: 'kurativní', paliativni: 'paliativní' } as const;
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
  const ecogDiff =
    ecog.physician && ecog.patient ? Math.abs(ecog.physician.value - ecog.patient.value) : null;
  const ecogWarning = ecogDiff !== null && ecogDiff >= 1;

  return (
    <header className="space-y-3 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-lg font-bold tracking-tight text-foreground">{header.display_name}</p>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 text-muted-foreground">
            <CalendarDays className="h-3.5 w-3.5" aria-hidden /> MDT {formatDate(header.mdt_date)}
          </span>
          {redFlagCount > 0 && (
            <a
              href={redFlagsHref}
              className="inline-flex items-center gap-1 rounded-full border border-destructive/30 bg-destructive/10 px-2 py-0.5 font-semibold text-destructive hover:bg-destructive/15"
            >
              <ShieldAlert className="h-3.5 w-3.5" aria-hidden /> Varovné signály: {redFlagCount}
            </a>
          )}
        </div>
      </div>

      <div className="text-sm">
        <p className="font-semibold text-foreground">
          {header.diagnosis.text}{' '}
          <span className="font-mono text-xs font-normal text-muted-foreground">{header.diagnosis.icd10}</span>
          <Citations ids={[header.diagnosis.citation]} />
        </p>
        {header.tnm && (
          <p className="text-muted-foreground">
            {header.tnm.text}
            {header.tnm.stage && <> · stadium {header.tnm.stage}</>}
            <Citations ids={[header.tnm.citation]} />
          </p>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2">
        <div className="rounded-lg border border-border bg-background p-2 text-center">
          <p className="text-[11px] font-medium text-muted-foreground">ECOG lékař</p>
          {ecog.physician ? (
            <>
              <p className="text-4xl font-extrabold leading-tight text-foreground">{ecog.physician.value}</p>
              <p className="text-[10px] text-muted-foreground">
                {formatDate(ecog.physician.date)}
                <Citations ids={[ecog.physician.citation]} />
              </p>
            </>
          ) : (
            <p className="py-2 text-xs text-muted-foreground">Údaj chybí</p>
          )}
        </div>
        <div
          className={cn(
            'rounded-lg border p-2 text-center',
            ecogWarning ? 'border-orange-500/60 bg-orange-500/10' : 'border-border bg-background',
          )}
        >
          <p className="text-[11px] font-medium text-muted-foreground">ECOG pacient</p>
          {ecog.patient ? (
            <>
              <p className="text-2xl font-bold leading-tight text-foreground">{ecog.patient.value}</p>
              <p className="text-[10px] text-muted-foreground">
                {formatDate(ecog.patient.date)}
                <Citations ids={[ecog.patient.citation]} />
              </p>
            </>
          ) : (
            <p className="py-2 text-xs text-muted-foreground">Údaj chybí</p>
          )}
        </div>
        <div className="rounded-lg border border-border bg-background p-2 text-center">
          <p className="text-[11px] font-medium text-muted-foreground">Záměr</p>
          {header.intent ? (
            <>
              <p className="text-4xl font-extrabold leading-tight text-foreground">{header.intent.letter}</p>
              <p className="text-[10px] text-muted-foreground">
                {INTENT_LABEL[header.intent.code]} · {INTENT_SOURCE[header.intent.source]}
              </p>
            </>
          ) : (
            <p className="py-2 text-xs text-muted-foreground">Nezadán</p>
          )}
        </div>
      </div>
      {ecogWarning && (
        <p className="flex items-start gap-1.5 text-xs font-medium text-orange-700 dark:text-orange-300">
          <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          ECOG lékaře a pacienta se liší o {ecogDiff} (varovný signál, OBC-1.3). Pacient: „{ecog.patient?.answer_text}“
        </p>
      )}

      <div className="rounded-lg bg-muted/60 px-3 py-2 text-sm">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Otázka pro MDT</p>
        <p className="line-clamp-3 text-foreground">
          {header.mdt_question.text}
          <Citations ids={[header.mdt_question.citation]} />
        </p>
      </div>

      {header.comorbidities.length > 0 && (
        <div className="text-sm">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Komorbidity</p>
          <ul className="mt-1 flex flex-wrap gap-1.5">
            {header.comorbidities.map((c) => (
              <li key={c.citation} className="rounded-md border border-border px-2 py-0.5 text-xs">
                {c.text}
                {c.icd10 && <span className="ml-1 font-mono text-muted-foreground">{c.icd10}</span>}
                <Citations ids={[c.citation]} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {header.alerts.length > 0 && (
        <div className="border-l-2 border-purple-500 pl-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            Alergie, implantáty, předchozí výkony{' '}
            <span className="normal-case tracking-normal text-purple-700 dark:text-purple-300">· AI návrh</span>
          </p>
          <ul className="mt-1 space-y-1">
            {header.alerts.map((a) => (
              <li key={a.id}>
                <ClaimItem claim={a} />
              </li>
            ))}
          </ul>
        </div>
      )}
    </header>
  );
}
