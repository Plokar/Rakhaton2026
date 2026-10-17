'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useDraggable } from '@dnd-kit/core';
import { m } from 'motion/react';
import { ArrowRightLeft, FileText, GripVertical, MonitorUp, MoreHorizontal, PanelRight, Undo2 } from 'lucide-react';
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
} from '@/components/shadcn/context-menu';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/components/shadcn/dropdown-menu';
import { cn } from '@/lib/utils';
import type { MdtCase, MdtSessionListItem } from '@/types/mdt';
import { dayLabel, timeLabel } from '../dates';
import { shortPatient, spokenPatient } from '../patient';
import { openProjectorWindow } from '../projector';
import { ReadinessMark } from '../ReadinessBadge';
import { chipId, type ChipDragData } from './dnd';

export interface ChipActions {
  onOpen: () => void;
  onPrefetch: () => void;
  /** Kam smí přesunout (prázdné = přesun nepovolen). */
  moveTargets: MdtSessionListItem[];
  onMove: (target: MdtSessionListItem) => void;
}

/** Obsah čipu „P05 · Ž · 68  C50.4  81 %“; v úzkém sloupci se MKN a připravenost zalomí pod jméno. */
export function ChipFace({ item, overlay = false }: { item: MdtCase; overlay?: boolean }) {
  const icd10 = item.patient?.diagnosis?.icd10;
  return (
    <span
      className={cn(
        'flex min-h-9 w-full flex-wrap items-baseline gap-x-1.5 rounded-md px-1.5 py-1.5 text-[13px] leading-5',
        overlay && 'bg-popover shadow-[0_12px_32px_-12px_rgb(15_23_42/0.35)] ring-1 ring-border',
      )}
    >
      <span translate="no" className="whitespace-nowrap font-medium tabular-nums">{shortPatient(item)}</span>
      {icd10 && <span translate="no" className="text-muted-foreground">{icd10}</span>}
      {item.status === 'returned' && (
        <span className="inline-flex items-center self-center text-amber-800 dark:text-amber-300" title="Vráceno k doplnění">
          <Undo2 className="size-3.5" aria-hidden />
          <span className="sr-only">vráceno k doplnění</span>
        </span>
      )}
      {item.id != null && <ReadinessMark caseId={item.id} className="ml-auto" />}
    </span>
  );
}

const moveLabel = (s: MdtSessionListItem) => `${s.title}`;
const moveMeta = (s: MdtSessionListItem) => `${dayLabel(s.date)} ${timeLabel(s.date)}`;

