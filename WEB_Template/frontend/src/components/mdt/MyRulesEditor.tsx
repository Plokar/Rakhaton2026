'use client';

import * as React from 'react';
import { useQueries, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { mdtApi } from '@/lib/mdt-api';
import { fieldErrorMessage, queryKeys, useMyRules, useNormFields } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { DoctorNormInput, NormOp, RuleArea, TemplateArea } from '@/types/mdt';
import { AREAS } from './FactLayoutEditor';

/**
 * Moje požadavky na podklad a moje normy pro řešení (T-358–T-360, D-028, docs/UCTY_A_PVW.md §3 kroky 3–4).
 * Mění je jen lékař sám; správce je jen vidí. Použité v průvodci po prvním přihlášení i v Nastavení.
 */

export const RULE_AREAS: { id: RuleArea; label: string }[] = [
  { id: '*', label: 'Všechny diagnózy' },
  { id: 'PLI', label: 'Plíce' },
  { id: 'PRS', label: 'Prs' },
  { id: 'KRC', label: 'Kolorektum' },
  { id: 'OBC', label: 'Ostatní diagnózy' },
];
const OP_LABEL: Record<NormOp, string> = { '>=': '≥', '<=': '≤', '>': '>', '<': '<', '==': '=' };
const ECOG = [{ key: 'ecog.physician', label: 'ECOG (lékař)', category: 'header' }, { key: 'ecog.patient', label: 'ECOG podle pacienta (PROMs)', category: 'header' }];

const selectClass = 'h-9 rounded-lg border border-input bg-card px-2 text-sm';

function AreaTabs({ value, onChange, counts }: { value: RuleArea; onChange: (a: RuleArea) => void; counts?: Partial<Record<RuleArea, number>> }) {
  return (
    <div role="tablist" aria-label="Oblast diagnózy" className="flex flex-wrap gap-1.5">
      {RULE_AREAS.map((a) => (
        <button key={a.id} type="button" role="tab" aria-selected={value === a.id} onClick={() => onChange(a.id)}
          className={cn('rounded-md border px-2.5 py-1 text-[13px] font-medium',
            value === a.id ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-card text-muted-foreground hover:text-foreground')}>
          {a.label}{counts?.[a.id] ? ` (${counts[a.id]})` : ''}
        </button>
      ))}
    </div>
  );
}

/** Krok 3: údaje, které vyžaduji, když jsem na MDT pozvaný. Upozorní zadávajícího lékaře, nic neblokuje. */
export function RequirementsEditor() {
  const client = useQueryClient();
  const rules = useMyRules();
  const [area, setArea] = React.useState<RuleArea>('*');
  const catalogs = useQueries({
    queries: AREAS.map((a) => ({ queryKey: ['template-catalog', a], queryFn: () => mdtApi.getTemplateCatalog(a), staleTime: Infinity })),
  });
  const saved = rules.data?.requirements.find((r) => r.area === area);
  const [draft, setDraft] = React.useState<{ area: RuleArea; fields: string[]; note: string } | null>(null);
  const current = draft?.area === area ? draft : { area, fields: saved?.fields ?? [], note: saved?.note ?? '' };
  const [saving, setSaving] = React.useState(false);

  const groups = React.useMemo(() => {
    const areas: TemplateArea[] = area === '*' ? AREAS : [area];
    const facts = new Map<string, { key: string; label: string; category: string; categoryLabel: string }>();
    for (const e of ECOG) facts.set(e.key, { ...e, categoryLabel: 'Hlavička' });
    for (const [i, a] of AREAS.entries()) {
      if (!areas.includes(a)) continue;
      const catalog = catalogs[i]?.data;
      for (const f of catalog?.facts ?? []) {
        if (f.category === 'alerts' || facts.has(f.key)) continue;
        facts.set(f.key, { key: f.key, label: f.label, category: f.category,
          categoryLabel: catalog?.categories.find((c) => c.id === f.category)?.label ?? f.category });
      }
    }
    const out = new Map<string, { label: string; facts: { key: string; label: string }[] }>();
    for (const f of facts.values()) {
      if (!out.has(f.category)) out.set(f.category, { label: f.categoryLabel, facts: [] });
      out.get(f.category)!.facts.push(f);
    }
    return [...out.values()];
  }, [area, catalogs]);

  const loading = rules.isLoading || catalogs.some((c) => c.isLoading);
  const changed = JSON.stringify([current.fields, current.note]) !== JSON.stringify([saved?.fields ?? [], saved?.note ?? '']);
  const toggle = (key: string) => setDraft({ ...current, fields: current.fields.includes(key) ? current.fields.filter((k) => k !== key) : [...current.fields, key] });

  const save = async () => {
    setSaving(true);
    try {
      await mdtApi.saveRequirement(area, { fields: current.fields, note: current.note.trim() });
      await client.invalidateQueries({ queryKey: queryKeys.myRules });
      setDraft(null);
      toast.success('Požadavky uloženy', { description: RULE_AREAS.find((a) => a.id === area)?.label });
    } catch (err) {
      toast.error(fieldErrorMessage(err, 'Požadavky se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };

  const counts = Object.fromEntries((rules.data?.requirements ?? []).map((r) => [r.area, r.fields.length]));
  return (
    <div className="flex flex-col gap-3">
      <AreaTabs value={area} onChange={setArea} counts={counts} />
      {loading ? (
        <Skeleton className="h-48" />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            {groups.map((g) => (
              <fieldset key={g.label} className="rounded-lg border border-border p-3">
                <legend className="px-1 text-xs font-semibold text-muted-foreground">{g.label}</legend>
                <ul className="flex flex-col gap-1">
                  {g.facts.map((f) => (
                    <li key={f.key}>
                      <label className="flex items-start gap-2 text-sm">
                        <input type="checkbox" className="mt-0.5 size-4 accent-primary" checked={current.fields.includes(f.key)} onChange={() => toggle(f.key)} />
                        {f.label}
                      </label>
                    </li>
                  ))}
                </ul>
              </fieldset>
            ))}
          </div>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Poznámka pro zadávajícího lékaře (nepovinné)
            <Input value={current.note} maxLength={500} placeholder="např. k radikální radioterapii potřebuji plicní funkce ne starší 3 měsíců"
              onChange={(e) => setDraft({ ...current, note: e.target.value })} />
          </label>
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" onClick={() => void save()} disabled={!changed} isLoading={saving}>
              Uložit požadavky{current.fields.length ? ` (${current.fields.length})` : ''}
            </Button>
            {!changed && <span className="text-xs text-muted-foreground">Uloženo.</span>}
          </div>
        </>
      )}
    </div>
  );
}

const EMPTY_NORM: DoctorNormInput = { area: '*', field: '', op: '>=', value: 0, unit: '', procedure: '', note: '', source: '' };

/** Krok 4: moje normy pro řešení; na PVW se ukážou s výsledkem u pacienta, semafor nemění. */
export function NormsEditor() {
  const client = useQueryClient();
  const rules = useMyRules();
  const fields = useNormFields();
  const [form, setForm] = React.useState<DoctorNormInput & { valueText: string }>({ ...EMPTY_NORM, valueText: '' });
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState('');
  const set = <K extends keyof typeof form>(key: K, value: (typeof form)[K]) => setForm((f) => ({ ...f, [key]: value }));

  const refresh = () => client.invalidateQueries({ queryKey: queryKeys.myRules });
  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.field) return setError('Vyberte údaj.');
    if (!form.valueText.trim()) return setError('Vyplňte hodnotu.');
    setSaving(true);
    try {
      const { valueText, ...input } = form;
      await mdtApi.createNorm({ ...input, value: Number(valueText.replace(',', '.')) });
      await refresh();
      setForm({ ...EMPTY_NORM, area: form.area, valueText: '' });
      toast.success('Norma přidána');
    } catch (err) {
      setError(fieldErrorMessage(err, 'Normu se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };
  const remove = async (id: number) => {
    try {
      await mdtApi.deleteNorm(id);
      await refresh();
    } catch (err) {
      toast.error(fieldErrorMessage(err, 'Normu se nepodařilo smazat.'));
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {rules.isLoading ? (
        <Skeleton className="h-16" />
      ) : rules.data?.norms.length ? (
        <ul className="divide-y divide-border rounded-lg border border-border">
          {rules.data.norms.map((n) => (
            <li key={n.id} className="flex items-start gap-2 px-3 py-2 text-sm">
              <span className="min-w-0 flex-1">
                <span className="font-medium">{n.text}</span>
                <span className="text-muted-foreground"> · {n.area_label}{n.procedure && ` · ${n.procedure}`}</span>
                {n.source && <span translate="no" className="ml-1.5 font-mono text-[11px] text-muted-foreground">{n.source}</span>}
                {n.note && <span className="block text-xs text-muted-foreground">{n.note}</span>}
              </span>
              <Button type="button" size="sm" variant="ghost" aria-label={`Smazat normu ${n.text}`} onClick={() => void remove(n.id)}>
                <Trash2 aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-muted-foreground">Zatím žádná norma.</p>
      )}

      <form onSubmit={add} className="flex flex-col gap-3 rounded-lg border border-border p-3">
        <p className="text-sm font-medium">Nová norma</p>
        <div className="grid gap-3 sm:grid-cols-[1fr_2fr]">
          <label className="flex flex-col gap-1 text-xs font-semibold">
            Diagnózy
            <select className={selectClass} value={form.area} onChange={(e) => set('area', e.target.value as RuleArea)}>
              {RULE_AREAS.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-semibold">
            Údaj
            <select className={selectClass} value={form.field}
              onChange={(e) => {
                const field = fields.data?.find((f) => f.key === e.target.value);
                setForm((f) => ({ ...f, field: e.target.value, unit: field?.unit ?? '' }));
              }}>
              <option value="">Vyberte číselný údaj…</option>
              {(fields.data ?? []).map((f) => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
          </label>
        </div>
        <div className="grid grid-cols-[5rem_1fr_6rem] gap-3">
          <label className="flex flex-col gap-1 text-xs font-semibold">
            Podmínka
            <select className={selectClass} value={form.op} onChange={(e) => set('op', e.target.value as NormOp)}>
              {(Object.keys(OP_LABEL) as NormOp[]).map((op) => <option key={op} value={op}>{OP_LABEL[op]}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-xs font-semibold">
            Hodnota
            <Input inputMode="decimal" value={form.valueText} onChange={(e) => set('valueText', e.target.value)} placeholder="30" />
          </label>
          <label className="flex flex-col gap-1 text-xs font-semibold">
            Jednotka
            <Input value={form.unit} maxLength={20} onChange={(e) => set('unit', e.target.value)} placeholder="%" />
          </label>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-xs font-semibold">
            K postupu (nepovinné)
            <Input value={form.procedure} maxLength={120} onChange={(e) => set('procedure', e.target.value)} placeholder="resekce jater" />
          </label>
          <label className="flex flex-col gap-1 text-xs font-semibold">
            Zdroj, Evidence ID (nepovinné)
            <Input value={form.source} maxLength={60} onChange={(e) => set('source', e.target.value)} placeholder="KRC-2.1" spellCheck={false} />
          </label>
        </div>
        <label className="flex flex-col gap-1 text-xs font-semibold">
          Poznámka (nepovinné)
          <Input value={form.note} maxLength={300} onChange={(e) => set('note', e.target.value)} />
        </label>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <div>
          <Button type="submit" variant="outline" isLoading={saving}><Plus aria-hidden /> Přidat normu</Button>
        </div>
        <p className="text-xs text-muted-foreground">
          Normu vyhodnocuje aplikace z údajů pacienta s odkazem na zdroj. Když údaj chybí nebo je zapsaný jako rozmezí,
          ukáže „údaj chybí“ nebo „nelze posoudit“, nikdy neodhaduje. Barvu léčebných postupů norma nemění.
        </p>
      </form>
    </div>
  );
}
