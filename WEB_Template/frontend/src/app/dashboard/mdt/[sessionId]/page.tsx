'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { ArrowLeft, CalendarDays, UsersRound } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { formatDate } from '@/components/mdt/format';
import { AgendaItem, SESSION_STATUS } from '@/components/mdt/sessions';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';

/** Agenda zasedání (FR-P1, FR-P2): pacienti v pořadí, stav a přechod na podklad. */
export default function MdtSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = React.use(params);
  const { data: session, error, loading } = useApiData(mdtApi.getSession, sessionId);
  const cases = session ? [...session.cases].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)) : [];

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-3xl space-y-5">
        <Link
          href="/dashboard/mdt"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Zasedání
        </Link>

        {loading && (
          <div className="space-y-3" aria-busy="true">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-32 w-full" />
          </div>
        )}
        {error && (
          <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
        )}

        {session && (
          <>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">{session.title}</h1>
              <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <CalendarDays className="h-4 w-4" aria-hidden /> {formatDate(session.date)}
                </span>
                <span>{SESSION_STATUS[session.status]}</span>
                {session.chair && (
                  <span className="inline-flex items-center gap-1">
                    <UsersRound className="h-4 w-4" aria-hidden /> předseda {session.chair.name}
                  </span>
                )}
              </p>
            </div>

            {cases.length === 0 ? (
              <EmptyState
                icon={<UsersRound className="h-6 w-6" />}
                title="V agendě zatím nejsou pacienti"
                description="Pacienta zařazuje zadávající lékař formulářem s kontrolou úplnosti."
              />
            ) : (
              <ol className="space-y-3" aria-label="Agenda zasedání">
                {cases.map((c) => (
                  <AgendaItem key={c.id ?? c.patient_id} item={c} />
                ))}
              </ol>
            )}
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