/** Pacient v dlaždici zasedání: tažení, klik = rychlý přehled, kontextové menu a tlačítko „⋯“. */
export const PatientChip = React.memo(function PatientChip({
  item,
  session,
  draggable,
  dimmed,
  layoutId,
  actions,
}: {
  item: MdtCase & { id: number };
  session: MdtSessionListItem;
  /** Smí ho přetáhnout (role, otevřený board, široká obrazovka). */
  draggable: boolean;
  /** Zdrojová pozice během tažení (zástupný řádek). */
  dimmed: boolean;
  /** Sdílený layoutId: čip po přesunu „dojede“ do nového zasedání (NAVRH_UI §3.3). */
  layoutId?: string;
  actions: ChipActions;
}) {
  const router = useRouter();
  const data: ChipDragData = { type: 'case', item, from: session };
  const { attributes, listeners, setNodeRef } = useDraggable({
    id: chipId(item.id),
    data,
    disabled: !draggable,
    attributes: { roleDescription: draggable ? 'pacient, lze přesunout' : 'pacient' },
  });

  const projector = () => openProjectorWindow({ board: session.id, caseId: item.id, patient: item.patient_id });
  const detail = () => router.push(`/dashboard/cases/${item.id}`);
  const label = spokenPatient(item);

  return (
    <ContextMenu>
      <ContextMenuTrigger
        render={
          <m.li
            layout="position"
            layoutId={layoutId}
            className="group/chip relative rounded-md transition-colors hover:bg-muted/70 has-[:focus-visible]:bg-muted/70"
          />
        }
      >
        <div
          ref={setNodeRef}
          {...attributes}
          {...listeners}
          aria-label={`${label}${item.patient?.diagnosis ? `, ${item.patient.diagnosis.icd10}` : ''}`}
          onClick={actions.onOpen}
          onKeyDown={(e) => {
            listeners?.onKeyDown?.(e);
            if (e.key === 'Enter' && !e.defaultPrevented) actions.onOpen();
          }}
          onPointerEnter={actions.onPrefetch}
          onFocus={actions.onPrefetch}
          className={cn(
            'cursor-pointer rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring [@media(hover:none)]:pr-8',
            draggable && 'cursor-grab active:cursor-grabbing',
            dimmed && 'opacity-35',
          )}
        >
          <ChipFace item={item} />
        </div>
        {draggable && (
          <GripVertical
            className="pointer-events-none absolute -left-2.5 top-2.5 size-3 text-muted-foreground opacity-0 transition-opacity group-hover/chip:opacity-70 [@media(hover:none)]:hidden"
            aria-hidden
          />
        )}
        <DropdownMenu>
          <DropdownMenuTrigger
            aria-label={`Akce pro ${item.patient_id}`}
            className="absolute right-0.5 top-1 flex size-7 items-center justify-center rounded-md bg-muted text-muted-foreground opacity-0 outline-none transition-opacity hover:bg-background hover:text-foreground focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring group-hover/chip:opacity-100 data-[popup-open]:opacity-100 [@media(hover:none)]:bg-transparent [@media(hover:none)]:opacity-100"
          >
            <MoreHorizontal className="size-4" aria-hidden />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuItem onClick={actions.onOpen}>
              <PanelRight aria-hidden /> Rychlý přehled
            </DropdownMenuItem>
            <DropdownMenuItem onClick={detail}>
              <FileText aria-hidden /> Otevřít detail
            </DropdownMenuItem>
            {actions.moveTargets.length > 0 && (
              <DropdownMenuSub>
                <DropdownMenuSubTrigger>
                  <ArrowRightLeft aria-hidden /> Přesunout na…
                </DropdownMenuSubTrigger>
                <DropdownMenuSubContent className="w-72">
                  {actions.moveTargets.map((target) => (
                    <DropdownMenuItem key={target.id} onClick={() => actions.onMove(target)}>
                      <span className="min-w-0 flex-1 truncate">{moveLabel(target)}</span>
                      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{moveMeta(target)}</span>
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuSubContent>
              </DropdownMenuSub>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={projector}>
              <MonitorUp aria-hidden /> Okno pro projektor
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </ContextMenuTrigger>
      <ContextMenuContent className="w-56">
        <ContextMenuItem onClick={actions.onOpen}>
          <PanelRight aria-hidden /> Rychlý přehled
        </ContextMenuItem>
        <ContextMenuItem onClick={detail}>
          <FileText aria-hidden /> Otevřít detail
        </ContextMenuItem>
        {actions.moveTargets.length > 0 && (
          <ContextMenuSub>
            <ContextMenuSubTrigger>
              <ArrowRightLeft aria-hidden /> Přesunout na…
            </ContextMenuSubTrigger>
            <ContextMenuSubContent className="w-72">
              {actions.moveTargets.map((target) => (
                <ContextMenuItem key={target.id} onClick={() => actions.onMove(target)}>
                  <span className="min-w-0 flex-1 truncate">{moveLabel(target)}</span>
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{moveMeta(target)}</span>
                </ContextMenuItem>
              ))}
            </ContextMenuSubContent>
          </ContextMenuSub>
        )}
        <ContextMenuSeparator />
        <ContextMenuItem onClick={projector}>
          <MonitorUp aria-hidden /> Okno pro projektor
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
});
