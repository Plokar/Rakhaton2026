'use client';

import * as React from 'react';
import { CircleCheck, CircleDashed, Info, RotateCcw, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { IntakeField, IntakePrefill, IntakeWarning, Severity, WarningKind } from '@/types/mdt';
import { Citations } from './citations';

const KIND_LABEL: Record<WarningKind, string> = {
  missing: 'CHYBÍ',
  out_of_range: 'MIMO NORMU',
  conflict: 'ROZPOR',
  ai_uncertain: 'NEJISTOTA AI',
};
const SEVERITY_CLASS: Record<Severity, string> = {
  high: 'border-l-red-500',
  moderate: 'border-l-orange-500',
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
  const canSubmit = !missingQuestion && ecog !== null && intent !== null;

  const toggleSkip = (f: IntakeField) =>
    setSkipped((prev) => {
      const next = new Set(prev);
      if (next.has(f.id)) next.delete(f.id);
      else next.add(f.id);
      return next;
    });

  return (
    <form
      className="space-y-5"
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
        <h2 className="mb-2 text-sm font-semibold text-foreground">Údaje z IRIS</h2>
        <ul className="divide-y divide-border rounded-lg border border-border">
          {fields.map((f) => {
            const isSkipped = skipped.has(f.id);
            const missing = f.status === 'missing' || f.status === 'pending';
            return (
              <li key={f.id} className="flex flex-wrap items-start gap-2 px-3 py-2 text-sm">
                {missing && !isSkipped ? (
                  <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-orange-600 dark:text-orange-400" aria-hidden />
                ) : isSkipped ? (
                  <CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                ) : (
                  <CircleCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" aria-hidden />
                )}
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-foreground">
                    {f.label}
                    {f.required_by && <Citations ids={[f.required_by]} />}
                  </p>
                  {isSkipped ? (
                    <p className="text-xs text-muted-foreground">Chybí (přeskočeno lékařem), v podkladu zůstane jako chybějící údaj</p>
                  ) : (
                    <p className={cn('text-xs', missing ? 'font-semibold text-orange-700 dark:text-orange-300' : 'text-muted-foreground')}>
                      {missing ? `CHYBÍ${f.value ? `: ${f.value}` : ''}` : f.value}
                      {f.citation && <Citations ids={[f.citation]} />}
                    </p>
                  )}
                  {fillHint === f.id && (
                    <p className="mt-1 flex items-start gap-1 text-[11px] text-muted-foreground">
                      <Info className="mt-0.5 h-3 w-3 shrink-0" aria-hidden />
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
                        {isSkipped ? <><RotateCcw className="h-3.5 w-3.5" /> Vrátit</> : 'Přeskočit'}
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
        <h2 className="mb-2 text-sm font-semibold text-foreground">Varování ({active.length})</h2>
        {active.length === 0 && <p className="text-sm text-muted-foreground">Žádné aktivní varování.</p>}
        <ul className="space-y-2">
          {active.map((w) => (
            <li key={w.id} className={cn('rounded-lg border border-border border-l-4 bg-background px-3 py-2', SEVERITY_CLASS[w.severity])}>
              <div className="flex flex-wrap items-start gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-foreground">
                    <span className="mr-1.5 rounded bg-muted px-1.5 py-0.5 text-[10px] font-bold tracking-wide">{KIND_LABEL[w.kind]}</span>
                    {w.title}
                  </p>
                  <p className="mt-0.5 text-sm text-foreground">
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

      <section className="grid gap-4 sm:grid-cols-2">
        <div>
          <h2 className="mb-2 text-sm font-semibold text-foreground">ECOG (zadává nebo potvrzuje lékař)</h2>
          <div className="flex gap-1.5" role="radiogroup" aria-label="ECOG">
            {[0, 1, 2, 3, 4].map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={ecog === v}
                onClick={() => setEcog(v)}
                className={cn(
                  'h-12 w-12 rounded-lg border text-2xl font-extrabold transition',
                  ecog === v ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-foreground hover:bg-accent',
                )}
              >
                {v}
              </button>
            ))}
          </div>
          {prefill.ecog_physician && (
            <p className="mt-1 text-[11px] text-muted-foreground">
              Předvyplněno z IRIS: ECOG {prefill.ecog_physician.value}
              <Citations ids={[prefill.ecog_physician.citation]} />
            </p>
          )}
        </div>
        <div>
          <h2 className="mb-2 text-sm font-semibold text-foreground">Předpokládaný záměr</h2>
          <div className="flex gap-1.5" role="radiogroup" aria-label="Záměr">
            {(['C', 'P'] as const).map((v) => (
              <button
                key={v}
                type="button"
                role="radio"
                aria-checked={intent === v}
                onClick={() => setIntent(v)}
                className={cn(
                  'flex h-12 flex-1 flex-col items-center justify-center rounded-lg border transition',
                  intent === v ? 'border-primary bg-primary text-primary-foreground' : 'border-border text-foreground hover:bg-accent',
                )}
              >
                <span className="text-xl font-extrabold leading-none">{v}</span>
                <span className="text-[10px]">{v === 'C' ? 'kurativní' : 'paliativní'}</span>
              </button>
            ))}
          </div>
          <p className="mt-1 text-[11px] text-muted-foreground">
            {prefill.intent_prefill ? 'Předvyplněno z poslední MDT.' : 'Minulá MDT rozhodnutí odložila, vyberte C nebo P.'}
          </p>
        </div>
      </section>

      <label className="flex items-start gap-2 text-sm text-foreground">
        <input type="checkbox" className="mt-1" checked={imaging} onChange={(e) => setImaging(e.target.checked)} />
        <span>
          Snímek mladší než 3 měsíce
          <span className="block text-[11px] text-muted-foreground">
            Připomínka. Pro radikální léčbu a změnu linie musí být staging ≤ 6 týdnů (OBC-1.2), před resekcí jater ≤ 4–6 týdnů
            (KRC-2.4); kontrola stagingu běží automaticky.
          </span>
        </span>
      </label>

      <div className="flex flex-wrap items-center justify-end gap-3 border-t border-border pt-4">
        {!canSubmit && !missingQuestion && <span className="text-xs text-muted-foreground">Zadejte ECOG a záměr C/P.</span>}
        <Button type="submit" disabled={!canSubmit} isLoading={submitting}>
          Zařadit do boardu
        </Button>
      </div>
    </form>
  );
}
