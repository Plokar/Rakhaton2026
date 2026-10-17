'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowDown, ArrowUp, Eye, EyeOff, GripVertical, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Skeleton } from '@/components/shadcn/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys, useIntakeQuery, useObservationsQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtCase, ProjectorBlock, ProjectorLayout } from '@/types/mdt';
import { FactIcon } from './FactIcon';
import { buildKeyFacts } from './key-facts';
import { shortPatient } from './patient';
import { CaseQuickViewProjector, orderedBlocks, orderedFacts, useQuickViewSources } from './quick-view';

type Row = { id: string; name: string; label: React.ReactNode; hidden: boolean };

function moved<T>(list: T[], from: number, to: number): T[] {
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

/** Seznam s přetažením (myš) a šipkami (klávesnice); oko skryje položku v okně pro projektor. */
function SortableRows({ rows, onMove, onToggle }: { rows: Row[]; onMove: (from: number, to: number) => void; onToggle: (id: string) => void }) {
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
            aria-label={`${row.hidden ? 'Zobrazit' : 'Skrýt'} v okně pro projektor: ${row.name}`}
            title={row.hidden ? 'Zobrazit' : 'Skrýt'}
            className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            {row.hidden ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
          </button>
          <button
            type="button"
            onClick={() => onMove(i, i - 1)}
            disabled={i === 0}
            aria-label={`Posunout výš: ${row.name}`}
            className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-30"
          >
            <ArrowUp className="size-3.5" aria-hidden />
          </button>
          <button
            type="button"
            onClick={() => onMove(i, i + 1)}
            disabled={i === rows.length - 1}
            aria-label={`Posunout níž: ${row.name}`}
            className="rounded p-1 text-muted-foreground hover:bg-accent disabled:opacity-30"
          >
            <ArrowDown className="size-3.5" aria-hidden />
          </button>
        </li>
      ))}
    </ol>
  );
}

/**
 * Úprava okna pro projektor u případu (T-333): zadávající lékař skryje karty nebo jednotlivé klíčové údaje
 * a přetažením změní jejich pořadí. Skrývá se jen v projektoru, podklad i detail zůstávají celé (D-019).
 */
export function ProjectorLayoutEditor({
  patientId,
  value,
  onChange,
}: {
  patientId: string;
  value: ProjectorLayout;
  onChange: (next: ProjectorLayout) => void;
}) {
  const intake = useIntakeQuery(patientId);
  const observations = useObservationsQuery(patientId);
  const facts = React.useMemo(() => buildKeyFacts(intake.data, observations.data).facts, [intake.data, observations.data]);
  const blocks = orderedBlocks(value);
  const factRows = orderedFacts(facts, value);
  const blockHidden = blocks.filter((b) => b.hidden).map((b) => b.id);
  const factHidden = factRows.filter((r) => r.hidden).map((r) => r.fact.id);
  const toggle = <T extends string>(list: T[], id: T) => (list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);

  return (
    <div className="flex flex-col gap-5">
      <section>
        <h3 className="text-sm font-semibold">Karty</h3>
        <p className="mb-2 text-xs text-muted-foreground">Přetáhněte nebo použijte šipky. Hlavička a otázka pro MDT zůstávají vždy.</p>
        <SortableRows
          rows={blocks.map((b) => ({ id: b.id, name: b.label, label: b.label, hidden: b.hidden }))}
          onMove={(from, to) => onChange({ ...value, blocks: { order: moved(blocks.map((b) => b.id), from, to), hidden: blockHidden } })}
          onToggle={(id) =>
            onChange({ ...value, blocks: { order: blocks.map((b) => b.id), hidden: toggle(blockHidden, id as ProjectorBlock) } })
          }
        />
      </section>
      <section>
        <h3 className="text-sm font-semibold">
          Klíčové údaje{' '}
          <span className="font-normal text-muted-foreground">
            ({factRows.length - factHidden.length} z {factRows.length} zobrazeno)
          </span>
        </h3>
        <p className="mb-2 text-xs text-muted-foreground">
          Když údaje přeskládáte, okno je ukáže přesně v tomto pořadí; jinak je řadí podle závažnosti.
        </p>
        {intake.isLoading || observations.isLoading ? (
          <div className="flex flex-col gap-1.5" aria-busy="true">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-9" />)}
          </div>
        ) : (
          <SortableRows
            rows={factRows.map(({ fact, hidden }) => ({
              id: fact.id,
              name: `${fact.abbr} (${fact.label})`,
              hidden,
              label: (
                <>
                  <FactIcon status={fact.status} className="size-3.5" />
                  <b translate="no" className="shrink-0 font-semibold">{fact.abbr}</b>
                  <span className="min-w-0 truncate text-muted-foreground">
                    {(fact.value ?? fact.label).replace(new RegExp(`^${fact.abbr.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}: `), '')}
                  </span>
                </>
              ),
            }))}
            onMove={(from, to) =>
              onChange({ ...value, facts: { order: moved(factRows.map((r) => r.fact.id), from, to), hidden: factHidden } })
            }
            onToggle={(id) => onChange({ ...value, facts: { order: value.facts?.order ?? [], hidden: toggle(factHidden, id) } })}
          />
        )}
      </section>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" variant="outline" size="sm" onClick={() => onChange({})}>
          <RotateCcw aria-hidden /> Obnovit výchozí
        </Button>
        <p className="text-xs text-muted-foreground">Skryté údaje zmizí jen z okna pro projektor, v podkladu a detailu pacienta zůstávají.</p>
      </div>
    </div>
  );
}

/** Dialog s editorem a živým náhledem okna pro projektor; ukládá zadávající, přizvaný lékař nebo předseda. */
export function ProjectorLayoutDialog({ item, open, onOpenChange }: { item: MdtCase; open: boolean; onOpenChange: (open: boolean) => void }) {
  const client = useQueryClient();
  const [draft, setDraft] = React.useState<ProjectorLayout>(() => item.projector_layout ?? {});
  const [saving, setSaving] = React.useState(false);
  const sources = useQuickViewSources({ sessionId: item.session, caseId: item.id ?? null, patientId: item.patient_id });

  const save = async () => {
    if (item.id === undefined) return;
    setSaving(true);
    try {
      await mdtApi.updateCase(item.id, { projector_layout: draft });
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.session(item.session) }),
        client.invalidateQueries({ queryKey: queryKeys.sessions }),
      ]);
      toast.success('Okno pro projektor uloženo', { description: 'Otevřené okno se přepne po obnovení dat.' });
      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Rozložení se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>Okno pro projektor · {shortPatient(item)}</DialogTitle>
          <DialogDescription>Skryjte, co komise na projektoru nepotřebuje, a přetažením seřaďte údaje. Vpravo je náhled.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-5 md:grid-cols-[minmax(0,1fr)_420px]">
          <div className="max-h-[65vh] overflow-y-auto pr-1">
            <ProjectorLayoutEditor patientId={item.patient_id} value={draft} onChange={setDraft} />
          </div>
          <div className="hidden h-[65vh] overflow-hidden rounded-xl border border-border md:block" aria-label="Náhled okna pro projektor">
            <CaseQuickViewProjector sources={sources} caseId={item.id ?? null} titleAs="h2" layout={draft} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Zrušit</Button>
          <Button onClick={save} disabled={saving}>{saving ? 'Ukládám…' : 'Uložit okno pro projektor'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
