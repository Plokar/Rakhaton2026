'use client';

import * as React from 'react';
import { Plus, Scale, Trash2, UserRoundSearch } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import type { Decision, EvidenceId, Light, ProcedureCompatibility, RedFlag, RoleId, Source } from '@/types/mdt';
import { Citations } from './citations';
import { CompatibilityLight } from './CompatibilityLight';
import { PractitionerPicker } from './PractitionerPicker';
import { ROLE_META } from './roles';

/** Koho vybírá popup lékařů (T-328): nového přítomného, nebo vlastníka úkolu. */
type PickerTarget = { kind: 'attendee'; index?: number } | { kind: 'task'; index: number };

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
  'nuclear_medicine', 'palliative_care', 'geriatrician', 'geneticist', 'coordinator',
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
 * Kontrola souladu s guidelines při zápisu (zadání B2), stejné pravidlo jako backend `guideline_deviation`:
 * zvolený postup má v semaforu „pozor“ / „vylučuje“, nebo předseda uvedl „není v souladu“ → chce krátké zdůvodnění.
 * Odchylka nic neblokuje; bez zdůvodnění jen nejde závěr potvrdit.
 */
export function guidelineDeviation(s: Sections): string | null {
  const risky = (s.options_considered ?? []).filter((o) => o.chosen && (o.light === 'red' || o.light === 'orange')).map((o) => o.title);
  const compliance = s.guideline_compliance;
  if (risky.length === 0 && !(compliance && !compliance.compliant)) return null;
  if (compliance?.reason.trim()) return null;
  return risky.length
    ? `Zvolený postup má v semaforu „pozor“ nebo „vylučuje“ (${risky.join('; ')}). Uveďte soulad s doporučenými postupy a krátké zdůvodnění.`
    : 'Závěr se odchyluje od doporučených postupů. Doplňte krátké zdůvodnění odchylky.';
}

/**
 * Co před potvrzením závěru zbývá (stejný princip jako formulář zařazení): nic se nesmí zapomenout.
 * Prázdný seznam = jde potvrdit. Odchylka od guidelines sama neblokuje, jen chce zdůvodnění (B2).
 */
export function decisionChecklist(decision: Decision, redFlagIds: string[]): string[] {
  const s = decision.sections;
  const todo: string[] = [];
  if (!s.question.text.trim()) todo.push('Projednaná otázka');
  if (!s.assessment.text.trim()) todo.push('Klinické zhodnocení');
  const chosen = (s.options_considered ?? []).some((o) => o.chosen);
  if (!chosen && !s.recommendation.some((r) => r.text.trim())) todo.push('Zvolený postup (zvažované možnosti) nebo krok doporučeného postupu');
  if (!s.guideline_compliance) todo.push('V souladu s guidelines? Ano / Ne');
  const deviation = guidelineDeviation(s);
  if (deviation) todo.push('Zdůvodnění souladu s guidelines (zvolený postup „pozor“ / „vylučuje“ nebo odchylka)');
  if (!s.conclusion.text.trim()) todo.push('Závěr MDT');
  const unnamed = decision.attendees.filter((a) => !a.user_id && a.role !== 'chair');
  if (unnamed.length) todo.push(`Přítomní: vybrat lékaře (${unnamed.map((a) => a.name || 'bez role').join(', ')})`);
  decision.tasks.forEach((t, i) => {
    const gaps = [!t.description.trim() && 'popis', !t.owner && 'komu', !t.due_date && 'termín'].filter(Boolean);
    if (gaps.length) todo.push(`Úkol ${i + 1}: ${gaps.join(', ')}`);
  });
  const open = redFlagIds.filter((id) => !decision.red_flags_acknowledged.includes(id)).length;
  if (open) todo.push(`Varovné signály vzít na vědomí: ${open}`);
  return todo;
}

type OptionRow = { id: string; title: string; light: Light | null; citations: EvidenceId[]; considered: boolean; chosen: boolean };

/**
 * Zvažované možnosti (všechny postupy ze semaforu, i červené, D-015) se zvoleným postupem a soulad s guidelines
 * (ano / ne + důvod odchylky). Barvu semaforu počítá kód, tady se jen uloží do záznamu.
 */
