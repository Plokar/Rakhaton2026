'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, useInvalidateCase } from '@/lib/queries';
import { JobProgress } from './JobProgress';

/**
 * Vytvoření (nebo přegenerování) podkladu přes job s průběhem (D-004). Smí předseda a zadávající
 * lékař (ARCH §6.3); po dokončení se obnoví podklad i semafor ve sdílené cache.
 */
export function useBriefJob(caseId: number | string) {
  const [jobId, setJobId] = React.useState<number | null>(null);
  const [starting, setStarting] = React.useState(false);
  const invalidate = useInvalidateCase();

  const start = React.useCallback(async () => {
    setStarting(true);
    try {
      const { job_id } = await mdtApi.generateBrief(String(caseId));
      setJobId(job_id);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Podklad se nepodařilo spustit.'));
    } finally {
      setStarting(false);
    }
  }, [caseId]);
  const onDone = React.useCallback(() => {
    setJobId(null);
    invalidate(caseId);
    toast.success('Podklad je připravený', { description: 'AI návrh s citacemi, rozhoduje lékař.' });
  }, [caseId, invalidate]);
  const onError = React.useCallback((message: string) => {
    setJobId(null);
    toast.error(message);
  }, []);

  const progress = jobId !== null ? <JobProgress jobId={jobId} onDone={onDone} onError={onError} /> : null;
  return { start, starting, running: jobId !== null, progress };
}

export function GenerateBrief({
  caseId,
  label = 'Vytvořit podklad',
  variant = 'default',
}: {
  caseId: number | string;
  label?: string;
  variant?: 'default' | 'outline' | 'ghost';
}) {
  const job = useBriefJob(caseId);
  if (job.progress) return job.progress;
  return (
    <Button variant={variant} onClick={job.start} isLoading={job.starting}>
      {label}
    </Button>
  );
}
