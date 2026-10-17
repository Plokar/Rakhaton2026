'use client';

import * as React from 'react';
import { FileText } from 'lucide-react';
import { Skeleton } from '@/components/shadcn/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { briefP03 } from '@/lib/fixtures';
import { apiErrorMessage, useBriefQuery } from '@/lib/queries';
import { BriefView } from './BriefView';
import { apiDataSource, fixtureDataSource } from './data-source';
import { DEMO_CASE } from './detail/CaseDetail';
import { GenerateBrief, useBriefJob } from './GenerateBrief';

export { DEMO_CASE };

/**
 * Podklad případu v úzkém okně `/brief/[caseId]` (FR-U2): načtení ze sdílené cache (nebo fixture
 * u `demo`), generování přes job s průběhem a zobrazení v `BriefView`.
 */
export function CaseBriefScreen({
  caseId,
  toolbar,
  canGenerate = false,
}: {
  caseId: string;
  toolbar?: React.ReactNode;
  /** Generovat podklad smí předseda a zadávající lékař (ARCH §6.3). */
  canGenerate?: boolean;
}) {
  const isDemo = caseId === DEMO_CASE;
  const query = useBriefQuery(isDemo ? null : caseId);
  const job = useBriefJob(caseId);
  const brief = isDemo ? briefP03 : query.data;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">{toolbar}</div>

      {isDemo && (
        <p className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
          Ukázkový podklad pacienta P03 z fixtures (syntetická data, bez backendu).
        </p>
      )}
      {job.progress}

      {!isDemo && query.isLoading && (
        <div className="flex flex-col gap-3" aria-busy="true" aria-label="Načítám podklad">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
          <Skeleton className="mt-4 h-32" />
        </div>
      )}
      {!isDemo && query.isError && (
        <p role="alert" className="text-sm text-destructive">{apiErrorMessage(query.error, 'Podklad se nepodařilo načíst.')}</p>
      )}
      {!isDemo && query.data === null && !job.running && (
        <EmptyState
          icon={<FileText aria-hidden />}
          title="Podklad ještě nevznikl"
          description={
            canGenerate
              ? 'AI připraví podklad z dat pacienta v IRIS podle nastavení předsedy. Trvá to několik sekund.'
              : 'Podklad připraví předseda nebo zadávající lékař.'
          }
          action={canGenerate ? <GenerateBrief caseId={caseId} /> : undefined}
        />
      )}
      {brief && <BriefView brief={brief} dataSource={isDemo ? fixtureDataSource : apiDataSource} />}
    </div>
  );
}
