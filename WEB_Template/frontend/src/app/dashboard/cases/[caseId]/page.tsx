'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { ArrowLeft, NotebookPen } from 'lucide-react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { BriefWindowLink } from '@/components/mdt/BriefWindowLink';
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
    <div className="mx-auto max-w-5xl">
      <CaseBriefScreen
        caseId={caseId}
        canGenerate={can.generateBrief(me)}
        toolbar={
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/dashboard/mdt"
              className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground shadow-2xs transition hover:bg-accent"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Zasedání MDT
            </Link>
            <BriefWindowLink
              caseId={caseId}
              className="h-8 rounded-lg border border-border bg-card px-3 text-xs font-semibold text-foreground shadow-2xs transition hover:bg-accent"
            >
              Otevřít v úzkém okně (vedle PACS)
            </BriefWindowLink>
            <Link
              href={`/dashboard/cases/${encodeURIComponent(caseId)}/record`}
              className="inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-semibold text-primary-foreground shadow-2xs transition hover:bg-primary/90"
            >
              <NotebookPen className="h-3.5 w-3.5" /> Závěr komise
            </Link>
          </div>
        }
      />
    </div>
  );
}
