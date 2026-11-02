'use client';

import * as React from 'react';
import { useQueries } from '@tanstack/react-query';
import { ArrowDown, ArrowUp, Eye, EyeOff, GripVertical, RotateCcw } from 'lucide-react';
import { Button } from '@/components/shadcn/button';
import { Skeleton } from '@/components/shadcn/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { cn } from '@/lib/utils';
import type { FactCategory, ProjectorBlock, ProjectorLayout, TemplateArea, TemplateCatalog, TemplatePreset } from '@/types/mdt';
import { AREA_LABEL, editorGroups, type LayoutItem } from './fact-layout';
import { FIELD_ABBR } from './key-facts';

const BLOCKS: { id: ProjectorBlock; label: string }[] = [
  { id: 'anamnesis', label: 'Anamnéza' },
  { id: 'facts', label: 'Klíčové údaje' },
  { id: 'treatments', label: 'Léčebné postupy' },
];
export const AREAS: TemplateArea[] = ['PLI', 'PRS', 'KRC', 'OBC'];

type Row = { id: string; name: string; label: React.ReactNode; hidden: boolean };

function moved<T>(list: T[], from: number, to: number): T[] {
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}
const toggled = <T extends string>(list: T[], id: T) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

/** Seznam s přetažením (myš) a šipkami (klávesnice); oko skryje položku. */
export function SortableRows({ rows, onMove, onToggle, hideVerb = 'Skrýt' }: {
  rows: Row[];
  onMove: (from: number, to: number) => void;
  onToggle: (id: string) => void;
  hideVerb?: string;
}) {
  const [drag, setDrag] = React.useState<number | null>(null);
  return (
    <ol className="flex flex-col gap-1">
      {rows.map((row, i) => (
        <li
          key={row.id}
          draggable
          onDragStart={() => setDrag(i)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => {
            if (drag !== null && drag !== i) onMove(drag, i);
            setDrag(null);
          }}
          onDragEnd={() => setDrag(null)}
          className={cn(
            'flex items-center gap-2 rounded-lg border border-border bg-card px-2 py-1.5 text-sm',
            drag === i && 'opacity-50',
            row.hidden && 'bg-muted/50 text-muted-foreground',
          )}
        >
          <GripVertical className="size-4 shrink-0 cursor-grab text-muted-foreground" aria-hidden />
          <span className={cn('flex min-w-0 flex-1 items-center gap-1.5', row.hidden && 'line-through')}>{row.label}</span>
          <button
            type="button"
            onClick={() => onToggle(row.id)}
            aria-pressed={!row.hidden}
            aria-label={`${row.hidden ? 'Zobrazit' : hideVerb}: ${row.name}`}
            title={row.hidden ? 'Zobrazit' : 'Skrýt'}
            className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            {row.hidden ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
          </button>
          <button type="button" onClick={() => onMove(i, i - 1)} disabled={i === 0} aria-label={`Posunout výš: ${row.name}`}
            className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-30">
            <ArrowUp className="size-3.5" aria-hidden />
          </button>
          <button type="button" onClick={() => onMove(i, i + 1)} disabled={i === rows.length - 1} aria-label={`Posunout níž: ${row.name}`}
            className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-30">
            <ArrowDown className="size-3.5" aria-hidden />
          </button>
        </li>
      ))}
    </ol>
  );
}

/**
 * Editor rozložení údajů (T-338): kategorie (pořadí, skrytí) a údaje v nich (pořadí, skrytí), u okna projektoru
 * i karty. Kategorie určuje systém, lékař mění jen pořadí a viditelnost (D-024). Skryté v podkladu zůstává.
 */
export function FactLayoutEditor({ items, value, onChange, blocks = false, hideVerb = 'Skrýt', loading = false }: {
  items: LayoutItem[];
  value: ProjectorLayout;
  onChange: (next: ProjectorLayout) => void;
  blocks?: boolean;
  hideVerb?: string;
  loading?: boolean;
}) {
  const groups = editorGroups(items, value);
  const categoryOrder = groups.map((g) => g.category);
  const hiddenCategories = groups.filter((g) => g.hidden).map((g) => g.category);
  const allKeys = groups.flatMap((g) => g.items.map((x) => x.item.key));
  const hiddenFacts = value.facts?.hidden ?? [];
  const setCategories = (order: FactCategory[], hidden: FactCategory[]) => onChange({ ...value, categories: { order, hidden } });
  const blockRows = (() => {
    const order = [...new Set([...(value.blocks?.order ?? []), ...BLOCKS.map((b) => b.id)])];
    const hidden = value.blocks?.hidden ?? [];
    return { order, hidden };
  })();
  const shown = items.length - groups.reduce((n, g) => n + (g.hidden ? g.items.length : g.items.filter((x) => x.hidden).length), 0);

  return (
    <div className="flex flex-col gap-5">
      {blocks && (
        <section>
          <h3 className="text-sm font-semibold">Karty</h3>
          <p className="mb-2 text-xs text-muted-foreground">Hlavička a otázka pro MDT zůstávají vždy.</p>
          <SortableRows
            hideVerb={hideVerb}
            rows={blockRows.order.map((id) => {
              const label = BLOCKS.find((b) => b.id === id)!.label;
              return { id, name: label, label, hidden: blockRows.hidden.includes(id) };
            })}
            onMove={(from, to) => onChange({ ...value, blocks: { order: moved(blockRows.order, from, to), hidden: blockRows.hidden } })}
            onToggle={(id) => onChange({ ...value, blocks: { order: blockRows.order, hidden: toggled(blockRows.hidden, id as ProjectorBlock) } })}
          />
        </section>
      )}
      {loading ? (
        <div className="flex flex-col gap-1.5" aria-busy="true">{[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-9" />)}</div>
      ) : (
        <>
          <section>
            <h3 className="text-sm font-semibold">
              Kategorie <span className="font-normal text-muted-foreground">(zobrazeno {shown} z {items.length} údajů)</span>
            </h3>
            <p className="mb-2 text-xs text-muted-foreground">
              Kategorie určuje systém, aby se výsledky vyšetření nepletly s dotazníky. Vy měníte pořadí a co je vidět.
            </p>
            <SortableRows
              hideVerb={hideVerb}
              rows={groups.map((g) => ({ id: g.category, name: g.label, label: g.label, hidden: g.hidden }))}
              onMove={(from, to) => setCategories(moved(categoryOrder, from, to), hiddenCategories)}
              onToggle={(id) => setCategories(categoryOrder, toggled(hiddenCategories, id as FactCategory))}
            />
          </section>
          {groups.map((g) => (
            <section key={g.category} className={cn(g.hidden && 'opacity-60')}>
              <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                {g.label}{g.hidden && ' · skrytá celá kategorie'}
              </h3>
              <SortableRows
                hideVerb={hideVerb}
                rows={g.items.map(({ item, hidden }) => ({
                  id: item.key,
                  name: `${item.abbr} (${item.label})`,
                  hidden,
                  label: (
                    <>
                      <b translate="no" className="shrink-0 font-semibold">{item.abbr}</b>
                      <span className="min-w-0 truncate text-muted-foreground">{item.detail ?? (item.label !== item.abbr ? item.label : null)}</span>
                    </>
                  ),
                }))}
                onMove={(from, to) => {
                  const keys = g.items.map((x) => x.item.key);
                  const next = moved(keys, from, to);
                  const start = allKeys.indexOf(keys[0]);
                  const order = [...allKeys.slice(0, start), ...next, ...allKeys.slice(start + keys.length)];
                  onChange({ ...value, categories: { order: categoryOrder, hidden: hiddenCategories }, facts: { order, hidden: hiddenFacts } });
                }}
                onToggle={(id) => onChange({ ...value, facts: { order: value.facts?.order ?? [], hidden: toggled(hiddenFacts, id) } })}
              />
            </section>
          ))}
        </>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="outline" size="sm" onClick={() => onChange({})}>
          <RotateCcw aria-hidden /> Obnovit výchozí
        </Button>
        <p className="text-xs text-muted-foreground">Skryté údaje jsou o klik dál, závažný údaj se ukáže vždy. Podklad zůstává celý.</p>
      </div>
    </div>
  );
}

/** Údaje katalogu oblasti jako položky editoru (zkratka jako v přehledu). */
export function catalogItems(catalog: TemplateCatalog | undefined): LayoutItem[] {
  return (catalog?.facts ?? []).map((f) => ({
    key: f.key,
    abbr: f.abbr ?? FIELD_ABBR[f.key] ?? (f.key.startsWith('alert:') ? f.key.slice(6) : f.label),
    label: f.label,
    category: f.category,
  }));
}

/** Preset pro profesi a oblast: shoda odbornosti, jinak výchozí. */
export function presetFor(presets: TemplatePreset[], specialty: string | null | undefined, area: TemplateArea): TemplatePreset | undefined {
  return presets.find((p) => specialty && p.specialties.includes(specialty) && (p.area === area || p.area === '*'))
    ?? presets.find((p) => p.id === 'vychozi');
}

/** Katalogy všech oblastí (veřejné, v cache natrvalo). */
export function useCatalogs() {
  const results = useQueries({
    queries: AREAS.map((area) => ({ queryKey: ['template-catalog', area], queryFn: () => mdtApi.getTemplateCatalog(area), staleTime: Infinity })),
  });
  return Object.fromEntries(AREAS.map((area, i) => [area, results[i]])) as Record<TemplateArea, (typeof results)[number]>;
}

/**
 * Šablony po oblastech (plíce, prs, kolorektum, ostatní): záložky, preset a editor. Řízená komponenta:
 * `value[area]` = rozložení (prázdné = výchozí pořadí). Používá registrace, Tým i Nastavení.
 */
export function TemplateAreasEditor({ value, onChange, specialty, initFromPresets = false }: {
  value: Partial<Record<TemplateArea, ProjectorLayout>>;
  onChange: (next: Partial<Record<TemplateArea, ProjectorLayout>>, presetId?: string) => void;
  specialty?: string | null;
  /** Při zakládání: oblasti bez hodnoty předvyplnit presetem podle profese. */
  initFromPresets?: boolean;
}) {
  const catalogs = useCatalogs();
  const [area, setArea] = React.useState<TemplateArea>(specialty === 'pulmonologist' ? 'PLI' : 'PLI');
  const ready = AREAS.every((a) => catalogs[a].data);
  const seeded = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (!initFromPresets || !ready || seeded.current === (specialty ?? '')) return;
    seeded.current = specialty ?? '';
    const next: Partial<Record<TemplateArea, ProjectorLayout>> = {};
    let used: string | undefined;
    for (const a of AREAS) {
      const preset = presetFor(catalogs[a].data!.presets, specialty, a);
      next[a] = preset?.layout ?? {};
      if (preset && preset.id !== 'vychozi') used = preset.id;
    }
    onChange(next, used);
  }, [initFromPresets, ready, specialty, catalogs, onChange]);

  const catalog = catalogs[area].data;
  const presets = catalog?.presets ?? [];
  return (
    <div className="flex flex-col gap-3">
      <div role="tablist" aria-label="Oblast šablony" className="flex flex-wrap gap-1">
        {AREAS.map((a) => (
          <button
            key={a}
            type="button"
            role="tab"
            aria-selected={a === area}
            onClick={() => setArea(a)}
            className={cn(
              'rounded-lg border px-3 py-1.5 text-sm transition-colors',
              a === area ? 'border-primary bg-primary/10 font-medium text-foreground' : 'border-border text-muted-foreground hover:bg-muted',
            )}
          >
            {AREA_LABEL[a]}
            {Object.keys(value[a] ?? {}).length > 0 && <span className="ml-1 text-xs text-primary">●</span>}
          </button>
        ))}
      </div>
      {presets.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">Začít od presetu:</span>
          {presets.map((p) => (
            <Button key={p.id} type="button" variant="outline" size="sm" title={p.note} onClick={() => onChange({ ...value, [area]: p.layout }, p.id)}>
              {p.name}
            </Button>
          ))}
        </div>
      )}
      <FactLayoutEditor
        items={catalogItems(catalog)}
        loading={!catalog}
        value={value[area] ?? {}}
        onChange={(layout) => onChange({ ...value, [area]: layout })}
      />
    </div>
  );
}
