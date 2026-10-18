'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { parseAsInteger, useQueryState } from 'nuqs';
import { useHotkeys } from 'react-hotkeys-hook';
import {
  CheckCheck,
  ChevronDown,
  ChevronUp,
  CircleCheck,
  ClipboardCheck,
  FileDown,
  FileText,
  GripVertical,
  LayoutList,
  MessagesSquare,
  MonitorUp,
  MoreHorizontal,
  NotebookPen,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  SlidersHorizontal,
  Trash2,
  Undo2,
  UsersRound,
} from 'lucide-react';
import { toast } from 'sonner';
import { PageCrumb } from '@/components/layout/TopBar';
import { Button, buttonVariants } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/shadcn/dropdown-menu';
import { Kbd } from '@/components/shadcn/kbd';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/shadcn/resizable';
import { Sheet, SheetContent, SheetTitle } from '@/components/shadcn/sheet';
import { useSidebar } from '@/components/shadcn/sidebar';
import { Skeleton } from '@/components/shadcn/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { useMediaQuery } from '@/hooks/use-media-query';
import { mdtApi } from '@/lib/mdt-api';
import { agendaOrder, apiErrorMessage, useAgendaOrder, useCaseStatus, useSaveSession, useSessionQuery, useSessionStatus } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtCase, MdtSessionDetail } from '@/types/mdt';
import { AddPatientSheet, intakePending } from '../AddPatientSheet';
import { BoardDialog } from '../BoardDialog';
import { BoardOutputsDialog, CloseBoardDialog } from '../CloseBoard';
import { CollaboratorsDialog } from '../CollaboratorsDialog';
import { ProjectorLayoutDialog } from '../ProjectorLayoutEditor';
import { dayLabel, timeLabel } from '../dates';
import { GenerateBrief } from '../GenerateBrief';
import { can, useMe } from '../me';
import { isDiscussed, shortPatient, spokenPatient } from '../patient';
import { openProjectorWindow, publishSelection } from '../projector';
import { CaseQuickViewWide, useQuickViewSources } from '../quick-view';
import { ReadinessMark } from '../ReadinessBadge';
import { SessionChat } from './SessionChat';
import { formatDuration, useCaseTimer } from './use-case-timer';
import { DiscussionRecorder } from './DiscussionRecorder';
import { useSessionChat } from './use-session-chat';

type Case = MdtCase & { id: number };

/** Po 5 minutách u pacienta čas zoranžoví (bez zvuku a blikání, NAVRH_UI §7.4). */
const LONG_SECONDS = 5 * 60;

/** Zkratky neplatí, když je otevřené menu, dialog nebo boční panel (zdroj citace). */
const overlayOpen = () =>
  Boolean(document.querySelector('[data-slot="sheet-content"], [data-slot="dialog-content"], [role="menu"]'));

/**
 * Jednání komise (NAVRH_UI §7): vlevo agenda, vpravo 30s rychlý přehled pacienta na řadě. Odpovídá
 * v tomto pořadí na otázky „kdo je na řadě, o čem rozhodujeme a co tomu brání“. Výběr pacienta se
 * rovnou publikuje do okna projektoru (T-512).
 */
