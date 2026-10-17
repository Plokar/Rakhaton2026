'use client';

import * as React from 'react';
import { ArrowDown, ArrowUp, GripVertical, TriangleAlert } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { BriefConfig, DetailLevel, EvidenceId, MdtCase, RoleId, SectionId } from '@/types/mdt';
import { Citations } from './citations';
import { ROLE_META } from './roles';

export const SECTION_LABEL: Record<SectionId, string> = {
  summary: 'Souhrn případu',
  timeline: 'Časová osa',
  red_flags: 'Varovné signály',
  anamnesis: 'Anamnéza',
  role_views: 'Sekce odborností (pohledy a posouzení rolí)',
  modalities: 'Léčebné metody a odborníci',
  decision_support: 'Možnosti léčby se semaforem',
  trials: 'Klinické studie',
  questions: 'Otázky k diskusi',
  mdt_question: 'Otázka pro MDT (velkým písmem)',
};
const DETAIL_LABEL: Record<DetailLevel, string> = { brief: 'stručně', standard: 'standardně', detailed: 'podrobně' };
const ROLES: RoleId[] = [
  'oncologist', 'surgeon', 'radiologist', 'pathologist', 'radiation_oncologist', 'pulmonologist', 'cardiologist', 'patient',
];

type Requirement = { role: RoleId; source: EvidenceId; reason: string };

/**
 * Role, které guidelines pro otázky na boardu vyžadují (RF-ROLES): resekabilita jaterních metastáz
 * KRC-2.1 (HPB chirurg + radiolog), NSCLC st. III PLI-2.1 (hrudní chirurg, radiační a klinický onkolog,
 * pneumolog, radiolog).
 */
export function requiredRoles(cases: MdtCase[]): Requirement[] {
  const out = new Map<RoleId, Requirement>();
  for (const c of cases) {
    const icd = c.patient?.diagnosis?.icd10 ?? '';
    const question = c.question ?? c.patient?.mdt_question ?? '';
    if (/^C(18|19|20)/.test(icd) && /resekab/i.test(question)) {
      for (const role of ['surgeon', 'radiologist'] as RoleId[]) {
        out.set(role, { role, source: 'KRC-2.1', reason: `resekabilita jaterních metastáz (${c.patient_id})` });
      }
    }
    if (/^C34/.test(icd)) {
      for (const role of ['surgeon', 'radiation_oncologist', 'oncologist', 'pulmonologist', 'radiologist'] as RoleId[]) {
        if (!out.has(role)) out.set(role, { role, source: 'PLI-2.1', reason: `NSCLC st. III (${c.patient_id})` });
      }
    }
  }
  return [...out.values()];
}

