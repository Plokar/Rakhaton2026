'use client';

import * as React from 'react';
import { MonitorUp } from 'lucide-react';
import { Skeleton } from '@/components/shadcn/skeleton';
import { useTemplateCatalog } from '@/lib/queries';
import type { ProjectorBlock, ProjectorLayout, TemplateArea } from '@/types/mdt';
import { AREA_LABEL } from './fact-layout';

const BLOCK_LABEL: Record<Exclude<ProjectorBlock, 'anamnesis'>, string> = {
  facts: 'Klíčové údaje',
  treatments: 'Léčebné postupy',
  norms: 'Normy pozvaných lékařů',
};
const MAX_CHIPS = 8;

/** Pořadí podle lékaře: známé položky v jeho pořadí, ostatní za nimi, skryté pryč. */
function arrange<T extends string>(all: T[], part?: { order?: T[]; hidden?: T[] }): T[] {
  const order = [...new Set([...(part?.order ?? []).filter((id) => all.includes(id)), ...all])];
  const hidden = new Set(part?.hidden ?? []);
  return order.filter((id) => !hidden.has(id));
}

/**
 * Živý náhled PVW (projektor view, okno pro projektor) podle šablony lékaře (T-363, D-025): rozvržení bez dat
 * pacienta, takže funguje i pro lékaře z jiné nemocnice a při zakládání účtu. Ukazuje, co uvidí komise
 * a v jakém pořadí; skutečný panel má navíc hodnoty, stav a citace.
 */
export function PvwSketch({ area, layout }: { area: TemplateArea; layout: ProjectorLayout | undefined }) {
  const catalog = useTemplateCatalog(area);
  const groups = React.useMemo(() => {
    const data = catalog.data;
    if (!data) return [];
    const categories = arrange(data.categories.map((c) => c.id), layout?.categories);
    const facts = arrange(data.facts.map((f) => f.key), layout?.facts);
    return categories
      .map((id) => ({
        id,
        label: id === 'alerts' ? 'Upozornění' : data.categories.find((c) => c.id === id)?.label ?? id,
        facts: facts.map((key) => data.facts.find((f) => f.key === key)!).filter((f) => f.category === id),
      }))
      .filter((g) => g.facts.length);
  }, [catalog.data, layout]);
  const blocks = arrange(['facts', 'treatments', 'norms'] as Exclude<ProjectorBlock, 'anamnesis'>[],
    layout?.blocks as { order?: Exclude<ProjectorBlock, 'anamnesis'>[]; hidden?: Exclude<ProjectorBlock, 'anamnesis'>[] } | undefined);

  return (
    <figure className="flex flex-col gap-2 rounded-xl border border-border bg-muted p-2" aria-label={`Náhled PVW pro oblast ${AREA_LABEL[area]}`}>
      <figcaption className="flex items-center gap-1.5 px-1 text-xs font-medium text-muted-foreground">
        <MonitorUp className="size-3.5" aria-hidden /> Náhled PVW · {AREA_LABEL[area]}
      </figcaption>
      <div className="rounded-lg bg-card px-3 py-2 text-[13px]">
        <span className="font-semibold">Pxx · pohlaví · věk</span>
        <span className="text-muted-foreground"> · diagnóza + TNM · ECOG lékař / pacient · C/P</span>
      </div>
      {catalog.isLoading ? (
        <Skeleton className="h-40" />
      ) : (
        blocks.map((b) => (
          <section key={b} className="rounded-lg bg-card px-3 py-2">
            <h3 className="text-sm font-semibold">{BLOCK_LABEL[b]}</h3>
            {b === 'facts' ? (
              <div className="mt-1.5 flex flex-col gap-2">
                {groups.map((g) => (
                  <div key={g.id}>
                    <p className="text-[11px] font-medium text-muted-foreground">{g.label}</p>
                    <ul className="mt-0.5 flex flex-wrap gap-1">
                      {g.facts.slice(0, MAX_CHIPS).map((f) => (
                        <li key={f.key} className="rounded border border-border px-1.5 py-0.5 text-[12px]">{f.abbr ?? f.label}</li>
                      ))}
                      {g.facts.length > MAX_CHIPS && <li className="px-1 text-[12px] text-muted-foreground">+{g.facts.length - MAX_CHIPS}</li>}
                    </ul>
                  </div>
                ))}
                {!groups.length && <p className="text-xs text-muted-foreground">Všechny údaje jsou skryté.</p>}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">
                {b === 'treatments'
                  ? 'Všechny postupy se semaforem souladu (barvu počítají pravidla).'
                  : 'Normy lékařů pozvaných na zasedání s hodnotou pacienta.'}
              </p>
            )}
          </section>
        ))
      )}
      <div className="rounded-lg bg-card px-3 py-2 text-[13px] text-muted-foreground">Otázka pro MDT · MKN-10</div>
      <p className="px-1 text-[11px] text-muted-foreground">Údaj se stavem „závažné“ se ukáže, i když ho skryjete.</p>
    </figure>
  );
}
