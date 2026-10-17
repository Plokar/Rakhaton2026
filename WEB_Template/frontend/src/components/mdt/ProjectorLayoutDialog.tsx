'use client';

import * as React from 'react';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type Announcements,
  type DragEndEvent,
  type Modifier,
  type UniqueIdentifier,
} from '@dnd-kit/core';
import { SortableContext, arrayMove, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { ArrowDown, ArrowUp, GripVertical, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { apiErrorMessage, useProjectorLayout } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtCase, ProjectorLayout, ProjectorSection } from '@/types/mdt';
import { buildKeyFacts } from './key-facts';
import { shortPatient } from './patient';
import { publishRefresh } from './projector';
import {
  CaseQuickViewProjector,
  PROJECTOR_BLOCKS,
  PROJECTOR_WINDOW_BLOCKS,
  projectorBlockOrder,
  projectorFactOrder,
  type QuickViewSources,
} from './quick-view';

interface Row {
  id: string;
  label: string;
  detail?: string;
}

const DEFAULT_BLOCKS = PROJECTOR_WINDOW_BLOCKS;
/** Bloky okna projektoru v uloženém pořadí (šablonu okno nemá, T-330). */
const windowBlocks = (layout: MdtCase['projector_layout']) =>
  projectorBlockOrder(layout).filter((b) => PROJECTOR_WINDOW_BLOCKS.includes(b));
const sameOrder = (a: readonly string[], b: readonly string[]) => a.length === b.length && a.every((id, i) => id === b[i]);
/** Řádky se posouvají jen svisle. */
const verticalOnly: Modifier = ({ transform }) => ({ ...transform, x: 0 });

/**
 * Pořadí informací ve shrnutí pro projektor (T-332): bloky úzkého panelu a klíčové údaje. Mění ho
 * zadávající lékař, přizvaný nebo předseda; uloží se k případu (`projector_layout`) a okno projektoru
 * se obnoví samo. Vpravo živý náhled úzkého panelu.
 */
export function ProjectorLayoutDialog({
  item,
  sources,
  open,
  onOpenChange,
}: {
  item: MdtCase;
  sources: QuickViewSources;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const save = useProjectorLayout(item.session);
  const { facts } = React.useMemo(
    () => buildKeyFacts(sources.intake.data, sources.observations.data),
    [sources.intake.data, sources.observations.data],
  );
  const [blocks, setBlocks] = React.useState<ProjectorSection[]>(() => windowBlocks(item.projector_layout));
  /** `null` = výchozí pořadí údajů (závažné nahoře, balené do řádků). */
  const [factIds, setFactIds] = React.useState<string[] | null>(() => item.projector_layout?.facts ?? null);
  // Esc během přesunu klávesnicí zruší jen přesun, ne celý dialog (příznak se uvolní až po dokončení události).
  const dragging = React.useRef(false);
  const onDragging = React.useCallback((active: boolean) => {
    if (active) dragging.current = true;
    else setTimeout(() => (dragging.current = false));
  }, []);

  const draft: ProjectorLayout = React.useMemo(
    () => ({
      ...(sameOrder(blocks, DEFAULT_BLOCKS) ? {} : { sections: blocks }),
      ...(factIds ? { facts: factIds } : {}),
    }),
    [blocks, factIds],
  );
  const orderedFacts = projectorFactOrder(facts, draft);
  const factRows: Row[] = orderedFacts.map((f) => ({ id: f.id, label: f.abbr, detail: f.value ?? 'chybí' }));
  const blockRows: Row[] = blocks.map((id) => ({ id, label: PROJECTOR_BLOCKS[id] }));

  const preview: QuickViewSources = React.useMemo(() => {
    const data = sources.session.data;
    if (!data) return sources;
    const cases = data.cases.map((c) => (c.id === item.id ? { ...c, projector_layout: draft } : c));
    return { ...sources, session: { ...sources.session, data: { ...data, cases } } };
  }, [sources, item.id, draft]);

  const reset = () => {
    setBlocks(DEFAULT_BLOCKS);
    setFactIds(null);
  };
  const submit = () => {
    if (item.id == null) return;
    save.mutate(
      { caseId: item.id, layout: draft },
      {
        onSuccess: () => {
          publishRefresh(item.session);
          toast.success('Pořadí na projektoru uloženo', { description: 'Okno projektoru se obnoví samo.' });
          onOpenChange(false);
        },
        onError: (error) => toast.error(apiErrorMessage(error, 'Pořadí se nepodařilo uložit.')),
      },
    );
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next, details) => {
        if (dragging.current && details.reason === 'escape-key') {
          // Esc patří přesunu (dnd-kit ho zruší), dialog zůstane otevřený.
          details.allowPropagation();
          details.cancel();
          return;
        }
        if (!save.isPending) onOpenChange(next);
      }}
    >
      <DialogContent className="max-h-[calc(100dvh-2rem)] grid-rows-[auto_minmax(0,1fr)_auto] sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>Pořadí na projektoru · {shortPatient(item)}</DialogTitle>
          <DialogDescription>
            Přetáhněte za úchyt nebo posuňte šipkami. Platí pro tohoto pacienta, vidí ho celá komise.
          </DialogDescription>
        </DialogHeader>
        <div className="grid min-h-0 gap-5 md:grid-cols-[minmax(0,1fr)_380px]">
          <div className="flex min-h-0 flex-col gap-5 overflow-y-auto pr-1">
            <SortableRows
              title="Bloky"
              hint="Hlavička s ECOG nahoře a otázka komise dole zůstávají."
              rows={blockRows}
              onMove={(from, to) => setBlocks((prev) => arrayMove(prev, from, to))}
              onDragging={onDragging}
            />
            <SortableRows
              title="Klíčové údaje"
              hint={factIds ? 'Vlastní pořadí.' : 'Výchozí pořadí: závažné a mimo normu nahoře.'}
              rows={factRows}
              empty="Klíčové údaje se ještě načítají nebo v IRIS chybí."
              onMove={(from, to) => setFactIds(arrayMove(orderedFacts.map((f) => f.id), from, to))}
              onDragging={onDragging}
            />
          </div>
          <section aria-label="Náhled úzkého panelu" className="hidden min-h-0 flex-col gap-1.5 md:flex">
            <p className="text-xs font-medium text-muted-foreground">Náhled</p>
            <div className="h-[min(640px,calc(100dvh-14rem))] overflow-hidden rounded-lg border border-border">
              <CaseQuickViewProjector sources={preview} caseId={item.id ?? null} titleAs="h2" />
            </div>
          </section>
        </div>
        <DialogFooter className="items-center sm:justify-between">
          <Button variant="ghost" onClick={reset} disabled={sameOrder(blocks, DEFAULT_BLOCKS) && !factIds}>
            <RotateCcw aria-hidden /> Výchozí pořadí
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={save.isPending}>
              Zrušit
            </Button>
            <Button onClick={submit} disabled={save.isPending}>
              Uložit pořadí
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function SortableRows({
  title,
  hint,
  rows,
  empty,
  onMove,
  onDragging,
}: {
  title: string;
  hint: string;
  rows: Row[];
  empty?: string;
  onMove: (from: number, to: number) => void;
  onDragging: (active: boolean) => void;
}) {
  const headingId = React.useId();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const ids = rows.map((r) => r.id);
  const label = (id: UniqueIdentifier) => rows.find((r) => r.id === id)?.label ?? String(id);
  const position = (id: UniqueIdentifier | undefined) => `pozici ${ids.indexOf(String(id)) + 1} z ${ids.length}`;
  const announcements: Announcements = {
    onDragStart: ({ active }) => `Zvednuto: ${label(active.id)}, ${position(active.id)}.`,
    onDragOver: ({ active, over }) => (over ? `${label(active.id)} na ${position(over.id)}.` : undefined),
    onDragEnd: ({ active, over }) => (over ? `${label(active.id)} položeno na ${position(over.id)}.` : `${label(active.id)} položeno.`),
    onDragCancel: ({ active }) => `Přesun zrušen, ${label(active.id)} zůstává na ${position(active.id)}.`,
  };
  const onDragEnd = ({ active, over }: DragEndEvent) => {
    onDragging(false);
    if (!over || active.id === over.id) return;
    onMove(ids.indexOf(String(active.id)), ids.indexOf(String(over.id)));
  };

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <h3 id={headingId} className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border px-3 py-3 text-[13px] text-muted-foreground">{empty}</p>
      ) : (
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          modifiers={[verticalOnly]}
          onDragStart={() => onDragging(true)}
          onDragEnd={onDragEnd}
          onDragCancel={() => onDragging(false)}
          accessibility={{
            announcements,
            screenReaderInstructions: {
              draggable: 'Mezerníkem řádek zvednete, šipkami nahoru a dolů posunete, mezerníkem položíte, Esc přesun zruší.',
            },
          }}
        >
          <SortableContext items={ids} strategy={verticalListSortingStrategy}>
            <ol className="divide-y divide-border rounded-lg border border-border bg-card">
              {rows.map((row, i) => (
                <SortableRow
                  key={row.id}
                  row={row}
                  index={i}
                  count={rows.length}
                  onUp={() => onMove(i, i - 1)}
                  onDown={() => onMove(i, i + 1)}
                />
              ))}
            </ol>
          </SortableContext>
        </DndContext>
      )}
    </section>
  );
}