function GuidelineCompliance({
  s,
  set,
  options,
  readOnly,
}: {
  s: Sections;
  set: (patch: Partial<Sections>) => void;
  options: ProcedureCompatibility[];
  readOnly: boolean;
}) {
  const saved = new Map((s.options_considered ?? []).map((o) => [o.id, o]));
  const rows: OptionRow[] = options.length
    ? options.map((o) => ({
        id: o.id,
        title: o.title,
        light: o.compatibility.overall,
        citations: o.guideline_citations,
        considered: saved.has(o.id),
        chosen: saved.get(o.id)?.chosen ?? false,
      }))
    : (s.options_considered ?? []).map((o) => ({ ...o, light: o.light ?? null, citations: [], considered: true }));
  const shown = readOnly ? rows.filter((r) => r.considered) : rows;
  const compliance = s.guideline_compliance ?? null;
  const deviation = guidelineDeviation(s);
  const reasonId = React.useId();

  const write = (row: OptionRow, next: { considered: boolean; chosen: boolean }) => {
    const rest = (s.options_considered ?? []).filter((o) => o.id !== row.id);
    set({
      options_considered: next.considered || next.chosen
        ? [...rest, { id: row.id, title: row.title, light: row.light, chosen: next.chosen }]
        : rest,
    });
  };
  const setCompliant = (compliant: boolean) => {
    const chosenCitations = rows.filter((r) => r.chosen).flatMap((r) => r.citations);
    set({
      guideline_compliance: {
        compliant,
        reason: compliance?.reason ?? '',
        citations: compliance?.citations.length ? compliance.citations : [...new Set(chosenCitations)],
      },
    });
  };

  return (
    <Field
      label="Zvažované možnosti a soulad s doporučenými postupy"
      hint={<span className="font-normal text-muted-foreground">semafor počítá kód, rozhoduje komise</span>}
    >
      {shown.length > 0 ? (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {shown.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
              <label className="flex min-w-0 flex-1 items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  className="mt-1"
                  checked={row.considered}
                  disabled={readOnly}
                  onChange={(e) => write(row, { considered: e.target.checked, chosen: e.target.checked && row.chosen })}
                />
                <span className="min-w-0">
                  {row.title}
                  <Citations ids={row.citations} />
                </span>
              </label>
              {row.light && <CompatibilityLight light={row.light} />}
              <label className={cn('flex items-center gap-1.5 text-xs font-medium', row.chosen ? 'text-foreground' : 'text-muted-foreground')}>
                <input
                  type="checkbox"
                  checked={row.chosen}
                  disabled={readOnly}
                  onChange={(e) => write(row, { considered: true, chosen: e.target.checked })}
                />
                zvoleno
              </label>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">
          {readOnly ? 'Zvažované možnosti nebyly zapsány.' : 'Možnosti ze semaforu se načítají z podkladu případu.'}
        </p>
      )}

      <fieldset className="flex flex-wrap items-center gap-x-4 gap-y-1.5 pt-1 text-sm">
        <legend className="sr-only">Soulad s doporučenými postupy</legend>
        <span className="text-[13px] font-medium">V souladu s guidelines?</span>
        {([true, false] as const).map((value) => (
          <label key={String(value)} className="flex items-center gap-1.5">
            <input
              type="radio"
              name="guideline-compliance"
              checked={compliance?.compliant === value}
              disabled={readOnly}
              onChange={() => setCompliant(value)}
            />
            {value ? 'Ano' : 'Ne, odchylka'}
          </label>
        ))}
        {compliance && compliance.citations.length > 0 && (
          <span className="text-xs text-muted-foreground">
            Pasáže:
            <Citations ids={compliance.citations} />
          </span>
        )}
      </fieldset>
      {(deviation || (compliance && (!compliance.compliant || compliance.reason))) && (
        <div className="space-y-1">
          <label htmlFor={reasonId} className="text-[13px] font-medium">Zdůvodnění odchylky</label>
          <Input
            id={reasonId}
            value={compliance?.reason ?? ''}
            disabled={readOnly}
            placeholder="Krátce, proč se komise od doporučených postupů odchyluje"
            onChange={(e) =>
              set({ guideline_compliance: { compliant: compliance?.compliant ?? false, citations: compliance?.citations ?? [], reason: e.target.value } })
            }
          />
        </div>
      )}
      {deviation && (
        <p role="status" className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:bg-amber-400/10 dark:text-amber-200">
          <Scale className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            <span className="font-medium">Kontrola souladu s guidelines:</span> {deviation} Závěr to neblokuje, bez zdůvodnění ho ale nejde potvrdit.
          </span>
        </p>
      )}
    </Field>
  );
}

/** Odlišná stanoviska členů komise (zadání C): kdo, v jaké roli a co. */
function Dissent({ s, set, readOnly }: { s: Sections; set: (patch: Partial<Sections>) => void; readOnly: boolean }) {
  const items = s.dissent ?? [];
  const update = (i: number, patch: Partial<NonNullable<Sections['dissent']>[number]>) =>
    set({ dissent: items.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
  return (
    <Field label="Odlišná stanoviska členů">
      {items.length === 0 && <p className="text-sm text-muted-foreground">Bez odlišného stanoviska.</p>}
      <ul className="space-y-2">
        {items.map((d, i) => (
          <li key={i} className="space-y-1.5 rounded-lg border border-border p-2">
            <div className="flex flex-wrap items-center gap-2">
              <Input
                className="min-w-0 flex-1"
                value={d.member}
                disabled={readOnly}
                aria-label="Člen komise"
                placeholder="Jméno nebo kód lékaře"
                onChange={(e) => update(i, { member: e.target.value })}
              />
              <select
                className={fieldClass}
                value={d.role}
                disabled={readOnly}
                aria-label="Role"
                onChange={(e) => update(i, { role: e.target.value as RoleId | 'chair' })}
              >
                {ATTENDEE_ROLES.map((r) => (
                  <option key={r} value={r}>{roleLabel(r)}</option>
                ))}
              </select>
              {!readOnly && (
                <button
                  type="button"
                  onClick={() => set({ dissent: items.filter((_, j) => j !== i) })}
                  className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-destructive"
                  aria-label="Odebrat stanovisko"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <Textarea
              rows={2}
              value={d.text}
              disabled={readOnly}
              aria-label="Stanovisko"
              placeholder="V čem se stanovisko liší a proč"
              onChange={(e) => update(i, { text: e.target.value })}
            />
          </li>
        ))}
      </ul>
      {!readOnly && (
        <button
          type="button"
          onClick={() => set({ dissent: [...items, { member: '', role: 'surgeon', text: '' }] })}
          className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden /> Přidat odlišné stanovisko
        </button>
      )}
    </Field>
  );
}

/**
 * Zápis závěru komise ve struktuře záznamu MDT z datasetu (FR-C1, C2, R4, D-009): otázka, zhodnocení,
 * záměr, postup po modalitách, zvažované možnosti a soulad s guidelines (zadání B2, C), diagnostika, studie,
 * re-MDT, závěr, podmíněné doporučení (OBC-1.1), priorita nádorů (OBC-1.4), přítomní, odlišná stanoviska,
 * úkoly a varovné signály. AI text je odlišený, rozhoduje lékař.
 */
export function DecisionEditor({
  decision,
  onChange,
  readOnly,
  redFlags,
  options = [],
}: {
  decision: Decision;
  onChange: (d: Decision) => void;
  readOnly: boolean;
  redFlags: RedFlag[];
  /** Postupy ze semaforu (GET compatibility) pro zvažované možnosti; bez nich se ukáže jen uložený výběr. */
  options?: ProcedureCompatibility[];
}) {
  const s = decision.sections;
  const set = (patch: Partial<Sections>) => onChange({ ...decision, sections: { ...s, ...patch } });
  const setTop = (patch: Partial<Decision>) => onChange({ ...decision, ...patch });
  const [picker, setPicker] = React.useState<PickerTarget | null>(null);

  return (
    <div className="space-y-5">
      <PractitionerPicker
        open={picker !== null}
        onOpenChange={(open) => !open && setPicker(null)}
        title={picker?.kind === 'task' ? 'Komu úkol přidělit' : 'Přidat přítomného'}
        excludeIds={picker?.kind === 'attendee' ? decision.attendees.map((a) => a.user_id) : []}
        preferRole={picker?.kind === 'attendee' && picker.index !== undefined ? decision.attendees[picker.index]?.role : null}
        onSelect={(p) => {
          if (picker?.kind === 'attendee' && picker.index !== undefined) {
            // řádek role z nastavení podkladu („Chirurg“) dostane konkrétního lékaře, role zůstává
            const i = picker.index;
            setTop({ attendees: decision.attendees.map((x, j) => (j === i ? { ...x, user_id: p.id, name: p.name } : x)) });
          } else if (picker?.kind === 'attendee') {
            setTop({ attendees: [...decision.attendees, { user_id: p.id, name: p.name, role: p.role ?? 'oncologist' }] });
          } else if (picker?.kind === 'task') {
            const i = picker.index;
            setTop({
              tasks: decision.tasks.map((x, j) => (j === i ? { ...x, owner: p.id, owner_name: p.name, source: afterEdit(x.source) } : x)),
            });
          }
        }}
      />
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

      <GuidelineCompliance s={s} set={set} options={options} readOnly={readOnly} />

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
              {a.user_id || readOnly ? (
                <span className="min-w-0 flex-1 truncate text-sm" title={a.user_id || undefined}>
                  {a.name || a.user_id || 'Bez jména'}
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => setPicker({ kind: 'attendee', index: i })}
                  className="inline-flex min-w-0 flex-1 items-center gap-1.5 truncate text-left text-sm text-primary hover:underline"
                >
                  <UserRoundSearch className="h-3.5 w-3.5 shrink-0" aria-hidden />
                  <span className="truncate">{a.name ? `${a.name}: vybrat lékaře…` : 'Vybrat lékaře…'}</span>
                </button>
              )}
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
            onClick={() => setPicker({ kind: 'attendee' })}
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

      <Dissent s={s} set={set} readOnly={readOnly} />

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
                  <button
                    type="button"
                    disabled={readOnly}
                    onClick={() => setPicker({ kind: 'task', index: i })}
                    aria-label={`Komu: ${t.owner_name || t.owner || 'nevybráno'}. Vybrat lékaře`}
                    title={t.owner || undefined}
                    className={cn(fieldClass, 'flex min-w-0 items-center gap-1.5 text-left disabled:cursor-default', !t.owner && 'text-muted-foreground')}
                  >
                    <UserRoundSearch className="h-3.5 w-3.5 shrink-0" aria-hidden />
                    <span className="truncate">{t.owner_name || t.owner || 'Vybrat lékaře…'}</span>
                  </button>
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
