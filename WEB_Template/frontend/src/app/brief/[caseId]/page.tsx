'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { CaseBriefScreen } from '@/components/mdt/CaseBriefScreen';
import { can, MeProvider, useMe } from '@/components/mdt/me';
import { ThemeToggle } from '@/components/ui/theme-toggle';

/**
 * Podklad v samostatném úzkém okně bez navigace (FR-U2, D-017): lékař ho má vedle PACS.
 * Chráněno v proxy.ts stejně jako /dashboard. Detail úzkého rozložení dodělává T-505.
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
    <main className="mx-auto w-full max-w-xl px-3 py-3">
      <CaseBriefScreen
        caseId={caseId}
        canGenerate={can.generateBrief(me)}
        toolbar={
          <div className="flex w-full items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground">MDT Copilot · podklad</span>
            <ThemeToggle />
          </div>
        }
      />
    </main>
  );
}
