'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, CalendarDays, Pencil, SlidersHorizontal, Trash2, UserPlus, UsersRound } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { BoardDialog } from '@/components/mdt/BoardDialog';
import { formatDate } from '@/components/mdt/format';
import { can, useMe } from '@/components/mdt/me';
import { AgendaItem, SESSION_STATUS, sortSessions } from '@/components/mdt/sessions';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi, type SessionInput } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';

// Klíč „sessionId|verze“: po úpravě se agenda načte znovu.
const fetchSession = (key: string) => mdtApi.getSession(key.split('|')[0]);
const fetchSessions = () => mdtApi.getSessions();

/** Agenda zasedání (FR-P1, FR-P2): pacienti v pořadí, stav, přechod na podklad, přesun mezi boardy. */
export default function MdtSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = React.use(params);
  return (
    <DashboardLayout>
      <AgendaContent sessionId={sessionId} />
    </DashboardLayout>
  );
}

function AgendaContent({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const me = useMe();
  const [version, setVersion] = React.useState(0);
  const [editing, setEditing] = React.useState(false);
  const [deleteError, setDeleteError] = React.useState<string | null>(null);
  const { data: session, error, loading } = useApiData(fetchSession, `${sessionId}|${version}`);
  const { data: allSessions } = useApiData(fetchSessions, String(version));
  const cases = session ? [...session.cases].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)) : [];
  const moveTargets = allSessions ? sortSessions(allSessions.filter((s) => String(s.id) !== sessionId && s.status !== 'closed')) : [];
  const reload = () => setVersion((v) => v + 1);

  const update = async (input: SessionInput) => {
    await mdtApi.updateSession(Number(sessionId), input);
    reload();
  };
  const remove = async () => {
    if (!window.confirm('Smazat prázdný board?')) return;
    try {
      await mdtApi.deleteSession(Number(sessionId));
      router.push('/dashboard/mdt');
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Board se nepodařilo smazat.');
    }
  };

  return (
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
          <div className="flex flex-wrap items-start justify-between gap-3">
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
            <div className="flex flex-wrap gap-2">
              {can.generateBrief(me) && (
                <Link
                  href={`/dashboard/mdt/${encodeURIComponent(sessionId)}/add`}
                  className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
                >
                  <UserPlus className="h-3.5 w-3.5" aria-hidden /> Zařadit pacienta
                </Link>
              )}
              <Link
                href={`/dashboard/mdt/${encodeURIComponent(sessionId)}/setup`}
                className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border px-3 text-xs font-medium text-foreground hover:bg-accent"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden /> {can.manageBoards(me) ? 'Nastavit podklad' : 'Nastavení podkladu'}
              </Link>
            {can.manageBoards(me) && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setEditing(true)} className="gap-1.5">
                  <Pencil className="h-3.5 w-3.5" /> Upravit
                </Button>
                {cases.length === 0 && (
                  <Button variant="outline" size="sm" onClick={remove} className="gap-1.5 text-destructive">
                    <Trash2 className="h-3.5 w-3.5" /> Smazat
                  </Button>
                )}
              </div>
            )}
            </div>
          </div>
          {deleteError && <p className="text-sm text-destructive">{deleteError}</p>}

          {cases.length === 0 ? (
            <EmptyState
              icon={<UsersRound className="h-6 w-6" />}
              title="V agendě zatím nejsou pacienti"
              description="Pacienta zařazuje zadávající lékař formulářem s kontrolou úplnosti."
            />
          ) : (
            <ol className="space-y-3" aria-label="Agenda zasedání">
              {cases.map((c) => (
                <AgendaItem
                  key={c.id ?? c.patient_id}
                  item={c}
                  moveTargets={moveTargets}
                  onMove={
                    c.id !== undefined && can.editCase(me, c)
                      ? async (target) => {
                          await mdtApi.updateCase(c.id as number, { session: target });
                          reload();
                        }
                      : undefined
                  }
                />
              ))}
            </ol>
          )}

          {editing && <BoardDialog open session={session} onClose={() => setEditing(false)} onSubmit={update} />}
        </>
      )}
    </div>
  );
}
