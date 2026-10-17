'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { Activity } from 'lucide-react';
import { CaseBriefScreen } from '@/components/mdt/CaseBriefScreen';
import { can, MeProvider, useMe } from '@/components/mdt/me';
import { ThemeToggle } from '@/components/ui/theme-toggle';

/**
 * Podklad v samostatném úzkém okně bez navigace (FR-U2, D-017): lékař ho má vedle PACS.
 * Chráněno v proxy.ts stejně jako /dashboard.
 */
export default function BriefWindowPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = React.use(params);
  return (
    <MeProvider userId="brief">
      <BriefWindow caseId={caseId} />
    </MeProvider>
  );
}

function BriefWindow({ caseId }: { caseId: string }) {
  const me = useMe();
  return (
    <main className="mx-auto w-full max-w-xl px-4 py-3">
      <CaseBriefScreen
        caseId={caseId}
        canGenerate={can.generateBrief(me)}
        toolbar={
          <div className="flex w-full items-center justify-between">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Activity className="size-3.5 text-primary" aria-hidden />
              <span translate="no">MedTeam</span> · podklad pro komisi
            </span>
            <ThemeToggle />
          </div>
        }
      />
    </main>
  );
}
