'use client';

import * as React from 'react';
import Link from 'next/link';
import { Activity, Check, ChevronDown, ClipboardList, Copy, MonitorUp, Plus } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { BoardDialog } from '@/components/mdt/BoardDialog';
import { can, meLabel, useMe } from '@/components/mdt/me';
import { meetingDate, meetingTime, ProjectorPanel } from '@/components/mdt/ProjectorPanel';
import { openProjectorWindow, projectorHref, publishSelection, type ProjectorSelection } from '@/components/mdt/projector';
import { Avatar } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Dialog, DialogClose, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi, type SessionInput } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import { cn } from '@/lib/utils';
import type { MdtCase, MdtSessionDetail, MdtSessionListItem, Me } from '@/types/mdt';

const fetchSessions = () => mdtApi.getSessions();
const fetchSession = async (id: string): Promise<MdtSessionDetail | null> => (id ? mdtApi.getSession(id) : null);

const STATUS_LABEL: Record<MdtSessionListItem['status'], string> = {
  planned: 'plánováno',
  in_progress: 'probíhá',
  closed: 'uzavřeno',
};

const casesLabel = (n: number) => (n === 1 ? 'případ' : n >= 2 && n <= 4 ? 'případy' : 'případů');
const initials = (name: string) => name.split(/\s+/).map((part) => part[0]).join('').slice(0, 2);

/** Nejbližší nadcházející board, jinak první v seznamu. */
function defaultBoardId(boards: MdtSessionListItem[]): number | null {
  const today = new Date().toISOString().slice(0, 10);
  return (boards.find((b) => b.date.slice(0, 10) >= today) ?? boards[0])?.id ?? null;
}

/**
 * Admin okno (T-512, náčrt „1. okno“): boardy s počtem případů a termínem zasedání, rozbalení na případy,
 * přidání boardu a uživatelů. Vybraný případ se zobrazí v druhém, úzkém okně pro projektor vedle snímku
 * z PACS (`/projector`); na širokém monitoru je vpravo jeho náhled.
 */
export function AdminBoardWorkspace({
  initialBoard,
  initialSelection,
}: {
  initialBoard?: number;
  initialSelection?: ProjectorSelection | null;
}) {
  return (
    <DashboardLayout>
      <AdminBoardContent initialBoard={initialBoard} initialSelection={initialSelection ?? null} />
    </DashboardLayout>
  );
}

