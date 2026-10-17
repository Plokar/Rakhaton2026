'use client';

import * as React from 'react';
import { mdtApi, type GenerationJob } from '@/lib/mdt-api';

const STATUS_LABEL: Record<GenerationJob['status'], string> = {
  queued: 'Ve frontě…',
  running: 'Připravuji podklad…',
  done: 'Hotovo',
  error: 'Podklad se nepodařilo připravit',
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
    <div className="flex w-full max-w-sm flex-col gap-1.5" role="status" aria-live="polite">
      <p className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium">{STATUS_LABEL[job?.status ?? 'queued']}</span>
        <span className="text-xs tabular-nums text-muted-foreground">{progress} %</span>
      </p>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary transition-[width] duration-500 motion-reduce:transition-none" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