export function MeetingView({ sessionId }: { sessionId: number }) {
  const router = useRouter();
  const me = useMe();
  const session = useSessionQuery(sessionId);
  const cases = agendaOrder(session.data).filter((c): c is Case => c.id != null);
  const [param, setParam] = useQueryState('pacient', parseAsInteger);
  const current = cases.find((c) => c.id === param) ?? cases.find((c) => !isDiscussed(c)) ?? cases[0] ?? null;
  const index = current ? cases.indexOf(current) : -1;
  const sources = useQuickViewSources({ sessionId, caseId: current?.id ?? null, patientId: current?.patient_id ?? null });
  const { elapsed, total } = useCaseTimer(sessionId, current?.id ?? null);
  const status = useCaseStatus(sessionId);
  const wide = useMediaQuery('(min-width: 1024px)');
  const chair = can.manageBoards(me);
  const [adding, setAdding] = React.useState(false);
  const [completing, setCompleting] = React.useState<string | null>(null);
  const [collaborating, setCollaborating] = React.useState(false);
  const [editingProjector, setEditingProjector] = React.useState(false);
  const chat = useSessionChat(sessionId, me);
  const reorder = useAgendaOrder(sessionId);
  const [moved, setMoved] = React.useState('');
  useFocusLayout();

  React.useEffect(() => {
    if (current) publishSelection({ board: sessionId, caseId: current.id, patient: current.patient_id });
  }, [sessionId, current?.id, current?.patient_id, current]);

  const select = React.useCallback((item: Case) => void setParam(item.id), [setParam]);
  const go = (delta: number) => {
    const next = cases[index + delta];
    if (next) select(next);
  };
  const toggleDiscussed = () => {
    if (!current || !chair) return;
    const next = isDiscussed(current) ? 'in_discussion' : 'decided';
    status.mutate(
      { caseId: current.id, status: next },
      {
        onSuccess: () => toast(next === 'decided' ? `${current.patient_id} projednán` : `${current.patient_id} znovu na řadě`),
        onError: (err) => toast.error(apiErrorMessage(err, 'Stav případu se nepodařilo uložit.')),
      },
    );
  };
  /** T-324: předseda přeskládá agendu (přetažení nebo Alt+↑/↓); pořadí uloží server, při chybě se vrátí. */
  const move = (from: number, to: number) => {
    if (to < 0 || to >= cases.length || from === to) return;
    const ids = cases.map((c) => c.id);
    const [id] = ids.splice(from, 1);
    ids.splice(to, 0, id);
    const item = cases[from];
    reorder.mutate(ids, {
      onSuccess: () => setMoved(`${item.patient_id} je na ${to + 1}. místě agendy.`),
      onError: (err) => toast.error(apiErrorMessage(err, 'Pořadí agendy se nepodařilo uložit.')),
    });
  };
  const canReorder = chair && session.data?.status !== 'closed' && cases.length > 1;
  const projector = () => {
    if (current) openProjectorWindow({ board: sessionId, caseId: current.id, patient: current.patient_id });
    else openProjectorWindow(null);
  };

  const hk = { preventDefault: true, ignoreEventWhen: overlayOpen };
  useHotkeys('down, j', () => go(1), hk, [index, cases]);
  useHotkeys('up, k', () => go(-1), hk, [index, cases]);
  useHotkeys('d', () => current && router.push(`/dashboard/cases/${current.id}`), hk, [current]);
  useHotkeys('z', () => current && router.push(`/dashboard/cases/${current.id}/record`), hk, [current]);
  useHotkeys('p', projector, hk, [current]);
  useHotkeys('h', toggleDiscussed, hk, [current, chair]);
  useHotkeys('c', () => chat.setOpen(!chat.open), hk, [chat.open, chat.setOpen]);

  if (session.isLoading) return <MeetingSkeleton />;
  if (session.isError || !session.data) {
    return (
      <div className="p-6">
        <p role="alert" className="text-sm text-destructive">
          {apiErrorMessage(session.error, 'Zasedání se nepodařilo načíst.')}{' '}
          <Link href="/dashboard" className="font-medium underline underline-offset-4">Zpět na kalendář</Link>
        </p>
      </div>
    );
  }

  const board = session.data;
  const discussed = cases.filter(isDiscussed).length;
  // Chat vedle přehledu jen ve třísloupcovém jednání; jinak (úzký displej, prázdná agenda) jako boční panel.
  const inlineChat = cases.length > 0 && wide;
  const chatProps = {
    chat,
    current,
    closed: board.status === 'closed',
    onSelectCase: (caseId: number) => void setParam(caseId),
  };

  const main = current ? (
    <div className="mx-auto w-full max-w-[1200px] px-4 py-5 sm:px-6 lg:px-8">
      {current.status === 'returned' && (
        <p className="mb-4 flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:bg-amber-400/10 dark:text-amber-200">
          <Undo2 className="mt-0.5 size-4 shrink-0" aria-hidden />
          Případ je vrácený k doplnění podkladů (OBC-1.1). Zadávající lékař doplní chybějící údaje v dokumentaci.
        </p>
      )}
      {intakePending(current) && (
        <div className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950 dark:border-amber-500/40 dark:bg-amber-400/10 dark:text-amber-200">
          <ClipboardCheck className="size-4 shrink-0" aria-hidden />
          <span className="min-w-0 flex-1">
            Zařazení čeká na dokončení: kontrola úplnosti, ECOG, záměr C/P a varování.
            {!can.editCase(me, current) && ` Dokončí ho zadávající lékař${current.created_by ? ` (${current.created_by.name})` : ''}.`}
          </span>
          {can.editCase(me, current) && board.status !== 'closed' && (
            <Button size="sm" onClick={() => setCompleting(current.patient_id)}>Dokončit zařazení</Button>
          )}
        </div>
      )}
      <CaseQuickViewWide
        key={current.id}
        sources={sources}
        caseId={current.id}
        warningsHref={`/dashboard/cases/${current.id}#varovani`}
        anamnesisEmpty={
          sources.brief.data === null && can.editCase(me, current) ? (
            <div className="flex flex-col items-start gap-2">
              <p className="text-sm text-muted-foreground">
                Podklad zatím nevznikl. Přehled výše stojí na datech z IRIS a pravidlech, anamnézu doplní AI.
              </p>
              <GenerateBrief caseId={current.id} variant="outline" />
            </div>
          ) : undefined
        }
        toolbar={
          <CaseToolbar
            item={current}
            index={index}
            count={cases.length}
            chair={chair}
            onPrev={() => go(-1)}
            onNext={() => go(1)}
            onToggleDiscussed={toggleDiscussed}
            busy={status.isPending}
            onCollaborate={can.inviteToCase(me, current) ? () => setCollaborating(true) : undefined}
            onEditProjector={can.editCase(me, current) ? () => setEditingProjector(true) : undefined}
          />
        }
      />
      {collaborating && <CollaboratorsDialog key={`collab-${current.id}`} item={current} open onOpenChange={setCollaborating} />}
      {editingProjector && <ProjectorLayoutDialog key={`pjl-${current.id}`} item={current} open onOpenChange={setEditingProjector} />}
    </div>
  ) : (
    <div className="flex flex-1 items-center justify-center p-6">
      <EmptyState
        className="w-full max-w-lg"
        icon={<UsersRound aria-hidden />}
        title="V agendě zatím nejsou pacienti"
        description="Pacienta zařazuje zadávající lékař nebo předseda. Formulář zkontroluje úplnost podkladů."
        action={
          can.generateBrief(me) && board.status !== 'closed' ? (
            <Button size="lg" onClick={() => setAdding(true)}>
              <Plus aria-hidden /> Zařadit pacienta
            </Button>
          ) : undefined
        }
      />
    </div>
  );

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] min-h-0 flex-col">
      <PageCrumb>{board.title}</PageCrumb>
      <MeetingHeader
        board={board}
        discussed={discussed}
        count={cases.length}
        total={total}
        onProjector={projector}
        onAdd={() => setAdding(true)}
        chatOpen={chat.open}
        unread={chat.unread}
        onChat={() => chat.setOpen(!chat.open)}
      />
      {inlineChat ? (
        <ResizablePanelGroup className="min-h-0 flex-1">
          <ResizablePanel id="agenda" defaultSize={288} minSize={240} maxSize={360} groupResizeBehavior="preserve-pixel-size" className="min-h-0">
            <MeetingRail
              cases={cases}
              current={current}
              elapsed={elapsed}
              onSelect={select}
              onMove={canReorder ? move : undefined}
              announcement={moved}
              recorder={<DiscussionRecorder cases={cases} current={current} />}
            />
          </ResizablePanel>
          <ResizableHandle withHandle aria-label="Šířka agendy" />
          <ResizablePanel id="prehled" className="min-h-0">
            <div className="relative h-full overflow-y-auto">{main}</div>
          </ResizablePanel>
          {chat.open && (
            <>
              <ResizableHandle withHandle aria-label="Šířka chatu" />
              <ResizablePanel id="chat" defaultSize={340} minSize={280} maxSize={480} groupResizeBehavior="preserve-pixel-size" className="min-h-0">
                <SessionChat {...chatProps} onClose={() => chat.setOpen(false)} />
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>
      ) : (
        <div className="relative min-h-0 flex-1 overflow-y-auto">
          {cases.length > 0 && <AgendaPicker cases={cases} current={current} onSelect={select} />}
          {cases.length > 0 && <DiscussionRecorder cases={cases} current={current} className="border-b bg-card" />}
          {main}
        </div>
      )}
      {!inlineChat && (
        <Sheet open={chat.open} onOpenChange={chat.setOpen}>
          <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-md">
            <SessionChat {...chatProps} Title={SheetTitle} />
          </SheetContent>
        </Sheet>
      )}
      <AddPatientSheet session={adding ? board : null} onClose={() => setAdding(false)} />
      <AddPatientSheet session={completing ? board : null} patientId={completing} onClose={() => setCompleting(null)} />
    </div>
  );
}