/** Rozbalený board a vybraný případ drží URL (`?board=&case=&patient=`): obnovení stránky o ně nepřijde. */
function syncUrl(board: number | null, selection: ProjectorSelection | null) {
  const params = new URLSearchParams();
  if (board) params.set('board', String(board));
  if (selection) {
    params.set('board', String(selection.board));
    params.set('case', String(selection.caseId));
    params.set('patient', selection.patient);
  }
  const query = params.toString();
  window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`);
}

function AdminBoardContent({ initialBoard, initialSelection }: { initialBoard?: number; initialSelection: ProjectorSelection | null }) {
  const me = useMe();
  const [refresh, setRefresh] = React.useState(0);
  const [openBoard, setOpenBoard] = React.useState<number | null | undefined>(initialSelection?.board ?? initialBoard);
  const [selection, setSelection] = React.useState(initialSelection);
  const [creating, setCreating] = React.useState(false);
  const [inviting, setInviting] = React.useState(false);

  const sessions = useApiData(fetchSessions, String(refresh));
  const boards = React.useMemo(() => (sessions.data ?? []).toSorted((a, b) => a.date.localeCompare(b.date)), [sessions.data]);
  const activeBoardId = openBoard === undefined ? defaultBoardId(boards) : openBoard;
  const agenda = useApiData(fetchSession, activeBoardId ? String(activeBoardId) : '');
  const canManage = can.manageBoards(me);
  const selectedLabel = selection
    ? agenda.data?.cases.find((c) => c.id === selection.caseId)?.patient?.display_name ?? selection.patient
    : null;

  const createBoard = async (input: SessionInput) => {
    const created = await mdtApi.createSession(input);
    setRefresh((value) => value + 1);
    setOpenBoard(created.id);
    syncUrl(created.id, selection);
  };

  const toggleBoard = (boardId: number) => {
    const next = boardId === activeBoardId ? null : boardId;
    setOpenBoard(next);
    syncUrl(next, selection);
  };

  const selectCase = (boardId: number, item: MdtCase) => {
    if (!item.id) return;
    const next = { board: boardId, caseId: item.id, patient: item.patient_id };
    setSelection(next);
    syncUrl(boardId, next);
    publishSelection(next);
  };

  return (
    <div className="-m-4 flex min-h-[calc(100dvh-4rem)] flex-col sm:-m-6 lg:-m-8 lg:h-[calc(100dvh-4rem)] lg:flex-row">
      <section aria-labelledby="boards-title" className="flex min-h-0 w-full flex-1 flex-col bg-card lg:w-[440px] lg:flex-none lg:border-r lg:border-border">
        <h1 id="boards-title" className="sr-only">Boardy MDT</h1>
        <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
          <Link
            href="/dashboard"
            aria-label="MedTeam, přehled"
            className="flex items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Activity className="size-5" aria-hidden />
            </span>
            <span className="text-lg font-bold tracking-tight">MedTeam</span>
          </Link>
          {canManage && (
            <Button size="sm" onClick={() => setCreating(true)}>
              <Plus className="size-4" aria-hidden />
              Přidat board
            </Button>
          )}
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          {sessions.loading ? (
            <div className="flex flex-col gap-2" aria-busy="true">
              <Skeleton className="h-28 rounded-xl" />
              <Skeleton className="h-28 rounded-xl" />
            </div>
          ) : sessions.error ? (
            <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              Boardy se nepodařilo načíst ({sessions.error}). Obnovte stránku (F5).
            </p>
          ) : boards.length === 0 ? (
            <EmptyState
              title="Zatím žádný board"
              description={canManage ? 'Založte první zasedání MDT tlačítkem „Přidat board“.' : 'Zasedání MDT zakládá předseda komise.'}
            />
          ) : (
            <ul className="flex flex-col gap-2">
              {boards.map((board) => (
                <BoardCard
                  key={board.id}
                  board={board}
                  expanded={board.id === activeBoardId}
                  onToggle={() => toggleBoard(board.id)}
                  agenda={board.id === activeBoardId ? agenda : null}
                  selectedCaseId={selection?.caseId ?? null}
                  onSelectCase={(item) => selectCase(board.id, item)}
                />
              ))}
            </ul>
          )}
        </div>

        {selection && (
          <div className="flex items-center gap-3 border-t border-border bg-primary/5 px-4 py-2.5">
            <div className="min-w-0 flex-1">
              <p translate="no" className="truncate text-sm font-semibold">{selectedLabel}</p>
              <p className="text-xs text-muted-foreground">Otevřené okno projektoru se přepne samo.</p>
            </div>
            <ProjectorLink selection={selection} />
          </div>
        )}

        <TeamStrip me={me} canInvite={canManage} onInvite={() => setInviting(true)} />
      </section>

      <section aria-label="Náhled okna pro projektor" className="hidden min-h-0 flex-1 flex-col items-center gap-3 bg-muted/30 p-6 lg:flex">
        <div className="flex w-full max-w-[400px] items-center justify-between gap-3">
          <p className="text-sm font-medium text-muted-foreground">Náhled okna pro projektor</p>
          <ProjectorLink selection={selection} variant="outline" />
        </div>
        <div className="min-h-0 w-full max-w-[400px] flex-1 overflow-hidden rounded-xl border border-border bg-background shadow-sm">
          <ProjectorPanel
            key={selection ? `${selection.board}:${selection.caseId}` : 'empty'}
            selection={selection}
            titleAs="h2"
          />
        </div>
      </section>

      {creating && <BoardDialog open onClose={() => setCreating(false)} onSubmit={createBoard} />}
      {inviting && <InviteDialog onClose={() => setInviting(false)} />}
    </div>
  );
}

type Loaded<T> = { data?: T; error?: string; loading: boolean };

function BoardCard({
  board,
  expanded,
  onToggle,
  agenda,
  selectedCaseId,
  onSelectCase,
}: {
  board: MdtSessionListItem;
  expanded: boolean;
  onToggle: () => void;
  agenda: Loaded<MdtSessionDetail | null> | null;
  selectedCaseId: number | null;
  onSelectCase: (item: MdtCase) => void;
}) {
  const count = board.patients.length;
  const panelId = `board-${board.id}-cases`;
  return (
    <li
      className={cn(
        'rounded-xl border bg-background transition-colors',
        expanded ? 'border-primary/40 shadow-sm' : 'border-border hover:border-primary/30',
      )}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={panelId}
        className="block w-full rounded-xl p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="flex items-start justify-between gap-3">
          <span className="min-w-0 text-[15px] font-semibold leading-snug">{board.title}</span>
          <time dateTime={board.date} className="shrink-0 text-right leading-tight tabular-nums">
            <span className="block text-sm font-semibold">{meetingDate(board.date)}</span>
            <span className="block text-sm text-muted-foreground">{meetingTime(board.date)}</span>
          </time>
        </span>
        <span className="mt-1 block text-2xl font-bold leading-none tabular-nums">
          {count} <span className="text-base font-medium text-muted-foreground">{casesLabel(count)}</span>
        </span>
        <span className="mt-3 flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="truncate">
            {board.chair ? `Předseda ${board.chair.name}` : 'Předseda nepřiřazen'} · {STATUS_LABEL[board.status]}
          </span>
          <ChevronDown
            className={cn('size-4 shrink-0 transition-transform duration-200 motion-reduce:transition-none', expanded && 'rotate-180')}
            aria-hidden
          />
        </span>
      </button>

      {expanded && agenda && (
        <div id={panelId} className="border-t border-border p-2">
          {agenda.loading ? (
            <div className="flex flex-col gap-1.5 p-1" aria-busy="true">
              <Skeleton className="h-11" />
              <Skeleton className="h-11" />
            </div>
          ) : agenda.error ? (
            <p role="alert" className="p-2 text-sm text-destructive">
              Případy boardu se nepodařilo načíst. Sbalte board a rozbalte ho znovu.
            </p>
          ) : !agenda.data?.cases.length ? (
            <p className="p-2 text-sm text-muted-foreground">Board zatím nemá zařazené případy.</p>
          ) : (
            <ul className="flex flex-col gap-0.5">
              {agenda.data.cases.map((item) => (
                <li key={item.id}>
                  <CaseRow item={item} selected={item.id === selectedCaseId} onSelect={() => onSelectCase(item)} />
                </li>
              ))}
            </ul>
          )}
          <Link
            href={`/dashboard/mdt/${board.id}`}
            className="mt-1.5 flex items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <ClipboardList className="size-3.5" aria-hidden />
            Otevřít agendu boardu
          </Link>
        </div>
      )}
    </li>
  );
}

function CaseRow({ item, selected, onSelect }: { item: MdtCase; selected: boolean; onSelect: () => void }) {
  const diagnosis = item.patient?.diagnosis;
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={cn(
        'flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        selected ? 'bg-primary/10 ring-1 ring-inset ring-primary/30' : 'hover:bg-muted',
      )}
    >
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-semibold">{item.patient?.display_name ?? item.patient_id}</span>
        <span className="block truncate text-xs text-muted-foreground">
          {diagnosis ? `${diagnosis.icd10} · ${diagnosis.text}` : 'Diagnóza v záznamu chybí'}
        </span>
      </span>
      <span className="flex shrink-0 items-center gap-1 text-xs font-semibold tabular-nums">
        <span className="rounded-md border border-border px-1.5 py-0.5" title="Performance status (ECOG) podle lékaře">
          PS {item.ecog ?? '–'}
        </span>
        <span
          className="min-w-6 rounded-md border border-border px-1.5 py-0.5 text-center"
          title={item.intent === 'C' ? 'Kurativní záměr' : item.intent === 'P' ? 'Paliativní záměr' : 'Záměr zatím nezvolen'}
        >
          {item.intent ?? '–'}
        </span>
      </span>
    </button>
  );
}

/** Otevře úzké okno projektoru; když prohlížeč popup zablokuje, odkaz se otevře v nové záložce. */
function ProjectorLink({ selection, variant = 'default' }: { selection: ProjectorSelection | null; variant?: 'default' | 'outline' }) {
  const open = (e: React.MouseEvent<HTMLAnchorElement>) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    if (openProjectorWindow(selection)) e.preventDefault();
  };
  return (
    <a
      href={projectorHref(selection)}
      target="_blank"
      rel="noopener"
      onClick={open}
      className={cn(
        'inline-flex h-8 shrink-0 items-center gap-1.5 rounded-md px-3 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        variant === 'default'
          ? 'bg-primary text-primary-foreground hover:bg-primary/90'
          : 'border border-border bg-card text-foreground hover:bg-accent',
      )}
    >
      <MonitorUp className="size-4" aria-hidden />
      Okno pro projektor
    </a>
  );
}

function TeamStrip({ me, canInvite, onInvite }: { me: Me | null; canInvite: boolean; onInvite: () => void }) {
  return (
    <footer className="flex items-center gap-3 border-t border-border px-4 py-3">
      <span className="text-xs font-medium text-muted-foreground">Tým komise</span>
      <div className="flex min-w-0 flex-1 items-center gap-2">
        {me ? (
          <>
            <Avatar size="sm" fallback={initials(me.name)} alt={me.name} />
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium">{me.name}</span>
              <span className="block truncate text-xs text-muted-foreground">{meLabel(me)}</span>
            </span>
          </>
        ) : (
          <Skeleton className="h-7 w-36" />
        )}
      </div>
      {canInvite && (
        <button
          type="button"
          onClick={onInvite}
          aria-label="Přidat uživatele do týmu"
          title="Přidat uživatele"
          className="flex size-8 shrink-0 items-center justify-center rounded-full border border-dashed border-primary/60 text-primary transition-colors hover:bg-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Plus className="size-4" aria-hidden />
        </button>
      )}
    </footer>
  );
}

/**
 * Přidání uživatele: API zatím nemá seznam členů ani pozvánky (PROGRESS Q24). Přihlášený admin se na
 * /register nedostane (proxy ho vrátí na dashboard), proto mu dáme odkaz, který pošle kolegovi.
 */
function InviteDialog({ onClose }: { onClose: () => void }) {
  const [copy, setCopy] = React.useState<'idle' | 'done' | 'failed'>('idle');
  const link = `${window.location.origin}/register`;
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopy('done');
    } catch {
      setCopy('failed');     // schránka bez HTTPS nebo bez oprávnění: odkaz zůstane k ručnímu zkopírování
    }
  };
  return (
    <Dialog open onOpenChange={(next) => !next && onClose()}>
      <DialogClose onClick={onClose} />
      <DialogHeader>
        <DialogTitle>Přidat uživatele</DialogTitle>
        <DialogDescription>
          Pošlete kolegovi odkaz na registraci. Po registraci má přístup člena komise. Roli předsedy a odbornost
          zatím nastavuje správce systému.
        </DialogDescription>
      </DialogHeader>
      <p role="status" className="sr-only">{copy === 'done' ? 'Odkaz na registraci je ve schránce.' : ''}</p>
      {copy === 'failed' && (
        <p role="alert" className="rounded-md border border-border bg-muted/50 px-3 py-2 text-sm">
          Odkaz se nepodařilo zkopírovat, označte ho ručně: <span className="select-all font-medium">{link}</span>
        </p>
      )}
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Zavřít</Button>
        <Button onClick={copyLink}>
          {copy === 'done' ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
          {copy === 'done' ? 'Odkaz zkopírován' : 'Zkopírovat odkaz na registraci'}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
