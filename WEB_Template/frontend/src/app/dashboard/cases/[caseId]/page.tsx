'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { ArrowLeft, NotebookPen, PanelRightOpen } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { CaseBriefScreen } from '@/components/mdt/CaseBriefScreen';
import { can, useMe } from '@/components/mdt/me';

/** Podklad pro komisi v aplikaci (ARCH §7.1). Totéž bez navigace v úzkém okně: `/brief/[caseId]`. */
export default function CaseBriefPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = React.use(params);
  return (
    <DashboardLayout>
      <CaseContent caseId={caseId} />
    </DashboardLayout>
  );
}

function CaseContent({ caseId }: { caseId: string }) {
  const me = useMe();
  return (
    <div className="mx-auto max-w-3xl">
      <CaseBriefScreen
        caseId={caseId}
        canGenerate={can.generateBrief(me)}
        toolbar={
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard/mdt"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Zasedání
            </Link>
            <a
              href={`/brief/${encodeURIComponent(caseId)}`}
              target="_blank"
              rel="noopener"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <PanelRightOpen className="h-3.5 w-3.5" /> Otevřít v úzkém okně
            </a>
            <Link
              href={`/dashboard/cases/${encodeURIComponent(caseId)}/record`}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              <NotebookPen className="h-3.5 w-3.5" /> Závěr komise
            </Link>
          </div>
        }
      />
    </div>
  );
}
