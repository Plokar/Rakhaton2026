'use client';

import * as React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FileAudio, HeartHandshake } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { ApiError } from '@/lib/api';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { AiBlock } from './AiBlock';
import { ClaimList } from './ClaimList';
import { JobProgress } from './JobProgress';

/** Spuštění jobu s průběhem (D-004); `onDone` po dokončení, chyba jako toast. */
function useJob(onDone: () => void, failMessage: string) {
  const [jobId, setJobId] = React.useState<number | null>(null);
  const [starting, setStarting] = React.useState<string | null>(null);
  const run = async (what: string, start: () => Promise<{ job_id: number }>) => {
    setStarting(what);
    try {
      setJobId((await start()).job_id);
    } catch (err) {
      toast.error(apiErrorMessage(err, failMessage));
    } finally {
      setStarting(null);
    }
  };
  const done = React.useCallback(() => {
    setJobId(null);
    onDone();
  }, [onDone]);
  const failed = React.useCallback((message: string) => {
    setJobId(null);
    toast.error(message);
  }, []);
  return { run, starting, jobId, done, failed };
}

/**
 * AI zapisovatel (BON-3, ARCH §5.6): nahrávka diskuse nebo vložený přepis → přepis s mluvčími do IRIS
 * (`DocumentReference/Pxx-mdtNN-prepis`) → draft závěru s citacemi úseků. Draft lékař zkontroluje a upraví.
 */
export function ScribePanel({ caseId, onDraft }: { caseId: string; onDraft: () => void }) {
  const [transcript, setTranscript] = React.useState('');
  const fileRef = React.useRef<HTMLInputElement>(null);
  const job = useJob(onDraft, 'Zapisovatele se nepodařilo spustit.');

  return (
    <section className="rounded-xl border border-border bg-card p-4" aria-labelledby="scribe-title">
      <h2 id="scribe-title" className="text-[15px] font-semibold">AI zapisovatel</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Nahrajte záznam diskuse komise (do 20 MB), nebo vložte přepis. AI z něj připraví draft závěru s citacemi úseků
        přepisu a nahradí jím současný draft. Potvrzený závěr zapisovatel nepřepíše.
      </p>
      {job.jobId !== null ? (
        <div className="mt-3">
          <JobProgress jobId={job.jobId} onDone={job.done} onError={job.failed} runningLabel="Přepisuji diskusi a připravuji draft…" />
        </div>
      ) : (
        <div className="mt-3 flex flex-col gap-3">
          <div>
            <input
              ref={fileRef}
              type="file"
              accept="audio/*"
              className="sr-only"
              tabIndex={-1}
              aria-hidden
              onChange={(e) => {
                const audio = e.target.files?.[0];
                e.target.value = '';
                if (audio) void job.run('audio', () => mdtApi.scribe(caseId, { audio }));
              }}
            />
            <Button variant="outline" onClick={() => fileRef.current?.click()} isLoading={job.starting === 'audio'} disabled={job.starting !== null}>
              <FileAudio aria-hidden /> Nahrát nahrávku diskuse
            </Button>
          </div>
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium">Nebo vložte přepis</span>
            <Textarea
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              rows={4}
              placeholder={'[00:12] onkolog: Pacient je po šesti cyklech FOLFOX…\n[00:40] chirurg: Resekce jater je možná dvoudobě…'}
            />
          </label>
          <div>
            <Button
              variant="outline"
              disabled={!transcript.trim() || job.starting !== null}
              isLoading={job.starting === 'transcript'}
              onClick={() => void job.run('transcript', () => mdtApi.scribe(caseId, { transcript }))}
            >
              Vytvořit draft z přepisu
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

/**
 * Shrnutí pro pacienta (BON-4): laický text z potvrzeného závěru, každá věta s citací; zohlední prioritu
 * a postoj pacienta z PROMs. Je v PDF i FHIR exportu (`DocumentReference/Pxx-mdtNN-pacient`).
 */
export function PatientSummaryPanel({ caseId, canGenerate }: { caseId: string; canGenerate: boolean }) {
  const client = useQueryClient();
  const summary = useQuery({
    queryKey: ['case', caseId, 'patient-summary'],
    queryFn: () =>
      mdtApi.getPatientSummary(caseId).catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }),
  });
  const refresh = React.useCallback(() => {
    void client.invalidateQueries({ queryKey: ['case', caseId, 'patient-summary'] });
    toast.success('Shrnutí pro pacienta je připravené', { description: 'AI návrh, před předáním ho zkontroluje lékař.' });
  }, [client, caseId]);
  const job = useJob(refresh, 'Shrnutí se nepodařilo spustit.');

  if (summary.isLoading) return null;
  if (summary.data) {
    return (
      <AiBlock title="Shrnutí pro pacienta">
        <ClaimList claims={summary.data.items} />
        <p className="mt-3 text-xs text-muted-foreground">
          Laický text ze schváleného závěru ({summary.data.document_reference}). Před předáním pacientovi ho zkontroluje
          lékař. Je v exportu PDF i FHIR.
        </p>
      </AiBlock>
    );
  }
  if (!canGenerate) return null;
  return (
    <div className="flex flex-col items-start gap-2">
      {job.jobId !== null ? (
        <JobProgress jobId={job.jobId} onDone={job.done} onError={job.failed} runningLabel="Píšu shrnutí pro pacienta…" />
      ) : (
        <Button variant="outline" onClick={() => void job.run('summary', () => mdtApi.generatePatientSummary(caseId))} isLoading={job.starting !== null}>
          <HeartHandshake aria-hidden /> Připravit shrnutí pro pacienta
        </Button>
      )}
      {summary.isError && <p role="alert" className="text-sm text-destructive">{apiErrorMessage(summary.error, 'Shrnutí se nepodařilo načíst.')}</p>}
    </div>
  );
}
