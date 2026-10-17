'use client';

import * as React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { Decision, RedFlag, RoleId, Source } from '@/types/mdt';
import { Citations } from './citations';
import { ROLE_META } from './roles';

type Sections = Decision['sections'];
type Sourced = { text: string; source: Source };

export const MODALITY_LABEL: Record<string, string> = {
  chirurgie: 'Chirurgie',
  chemoterapie: 'Chemoterapie',
  rt: 'Radioterapie',
  hormonalni: 'Hormonální léčba',
  cilena: 'Cílená léčba',
  imunoterapie: 'Imunoterapie',
  'jina-systemova': 'Jiná systémová léčba',
  diagnostika: 'Diagnostika',
  sledovani: 'Sledování',
};
const INTENT_LABEL: Record<Sections['intent'], string> = {
  kurativni: 'Kurativní (C)',
  paliativni: 'Paliativní (P)',
  odlozeno: 'Odloženo – doplnit diagnostiku',
};
const MDT_TYPE_LABEL: Record<Decision['mdt_type'], string> = {
  primarni: 'Primární projednání',
  progrese: 'Progrese / recidiva',
  restaging: 'Restaging / hodnocení odpovědi',
};
const TASK_STATUS_LABEL: Record<Decision['tasks'][number]['status'], string> = {
  requested: 'Zadáno',
  'in-progress': 'Probíhá',
  completed: 'Hotovo',
};
const ATTENDEE_ROLES: (RoleId | 'chair')[] = [
  'chair', 'oncologist', 'surgeon', 'radiologist', 'pathologist', 'radiation_oncologist', 'pulmonologist', 'cardiologist',
];
const roleLabel = (r: RoleId | 'chair') => (r === 'chair' ? 'Předseda' : ROLE_META[r].label);

/** Úprava textu od AI z něj udělá „AI návrh upravený lékařem“ (FR-R4). */
const afterEdit = (source: Source): Source => (source === 'ai' ? 'ai_edited' : source);

const fieldClass = 'h-9 rounded-lg border border-input bg-card px-2.5 text-sm text-foreground disabled:opacity-70';

function SourceBadge({ source }: { source: Source }) {
  if (source === 'human') return null;
  return (
    <span className="inline-flex items-center rounded-md bg-ai-soft px-1.5 py-0.5 text-xs font-medium text-ai">
      {source === 'ai' ? 'AI návrh' : 'AI návrh upravený lékařem'}
    </span>
  );
}

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="flex flex-wrap items-center gap-2 text-[13px] font-medium">{label}{hint}</p>
      {children}
    </div>
  );
}

function SourcedText({
  label,
  value,
  onChange,
  readOnly,
  rows = 3,
  citations,
}: {
  label: string;
  value: Sourced;
  onChange: (v: Sourced) => void;
  readOnly: boolean;
  rows?: number;
  citations?: string[];
}) {
  const id = React.useId();
  return (
    <div className={cn('space-y-1.5', value.source !== 'human' && 'border-l-2 border-ai pl-3')}>
      <label htmlFor={id} className="flex flex-wrap items-center gap-2 text-[13px] font-medium">
        {label} <SourceBadge source={value.source} />
      </label>
      <Textarea
        id={id}
        rows={rows}
        value={value.text}
        disabled={readOnly}
        onChange={(e) => onChange({ text: e.target.value, source: afterEdit(value.source) })}
      />
      {citations && citations.length > 0 && (
        <p className="text-xs text-muted-foreground">
          Zdroje:
          <Citations ids={citations} />
        </p>
      )}
    </div>
  );
}

