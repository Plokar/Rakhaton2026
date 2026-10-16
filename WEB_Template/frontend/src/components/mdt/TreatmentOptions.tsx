'use client';

import * as React from 'react';
import { ChevronDown, Calculator, MessageCircle } from 'lucide-react';
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
      <p className="text-xs text-muted-foreground">
        Soulad se stavem pacienta: barvu počítají pravidla z doporučených postupů, ne AI. Barva není doporučení,
        zobrazují se všechny možnosti.
      </p>
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
    <li className="rounded-lg border border-border bg-background p-3">
      <div className="flex flex-wrap items-start gap-2">
        <p className="min-w-0 flex-1 text-sm font-semibold text-foreground">
          {option.title}
          <Citations ids={option.guideline_citations} />
        </p>
        <CompatibilityLight light={c.overall} />
      </div>
      <p className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
        <span className={cn('rounded-full border px-1.5 py-0.5 font-semibold', role.className)}>{role.label}</span>
        <span>vyjadřuje se k metodě · {c.modality}</span>
      </p>

      {option.rationale.length > 0 && (
        <div className="mt-2">
          <ClaimList claims={option.rationale} />
        </div>
      )}
      {option.prerequisites_missing.length > 0 && (
        <div className="mt-2">
          <ClaimList claims={option.prerequisites_missing} />
        </div>
      )}
      {option.considerations.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-foreground">
          {option.considerations.map((t) => (
            <li key={t}>{t}</li>
          ))}
        </ul>
      )}

      {c.patient_preferences.length > 0 && (
        <div className="mt-2 rounded-md bg-muted/60 px-2 py-1.5">
          <p className="flex items-center gap-1 text-[11px] font-semibold text-muted-foreground">
            <MessageCircle className="h-3 w-3" aria-hidden /> Preference pacienta (barvu nemění)
          </p>
          <ul className="mt-1 space-y-1">
            {c.patient_preferences.map((p) => (
              <li key={p.id}>
                <ClaimItem claim={p} />
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', !open && '-rotate-90')} aria-hidden />
        Pravidla souladu ({c.rules.length})
      </button>
      {open && (
        <ul className="mt-2 space-y-1.5">
          {c.rules.map((r) => (
            <RuleRow key={r.rule_id} rule={r} />
          ))}
        </ul>
      )}
    </li>
  );
}

function RuleRow({ rule }: { rule: CompatibilityRuleResult }) {
  return (
    <li className="flex flex-col gap-1 rounded-md border border-border/70 px-2 py-1.5 text-sm sm:flex-row sm:items-start sm:gap-2">
      <CompatibilityLight light={rule.status} className="self-start" />
      <div className="min-w-0 flex-1">
        <p className="text-foreground">
          {rule.text}
          <Citations ids={[...rule.patient_citations, rule.rule_citation]} />
        </p>
        <p className="font-mono text-[10px] text-muted-foreground">{rule.rule_id}</p>
        {rule.derived && (
          <p className="mt-0.5 flex items-center gap-1 text-[11px] text-muted-foreground">
            <Calculator className="h-3 w-3" aria-hidden /> {rule.derived.formula}
            <Citations ids={rule.derived.inputs} />
          </p>
        )}
      </div>
    </li>
  );
}
