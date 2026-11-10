'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { CircleCheck, CircleDashed, CircleHelp, CircleMinus, CircleX, UserRoundSearch } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys, useCaseDoctorRules } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { DoctorRules, DoctorRulesDoctor, NormResult, RequirementItem } from '@/types/mdt';
import { Citations } from './citations';
import { formatDate } from './format';
import { ROLE_META } from './roles';

/**
 * Požadavky a normy pozvaných lékařů u pacienta (T-359, T-360, D-028, docs/UCTY_A_PVW.md §3).
 *
 * - Požadavek je upozornění pro zadávajícího lékaře, ne blokace. Rozhodne, zda lékaře u pacienta potřebuje;
 *   odkliknutí se zapíše a nezmizí (D-019).
 * - Norma je osobní kritérium lékaře s autorem. Vyhodnocuje ji kód s citací faktu pacienta; barvu semaforu
 *   nemění (D-015), proto tu nejsou barvy semaforu, jen ikona a text.
 */

export const NORM_STATUS: Record<NormResult['status'], { label: string; icon: React.ElementType; className: string }> = {
  met: { label: 'splněno', icon: CircleCheck, className: 'text-foreground' },
  not_met: { label: 'nesplněno', icon: CircleX, className: 'font-semibold text-foreground' },
  missing: { label: 'údaj chybí', icon: CircleDashed, className: 'text-muted-foreground' },
  not_evaluable: { label: 'nelze posoudit', icon: CircleHelp, className: 'text-muted-foreground' },
};

const ITEM_STATUS: Record<RequirementItem['status'], { label: string; icon: React.ElementType; className: string }> = {
  present: { label: 'je', icon: CircleCheck, className: 'text-muted-foreground' },
  missing: { label: 'chybí', icon: CircleX, className: 'font-medium text-foreground' },
  pending: { label: 'čeká se', icon: CircleDashed, className: 'font-medium text-foreground' },
  skipped: { label: 'přeskočeno lékařem', icon: CircleMinus, className: 'text-muted-foreground' },
};

export function doctorLabel(d: Pick<DoctorRulesDoctor, 'name' | 'specialty' | 'organization' | 'is_external'>): string {
  const specialty = d.specialty ? ROLE_META[d.specialty]?.label.toLowerCase() : null;
  return [d.name, specialty, d.is_external && d.organization ? d.organization : null].filter(Boolean).join(' · ');
}

/** Jedna norma s výsledkem: „FLR ≥ 30 % · pacient 38 % [P03-img04#3] · splněno“. */
export function NormLine({ norm, author, className }: {
  norm: DoctorRulesDoctor['norms'][number];
  author?: string;
  className?: string;
}) {
  const meta = NORM_STATUS[norm.result.status];
  const Icon = meta.icon;
  return (
    <li className={cn('flex items-start gap-2 text-[13px] leading-snug', className)}>
      <Icon className={cn('mt-0.5 size-4 shrink-0', meta.className)} aria-hidden />
      <span className="min-w-0 flex-1">
        {author && <span className="text-muted-foreground">{author}: </span>}
        <span className="font-medium">{norm.text}</span>
        {norm.procedure && <span className="text-muted-foreground"> ({norm.procedure})</span>}
        {norm.result.value && (
          <span className="text-muted-foreground"> · pacient {norm.result.value}</span>
        )}
        {norm.result.citation && <Citations ids={[norm.result.citation]} />}
        {norm.source && <Citations ids={[norm.source]} />}
        <span className={cn('ml-1', meta.className)}> · {meta.label}</span>
        {norm.result.reason && <span className="block text-xs text-muted-foreground">{norm.result.reason}</span>}
      </span>
    </li>
  );
}

type Decision = 'needed' | 'not_needed';

/**
 * Panel pro zadávajícího lékaře: co pozvaní lékaři u pacienta vyžadují a co chybí.
 * `intake` = při zařazení (rozhodnutí se odešle s případem), `caseId` = u případu (uloží se hned).
 */
