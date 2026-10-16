'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { CalendarDays, Plus } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { BoardDialog } from '@/components/mdt/BoardDialog';
import { can, useMe } from '@/components/mdt/me';
import { SessionCard, sortSessions } from '@/components/mdt/sessions';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi, type SessionInput } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';

const fetchSessions = () => mdtApi.getSessions();

/** Seznam zasedání (boardů) → agenda /dashboard/mdt/[sessionId] (FR-P1). Board zakládá předseda. */
export default function MdtSessionsPage() {
  return (
    <DashboardLayout>
      <SessionsContent />
    </DashboardLayout>
  );
}

function SessionsContent() {
  const me = useMe();
  const [version, setVersion] = React.useState(0);
  const [creating, setCreating] = React.useState(false);
  const { data, error, loading } = useApiData(fetchSessions, String(version));
  const sessions = data ? sortSessions(data) : [];

  const create = async (input: SessionInput) => {
    await mdtApi.createSession(input);
    setVersion((v) => v + 1);
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">Zasedání MDT</h1>
          <p className="mt-1 text-sm text-muted-foreground">Boardy komise s termínem a agendou zařazených pacientů.</p>
        </div>
        {can.manageBoards(me) && (
          <Button size="sm" onClick={() => setCreating(true)} className="h-9 gap-1.5">
            <Plus className="h-4 w-4" /> Nový board
          </Button>
        )}
      </div>

      {loading && (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}
      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      )}
      {data && sessions.length === 0 && (
        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title="Zatím žádná zasedání"
          description="Board zakládá a termín mění předseda komise. Boardy z nominací v IRIS vytvoří příkaz seed_mdt."
        />
      )}
      {sessions.length > 0 && (
        <ul className="space-y-3">
          {sessions.map((s) => (
            <li key={s.id}>
              <SessionCard session={s} />
            </li>
          ))}
        </ul>
      )}

      {creating && <BoardDialog open onClose={() => setCreating(false)} onSubmit={create} />}
    </div>
  );
}
