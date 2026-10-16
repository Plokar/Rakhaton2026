'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { EmptyState } from '@/components/ui/empty-state';
import { ListChecks } from 'lucide-react';

// Úkoly po zasedání (FR-P3): stav úkolů a termín re-MDT. Data doplní T-511.
export default function MdtTasksPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Úkoly po zasedání</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Úkoly z potvrzených závěrů komise, jejich stav a termíny opětovného projednání.
          </p>
        </div>

        <EmptyState
          icon={<ListChecks className="h-6 w-6" />}
          title="Zatím žádné úkoly"
          description="Úkoly vzniknou po potvrzení závěru komise (T-511)."
        />
      </div>
    </DashboardLayout>
  );
}
