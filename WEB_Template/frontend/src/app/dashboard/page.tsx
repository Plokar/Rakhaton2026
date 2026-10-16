'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { SessionCard, sortSessions } from '@/components/mdt/sessions';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import { ArrowUpRight, CalendarDays, FileText, ListChecks } from 'lucide-react';

// Přehled MDT (ARCH §7.1): nadcházející boardy (zasedání) a úkoly po termínu (T-511).
export default function DashboardPage() {
  const { user } = useAuth();
  const { data, error, loading } = useApiData(mdtApi.getSessions, '');
  const upcoming = data ? sortSessions(data.filter((s) => s.status !== 'closed')).slice(0, 4) : [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground">Klinický přehled MDT</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {user?.first_name ? `${user.first_name}, ` : ''}zasedání komise (boardy), zařazení pacienti a úkoly po termínu.
            </p>
          </div>
          <Link
            href="/dashboard/mdt"
            className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3.5 text-xs font-semibold text-primary-foreground shadow-2xs hover:bg-primary/90"
          >
            <CalendarDays className="h-3.5 w-3.5" aria-hidden /> Otevřít boardy MDT
          </Link>
        </div>

        <Link
          href="/dashboard/cases/demo"
          className="group flex flex-wrap items-center justify-between gap-4 rounded-xl border border-primary/35 bg-card p-4 shadow-xs transition hover:border-primary hover:bg-primary/[0.04]"
        >
          <div className="flex items-start gap-3.5">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-primary/25 bg-primary/10 text-primary">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-base font-extrabold text-foreground group-hover:text-primary transition-colors">
                  Ukázkový 30s podklad pacienta P03
                </span>
                <span className="rounded border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-xs font-bold text-primary">
                  C18.7 · Stádium IV
                </span>
                <span className="rounded border border-border bg-muted px-2 py-0.5 font-mono text-xs font-bold text-foreground">
                  ECOG 0 · Záměr C
                </span>
              </div>
              <span className="mt-1 block text-xs text-muted-foreground">
                Adenokarcinom sigmoidea s jaterními metastázami · posouzení resekability jater a sekvence léčby (data z fixtures, funguje i bez backendu)
              </span>
            </div>
          </div>
          <span className="inline-flex items-center gap-1 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-bold text-foreground group-hover:border-primary/40 group-hover:text-primary">
            Otevřít 30s podklad <ArrowUpRight className="h-3.5 w-3.5" />
          </span>
        </Link>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base font-semibold">Zasedání MDT</CardTitle>
                <CardDescription className="text-xs mt-0.5">Boardy, termíny a zařazení pacienti</CardDescription>
              </div>
              <Link
                href="/dashboard/mdt"
                className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
              >
                Všechna zasedání <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </CardHeader>
            <CardContent>
              {loading && <Skeleton className="h-24 w-full" />}
              {error && <p className="text-sm text-destructive">{error}</p>}
              {data && upcoming.length === 0 && (
                <EmptyState
                  icon={<CalendarDays className="h-6 w-6" />}
                  title="Žádná nadcházející zasedání"
                  description="Board zakládá a termín mění předseda komise."
                />
              )}
              {upcoming.length > 0 && (
                <ul className="space-y-2">
                  {upcoming.map((s) => (
                    <li key={s.id}>
                      <SessionCard session={s} />
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle className="text-base font-semibold">Úkoly po termínu</CardTitle>
                <CardDescription className="text-xs mt-0.5">Úkoly z potvrzených závěrů komise</CardDescription>
              </div>
              <Link
                href="/dashboard/tasks"
                className="text-xs font-semibold text-primary hover:underline flex items-center gap-1"
              >
                Všechny úkoly <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </CardHeader>
            <CardContent>
              <EmptyState
                icon={<ListChecks className="h-6 w-6" />}
                title="Žádné úkoly po termínu"
                description="Úkoly vzniknou po potvrzení závěru komise."
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
