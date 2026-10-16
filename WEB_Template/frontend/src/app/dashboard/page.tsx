'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { ArrowUpRight, CalendarDays, ListChecks } from 'lucide-react';

// Přehled MDT (ARCH §7.1): boardy = zasedání, případy a jejich stav, úkoly po termínu.
// Data doplní T-109 (boardy a agenda) a T-511 (úkoly po zasedání).
export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Přehled</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {user?.first_name ? `${user.first_name}, ` : ''}zasedání komise, zařazení pacienti a úkoly po termínu.
          </p>
        </div>

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
              <EmptyState
                icon={<CalendarDays className="h-6 w-6" />}
                title="Zatím žádná zasedání"
                description="Boardy a agenda se načtou z backendu, jakmile bude hotový seed zasedání (T-109)."
              />
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
                description="Úkoly vzniknou po potvrzení závěru komise (T-511)."
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
