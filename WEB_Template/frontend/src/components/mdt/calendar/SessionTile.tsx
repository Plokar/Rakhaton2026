'use client';

import * as React from 'react';
import Link from 'next/link';
import { useDndContext, useDroppable } from '@dnd-kit/core';
import { Ban, Lock, Plus } from 'lucide-react';
import { Button } from '@/components/shadcn/button';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/shadcn/tooltip';
import { cn } from '@/lib/utils';
import type { MdtCase, MdtSessionDetail, MdtSessionListItem } from '@/types/mdt';
import { dayLabel, patientsLabel, timeLabel } from '../dates';
import { tileId, type ChipDragData, type TileDropData } from './dnd';

const MAX_CHIPS = 6;

/**
 * Dlaždice jednoho zasedání v kalendáři (NAVRH_UI §6.2): název komise s „+“ vpravo nahoře, čas,
 * počet a stav, pacienti v pořadí agendy. Zároveň cíl pro přesun pacienta (dnd-kit).
 */
export function SessionTile({
  session,
  detail,
  open,
  canAdd,
  onAdd,
  renderChip,
}: {
  session: MdtSessionListItem;
  detail: MdtSessionDetail | undefined;
  /** Otevřený a nadcházející board: přijímá pacienty. */
  open: boolean;
  canAdd: boolean;
  onAdd: () => void;
  renderChip: (item: MdtCase & { id: number }) => React.ReactNode;
}) {
  const data: TileDropData = { type: 'session', session, open };
  const { setNodeRef, isOver } = useDroppable({ id: tileId(session.id), data, disabled: !open });
  const { active } = useDndContext();
  const dragged = active?.data.current as ChipDragData | undefined;
  const dragging = dragged?.type === 'case';
  const isSource = dragging && dragged.from.id === session.id;
  const accepts = dragging && open && !isSource;
  const blocked = dragging && !open && !isSource;

  const cases = detail
    ? detail.cases.toSorted((a, b) => (a.order ?? 0) - (b.order ?? 0)).filter((c): c is MdtCase & { id: number } => c.id != null)
    : [];
  const count = detail ? cases.length : session.patients.length;
  const overflow = cases.length > MAX_CHIPS;
  const shown = overflow ? cases.slice(0, MAX_CHIPS - 1) : cases;
  const status = session.status === 'in_progress' ? 'probíhá' : session.status === 'closed' ? 'uzavřeno' : null;
  const when = `${dayLabel(session.date)} ${timeLabel(session.date)}`;

  return (
    <section
      ref={setNodeRef}
      aria-label={`${session.title}, ${when}, ${patientsLabel(count)}${status ? `, ${status}` : ''}`}
      className={cn(
        'relative rounded-xl border border-border bg-card p-3 transition-[border-color,box-shadow,opacity] duration-150 motion-reduce:transition-none',
        !open && !dragging && 'bg-card/60',
        accepts && 'border-primary/50',
        accepts && isOver && 'border-primary ring-2 ring-primary/25',
        blocked && 'opacity-45',
      )}
    >
      <div className="flex items-start gap-1">
        <Link
          href={`/dashboard/mdt/${session.id}`}
          className="line-clamp-2 min-w-0 flex-1 rounded-sm text-sm font-semibold leading-snug underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          title={session.title}
        >
          {session.title}
        </Link>
        {canAdd && open && (
          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={onAdd}
                  aria-label={`Zařadit pacienta na ${session.title}, ${when}`}
                  className="-mr-1 -mt-1 text-muted-foreground hover:text-foreground"
                />
              }
            >
              <Plus aria-hidden />
            </TooltipTrigger>
            <TooltipContent>Zařadit pacienta</TooltipContent>
          </Tooltip>
        )}
      </div>
      <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
        <span className="tabular-nums">{timeLabel(session.date)}</span>
        <span aria-hidden>·</span>
        <span>{patientsLabel(count)}</span>
        {status === 'probíhá' && (
          <span className="inline-flex items-center gap-1 font-medium text-primary">
            <span className="size-1.5 rounded-full bg-primary" aria-hidden /> probíhá
          </span>
        )}
        {status === 'uzavřeno' && (
          <span className="inline-flex items-center gap-1">
            <Lock className="size-3" aria-hidden /> uzavřeno
          </span>
        )}
      </p>

      {!detail && session.patients.length > 0 ? (
        <div className="mt-2 flex flex-col gap-1.5" aria-busy="true">
          {session.patients.slice(0, 3).map((pid) => <Skeleton key={pid} className="h-7" />)}
        </div>
      ) : cases.length > 0 ? (
        <ul className="-mx-1 mt-2 flex flex-col">{shown.map((item) => <React.Fragment key={item.id}>{renderChip(item)}</React.Fragment>)}</ul>
      ) : (
        <p className="mt-2 text-xs text-muted-foreground">{open ? 'Zatím bez pacientů' : 'Bez pacientů'}</p>
      )}
      {overflow && (
        <Link
          href={`/dashboard/mdt/${session.id}`}
          className="mt-1 inline-block rounded-sm px-1 text-xs font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
        >
          + {cases.length - shown.length} další v agendě
        </Link>
      )}

      {accepts && (
        <p className={cn('mt-2 text-xs font-medium', isOver ? 'text-primary' : 'text-muted-foreground')} aria-hidden>
          Přesunout sem
        </p>
      )}
      {blocked && (
        <p className="mt-2 inline-flex items-center gap-1 text-xs text-muted-foreground" aria-hidden>
          <Ban className="size-3.5" /> {session.status === 'closed' ? 'Uzavřený board' : 'Minulé zasedání'}
        </p>
      )}
    </section>
  );
}
