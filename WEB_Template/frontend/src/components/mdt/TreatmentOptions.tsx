'use client';

import * as React from 'react';
import { ChevronDown, Calculator, MessageCircle, Scale } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CompatibilityRuleResult, TreatmentOption } from '@/types/mdt';
import { Citations } from './citations';
import { ClaimItem, ClaimList } from './ClaimList';
import { CompatibilityLight } from './CompatibilityLight';
import { ROLE_META } from './roles';

/**
 * Možnosti léčby z doporučených postupů (FR-D1) se semaforem souladu se stavem pacienta (FR-D4).
 * Vždy všechny možnosti, i červené; žádné pořadí jako doporučení (D-015).
 */
export function TreatmentOptions({ options }: { options: TreatmentOption[] }) {
  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
        <Scale className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
        <span>
          <strong className="font-semibold text-foreground">Semafor souladu se stavem pacienta:</strong> barvu počítají
          deterministická pravidla z doporučených postupů, ne AI. Barva není doporučení, zobrazují se všechny možnosti.
        </span>
      </div>
      <ul className="space-y-3">
        {options.map((o) => (
          <OptionCard key={o.id} option={o} />
        ))}
      </ul>
    </div>
  );
}

function OptionCard({ option }: { option: TreatmentOption }) {
  const [open, setOpen] = React.useState(option.compatibility.overall !== 'green');
  const c = option.compatibility;
  const role = ROLE_META[c.owner_role];
  return (
    <li className="rounded-xl border border-border bg-background p-4 shadow-2xs">
      <div className="flex flex-wrap items-start justify-between gap-2.5">
        <div className="min-w-0 flex-1">
          <p className="text-base font-bold leading-snug text-foreground">
            {option.title}
            <Citations ids={option.guideline_citations} />
          </p>
          <p className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <span className={cn('rounded-md border px-2 py-0.5 font-bold', role.className)}>{role.label}</span>
            <span>vyjadřuje se k metodě · <strong className="font-semibold text-foreground">{c.modality}</strong></span>
          </p>
        </div>
        <CompatibilityLight light={c.overall} className="shrink-0" />
      </div>

      {option.rationale.length > 0 && (
        <div className="mt-3">
          <ClaimList claims={option.rationale} />
        </div>
      )}
      {option.prerequisites_missing.length > 0 && (
        <div className="mt-2.5">
          <ClaimList claims={option.prerequisites_missing} />
        </div>
      )}
      {option.considerations.length > 0 && (
        <ul className="mt-2.5 list-disc space-y-1 pl-5 text-sm text-foreground">
          {option.considerations.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}

      {c.patient_preferences.length > 0 && (
        <div className="mt-3 rounded-lg border border-border bg-muted/50 px-3 py-2">
          <p className="flex items-center gap-1.5 text-xs font-bold text-foreground">
            <MessageCircle className="h-3.5 w-3.5 text-primary" aria-hidden /> Preference pacienta (barvu semaforu nemění)
          </p>
          <ul className="mt-1.5 space-y-1">
            {c.patient_preferences.map((p) => (
              <li key={p.id}>
                <ClaimItem claim={p} />
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-3 border-t border-border/70 pt-2.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-bold text-foreground transition hover:bg-accent"
        >
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform text-muted-foreground', !open && '-rotate-90')} aria-hidden />
          Pravidla souladu ({c.rules.length})
        </button>
        {open && (
          <ul className="mt-2 space-y-2">
            {c.rules.map((r) => (
              <RuleRow key={r.rule_id} rule={r} />
            ))}
          </ul>
        )}
      </div>
    </li>
  );
}

function RuleRow({ rule }: { rule: CompatibilityRuleResult }) {
  return (
    <li className="flex flex-col gap-1.5 rounded-lg border border-border bg-card/70 px-3 py-2 text-sm sm:flex-row sm:items-start sm:gap-3">
      <CompatibilityLight light={rule.status} className="self-start shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-medium text-foreground">
          {rule.text}
          <Citations ids={[...rule.patient_citations, rule.rule_citation]} />
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5">
          <span className="font-mono text-[11px] font-semibold text-muted-foreground">{rule.rule_id}</span>
          {rule.derived && (
            <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
              <Calculator className="h-3 w-3 text-primary" aria-hidden /> {rule.derived.formula}
              <Citations ids={rule.derived.inputs} />
            </span>
          )}
        </div>
      </div>
    </li>
  );
}