export function RequirementsPanel({
  rules,
  loading,
  error,
  caseId,
  canDecide = false,
  decisions,
  onDecide,
  className,
}: {
  rules: DoctorRules | undefined;
  loading?: boolean;
  error?: unknown;
  /** U případu: rozhodnutí se uloží na server, s volbou úkolů na chybějící údaje. */
  caseId?: number;
  canDecide?: boolean;
  /** Při zařazení: rozhodnutí drží formulář. */
  decisions?: Record<number, Decision>;
  onDecide?: (userId: number, decision: Decision) => void;
  className?: string;
}) {
  const client = useQueryClient();
  const [saving, setSaving] = React.useState<number | null>(null);
  const doctors = (rules?.doctors ?? []).filter((d) => d.requirement);
  if (loading && !rules) return <p className={cn('text-sm text-muted-foreground', className)}>Načítám požadavky pozvaných lékařů…</p>;
  if (error) {
    return <p role="alert" className={cn('text-sm text-destructive', className)}>{apiErrorMessage(error, 'Požadavky lékařů se nepodařilo načíst.')}</p>;
  }
  if (!doctors.length) return null;

  const decide = async (doctor: DoctorRulesDoctor, decision: Decision, prepTasks = false) => {
    if (caseId === undefined) return onDecide?.(doctor.user_id, decision);
    setSaving(doctor.user_id);
    try {
      const saved = await mdtApi.decideRequirement(caseId, { user_id: doctor.user_id, decision, prep_tasks: prepTasks });
      client.setQueryData(queryKeys.caseDoctorRules(caseId), saved);
      toast(decision === 'needed' ? `${doctor.name}: u pacienta potřebujete` : `${doctor.name}: u pacienta nepotřebujete`, {
        description: saved.fhir_written.length ? `Úkoly k doplnění: ${saved.fhir_written.length}` : undefined,
      });
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Rozhodnutí se nepodařilo uložit.'));
    } finally {
      setSaving(null);
    }
  };

  return (
    <section aria-labelledby="req-heading" className={cn('flex flex-col gap-2', className)}>
      <h3 id="req-heading" className="flex items-center gap-2 text-sm font-semibold">
        <UserRoundSearch className="size-4" aria-hidden /> Požadavky pozvaných lékařů
      </h3>
      <p className="text-xs text-muted-foreground">
        Pozvaní lékaři u pacientů s {rules?.area_label.toLowerCase() ?? 'touto diagnózou'} vyžadují tyto údaje. Rozhodněte, zda
        lékaře u pacienta potřebujete; pacienta jde zařadit i bez nich.
      </p>
      <ul className="flex flex-col gap-2">
        {doctors.map((d) => {
          const req = d.requirement!;
          const current = caseId === undefined ? decisions?.[d.user_id] : d.decision?.decision;
          return (
            <li key={d.user_id} className="rounded-lg border border-border bg-card p-3">
              <p className="text-sm font-medium">{doctorLabel(d)}</p>
              {req.note && <p className="text-xs text-muted-foreground">„{req.note}“</p>}
              <ul className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1">
                {req.items.map((i) => {
                  const meta = ITEM_STATUS[i.status];
                  const Icon = meta.icon;
                  return (
                    <li key={i.key} className={cn('flex items-center gap-1 text-[13px]', meta.className)} title={i.value ?? undefined}>
                      <Icon className="size-3.5 shrink-0" aria-hidden />
                      {i.label}
                      <span className="sr-only">: {meta.label}</span>
                      {i.status !== 'present' && <span className="text-xs text-muted-foreground"> ({meta.label})</span>}
                    </li>
                  );
                })}
              </ul>
              {d.norms.length > 0 && (
                <ul className="mt-2 flex flex-col gap-1 border-t border-border pt-2">
                  {d.norms.map((n) => <NormLine key={n.id} norm={n} />)}
                </ul>
              )}
              {d.decision && caseId !== undefined && (
                <p className="mt-1.5 text-xs text-muted-foreground">
                  {d.decision.decision === 'needed' ? 'Potřebuji' : 'Nepotřebuji'} · {d.decision.by}, {formatDate(d.decision.at)}
                  {d.decision.note && ` · ${d.decision.note}`}
                </p>
              )}
              {canDecide && (
                <div className="mt-2 flex flex-wrap gap-1.5" role="group" aria-label={`Rozhodnutí: ${d.name}`}>
                  <Button type="button" size="sm" variant={current === 'needed' ? 'default' : 'outline'}
                    aria-pressed={current === 'needed'} disabled={saving === d.user_id} onClick={() => void decide(d, 'needed')}>
                    Potřebuji
                  </Button>
                  {caseId !== undefined && req.missing.length > 0 && (
                    <Button type="button" size="sm" variant="outline" disabled={saving === d.user_id}
                      onClick={() => void decide(d, 'needed', true)}>
                      Potřebuji, chybějící do úkolů
                    </Button>
                  )}
                  <Button type="button" size="sm" variant={current === 'not_needed' ? 'default' : 'outline'}
                    aria-pressed={current === 'not_needed'} disabled={saving === d.user_id} onClick={() => void decide(d, 'not_needed')}>
                    Nepotřebuji
                  </Button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

/** Požadavky pozvaných lékařů u případu (detail): rozhoduje zadávající lékař, ostatní jen vidí. */
export function CaseRequirements({ caseId, canDecide, className }: { caseId: number; canDecide: boolean; className?: string }) {
  const rules = useCaseDoctorRules(caseId);
  if (!rules.data?.doctors.some((d) => d.requirement)) return null;
  return (
    <div className={cn('rounded-xl border border-border bg-card p-4', className)}>
      <RequirementsPanel rules={rules.data} error={rules.error} caseId={caseId} canDecide={canDecide} />
    </div>
  );
}