/**
 * Jednání je režim soustředění: pod 1440 px (projektor 1024 × 768) se postranní panel sbalí na ikony,
 * aby přehled pacienta měl místo. Po odchodu z jednání se vrátí, jak byl.
 */
function useFocusLayout() {
  const { open, setOpen, isMobile } = useSidebar();
  const initial = React.useRef({ open, isMobile, setOpen });
  React.useEffect(() => {
    const { open: wasOpen, isMobile: mobile, setOpen: set } = initial.current;
    if (mobile || !wasOpen || window.innerWidth >= 1440) return;
    const frame = requestAnimationFrame(() => set(false));
    return () => {
      cancelAnimationFrame(frame);
      set(true);
    };
  }, []);
}

function MeetingHeader({
  board,
  discussed,
  count,
  total,
  onProjector,
  onAdd,
  chatOpen,
  unread,
  onChat,
}: {
  board: MdtSessionDetail;
  discussed: number;
  count: number;
  total: number;
  onProjector: () => void;
  onAdd: () => void;
  chatOpen: boolean;
  unread: number;
  onChat: () => void;
}) {
  const router = useRouter();
  const me = useMe();
  const save = useSaveSession();
  const sessionStatus = useSessionStatus();
  const [editing, setEditing] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [closing, setClosing] = React.useState(false);
  const [outputs, setOutputs] = React.useState<'closed' | 'view' | null>(null);
  const chair = can.manageBoards(me);
  const status = board.status === 'in_progress' ? 'probíhá' : board.status === 'closed' ? 'uzavřeno' : null;

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-6 gap-y-2 border-b border-border bg-card px-4 py-3 sm:px-6">
      <div className="min-w-0 basis-full sm:basis-0 sm:flex-1">
        <h1 className="truncate text-lg font-semibold tracking-tight">{board.title}</h1>
        <p className="flex flex-wrap items-center gap-x-2 text-[13px] text-muted-foreground">
          <span className="tabular-nums">
            {dayLabel(board.date)} {timeLabel(board.date)}
          </span>
          {board.chair && <span>předseda {board.chair.name}</span>}
          {status && <span className={cn(status === 'probíhá' && 'font-medium text-primary')}>{status}</span>}
        </p>
      </div>
      {count > 0 && (
        <p className="text-[13px] tabular-nums text-muted-foreground" aria-live="polite">
          <span className="font-medium text-foreground">{discussed} / {count}</span> projednáno · {formatDuration(total)}
        </p>
      )}
      <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
        <Button variant={chatOpen ? 'secondary' : 'outline'} size="lg" onClick={onChat} aria-pressed={chatOpen} aria-label="Chat" title="Chat lékařů zasedání (C)">
          <MessagesSquare aria-hidden /> <span className="hidden sm:inline">Chat</span>
          {unread > 0 && (
            <>
              <span aria-hidden className="min-w-5 rounded-full bg-primary px-1.5 text-xs leading-5 tabular-nums text-primary-foreground">
                {unread > 99 ? '99+' : unread}
              </span>
              <span className="sr-only">{unread} nepřečtených</span>
            </>
          )}
        </Button>
        <Button variant="outline" size="lg" onClick={onProjector} aria-label="Projektor" title="Okno pro projektor (P)">
          <MonitorUp aria-hidden /> <span className="hidden sm:inline">Projektor</span>
        </Button>
        {chair && board.status !== 'closed' && count > 0 && (
          <Button variant="outline" size="lg" onClick={() => setClosing(true)} aria-label="Ukončit board" title="Ukončit board a stáhnout výstupy">
            <CheckCheck aria-hidden /> <span className="hidden sm:inline">Ukončit board</span>
          </Button>
        )}
        {chair && board.status === 'closed' && (
          <Button variant="outline" size="lg" onClick={() => setOutputs('view')}>
            <FileDown aria-hidden /> Výstupy
          </Button>
        )}
        {can.generateBrief(me) && board.status !== 'closed' && (
          <Button size="lg" onClick={onAdd}>
            <Plus aria-hidden /> Zařadit
          </Button>
        )}
        <DropdownMenu>
          <DropdownMenuTrigger render={<Button variant="ghost" size="icon-lg" aria-label="Další akce zasedání" />}>
            <MoreHorizontal aria-hidden />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuItem onClick={() => router.push(`/dashboard/mdt/${board.id}/setup`)}>
              <SlidersHorizontal aria-hidden /> {chair ? 'Nastavit podklad' : 'Nastavení podkladu'}
            </DropdownMenuItem>
            {chair && (
              <>
                <DropdownMenuItem onClick={() => setEditing(true)}>
                  <Pencil aria-hidden /> Upravit board
                </DropdownMenuItem>
                {board.status === 'closed' && (
                  <DropdownMenuItem
                    onClick={() =>
                      sessionStatus.mutate(
                        { id: board.id, status: 'in_progress' },
                        {
                          onSuccess: () => toast('Board je znovu otevřený'),
                          onError: (err) => toast.error(apiErrorMessage(err, 'Board se nepodařilo otevřít.')),
                        },
                      )
                    }
                  >
                    <RotateCcw aria-hidden /> Znovu otevřít board
                  </DropdownMenuItem>
                )}
                {count === 0 && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem variant="destructive" onClick={() => setDeleting(true)}>
                      <Trash2 aria-hidden /> Smazat board
                    </DropdownMenuItem>
                  </>
                )}
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {editing && (
        <BoardDialog
          open
          session={board}
          onClose={() => setEditing(false)}
          onSubmit={async (input) => {
            await save.mutateAsync({ id: board.id, input });
            toast.success('Board uložen');
          }}
        />
      )}
      <DeleteBoardDialog board={deleting ? board : null} onClose={() => setDeleting(false)} />
      {closing && <CloseBoardDialog board={board} open onOpenChange={setClosing} onClosed={() => setOutputs('closed')} />}
      {outputs && (
        <BoardOutputsDialog sessionId={board.id} open justClosed={outputs === 'closed'} onOpenChange={(next) => !next && setOutputs(null)} />
      )}
    </div>
  );
}

