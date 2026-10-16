'use client';

import * as React from 'react';
import { FileText, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api';
import { briefP03, evidenceP03 } from '@/lib/fixtures';
import { mdtApi, type StoredBrief } from '@/lib/mdt-api';
import { BriefView } from './BriefView';
import { JobProgress } from './JobProgress';
import type { SourceLoader } from './SourceDrawer';

/** Případ `demo` = podklad P03 z fixtures, bez backendu (ARCH §7.3). */
export const DEMO_CASE = 'demo';

const loadFixtureSource: SourceLoader = async (id) => {
  const source = (await evidenceP03())[id];
  if (!source) throw new Error('Zdroj ve fixtures není.');
  return source;
};
const loadApiSource: SourceLoader = (id) => mdtApi.getEvidence(id);

type LoadState = { key: string; brief?: StoredBrief; missing?: boolean; error?: string };

/**
 * Podklad případu: načtení z API (nebo fixture u `demo`), generování přes job s průběhem
 * a zobrazení v `BriefView`. Sdílí ho `/dashboard/cases/[caseId]` a úzké okno `/brief/[caseId]`.
 */
export function CaseBriefScreen({ caseId, toolbar }: { caseId: string; toolbar?: React.ReactNode }) {
  const isDemo = caseId === DEMO_CASE;
  const [version, setVersion] = React.useState(0);
  const [loaded, setLoaded] = React.useState<LoadState | null>(null);
  const [jobId, setJobId] = React.useState<number | null>(null);
  const [jobError, setJobError] = React.useState<string | null>(null);
  const key = `${caseId}:${version}`;

  React.useEffect(() => {
    if (isDemo) return;
    let cancelled = false;
    mdtApi
      .getBrief(caseId)
      .then((brief) => !cancelled && setLoaded({ key, brief }))
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) setLoaded({ key, missing: true });
        else setLoaded({ key, error: err instanceof Error ? err.message : 'Podklad se nepodařilo načíst.' });
      });
    return () => {
      cancelled = true;
    };
  }, [caseId, isDemo, key]);

  const current: LoadState | null = isDemo ? { key, brief: briefP03 } : loaded?.key === key ? loaded : null;

  const generate = async () => {
    setJobError(null);
    try {
      const { job_id } = await mdtApi.generateBrief(caseId);
      setJobId(job_id);
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'Generování se nepodařilo spustit.');
    }
  };
  const onJobDone = React.useCallback(() => {
    setJobId(null);
    setVersion((v) => v + 1);
  }, []);
  const onJobError = React.useCallback((message: string) => {
    setJobId(null);
    setJobError(message);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {toolbar}
        {!isDemo && current?.brief && jobId === null && (
          <Button variant="outline" size="sm" onClick={generate} className="ml-auto gap-1.5">
            <RefreshCw className="h-3.5 w-3.5" /> Přegenerovat
          </Button>
        )}
      </div>

      {isDemo && (
        <p className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
          Ukázkový podklad pacienta P03 z fixtures (bez backendu). Zdroje citací jsou odpovědi resolveru z datasetu.
        </p>
      )}

      {jobId !== null && <JobProgress jobId={jobId} onDone={onJobDone} onError={onJobError} />}
      {jobError && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {jobError}
        </p>
      )}

      {!current && (
        <div className="space-y-3" aria-busy="true" aria-label="Načítám podklad">
          <Skeleton className="h-56 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}
      {current?.missing && jobId === null && (
        <EmptyState
          icon={<FileText className="h-6 w-6" />}
          title="Podklad ještě nebyl vygenerován"
          description="AI připraví podklad z dat pacienta v IRIS podle nastavení předsedy. Trvá to několik sekund."
          action={<Button onClick={generate}>Vygenerovat podklad</Button>}
        />
      )}
      {current?.error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {current.error}
        </p>
      )}
      {current?.brief && <BriefView brief={current.brief} loadSource={isDemo ? loadFixtureSource : loadApiSource} />}
    </div>
  );
}