function Optional({
  present,
  label,
  onAdd,
  onRemove,
  readOnly,
  children,
}: {
  present: boolean;
  label: string;
  onAdd: () => void;
  onRemove: () => void;
  readOnly: boolean;
  children: React.ReactNode;
}) {
  if (!present) {
    return readOnly ? null : (
      <button type="button" onClick={onAdd} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
        <Plus className="h-3.5 w-3.5" aria-hidden /> {label}
      </button>
    );
  }
  return (
    <div className="relative rounded-lg border border-border p-3">
      {!readOnly && (
        <button
          type="button"
          onClick={onRemove}
          className="absolute right-2 top-2 rounded p-1 text-muted-foreground hover:bg-accent hover:text-destructive"
          aria-label={`Odebrat: ${label}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      )}
      {children}
    </div>
  );
}

/**
 * Zápis závěru komise ve struktuře záznamu MDT z datasetu (FR-C1, C2, R4, D-009): otázka, zhodnocení,
 * záměr, postup po modalitách, diagnostika, studie, re-MDT, závěr, podmíněné doporučení (OBC-1.1),
 * priorita nádorů (OBC-1.4), přítomní, úkoly a varovné signály. AI text je odlišený, rozhoduje lékař.
 */
export function DecisionEditor({
  decision,
  onChange,
  readOnly,
  redFlags,
}: {
  decision: Decision;
  onChange: (d: Decision) => void;
  readOnly: boolean;
  redFlags: RedFlag[];
}) {
  const s = decision.sections;
  const set = (patch: Partial<Sections>) => onChange({ ...decision, sections: { ...s, ...patch } });
  const setTop = (patch: Partial<Decision>) => onChange({ ...decision, ...patch });

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Typ projednání">
          <select
            className={fieldClass}
            value={decision.mdt_type}
            disabled={readOnly}
            onChange={(e) => setTop({ mdt_type: e.target.value as Decision['mdt_type'] })}
          >
            {Object.entries(MDT_TYPE_LABEL).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </Field>
        <Field label="Léčebný záměr">
          <select
            className={fieldClass}
            value={s.intent}
            disabled={readOnly}
            onChange={(e) => set({ intent: e.target.value as Sections['intent'] })}
          >
            {Object.entries(INTENT_LABEL).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </Field>
      </div>

      <SourcedText label="Projednaná otázka" value={s.question} onChange={(v) => set({ question: v })} readOnly={readOnly} rows={2} />
      <SourcedText
        label="Klinické zhodnocení"
        value={s.assessment}
        onChange={(v) => set({ assessment: { ...s.assessment, ...v } })}
        readOnly={readOnly}
        rows={5}
        citations={s.assessment.citations}
      />

      <Field label="Doporučený postup">
        <ul className="space-y-2">
          {s.recommendation.map((r, i) => (
            <li key={i} className={cn('space-y-1.5 rounded-lg border border-border p-2', r.source !== 'human' && 'border-l-2 border-l-ai')}>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  className={fieldClass}
                  value={r.modality}
                  disabled={readOnly}
                  aria-label="Modalita"
                  onChange={(e) =>
                    set({ recommendation: s.recommendation.map((x, j) => (j === i ? { ...x, modality: e.target.value, source: afterEdit(x.source) } : x)) })
                  }
                >
                  {Object.entries(MODALITY_LABEL).map(([v, l]) => (
                    <option key={v} value={v}>{l}</option>
                  ))}
                </select>
                <SourceBadge source={r.source} />
                {!readOnly && (
                  <button
                    type="button"
                    onClick={() => set({ recommendation: s.recommendation.filter((_, j) => j !== i) })}
                    className="ml-auto rounded p-1 text-muted-foreground hover:bg-accent hover:text-destructive"
                    aria-label="Odebrat krok postupu"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <Textarea
                rows={2}
                value={r.text}
                disabled={readOnly}
                aria-label={`Postup: ${MODALITY_LABEL[r.modality] ?? r.modality}`}
                onChange={(e) =>
                  set({ recommendation: s.recommendation.map((x, j) => (j === i ? { ...x, text: e.target.value, source: afterEdit(x.source) } : x)) })
                }
              />
            </li>
          ))}
        </ul>
        {!readOnly && (
          <button
            type="button"
            onClick={() => set({ recommendation: [...s.recommendation, { modality: 'chirurgie', text: '', source: 'human' }] })}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden /> Přidat krok postupu
          </button>
        )}
      </Field>

      <Optional
        present={!!s.extra_diagnostics}
        label="Doplňující diagnostika"
        readOnly={readOnly}
        onAdd={() => set({ extra_diagnostics: { text: '', source: 'human' } })}
        onRemove={() => set({ extra_diagnostics: undefined })}
      >
        {s.extra_diagnostics && (
          <SourcedText label="Doplňující diagnostika" value={s.extra_diagnostics} onChange={(v) => set({ extra_diagnostics: v })} readOnly={readOnly} rows={2} />
        )}
      </Optional>

      <Optional
        present={!!s.trial}
        label="Klinická studie"
        readOnly={readOnly}
        onAdd={() => set({ trial: { text: '', study_ids: [], source: 'human' } })}
        onRemove={() => set({ trial: undefined })}
      >
        {s.trial && (
          <div className="space-y-2">
            <SourcedText
              label="Klinická studie"
              value={s.trial}
              onChange={(v) => set({ trial: { ...s.trial!, ...v } })}
              readOnly={readOnly}
              rows={2}
            />
            <Field label="Studie (ID oddělená čárkou)">
              <Input
                value={s.trial.study_ids.join(', ')}
                disabled={readOnly}
                placeholder="RKT-03"
                onChange={(e) =>
                  set({ trial: { ...s.trial!, study_ids: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) } })
                }
              />
            </Field>
          </div>
        )}
      </Optional>

      <Optional
        present={!!s.re_mdt}
        label="Plánované re-MDT"
        readOnly={readOnly}
        onAdd={() => set({ re_mdt: { date: '', reason: '' } })}
        onRemove={() => set({ re_mdt: undefined })}
      >
        {s.re_mdt && (
          <div className="grid gap-2 sm:grid-cols-[10rem_1fr]">
            <Field label="Re-MDT">
              <Input type="date" value={s.re_mdt.date} disabled={readOnly} onChange={(e) => set({ re_mdt: { ...s.re_mdt!, date: e.target.value } })} />
            </Field>
            <Field label="Důvod">
              <Input value={s.re_mdt.reason} disabled={readOnly} onChange={(e) => set({ re_mdt: { ...s.re_mdt!, reason: e.target.value } })} />
            </Field>
          </div>
        )}
      </Optional>

      <SourcedText label="Závěr MDT" value={s.conclusion} onChange={(v) => set({ conclusion: v })} readOnly={readOnly} rows={3} />

      <Optional
        present={!!s.conditional}
        label="Podmíněné doporučení (neúplné podklady, OBC-1.1)"
        readOnly={readOnly}
        onAdd={() => set({ conditional: { text: '', missing: [], source: 'human' } })}
        onRemove={() => set({ conditional: undefined })}
      >
        {s.conditional && (
          <div className="space-y-2">
            <SourcedText
              label="Podmíněné doporučení (OBC-1.1)"
              value={s.conditional}
              onChange={(v) => set({ conditional: { ...s.conditional!, ...v } })}
              readOnly={readOnly}
              rows={2}
            />
            <Field label="Co chybí (oddělené čárkou)">
              <Input
                value={s.conditional.missing.join(', ')}
                disabled={readOnly}
                onChange={(e) =>
                  set({ conditional: { ...s.conditional!, missing: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) } })
                }
              />
            </Field>
          </div>
        )}
      </Optional>

      <Optional
        present={!!s.tumor_priority}
        label="Priorita léčby a plán druhého nádoru (OBC-1.4)"
        readOnly={readOnly}
        onAdd={() => set({ tumor_priority: { text: '', source: 'human' } })}
        onRemove={() => set({ tumor_priority: undefined })}
      >
        {s.tumor_priority && (
          <SourcedText
            label="Priorita léčby a plán druhého nádoru (OBC-1.4)"
            value={s.tumor_priority}
            onChange={(v) => set({ tumor_priority: v })}
            readOnly={readOnly}
            rows={2}
          />
        )}
      </Optional>

      <Field label="Přítomní">
        <ul className="space-y-1.5">
          {decision.attendees.map((a, i) => (
            <li key={i} className="flex flex-wrap items-center gap-2">
              <Input
                className="min-w-0 flex-1"
                value={a.name}
                disabled={readOnly}
                aria-label="Jméno nebo kód lékaře"
                onChange={(e) => setTop({ attendees: decision.attendees.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)) })}
              />
              <select
                className={fieldClass}
                value={a.role}
                disabled={readOnly}
                aria-label="Role"
                onChange={(e) =>
                  setTop({ attendees: decision.attendees.map((x, j) => (j === i ? { ...x, role: e.target.value as RoleId | 'chair' } : x)) })
                }
              >
                {ATTENDEE_ROLES.map((r) => (
                  <option key={r} value={r}>{roleLabel(r)}</option>
                ))}
              </select>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => setTop({ attendees: decision.attendees.filter((_, j) => j !== i) })}
                  className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-destructive"
                  aria-label="Odebrat přítomného"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </li>
          ))}
        </ul>
        {!readOnly && (
          <button
            type="button"
            onClick={() => setTop({ attendees: [...decision.attendees, { user_id: '', name: '', role: 'oncologist' }] })}
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden /> Přidat přítomného
          </button>
        )}
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input
            type="checkbox"
            checked={decision.patient_present}
            disabled={readOnly}
            onChange={(e) => setTop({ patient_present: e.target.checked })}
          />
          Pacient byl přítomen
        </label>
      </Field>

      <Field label="Úkoly po zasedání">
        <ul className="space-y-2">
          {decision.tasks.map((t, i) => {
            const update = (patch: Partial<typeof t>) =>
              setTop({ tasks: decision.tasks.map((x, j) => (j === i ? { ...x, ...patch, source: afterEdit(x.source) } : x)) });
            return (
              <li key={t.id} className={cn('space-y-1.5 rounded-lg border border-border p-2', t.source !== 'human' && 'border-l-2 border-l-ai')}>
                <div className="flex items-center gap-2">
                  <SourceBadge source={t.source} />
                  {!readOnly && (
                    <button
                      type="button"
                      onClick={() => setTop({ tasks: decision.tasks.filter((_, j) => j !== i) })}
                      className="ml-auto rounded p-1 text-muted-foreground hover:bg-accent hover:text-destructive"
                      aria-label="Odebrat úkol"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
                <Input value={t.description} disabled={readOnly} aria-label="Úkol" placeholder="Co je potřeba udělat" onChange={(e) => update({ description: e.target.value })} />
                <div className="grid gap-2 sm:grid-cols-3">
                  <Input value={t.owner} disabled={readOnly} aria-label="Kdo" placeholder="Kdo (LEK-… / role)" onChange={(e) => update({ owner: e.target.value })} />
                  <Input type="date" value={t.due_date} disabled={readOnly} aria-label="Termín" onChange={(e) => update({ due_date: e.target.value })} />
                  <select
                    className={fieldClass}
                    value={t.status}
                    disabled={readOnly}
                    aria-label="Stav úkolu"
                    onChange={(e) => update({ status: e.target.value as typeof t.status })}
                  >
                    {Object.entries(TASK_STATUS_LABEL).map(([v, l]) => (
                      <option key={v} value={v}>{l}</option>
                    ))}
                  </select>
                </div>
              </li>
            );
          })}
        </ul>
        {!readOnly && (
          <button
            type="button"
            onClick={() =>
              setTop({
                tasks: [
                  ...decision.tasks,
                  { id: `task${String(decision.tasks.length + 1).padStart(2, '0')}-${Date.now() % 10000}`, description: '', owner: '', due_date: '', status: 'requested', source: 'human' },
                ],
              })
            }
            className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
          >
            <Plus className="h-3.5 w-3.5" aria-hidden /> Přidat úkol
          </button>
        )}
      </Field>

      {redFlags.length > 0 && (
        <Field label="Varovné signály, které komise vzala na vědomí" hint={<span className="font-normal text-muted-foreground">zapíší se do IRIS jako DetectedIssue</span>}>
          <ul className="space-y-1">
            {redFlags.map((f) => (
              <li key={f.id}>
                <label className="flex items-start gap-2 text-sm text-foreground">
                  <input
                    type="checkbox"
                    className="mt-1"
                    disabled={readOnly}
                    checked={decision.red_flags_acknowledged.includes(f.id)}
                    onChange={(e) =>
                      setTop({
                        red_flags_acknowledged: e.target.checked
                          ? [...decision.red_flags_acknowledged, f.id]
                          : decision.red_flags_acknowledged.filter((x) => x !== f.id),
                      })
                    }
                  />
                  <span>
                    {f.title} <span className="text-xs text-muted-foreground">({f.rule})</span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </Field>
      )}
    </div>
  );
}
