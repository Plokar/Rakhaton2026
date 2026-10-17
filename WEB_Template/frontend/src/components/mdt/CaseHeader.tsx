import { TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefHeader } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { Citations } from './citations';
import { ClaimItem } from './ClaimList';
import { EcogDifference, ecogDifference } from './EcogCompare';
import { formatDate } from './format';

const INTENT_LABEL = { kurativni: 'kurativní', paliativni: 'paliativní' } as const;
const INTENT_SOURCE = {
  previous_mdt: 'z předchozí MDT',
  physician: 'zadal lékař',
  mdt_decision: 'rozhodnutí MDT',
} as const;

/**
 * Hlavička podkladu v úzkém okně (D-018, FR-A1, FR-A2, FR-A4): orientace do 30 s. Místo jména a RČ
 * `P03 · muž · 67 let`, PS lékaře velký, vedle něj PS pacienta, záměr C/P, otázka pro MDT.
 */
export function CaseHeader({
  header,
  redFlagCount,
  redFlagsHref = '#varovani',
  status,
}: {
  header: BriefHeader;
  redFlagCount: number;
  redFlagsHref?: string;
  status: 'draft' | 'confirmed';
}) {
  const { ecog } = header;
  const differs = (ecogDifference(ecog) ?? 0) >= 1;

  return (
    <header className="flex flex-col gap-4">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <h1 translate="no" className="text-lg font-semibold leading-tight tracking-tight">{header.display_name}</h1>
          <p className="mt-1 text-[13px] leading-snug text-muted-foreground">
            <span translate="no" className="font-medium text-foreground">{header.diagnosis.icd10}</span> {header.diagnosis.text}
            <Citations ids={[header.diagnosis.citation]} />
          </p>
          {header.tnm && (
            <p className="text-[13px] text-muted-foreground">
              <span translate="no">{header.tnm.text}</span>
              {header.tnm.stage && <>, stadium {header.tnm.stage}</>}
              <Citations ids={[header.tnm.citation]} />
            </p>
          )}
          <p className="mt-0.5 text-xs tabular-nums text-muted-foreground">MDT {formatDate(header.mdt_date)}</p>
        </div>
        <dl className="flex shrink-0 gap-1.5">
          <div className="flex min-w-15 flex-col items-center rounded-lg bg-muted/70 px-2.5 py-1.5" title="Performance status (ECOG) podle lékaře, pod ním podle pacienta">
            <dt className="text-xs font-medium text-muted-foreground">PS</dt>
            <dd className="text-[1.75rem] font-semibold leading-8 tabular-nums">
              {ecog.physician?.value ?? '–'}
              {ecog.physician && <Citations ids={[ecog.physician.citation]} className="ml-0.5 align-super" />}
            </dd>
            <dd className={cn('inline-flex items-center gap-0.5 text-xs tabular-nums', differs ? 'font-medium text-amber-800 dark:text-amber-300' : 'text-muted-foreground')}>
              {differs && <TriangleAlert className="size-3" aria-hidden />}
              pac. {ecog.patient?.value ?? '–'}
            </dd>
          </div>
          <div className="flex min-w-15 flex-col items-center rounded-lg bg-muted/70 px-2.5 py-1.5" title={header.intent ? `Léčebný záměr ${INTENT_SOURCE[header.intent.source]}` : 'Léčebný záměr nezadán'}>
            <dt className="text-xs font-medium text-muted-foreground">C/P</dt>
            <dd className="text-[1.75rem] font-semibold leading-8">{header.intent?.letter ?? '–'}</dd>
            <dd className="text-xs text-muted-foreground">{header.intent ? INTENT_LABEL[header.intent.code] : 'nezadán'}</dd>
          </div>
        </dl>
      </div>

      <EcogDifference ecog={ecog} />

      <div className="rounded-lg border border-border bg-card px-3.5 py-3">
        <h2 className="text-xs font-medium text-muted-foreground">Otázka pro MDT</h2>
        <p className="mt-1 text-base font-semibold leading-snug text-balance">
          {header.mdt_question.text}
          <Citations ids={[header.mdt_question.citation]} />
        </p>
      </div>

      {redFlagCount > 0 && (
        <a href={redFlagsHref} className="inline-flex w-fit items-center gap-1.5 text-sm font-medium underline-offset-4 hover:underline">
          <TriangleAlert className="size-4 text-amber-700 dark:text-amber-400" aria-hidden />
          Varovné signály: <span className="tabular-nums">{redFlagCount}</span>
        </a>
      )}

      {header.comorbidities.length > 0 && (
        <div>
          <h2 className="mb-1 text-sm font-semibold">Komorbidity</h2>
          <ul className="flex flex-col gap-0.5 text-[13px]">
            {header.comorbidities.map((c) => (
              <li key={c.citation}>
                {c.icd10 && <span translate="no" className="mr-1.5 font-medium">{c.icd10}</span>}
                {c.text}
                <Citations ids={[c.citation]} />
              </li>
            ))}
          </ul>
        </div>
      )}

      {header.alerts.length > 0 && (
        <AiBlock title="Alergie, implantáty a výkony" status={status} headingLevel="h2">
          <ul className="flex flex-col gap-1.5">
            {header.alerts.map((a) => (
              <li key={a.id}>
                <ClaimItem claim={a} />
              </li>
            ))}
          </ul>
        </AiBlock>
      )}
    </header>
  );
}
