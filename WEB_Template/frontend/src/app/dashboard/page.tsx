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
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Přehled</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {user?.first_name ? `${user.first_name}, ` : ''}zasedání komise, zařazení pacienti a úkoly po termínu.
          </p>
        </div>

        <Link
          href="/dashboard/cases/demo"
          className="flex items-center gap-3 rounded-xl border border-dashed border-border bg-card px-4 py-3 text-sm transition hover:border-primary hover:bg-muted/40"
        >
          <FileText className="h-5 w-5 shrink-0 text-primary" />
          <span className="min-w-0 flex-1">
            <span className="font-semibold text-foreground">Ukázkový podklad P03</span>
            <span className="block text-xs text-muted-foreground">
              Kolorektální karcinom s jaterními metastázami, data z fixtures (funguje i bez backendu)
            </span>
          </span>
          <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />
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