function SortableRow({
  row,
  index,
  count,
  onUp,
  onDown,
}: {
  row: Row;
  index: number;
  count: number;
  onUp: () => void;
  onDown: () => void;
}) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, transition, isDragging } = useSortable({ id: row.id });
  return (
    <li
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), transition }}
      className={cn(
        'relative flex items-center gap-2 bg-card py-1 pr-1.5 pl-1 first:rounded-t-lg last:rounded-b-lg',
        isDragging && 'z-10 shadow-md ring-1 ring-border',
      )}
    >
      <button
        type="button"
        ref={setActivatorNodeRef}
        {...attributes}
        {...listeners}
        aria-label={`Přesunout: ${row.label}, pozice ${index + 1} z ${count}`}
        className="flex size-7 cursor-grab touch-none items-center justify-center rounded-md text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring active:cursor-grabbing"
      >
        <GripVertical className="size-4" aria-hidden />
      </button>
      <span className="w-5 shrink-0 text-right text-xs tabular-nums text-muted-foreground">{index + 1}</span>
      <span className="min-w-0 flex-1 truncate text-[13px]">
        <span className="font-medium">{row.label}</span>
        {row.detail && <span className="text-muted-foreground"> · {row.detail}</span>}
      </span>
      <Button variant="ghost" size="icon-sm" onClick={onUp} disabled={index === 0} aria-label={`Posunout výš: ${row.label}`}>
        <ArrowUp aria-hidden />
      </Button>
      <Button variant="ghost" size="icon-sm" onClick={onDown} disabled={index === count - 1} aria-label={`Posunout níž: ${row.label}`}>
        <ArrowDown aria-hidden />
      </Button>
    </li>
  );
}