/** Konfigurátor podkladu (FR-R1): sekce zap/vyp, pořadí, podrobnost, přítomné role, jazyk. */
export function SectionConfigurator({
  config,
  onChange,
  readOnly,
  requirements,
}: {
  config: BriefConfig;
  onChange: (c: BriefConfig) => void;
  readOnly: boolean;
  requirements: Requirement[];
}) {
  const [dragIndex, setDragIndex] = React.useState<number | null>(null);
  const sections = [...config.sections].sort((a, b) => a.order - b.order);
  const setSections = (next: typeof sections) =>
    onChange({ ...config, sections: next.map((s, i) => ({ ...s, order: i + 1 })) });
  const move = (from: number, to: number) => {
    if (to < 0 || to >= sections.length || from === to) return;
    const next = [...sections];
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    setSections(next);
  };
  const missing = requirements.filter((r) => !config.roles_present.includes(r.role));

  return (
    <div className="space-y-5">
      <div>
        <p className="mb-2 text-sm font-semibold">Sekce a pořadí</p>
        <ol className="space-y-1.5">
          {sections.map((s, i) => (
            <li
              key={s.id}
              draggable={!readOnly}
              onDragStart={() => setDragIndex(i)}
              onDragOver={(e) => !readOnly && e.preventDefault()}
              onDrop={() => {
                if (dragIndex !== null) move(dragIndex, i);
                setDragIndex(null);
              }}
              onDragEnd={() => setDragIndex(null)}
              className={cn(
                'flex flex-wrap items-center gap-2 rounded-lg border border-border bg-background px-2 py-1.5',
                dragIndex === i && 'opacity-50',
                !s.enabled && 'text-muted-foreground',
              )}
            >
              {!readOnly && <GripVertical className="size-4 shrink-0 text-muted-foreground" aria-hidden />}
              <label className="flex min-w-0 flex-1 items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={s.enabled}
                  disabled={readOnly}
                  onChange={(e) => setSections(sections.map((x) => (x.id === s.id ? { ...x, enabled: e.target.checked } : x)))}
                />
                <span className="truncate">{SECTION_LABEL[s.id]}</span>
              </label>
              <select
                className="h-8 rounded-md border border-input bg-card px-1.5 text-[13px] disabled:opacity-70"
                value={s.detail ?? config.detail_level}
                disabled={readOnly || !s.enabled}
                aria-label={`Podrobnost: ${SECTION_LABEL[s.id]}`}
                onChange={(e) =>
                  setSections(sections.map((x) => (x.id === s.id ? { ...x, detail: e.target.value as DetailLevel } : x)))
                }
              >
                {Object.entries(DETAIL_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
              {!readOnly && (
                <span className="flex">
                  <button
                    type="button"
                    onClick={() => move(i, i - 1)}
                    disabled={i === 0}
                    className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-30"
                    aria-label={`Posunout výš: ${SECTION_LABEL[s.id]}`}
                  >
                    <ArrowUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => move(i, i + 1)}
                    disabled={i === sections.length - 1}
                    className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-30"
                    aria-label={`Posunout níž: ${SECTION_LABEL[s.id]}`}
                  >
                    <ArrowDown className="h-3.5 w-3.5" />
                  </button>
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>

      <div>
        <p className="mb-2 text-sm font-semibold">Přítomní (pohledy a posouzení rolí)</p>
        <div className="flex flex-wrap gap-2">
          {ROLES.map((r) => (
            <label
              key={r}
              className={cn(
                'flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs',
                config.roles_present.includes(r) ? ROLE_META[r].className : 'border-border text-muted-foreground',
              )}
            >
              <input
                type="checkbox"
                checked={config.roles_present.includes(r)}
                disabled={readOnly}
                onChange={(e) =>
                  onChange({
                    ...config,
                    roles_present: e.target.checked
                      ? [...config.roles_present, r]
                      : config.roles_present.filter((x) => x !== r),
                  })
                }
              />
              {ROLE_META[r].label}
            </label>
          ))}
        </div>
        {missing.length > 0 && (
          <ul className="mt-2 space-y-1">
            {missing.map((m) => (
              <li key={m.role} className="flex items-start gap-1.5 text-[13px] font-medium text-amber-800 dark:text-amber-300">
                <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                <span>
                  Chybí role {ROLE_META[m.role].label.toLowerCase()}, kterou guidelines vyžadují: {m.reason}
                  <Citations ids={[m.source]} />
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <label className="flex flex-col gap-1.5 text-[13px] font-medium">
          <span className="block">Podrobnost celkově</span>
          <select
            className="h-9 w-full rounded-lg border border-input bg-card px-2 text-sm font-normal disabled:opacity-70"
            value={config.detail_level}
            disabled={readOnly}
            onChange={(e) => onChange({ ...config, detail_level: e.target.value as DetailLevel })}
          >
            {Object.entries(DETAIL_LABEL).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-[13px] font-medium">
          <span className="block">Jazyk</span>
          <select
            className="h-9 w-full rounded-lg border border-input bg-card px-2 text-sm font-normal disabled:opacity-70"
            value={config.language}
            disabled={readOnly}
            onChange={(e) => onChange({ ...config, language: e.target.value as BriefConfig['language'] })}
          >
            <option value="cs">čeština</option>
            <option value="sk">slovenčina</option>
            <option value="en">English</option>
          </select>
        </label>
        <label className="flex items-end gap-2 pb-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={config.hide_unverified}
            disabled={readOnly}
            onChange={(e) => onChange({ ...config, hide_unverified: e.target.checked })}
          />
          Skrýt neověřená tvrzení
        </label>
      </div>
    </div>
  );
}
