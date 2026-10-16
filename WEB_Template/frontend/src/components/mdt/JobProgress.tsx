'use client';

import * as React from 'react';
import { LoaderCircle } from 'lucide-react';
import { mdtApi, type GenerationJob } from '@/lib/mdt-api';

const STATUS_LABEL: Record<GenerationJob['status'], string> = {
  queued: 'Ve frontě…',
  running: 'Generuji podklad…',
  done: 'Hotovo',
  error: 'Generování selhalo',
};

/** Průběh generování podkladu: polling `/api/jobs/{id}/` à 1 s (D-004). */
export function JobProgress({
  jobId,
  onDone,
  onError,
}: {
  jobId: number;
  onDone: (job: GenerationJob) => void;
  onError: (message: string) => void;
}) {
  const [job, setJob] = React.useState<GenerationJob | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = () => {
      mdtApi
        .getJob(jobId)
        .then((next) => {
          if (cancelled) return;
          setJob(next);
          if (next.status === 'done') onDone(next);
          else if (next.status === 'error') onError(next.error ?? STATUS_LABEL.error);
          else timer = setTimeout(poll, 1000);
        })
        .catch((err: unknown) => !cancelled && onError(err instanceof Error ? err.message : STATUS_LABEL.error));
    };
    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId, onDone, onError]);

  const progress = job?.progress ?? 0;
  return (
    <div className="rounded-xl border border-border bg-card p-4" role="status" aria-live="polite">
      <p className="flex items-center gap-2 text-sm font-medium text-foreground">
        <LoaderCircle className="h-4 w-4 animate-spin text-purple-500" aria-hidden />
        {STATUS_LABEL[job?.status ?? 'queued']}
        <span className="ml-auto font-mono text-xs text-muted-foreground">{progress} %</span>
      </p>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-purple-500 transition-all duration-500" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
