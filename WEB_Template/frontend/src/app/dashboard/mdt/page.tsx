'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { EmptyState } from '@/components/ui/empty-state';
import { CalendarDays } from 'lucide-react';

// Seznam zasedání (boardů) → agenda /dashboard/mdt/[sessionId]. Data doplní T-109, zakládání boardů T-501.
export default function MdtSessionsPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Zasedání MDT</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Boardy komise s termínem a agendou zařazených pacientů.
          </p>
        </div>

        <EmptyState
          icon={<CalendarDays className="h-6 w-6" />}
          title="Zatím žádná zasedání"
          description="Seznam boardů se načte z backendu (T-109). Board zakládá a termín mění předseda komise."
        />
      </div>
    </DashboardLayout>
  );
}
