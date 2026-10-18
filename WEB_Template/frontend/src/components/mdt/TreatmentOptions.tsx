'use client';

import * as React from 'react';
import { Calculator, ChevronRight, MessageCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { CompatibilityRuleResult, TreatmentOption } from '@/types/mdt';
import { Citations } from './citations';
import { NationalRuleNote } from './NationalRuleNote';
import { ClaimItem, ClaimList } from './ClaimList';
import { CompatibilityLight, LightIcon } from './CompatibilityLight';
import { RoleBadge } from './RoleSection';

/**
 * Možnosti léčby z doporučených postupů (FR-D1) se semaforem souladu se stavem pacienta (FR-D4).
 * Vždy všechny možnosti, i červené, v pořadí z podkladu (ne podle barvy); žádné „doporučujeme“ (D-015).
 * Řádek = postup · semafor · rozhodující pravidlo · kdo se vyjadřuje (NAVRH_UI §8).
 */
export function TreatmentOptions({ options }: { options: TreatmentOption[] }) {
  return (
    <div className="flex flex-col gap-2">
      <ul className="divide-y divide-border rounded-lg border border-border bg-card">
        {options.map((o) => (
          <OptionRow key={o.id} option={o} />
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Barvu počítají deterministická pravidla z doporučených postupů, ne AI. Ukazuje soulad se stavem pacienta, nejde o doporučení.
      </p>
    </div>
  );
}

function OptionRow({ option }: { option: TreatmentOption }) {
  const c = option.compatibility;
  const [open, setOpen] = React.useState(false);
  const decisive = c.rules.filter((r) => r.status === c.overall).slice(0, 2);
  const bodyId = React.useId();
  return (
    <li className="px-3.5 py-3">
      <div className="flex flex-wrap items-start gap-x-3 gap-y-1.5">
        <div className="min-w-0 flex-1 basis-72">
          <p className="text-sm font-semibold leading-snug">
            {option.title}
            <Citations ids={option.guideline_citations} />
          </p>
          {decisive.map((r) => (
            <p key={r.rule_id} className="mt-0.5 text-[13px] leading-snug text-muted-foreground">
              {r.text}
              <Citations ids={[...r.patient_citations, r.rule_citation]} />
            </p>
          ))}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <RoleBadge role={c.owner_role} />
          <CompatibilityLight light={c.overall} />
        </div>
      </div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={bodyId}
        className="mt-1.5 inline-flex items-center gap-1 rounded-md text-xs font-medium text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <ChevronRight className={cn('size-3.5 transition-transform motion-reduce:transition-none', open && 'rotate-90')} aria-hidden />
        Zdůvodnění a pravidla ({c.rules.length})
      </button>
      {open && (
        <div id={bodyId} className="mt-2 flex flex-col gap-3 border-l-2 border-ai pl-3">
          {option.rationale.length > 0 && <ClaimList claims={option.rationale} />}
          {option.prerequisites_missing.length > 0 && <ClaimList claims={option.prerequisites_missing} />}
          {option.considerations.length > 0 && (
            <ul className="list-disc pl-5 text-sm">
              {option.considerations.map((t) => <li key={t}>{t}</li>)}
            </ul>
          )}
          {c.patient_preferences.length > 0 && (
            <div>
              <p className="mb-1 inline-flex items-center gap-1.5 text-[13px] font-medium">
                <MessageCircle className="size-4 text-muted-foreground" aria-hidden /> Preference pacienta (barvu nemění)
              </p>
              <ul className="flex flex-col gap-1">
                {c.patient_preferences.map((p) => <li key={p.id}><ClaimItem claim={p} /></li>)}
              </ul>
            </div>
          )}
          <ul className="flex flex-col gap-1.5">
            {c.rules.map((r) => <RuleRow key={r.rule_id} rule={r} />)}
          </ul>
        </div>
      )}
    </li>
  );
}

function RuleRow({ rule }: { rule: CompatibilityRuleResult }) {
  return (
    <li className="flex items-start gap-2 text-[13px] leading-snug">
      <span className="mt-0.5">
        <LightIcon light={rule.status} className="size-3.5" />
      </span>
      <div className="min-w-0 flex-1">
        <p>
          {rule.text}
          <Citations ids={[...rule.patient_citations, rule.rule_citation]} />
        </p>
        <NationalRuleNote rule={rule} />
        <p className="flex flex-wrap items-center gap-x-3 text-xs text-muted-foreground">
          <span translate="no">{rule.rule_id}</span>
          {rule.derived && (
            <span className="inline-flex items-center gap-1">
              <Calculator className="size-3" aria-hidden /> {rule.derived.formula}
              <Citations ids={rule.derived.inputs} />
            </span>
          )}
        </p>
      </div>
    </li>
  );
}
