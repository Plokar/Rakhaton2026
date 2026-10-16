'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { CalendarDays } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { SessionCard, sortSessions } from '@/components/mdt/sessions';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';

/** Seznam zasedání (boardů) → agenda /dashboard/mdt/[sessionId] (FR-P1). */
export default function MdtSessionsPage() {
  const { data, error, loading } = useApiData(mdtApi.getSessions, '');
  const sessions = data ? sortSessions(data) : [];

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-3xl space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Zasedání MDT</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Boardy komise s termínem a agendou zařazených pacientů.
          </p>
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
      </div>
    </DashboardLayout>
  );
}
