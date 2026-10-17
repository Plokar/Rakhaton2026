'use client';

import * as React from 'react';
import Link from 'next/link';
import { ChevronRight, Lock, Plus, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Page, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/shadcn/button';
import { Skeleton } from '@/components/shadcn/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { useSaveSession, useSessionsQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtSessionListItem } from '@/types/mdt';
import { BoardDialog } from './BoardDialog';
import { dayLabel, patientsLabel, pragueDay, timeLabel, todayPrague } from './dates';
import { InviteDialog } from './InviteDialog';
import { can, useMe } from './me';

/**
 * Seznam zasedání (NAVRH_UI §4): řádky místo karet, nadcházející nahoře, minulá pod nimi.
 * Plánování v týdnech je v kalendáři na Přehledu, projednání v Jednání komise.
 */
export function SessionList() {
  const me = useMe();
  const sessions = useSessionsQuery();
  const save = useSaveSession();
  const [creating, setCreating] = React.useState(false);
  const [inviting, setInviting] = React.useState(false);
  const [showPast, setShowPast] = React.useState(false);
  const today = todayPrague();
  const manage = can.manageBoards(me);

  const sorted = (sessions.data ?? []).toSorted((a, b) => a.date.localeCompare(b.date) || a.title.localeCompare(b.title, 'cs'));
  const upcoming = sorted.filter((s) => pragueDay(s.date) >= today);
  const past = sorted.filter((s) => pragueDay(s.date) < today).reverse();

  return (
    <Page className="max-w-5xl">
      <PageHeader
        title="Zasedání"
        meta="Boardy komisí s termínem a agendou pacientů"
        actions={
          manage && (
            <>
              <Button variant="outline" size="lg" onClick={() => setInviting(true)}>
                <UserPlus aria-hidden /> Pozvat kolegu
              </Button>
              <Button size="lg" onClick={() => setCreating(true)}>
                <Plus aria-hidden /> Nový board
              </Button>
            </>
          )
        }
      />

      {sessions.isLoading ? (
        <div className="flex flex-col gap-2" aria-busy="true">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}
        </div>
      ) : sessions.isError ? (
        <p role="alert" className="text-sm text-destructive">Zasedání se nepodařilo načíst. Obnovte stránku (F5).</p>
      ) : sorted.length === 0 ? (
        <EmptyState
          title="Zatím žádné zasedání"
          description={manage ? 'Založte první board tlačítkem „Nový board“.' : 'Zasedání zakládá předseda komise.'}
        />
      ) : (
        <>
          <section aria-labelledby="upcoming-title">
            <h2 id="upcoming-title" className="mb-2 text-base font-semibold">
              Nadcházející <span className="font-normal text-muted-foreground">({upcoming.length})</span>
            </h2>
            {upcoming.length ? <SessionRows sessions={upcoming} today={today} /> : <p className="text-sm text-muted-foreground">Žádné naplánované zasedání.</p>}
          </section>
          {past.length > 0 && (
            <section aria-labelledby="past-title">
              <h2 id="past-title" className="mb-2 text-base font-semibold">
                <button
                  type="button"
                  onClick={() => setShowPast(!showPast)}
                  aria-expanded={showPast}
                  className="inline-flex items-center gap-1.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <ChevronRight className={cn('size-4 transition-transform motion-reduce:transition-none', showPast && 'rotate-90')} aria-hidden />
                  Minulá <span className="font-normal text-muted-foreground">({past.length})</span>
                </button>
              </h2>
              {showPast && <SessionRows sessions={past} today={today} muted />}
            </section>
          )}
        </>
      )}

      {creating && (
        <BoardDialog
          open
          onClose={() => setCreating(false)}
          onSubmit={async (input) => {
            const created = await save.mutateAsync({ input });
            toast.success(`Board ${created.title} založen`, { description: `${dayLabel(created.date)} ${timeLabel(created.date)}` });
          }}
        />
      )}
      <InviteDialog open={inviting} onClose={() => setInviting(false)} />
    </Page>
  );
}

function SessionRows({ sessions, today, muted = false }: { sessions: MdtSessionListItem[]; today: string; muted?: boolean }) {
  return (
    <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card">
      {sessions.map((s) => {
        const isToday = pragueDay(s.date) === today;
        return (
          <li key={s.id}>
            <Link
              href={`/dashboard/mdt/${s.id}`}
              className={cn(
                'grid grid-cols-[6.5rem_minmax(0,1fr)_auto] items-center gap-x-4 px-4 py-3 transition-colors hover:bg-muted/60 focus-visible:bg-muted/60 focus-visible:outline-none sm:grid-cols-[6.5rem_3rem_minmax(0,1fr)_auto]',
                muted && 'text-muted-foreground',
              )}
            >
              <span className={cn('text-sm font-medium tabular-nums', isToday && 'text-primary')}>
                {isToday ? 'dnes' : dayLabel(s.date)}
                <span className="block text-xs font-normal text-muted-foreground sm:hidden">{timeLabel(s.date)}</span>
              </span>
              <span className="hidden text-sm tabular-nums text-muted-foreground sm:block">{timeLabel(s.date)}</span>
              <span className="min-w-0">
                <span className={cn('block truncate text-sm', !muted && 'font-medium text-foreground')}>{s.title}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {s.patients.length ? (
                    <span translate="no">{s.patients.join(', ')}</span>
                  ) : (
                    'Zatím bez pacientů'
                  )}
                  {s.chair && <> · předseda {s.chair.name}</>}
                </span>
              </span>
              <span className="flex items-center gap-3 text-xs text-muted-foreground">
                {s.status === 'in_progress' && <span className="font-medium text-primary">probíhá</span>}
                {s.status === 'closed' && (
                  <span className="inline-flex items-center gap-1">
                    <Lock className="size-3" aria-hidden /> uzavřeno
                  </span>
                )}
                <span className="hidden tabular-nums sm:inline">{patientsLabel(s.patients.length)}</span>
                <ChevronRight className="size-4" aria-hidden />
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
