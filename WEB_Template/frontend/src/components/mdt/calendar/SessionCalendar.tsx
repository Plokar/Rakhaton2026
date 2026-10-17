'use client';

import * as React from 'react';
import { DndContext, DragOverlay, type DragEndEvent, type DragStartEvent } from '@dnd-kit/core';
import { useQueryClient } from '@tanstack/react-query';
import { LazyMotion, MotionConfig, domMax } from 'motion/react';
import { parseAsArrayOf, parseAsInteger, parseAsString, useQueryState } from 'nuqs';
import { ChevronLeft, ChevronRight, ListFilter, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { Page, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/shadcn/button';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/shadcn/dropdown-menu';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/shadcn/tooltip';
import { useMediaQuery } from '@/hooks/use-media-query';
import {
  moveErrorMessage,
  prefetchQuickView,
  useMoveCase,
  useSaveSession,
  useSessionsQuery,
  useSessionsWithCases,
} from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtCase, MdtSession, MdtSessionListItem } from '@/types/mdt';
import { AddPatientSheet } from '../AddPatientSheet';
import { BoardDialog } from '../BoardDialog';
import { CollaboratorsDialog } from '../CollaboratorsDialog';
import {
  addDays,
  dayLabel,
  dayLabelLong,
  dayMonth,
  isoWeekKey,
  mondayOf,
  mondayOfWeekKey,
  pragueDay,
  rangeLabel,
  timeLabel,
  todayPrague,
  weekNumber,
  weekdayShort,
} from '../dates';
import { can, useMe } from '../me';
import { QuickViewSheet } from '../QuickViewSheet';
import { announcements, collision, screenReaderInstructions, useCalendarSensors, type ChipDragData, type TileDropData } from './dnd';
import { ChipFace, PatientChip } from './PatientChip';
import { SessionTile } from './SessionTile';

const WEEKS = 2;

/**
 * Přehled = kalendář zasedání (NAVRH_UI §6): sloupce = pracovní dny, v buňce dne dlaždice zasedání
 * s pacienty. Pacienty jde přetahovat mezi zasedáními (myš, dotyk, klávesnice) i přes „Přesunout na…“,
 * „+“ na dlaždici zařadí pacienta, klik na pacienta otevře rychlý přehled v bočním panelu.
 */
export function SessionCalendar() {
  const me = useMe();
  const client = useQueryClient();
  const today = todayPrague();
  const [week, setWeek] = useQueryState('tyden', parseAsString);
  const [openCase, setOpenCase] = useQueryState('pacient', parseAsInteger.withOptions({ history: 'push' }));
  const [committees, setCommittees] = useQueryState('komise', parseAsArrayOf(parseAsString).withDefault([]));

  const monday = mondayOfWeekKey(week) ?? mondayOf(today);
  const end = addDays(monday, WEEKS * 7 - 1);
  const inRange = React.useCallback((s: MdtSessionListItem) => {
    const day = pragueDay(s.date);
    return day >= monday && day <= end;
  }, [monday, end]);
  const { sessions, detail, loading, error } = useSessionsWithCases(inRange);
  const all = useSessionsQuery().data;

  const titles = React.useMemo(() => [...new Set((all ?? []).map((s) => s.title))].sort((a, b) => a.localeCompare(b, 'cs')), [all]);
  const visible = committees.length ? sessions.filter((s) => committees.includes(s.title)) : sessions;
  const isOpen = React.useCallback((s: MdtSession) => s.status !== 'closed' && pragueDay(s.date) >= today, [today]);
  const openBoards = React.useMemo(
    () => (all ?? []).filter(isOpen).toSorted((a, b) => a.date.localeCompare(b.date) || a.title.localeCompare(b.title, 'cs')),
    [all, isOpen],
  );

  const wide = useMediaQuery('(min-width: 1024px)');
  const sensors = useCalendarSensors(wide);
  const move = useMoveCase();
  const save = useSaveSession();
  const [dragging, setDragging] = React.useState<ChipDragData | null>(null);
  // Layout animace přesunu jen u „Přesunout na…“ a Vrátit; po tažení myší čip už je na místě.
  const [animateMoves, setAnimateMoves] = React.useState(true);
  const [addTo, setAddTo] = React.useState<MdtSession | null>(null);
  const [newBoardDay, setNewBoardDay] = React.useState<string | null>(null);
  const [collabCase, setCollabCase] = React.useState<MdtCase | null>(null);
  const manage = can.manageBoards(me);
  const canAdd = can.generateBrief(me);

  const doMove = React.useCallback(
    (item: MdtCase & { id: number }, from: MdtSessionListItem, to: MdtSessionListItem) => {
      const undo = () =>
        move.mutate(
          { caseId: item.id, from: to.id, to: from.id },
          {
            onSuccess: () => toast(`${item.patient_id} vrácen na ${from.title}`, { description: `${dayLabel(from.date)} ${timeLabel(from.date)}` }),
            onError: (err) => toast.error(moveErrorMessage(err)),
          },
        );
      move.mutate(
        { caseId: item.id, from: from.id, to: to.id },
        {
          onSuccess: () =>
            toast(`${item.patient_id} přesunut na ${to.title}`, {
              description: `${dayLabel(to.date)} ${timeLabel(to.date)}`,
              duration: 8000,
              action: { label: 'Vrátit', onClick: undo },
            }),
          onError: (err) => toast.error(moveErrorMessage(err)),
        },
      );
    },
    [move],
  );

  const onDragStart = (event: DragStartEvent) => {
    setAnimateMoves(false);
    setDragging((event.active.data.current as ChipDragData | undefined) ?? null);
  };
  const onDragEnd = (event: DragEndEvent) => {
    setDragging(null);
    window.setTimeout(() => setAnimateMoves(true), 250);
    const chip = event.active.data.current as ChipDragData | undefined;
    const tile = event.over?.data.current as TileDropData | undefined;
    if (!chip || !tile || !tile.open || tile.session.id === chip.from.id || chip.item.id == null) return;
    doMove(chip.item as MdtCase & { id: number }, chip.from, tile.session);
  };

  const a11y = React.useMemo(
    () => ({
      announcements: announcements({
        chip: (id) => (dragging && `case-${dragging.item.id}` === id ? dragging : undefined),
        tile: (id) => {
          const s = (all ?? []).find((x) => `session-${x.id}` === id);
          return s ? { type: 'session' as const, session: s, open: isOpen(s) } : undefined;
        },
      }),
      screenReaderInstructions,
    }),
    [dragging, all, isOpen],
  );

  const chipFor = (session: MdtSessionListItem, item: MdtCase & { id: number }) => {
    const canMove = isOpen(session) && can.editCase(me, item);
    return (
      <PatientChip
        key={item.id}
        item={item}
        session={session}
        draggable={wide && canMove}
        mine={canMove && item.created_by?.user_id === me?.user_id}
        dimmed={dragging?.item.id === item.id}
        layoutId={animateMoves ? `chip-${item.id}` : undefined}
        actions={{
          onOpen: () => void setOpenCase(item.id),
          onPrefetch: () => prefetchQuickView(client, { sessionId: session.id, caseId: item.id, patientId: item.patient_id }),
          moveTargets: canMove ? openBoards.filter((t) => t.id !== session.id) : [],
          onMove: (target) => doMove(item, session, target),
          onCollaborate: can.inviteToCase(me, item) ? () => setCollabCase(item) : undefined,
        }}
      />
    );
  };

  const byDay = new Map<string, MdtSessionListItem[]>();
  for (const s of visible.toSorted((a, b) => a.date.localeCompare(b.date) || a.title.localeCompare(b.title, 'cs'))) {
    const day = pragueDay(s.date);
    byDay.set(day, [...(byDay.get(day) ?? []), s]);
  }

  const tile = (s: MdtSessionListItem) => (
    <SessionTile
      key={s.id}
      session={s}
      detail={detail.get(s.id)}
      open={isOpen(s)}
      canAdd={canAdd}
      onAdd={() => setAddTo(s)}
      renderChip={(item) => chipFor(s, item)}
    />
  );

  const shiftWeek = (delta: number) => void setWeek(isoWeekKey(addDays(monday, delta * 7)));
  const thisWeek = mondayOf(today) === monday;

  return (
    <LazyMotion features={domMax} strict>
      <MotionConfig reducedMotion="user" transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}>
        <Page>
          <PageHeader
            title="Kalendář zasedání"
            meta={
              <span className="tabular-nums">
                Týden {weekNumber(monday)} a {weekNumber(addDays(monday, 7))} · {rangeLabel(monday, end)}
              </span>
            }
            actions={
              <>
                <div className="flex items-center rounded-lg border border-border bg-card p-0.5">
                  <Tooltip>
                    <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => shiftWeek(-1)} aria-label="Předchozí týden" />}>
                      <ChevronLeft aria-hidden />
                    </TooltipTrigger>
                    <TooltipContent>Předchozí týden</TooltipContent>
                  </Tooltip>
                  <Button variant="ghost" size="sm" onClick={() => void setWeek(null)} disabled={thisWeek} className="px-2.5">
                    Dnes
                  </Button>
                  <Tooltip>
                    <TooltipTrigger render={<Button variant="ghost" size="icon-sm" onClick={() => shiftWeek(1)} aria-label="Další týden" />}>
                      <ChevronRight aria-hidden />
                    </TooltipTrigger>
                    <TooltipContent>Další týden</TooltipContent>
                  </Tooltip>
                </div>
                <CommitteeFilter titles={titles} selected={committees} onChange={(next) => void setCommittees(next.length ? next : null)} />
                {manage && (
                  <Button size="lg" onClick={() => setNewBoardDay(today)}>
                    <Plus aria-hidden /> Nový board
                  </Button>
                )}
              </>
            }
          />

          {error ? (
            <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              Zasedání se nepodařilo načíst. Zkontrolujte připojení k serveru a obnovte stránku (F5).
            </p>
          ) : loading ? (
            <CalendarSkeleton />
          ) : (
            <DndContext
              sensors={sensors}
              collisionDetection={collision}
              onDragStart={onDragStart}
              onDragEnd={onDragEnd}
              onDragCancel={() => {
                setDragging(null);
                window.setTimeout(() => setAnimateMoves(true), 250);
              }}
              accessibility={a11y}
            >
              {wide ? (
                <div className="flex flex-col gap-8">
                  {Array.from({ length: WEEKS }, (_, w) => addDays(monday, w * 7)).map((start) => (
                    <WeekRow
                      key={start}
                      start={start}
                      today={today}
                      byDay={byDay}
                      tile={tile}
                      onEmptyDay={manage ? (day) => setNewBoardDay(day) : undefined}
                    />
                  ))}
                </div>
              ) : (
                <DayList byDay={byDay} today={today} tile={tile} />
              )}
              <DragOverlay dropAnimation={null}>{dragging ? <ChipFace item={dragging.item} overlay /> : null}</DragOverlay>
            </DndContext>
          )}

          {!loading && !error && visible.length === 0 && (
            <p className="text-sm text-muted-foreground">
              {committees.length ? 'Vybrané komise v tomto období nezasedají.' : 'V tomto období nejsou naplánovaná žádná zasedání.'}{' '}
              {!thisWeek && (
                <button type="button" className="font-medium text-foreground underline underline-offset-4" onClick={() => void setWeek(null)}>
                  Zpět na tento týden
                </button>
              )}
            </p>
          )}
        </Page>

        <QuickViewSheet caseId={openCase} onClose={() => void setOpenCase(null)} />
        <AddPatientSheet session={addTo} onClose={() => setAddTo(null)} />
        {collabCase && (
          <CollaboratorsDialog key={collabCase.id} item={collabCase} open onOpenChange={(open) => !open && setCollabCase(null)} />
        )}
        {newBoardDay && (
          <BoardDialog
            open
            defaultDay={newBoardDay}
            onClose={() => setNewBoardDay(null)}
            onSubmit={async (input) => {
              const created = await save.mutateAsync({ input });
              toast.success(`Board ${created.title} založen`, { description: `${dayLabel(created.date)} ${timeLabel(created.date)}` });
            }}
          />
        )}
      </MotionConfig>
    </LazyMotion>
  );
}