function DeleteBoardDialog({ board, onClose }: { board: MdtSessionDetail | null; onClose: () => void }) {
  const router = useRouter();
  const [busy, setBusy] = React.useState(false);
  const remove = async () => {
    if (!board) return;
    setBusy(true);
    try {
      await mdtApi.deleteSession(board.id);
      toast.success(`Board ${board.title} smazán`);
      router.push('/dashboard');
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Board se nepodařilo smazat.'));
      setBusy(false);
    }
  };
  return (
    <Dialog open={board !== null} onOpenChange={(open) => !open && !busy && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Smazat prázdný board?</DialogTitle>
          <DialogDescription>
            {board?.title}, {board && `${dayLabel(board.date)} ${timeLabel(board.date)}`}. Board nemá žádné pacienty, smazáním se nic dalšího nezmění.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" size="lg" onClick={onClose} disabled={busy}>Ponechat</Button>
          <Button variant="destructive" size="lg" onClick={remove} disabled={busy}>Smazat board</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Pruh agendy: pořadí, kdo je na řadě (výběr + ▶), projednaní ztlumení s ✓, čas u pacienta. */
function MeetingRail({
  cases,
  current,
  elapsed,
  onSelect,
  onMove,
  announcement = '',
  recorder,
}: {
  cases: Case[];
  current: Case | null;
  elapsed: Record<string, number>;
  onSelect: (item: Case) => void;
  /** Jen předseda (T-324): přetažení nebo Alt+↑/↓ změní pořadí agendy. */
  onMove?: (from: number, to: number) => void;
  announcement?: string;
  /** Nahrávání diskuse (BON-3) v boku pod agendou. */
  recorder: React.ReactNode;
}) {
  const [drag, setDrag] = React.useState<number | null>(null);
  const [over, setOver] = React.useState<number | null>(null);
  return (
    <nav aria-label="Agenda zasedání" className="flex h-full min-h-0 flex-col bg-card">
      <ol className="relative min-h-0 flex-1 overflow-y-auto p-2">
        {cases.map((item, i) => {
          const active = item.id === current?.id;
          const done = isDiscussed(item);
          const seconds = elapsed[item.id] ?? 0;
          return (
            <li
              key={item.id}
              draggable={Boolean(onMove)}
              onDragStart={(e) => {
                setDrag(i);
                e.dataTransfer.effectAllowed = 'move';
              }}
              onDragOver={(e) => {
                if (drag === null) return;
                e.preventDefault();
                setOver(i);
              }}
              onDrop={(e) => {
                e.preventDefault();
                if (drag !== null && drag !== i) onMove?.(drag, i);
                setDrag(null);
                setOver(null);
              }}
              onDragEnd={() => {
                setDrag(null);
                setOver(null);
              }}
              className={cn(
                'group/agenda relative rounded-lg',
                onMove && 'cursor-grab active:cursor-grabbing',
                drag === i && 'opacity-50',
                over === i && drag !== null && drag !== i && (drag < i ? 'shadow-[inset_0_-2px_0_var(--color-primary)]' : 'shadow-[inset_0_2px_0_var(--color-primary)]'),
              )}
            >
              <button
                type="button"
                onKeyDown={(e) => {
                  if (!onMove || !e.altKey || (e.key !== 'ArrowUp' && e.key !== 'ArrowDown')) return;
                  e.preventDefault();
                  e.stopPropagation();
                  onMove(i, e.key === 'ArrowUp' ? i - 1 : i + 1);
                }}
                aria-keyshortcuts={onMove ? 'Alt+ArrowUp Alt+ArrowDown' : undefined}
                onClick={() => onSelect(item)}
                aria-current={active ? 'true' : undefined}
                aria-label={`${i + 1}. ${spokenPatient(item)}${done ? ', projednáno' : ''}${active ? ', na řadě' : ''}`}
                className={cn(
                  'grid w-full grid-cols-[1.25rem_minmax(0,1fr)_auto] items-start gap-x-2 rounded-lg px-2 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  active ? 'bg-primary/10 ring-1 ring-inset ring-primary/30' : 'hover:bg-muted',
                  done && !active && 'text-muted-foreground',
                )}
              >
                <span className="relative pt-px text-right text-[13px] tabular-nums text-muted-foreground">
                  <span className={cn(onMove && 'group-hover/agenda:invisible')}>{i + 1}</span>
                  {onMove && (
                    <GripVertical className="absolute top-0.5 right-0 hidden size-4 group-hover/agenda:block" aria-hidden />
                  )}
                </span>
                <span className="min-w-0">
                  <span translate="no" className={cn('block truncate text-sm font-medium', done && !active && 'font-normal')}>
                    {shortPatient(item)}
                  </span>
                  <span className="mt-0.5 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span translate="no">{item.patient?.diagnosis?.icd10 ?? '–'}</span>
                    <ReadinessMark caseId={item.id} />
                    {intakePending(item) && <span className="font-medium text-amber-700 dark:text-amber-400">k dokončení</span>}
                  </span>
                </span>
                <span className="flex flex-col items-end gap-0.5 pt-px">
                  {active ? (
                    <Play className="size-3.5 fill-primary text-primary" aria-hidden />
                  ) : done ? (
                    <CircleCheck className="size-3.5 text-emerald-700 dark:text-emerald-400" aria-hidden />
                  ) : item.status === 'returned' ? (
                    <Undo2 className="size-3.5 text-amber-700 dark:text-amber-400" aria-hidden />
                  ) : (
                    <span className="size-3.5" aria-hidden />
                  )}
                  {seconds > 0 && (
                    <span className={cn('text-xs tabular-nums', seconds >= LONG_SECONDS ? 'font-medium text-amber-700 dark:text-amber-400' : 'text-muted-foreground')}>
                      {formatDuration(seconds)}
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      {recorder}
      <p className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">
        <Kbd>↑</Kbd> <Kbd>↓</Kbd> pacient · <Kbd>?</Kbd> zkratky
        {onMove && <span className="mt-1 block">Pořadí: přetáhněte, nebo <Kbd>Alt</Kbd>+<Kbd>↑</Kbd>/<Kbd>↓</Kbd></span>}
      </p>
      <p className="sr-only" aria-live="polite">{announcement}</p>
    </nav>
  );
}

/** Úzká obrazovka: agenda jako výběr nahoře, přehled na celou šířku (NAVRH_UI §7.5). */
function AgendaPicker({ cases, current, onSelect }: { cases: Case[]; current: Case | null; onSelect: (item: Case) => void }) {
  return (
    <div className="border-b border-border bg-card px-4 py-2.5">
      <label htmlFor="agenda-picker" className="sr-only">Pacient na řadě</label>
      <select
        id="agenda-picker"
        value={current?.id ?? ''}
        onChange={(e) => {
          const next = cases.find((c) => c.id === Number(e.target.value));
          if (next) onSelect(next);
        }}
        className="h-9 w-full rounded-lg border border-input bg-card px-2.5 text-sm"
      >
        {cases.map((c, i) => (
          <option key={c.id} value={c.id}>
            {i + 1}. {shortPatient(c)} · {c.patient?.diagnosis?.icd10 ?? ''}{isDiscussed(c) ? ' · projednáno' : ''}
          </option>
        ))}
      </select>
    </div>
  );
}

/** Akce pro pacienta pod hlavičkou přehledu: předchozí / detail / závěr / (projednáno) / další. */
function CaseToolbar({
  item,
  index,
  count,
  chair,
  onPrev,
  onNext,
  onToggleDiscussed,
  busy,
  onCollaborate,
  onEditProjector,
}: {
  item: Case;
  index: number;
  count: number;
  chair: boolean;
  onPrev: () => void;
  onNext: () => void;
  onToggleDiscussed: () => void;
  busy: boolean;
  /** Přizvat ke spolupráci (T-326): jen předseda nebo zadávající lékař. */
  onCollaborate?: () => void;
  /** Upravit okno pro projektor (T-333): zadávající, přizvaný lékař nebo předseda. */
  onEditProjector?: () => void;
}) {
  const done = isDiscussed(item);
  return (
    <div className="@container flex items-center gap-2 border-y border-border py-2">
      <Button variant="ghost" size="lg" onClick={onPrev} disabled={index <= 0} title="Předchozí pacient (↑ nebo K)" aria-label="Předchozí pacient">
        <ChevronUp aria-hidden /> <span className="hidden @3xl:inline">Předchozí</span>
      </Button>
      <span className="mx-auto flex flex-wrap items-center justify-center gap-2">
        <Link href={`/dashboard/cases/${item.id}`} className={buttonVariants({ size: 'lg' })} title="Otevřít detail (D)">
          <FileText aria-hidden /> <span className="@md:hidden">Detail</span><span className="hidden @md:inline">Otevřít detail</span> <Kbd className="ml-1 hidden bg-primary-foreground/15 text-primary-foreground @3xl:inline-flex">D</Kbd>
        </Link>
        <Link href={`/dashboard/cases/${item.id}/record`} className={buttonVariants({ variant: 'outline', size: 'lg' })} title="Závěr komise (Z)">
          <NotebookPen aria-hidden /> Závěr <span className="hidden @md:inline">komise</span> <Kbd className="ml-1 hidden @3xl:inline-flex">Z</Kbd>
        </Link>
        {chair && (
          <Button variant="outline" size="lg" onClick={onToggleDiscussed} disabled={busy} aria-pressed={done} title="Označit jako projednané (H)">
            <CircleCheck aria-hidden className={cn(done && 'text-emerald-700 dark:text-emerald-400')} />
            {done ? 'Projednáno' : 'Projednat'} <Kbd className="ml-1 hidden @3xl:inline-flex">H</Kbd>
          </Button>
        )}
        {onCollaborate && (
          <Button
            variant="outline"
            size="lg"
            onClick={onCollaborate}
            aria-label={item.collaborators?.length ? `Spolupráce, přizváno ${item.collaborators.length}` : 'Spolupráce'}
            title={item.collaborators?.length ? `Spolupracují: ${item.collaborators.map((u) => u.name).join(', ')}` : 'Přizvat lékaře ke spolupráci'}
          >
            <UsersRound aria-hidden />
            {/* popisek až na široké ploše, jinak se lišta zalomí (1440 px s agendou) */}
            <span className="hidden @5xl:inline">Spolupráce</span>
            {item.collaborators?.length ? <span className="tabular-nums">{item.collaborators.length}</span> : null}
          </Button>
        )}
        {onEditProjector && (
          <Button variant="outline" size="lg" onClick={onEditProjector} aria-label="Upravit okno pro projektor" title="Upravit okno pro projektor: skrýt nebo přeskládat údaje">
            <LayoutList aria-hidden />
            <span className="hidden @5xl:inline">Okno projektoru</span>
          </Button>
        )}
      </span>
      <Button variant="ghost" size="lg" onClick={onNext} disabled={index >= count - 1} title="Další pacient (↓ nebo J)" aria-label="Další pacient">
        <span className="hidden @3xl:inline">Další</span> <ChevronDown aria-hidden />
      </Button>
    </div>
  );
}

function MeetingSkeleton() {
  return (
    <div className="flex h-[calc(100dvh-3.5rem)] flex-col" aria-busy="true" aria-label="Načítám zasedání">
      <div className="flex items-center gap-4 border-b border-border px-6 py-3">
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton className="h-5 w-56" />
          <Skeleton className="h-3.5 w-40" />
        </div>
        <Skeleton className="h-9 w-28" />
      </div>
      <div className="flex min-h-0 flex-1">
        <div className="hidden w-72 flex-col gap-2 border-r border-border p-3 lg:flex">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-12" />)}
        </div>
        <div className="flex flex-1 flex-col gap-4 p-8">
          <Skeleton className="h-7 w-72" />
          <Skeleton className="h-4 w-96" />
          <Skeleton className="mt-6 h-64" />
        </div>
      </div>
    </div>
  );
}
