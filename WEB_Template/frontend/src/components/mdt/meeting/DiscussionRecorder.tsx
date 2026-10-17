'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Mic, Square } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { cn } from '@/lib/utils';
import { can, useMe } from '../me';

const MIN_SECONDS = 5;                       // kratší úsek = omylem zapnuté, neodesílá se
const MIME = ['audio/webm;codecs=opus', 'audio/ogg;codecs=opus', 'audio/mp4'];

interface Segment {
  rec: MediaRecorder;
  caseId: number;
  patient: string;
  started: number;
}

const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

/** Job zapisovatele (přepis + draft) do konce; polling à 1,5 s jako JobProgress (D-004). */
async function waitForJob(jobId: number): Promise<void> {
  for (;;) {
    const job = await mdtApi.getJob(jobId);
    if (job.status === 'done') return;
    if (job.status === 'error') throw new Error(job.error ?? 'Přepis se nepovedl.');
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}

/**
 * Nahrávání diskuse komise (BON-3): zapnutý přepínač nahrává pacienta na řadě; po přepnutí na dalšího pacienta
 * (nebo vypnutí) se jeho úsek sám odešle k přepisu (Whisper) a vznikne draft závěru s citacemi úseků přepisu.
 * Nahrávat smí předseda a zadávající lékař; potvrzený závěr zapisovatel nepřepíše (409).
 */
export function DiscussionRecorder({ current, className }: { current: { id: number; patient_id: string } | null; className?: string }) {
  const router = useRouter();
  const me = useMe();
  const [on, setOn] = React.useState(false);
  const [elapsed, setElapsed] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);
  const stream = React.useRef<MediaStream | null>(null);
  const segment = React.useRef<Segment | null>(null);

  const upload = React.useCallback(
    async (caseId: number, patient: string, blob: Blob, seconds: number) => {
      if (seconds < MIN_SECONDS || !blob.size) return;
      const ext = blob.type.includes('mp4') ? 'm4a' : blob.type.includes('ogg') ? 'ogg' : 'webm';
      const id = toast.loading(`Přepis diskuse ${patient} (${mmss(seconds)}) a draft závěru…`);
      try {
        const { job_id } = await mdtApi.scribe(String(caseId), { audio: new File([blob], `diskuse-${patient}.${ext}`, { type: blob.type }) });
        await waitForJob(job_id);
        toast.success(`Draft závěru ${patient} je připravený`, {
          id,
          description: 'Z přepisu diskuse, s citacemi úseků. Rozhoduje lékař.',
          action: { label: 'Otevřít', onClick: () => router.push(`/dashboard/cases/${caseId}/record`) },
        });
      } catch (err) {
        toast.error(apiErrorMessage(err, `Přepis diskuse ${patient} se nepovedl.`), { id });
      }
    },
    [router],
  );

  /** Ukončí úsek pacienta; `onstop` ho odešle. */
  const finish = React.useCallback(() => {
    const active = segment.current;
    segment.current = null;
    if (active && active.rec.state !== 'inactive') active.rec.stop();
  }, []);

  const start = React.useCallback(
    (caseId: number, patient: string) => {
      if (!stream.current) return;
      const mimeType = MIME.find((m) => MediaRecorder.isTypeSupported(m));
      // 32 kb/s: řeč je srozumitelná a 20 MB (limit přepisu) vystačí na ~80 min
      const rec = new MediaRecorder(stream.current, { ...(mimeType ? { mimeType } : {}), audioBitsPerSecond: 32_000 });
      const chunks: Blob[] = [];
      const started = Date.now();
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = () => void upload(caseId, patient, new Blob(chunks, { type: rec.mimeType }), Math.round((Date.now() - started) / 1000));
      rec.start(1000);
      segment.current = { rec, caseId, patient, started };
    },
    [upload],
  );

  const stopAll = React.useCallback(() => {
    finish();
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }, [finish]);

  // Přepnutí pacienta během nahrávání: úsek předchozího se odešle, nový začne.
  React.useEffect(() => {
    if (!on || !current || segment.current?.caseId === current.id) return;
    finish();
    start(current.id, current.patient_id);
  }, [on, current, finish, start]);

  React.useEffect(() => {
    if (!on) return;
    const timer = setInterval(() => setElapsed(segment.current ? Math.round((Date.now() - segment.current.started) / 1000) : 0), 1000);
    return () => clearInterval(timer);
  }, [on]);

  React.useEffect(() => stopAll, [stopAll]);            // odchod ze stránky: poslední úsek se odešle

  if (!can.generateBrief(me)) return null;

  const toggle = async () => {
    setError(null);
    if (on) {
      setOn(false);
      setElapsed(0);
      stopAll();
      return;
    }
    if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
      setError('Prohlížeč nahrávání nepodporuje.');
      return;
    }
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      setOn(true);
    } catch {
      setError('Prohlížeč nepovolil mikrofon. Povolte ho v nastavení stránky.');
    }
  };

  return (
    <div className={cn('flex flex-col gap-2 border-t border-border px-3 py-3', className)}>
      <Button variant={on ? 'destructive' : 'outline'} size="sm" aria-pressed={on} onClick={() => void toggle()} disabled={!current && !on}>
        {on ? <Square aria-hidden /> : <Mic aria-hidden />} {on ? 'Ukončit nahrávání' : 'Nahrávat diskusi'}
      </Button>
      {on ? (
        <p className="flex items-center gap-2 text-xs" aria-live="polite">
          <span className="size-2 shrink-0 animate-pulse rounded-full bg-red-600 motion-reduce:animate-none" aria-hidden />
          <span>
            Nahrává se <span translate="no" className="font-medium">{current?.patient_id}</span> ·{' '}
            <span className="tabular-nums">{mmss(elapsed)}</span>. Po přepnutí pacienta se úsek odešle k přepisu.
          </span>
        </p>
      ) : (
        <p className="text-xs text-muted-foreground">
          Diskuse ke každému pacientovi se po přepnutí odešle k přepisu (Whisper) a vznikne draft závěru. Zapněte jen se
          souhlasem přítomných.
        </p>
      )}
      {error && <p role="alert" className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