function WeekRow({
  start,
  today,
  byDay,
  tile,
  onEmptyDay,
}: {
  start: string;
  today: string;
  byDay: Map<string, MdtSessionListItem[]>;
  tile: (s: MdtSessionListItem) => React.ReactNode;
  onEmptyDay?: (day: string) => void;
}) {
  // Víkend jen, když na něj připadá zasedání.
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i)).filter((day, i) => i < 5 || byDay.has(day));
  return (
    <section aria-label={`Týden ${weekNumber(start)}, ${rangeLabel(start, addDays(start, days.length - 1))}`}>
      <h2 className="mb-2 text-sm font-medium text-muted-foreground">
        Týden {weekNumber(start)} <span className="font-normal tabular-nums">· {rangeLabel(start, addDays(start, 4))}</span>
      </h2>
      <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))` }}>
        {days.map((day) => {
          const sessions = byDay.get(day) ?? [];
          const past = day < today;
          const isToday = day === today;
          return (
            <div key={day} role="group" aria-label={`${dayLabelLong(`${day}T12:00:00Z`)}${isToday ? ', dnes' : ''}`} className="flex min-w-0 flex-col gap-2">
              <h3
                className={cn(
                  'flex items-baseline gap-1.5 border-b pb-1.5 text-sm',
                  isToday ? 'border-primary text-primary' : 'border-border',
                  past && !isToday && 'text-muted-foreground',
                )}
              >
                <span className="font-semibold capitalize">{weekdayShort(day)}</span>
                <span className="tabular-nums">{dayMonth(day)}</span>
                {isToday && <span className="ml-auto text-xs font-medium">dnes</span>}
              </h3>
              {sessions.length > 0 ? (
                sessions.map(tile)
              ) : onEmptyDay && !past ? (
                <button
                  type="button"
                  onClick={() => onEmptyDay(day)}
                  className="group/empty flex min-h-16 items-start justify-center rounded-xl border border-dashed border-transparent pt-2 text-xs text-muted-foreground/70 transition-colors hover:border-border hover:text-foreground focus-visible:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <span className="group-hover/empty:hidden group-focus-visible/empty:hidden">Bez zasedání</span>
                  <span className="hidden items-center gap-1 group-hover/empty:inline-flex group-focus-visible/empty:inline-flex">
                    <Plus className="size-3.5" aria-hidden /> Založit board
                  </span>
                </button>
              ) : (
                <p className="pt-2 text-center text-xs text-muted-foreground/70">Bez zasedání</p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** Úzká obrazovka (FR-U2): seznam po dnech, přesun jen přes menu „Přesunout na…“. */
function DayList({
  byDay,
  today,
  tile,
}: {
  byDay: Map<string, MdtSessionListItem[]>;
  today: string;
  tile: (s: MdtSessionListItem) => React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-6">
      {[...byDay.entries()].map(([day, sessions]) => (
        <section key={day} aria-label={dayLabelLong(`${day}T12:00:00Z`)} className="flex flex-col gap-2">
          <h2 className={cn('flex items-baseline gap-1.5 text-sm', day === today ? 'text-primary' : day < today && 'text-muted-foreground')}>
            <span className="font-semibold capitalize">{weekdayShort(day)}</span>
            <span className="tabular-nums">{dayMonth(day)}</span>
            {day === today && <span className="text-xs font-medium">dnes</span>}
          </h2>
          {sessions.map(tile)}
        </section>
      ))}
    </div>
  );
}

function CommitteeFilter({ titles, selected, onChange }: { titles: string[]; selected: string[]; onChange: (next: string[]) => void }) {
  if (titles.length < 2) return null;
  const toggle = (title: string, on: boolean) => onChange(on ? [...selected, title] : selected.filter((t) => t !== title));
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="lg" />}>
        <ListFilter aria-hidden />
        {selected.length ? `Komise (${selected.length})` : 'Všechny komise'}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-72">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Zobrazit komise</DropdownMenuLabel>
          {titles.map((title) => (
            <DropdownMenuCheckboxItem key={title} checked={selected.includes(title)} onCheckedChange={(on) => toggle(title, on)}>
              {title}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuGroup>
        {selected.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => onChange([])}>Zobrazit všechny</DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function CalendarSkeleton() {
  return (
    <div className="flex flex-col gap-8" aria-busy="true" aria-label="Načítám zasedání">
      {[0, 1].map((w) => (
        <div key={w} className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          {Array.from({ length: 5 }, (_, i) => (
            <div key={i} className="flex flex-col gap-2">
              <Skeleton className="h-5 w-20" />
              {(i + w) % 3 === 0 && <Skeleton className="h-28 rounded-xl" />}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
