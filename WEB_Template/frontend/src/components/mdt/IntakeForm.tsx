'use client';

import * as React from 'react';
import { CircleCheck, CircleDashed, Info, RotateCcw, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { IntakeField, IntakePrefill, IntakeWarning, Severity, WarningKind } from '@/types/mdt';
import { Citations } from './citations';

const KIND_LABEL: Record<WarningKind, string> = {
  missing: 'Chybí',
  out_of_range: 'Mimo normu',
  conflict: 'Rozpor',
  ai_uncertain: 'Nejistota AI',
};
/** Pruh vlevo = závažnost varování (D-017), vždy s textem typu. */
const SEVERITY_CLASS: Record<Severity, string> = {
  high: 'border-l-red-600 dark:border-l-red-500',
  moderate: 'border-l-amber-500',
  low: 'border-l-slate-400',
};
const UNSKIPPABLE = new Set(['mdt.question']); // OBC-1.1: bez otázky je případ neúplný

export type IntakeResult = {
  ecog: number;
  intent: 'C' | 'P';
  imaging_recent_checked: boolean;
  skipped_fields: string[];
  acknowledged: string[];
};

/**
 * Zařazení pacienta do boardu (FR-P4, ARCH §5.10, POZADAVKY §2.2): předvyplněné údaje z IRIS s citací,
 * chybějící údaj Doplnit / Přeskočit (otázku pro MDT přeskočit nelze), varování s „Beru na vědomí“,
 * ECOG a záměr C/P, připomínka snímku. Odkliknuté varování i přeskočený údaj v podkladu zůstanou (D-019).
 */
export function IntakeForm({
  prefill,
  submitting,
  onSubmit,
}: {
  prefill: IntakePrefill;
  submitting: boolean;
  onSubmit: (result: IntakeResult) => void;
}) {
  const [skipped, setSkipped] = React.useState<Set<string>>(new Set());
  const [acknowledged, setAcknowledged] = React.useState<Set<string>>(new Set());
  const [ecog, setEcog] = React.useState<number | null>(prefill.ecog_physician?.value ?? null);
  const [intent, setIntent] = React.useState<'C' | 'P' | null>(prefill.intent_prefill ?? null);
  const [imaging, setImaging] = React.useState(false);
  const [fillHint, setFillHint] = React.useState<string | null>(null);

  const fields = prefill.fields;
  const skippedCitations = new Set(fields.filter((f) => skipped.has(f.id) && f.citation).map((f) => f.citation as string));
  // Přeskočený údaj se dál nehlídá: varování, která na něm stojí, se v formuláři umlčí (v podkladu zůstanou).
  const silenced = (w: IntakeWarning) => w.citations.some((c) => skippedCitations.has(c));
  const active = prefill.warnings.filter((w) => !acknowledged.has(w.id) && !silenced(w));
  const done = prefill.warnings.filter((w) => acknowledged.has(w.id) || silenced(w));
  const question = fields.find((f) => f.id === 'mdt.question');
  const missingQuestion = !question || question.status !== 'present';
  // Zařazení projde až po vyřešení všeho: každý chybějící údaj doplněn nebo vědomě přeskočen,
  // každé varování vzato na vědomí, ECOG, záměr C/P a kontrola stáří snímku.
  const unresolvedFields = fields.filter((f) => (f.status === 'missing' || f.status === 'pending') && !skipped.has(f.id));
  const remaining: string[] = [
    ...unresolvedFields.map((f) => `Údaj „${f.label}“: doplnit nebo přeskočit`),
    ...(active.length > 0 ? [`Varování k potvrzení: ${active.length}`] : []),
    ...(ecog === null ? ['ECOG'] : []),
    ...(intent === null ? ['Záměr C/P'] : []),
    ...(imaging ? [] : ['Kontrola stáří snímku']),
  ];
  const canSubmit = !missingQuestion && remaining.length === 0;

  const toggleSkip = (f: IntakeField) =>
    setSkipped((prev) => {
      const next = new Set(prev);
      if (next.has(f.id)) next.delete(f.id);
      else next.add(f.id);
      return next;
    });

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        if (!canSubmit) return;
        onSubmit({
          ecog: ecog as number,
          intent: intent as 'C' | 'P',
          imaging_recent_checked: imaging,
          skipped_fields: [...skipped],
          acknowledged: [...acknowledged],
        });
      }}
    >
      <section>
        <h2 className="mb-2 text-sm font-semibold">Údaje z IRIS</h2>
        <ul className="divide-y divide-border rounded-lg border border-border bg-card">
          {fields.map((f) => {
            const isSkipped = skipped.has(f.id);
            const missing = f.status === 'missing' || f.status === 'pending';
            return (
              <li key={f.id} className="flex flex-wrap items-start gap-2 px-3 py-2 text-sm">
                {missing && !isSkipped ? (
                  <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden />
                ) : isSkipped ? (
                  <CircleDashed className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                ) : (
                  <CircleCheck className="mt-0.5 size-4 shrink-0 text-emerald-700 dark:text-emerald-400" aria-hidden />
                )}
                <div className="min-w-0 flex-1">
                  <p className="font-medium">
                    {f.label}
                    {f.required_by && <Citations ids={[f.required_by]} />}
                  </p>
                  {isSkipped ? (
                    <p className="text-[13px] text-muted-foreground">Chybí (přeskočeno lékařem), v podkladu zůstane jako chybějící údaj</p>
                  ) : (
                    <p className={cn('text-[13px]', missing ? 'font-medium text-amber-800 dark:text-amber-300' : 'text-muted-foreground')}>
                      {missing ? `Chybí${f.value ? `: ${f.value}` : ''}` : f.value}
                      {f.citation && <Citations ids={[f.citation]} />}
                    </p>
                  )}
                  {fillHint === f.id && (
                    <p className="mt-1 flex items-start gap-1 text-xs text-muted-foreground">
                      <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                      Doplňte údaj do dokumentace pacienta (IRIS); formulář ho po novém načtení převezme s citací.
                    </p>
                  )}
                </div>
                {missing && (
                  <div className="flex shrink-0 gap-1.5">
                    {!isSkipped && (
                      <Button type="button" variant="outline" size="sm" onClick={() => setFillHint(fillHint === f.id ? null : f.id)}>
                        Doplnit
                      </Button>
                    )}
                    {!UNSKIPPABLE.has(f.id) && (
                      <Button type="button" variant="ghost" size="sm" onClick={() => toggleSkip(f)} className="gap-1">
                        {isSkipped ? <><RotateCcw aria-hidden /> Vrátit</> : 'Přeskočit'}
                      </Button>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
        {missingQuestion && (
          <p className="mt-2 text-sm font-medium text-destructive">
            Chybí otázka pro MDT. Bez ní je případ neúplný a nelze ho zařadit (OBC-1.1).
          </p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold">
          Varování <span className="font-normal text-muted-foreground">({active.length})</span>
        </h2>
        {active.length === 0 && <p className="text-sm text-muted-foreground">Žádné aktivní varování.</p>}
        <ul className="flex flex-col gap-2">
          {active.map((w) => (
            <li key={w.id} className={cn('rounded-lg border border-border border-l-2 bg-card px-3 py-2', SEVERITY_CLASS[w.severity])}>
              <div className="flex flex-wrap items-start gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">
                    <span className="mr-1.5 text-xs font-medium text-muted-foreground">{KIND_LABEL[w.kind]}</span>
                    {w.title}
                  </p>
                  <p className="mt-0.5 text-[13px] leading-snug">
                    {w.detail}
                    <Citations ids={w.citations} />
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setAcknowledged((prev) => new Set(prev).add(w.id))}
                >
                  Beru na vědomí
                </Button>
              </div>
            </li>
          ))}
        </ul>
        {done.length > 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            Vzato na vědomí nebo umlčeno přeskočením: {done.length}. V podkladu pro komisi zůstávají (D-019).{' '}
            {acknowledged.size > 0 && (
              <button type="button" className="font-medium text-primary hover:underline" onClick={() => setAcknowledged(new Set())}>
                Vrátit odkliknutí
              </button>
            )}
          </p>
        )}
      </section>

      <section className="grid gap-5 sm:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-semibold">ECOG (zadává nebo potvrzuje lékař)</h2>
          <div className="flex gap-1.5" role="radiogroup" aria-label="ECOG">
            {[0, 1, 2, 3, 4].map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={ecog === v}
                onClick={() => setEcog(v)}
                className={cn(
                  'size-11 rounded-lg border text-xl font-semibold tabular-nums transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  ecog === v ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-card hover:bg-accent',
                )}
              >
                {v}
              </button>
            ))}
          </div>
          {prefill.ecog_physician && (
            <p className="mt-1.5 text-xs text-muted-foreground">
              Předvyplněno z IRIS: ECOG {prefill.ecog_physician.value}
              <Citations ids={[prefill.ecog_physician.citation]} />
            </p>
          )}
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold">Předpokládaný záměr</h2>
          <div className="flex gap-1.5" role="radiogroup" aria-label="Záměr">
            {(['C', 'P'] as const).map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={intent === v}
                onClick={() => setIntent(v)}
                className={cn(
                  'flex h-11 flex-1 items-center justify-center gap-2 rounded-lg border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  intent === v ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-card hover:bg-accent',
                )}
              >
                <span className="text-xl font-semibold leading-none">{v}</span>
                <span className="text-[13px]">{v === 'C' ? 'kurativní' : 'paliativní'}</span>
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-muted-foreground">
            {prefill.intent_prefill ? 'Předvyplněno z poslední MDT.' : 'Minulá MDT rozhodnutí odložila, vyberte C nebo P.'}
          </p>
        </div>
      </section>

      <label className="flex items-start gap-2.5 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-primary" checked={imaging} onChange={(e) => setImaging(e.target.checked)} />
        <span>
          Zkontroloval(a) jsem stáří snímku (doporučeno do 3 měsíců)
          <span className="mt-0.5 block text-xs text-muted-foreground">
            Připomínka. Pro radikální léčbu a změnu linie musí být staging ≤ 6 týdnů (OBC-1.2), před resekcí jater ≤ 4–6 týdnů
            (KRC-2.4); kontrola stagingu běží automaticky.
          </span>
        </span>
      </label>

      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
        {!canSubmit && !missingQuestion && (
          <div className="mr-auto text-xs text-muted-foreground" aria-live="polite">
            <p className="font-medium">Před zařazením zbývá:</p>
            <ul className="list-disc pl-4">
              {remaining.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </div>
        )}
        <Button type="submit" disabled={!canSubmit} isLoading={submitting}>
          Zařadit do boardu
        </Button>
      </div>
    </form>
  );
}
