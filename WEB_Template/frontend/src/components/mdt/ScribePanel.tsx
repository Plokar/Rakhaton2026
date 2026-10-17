'use client';

import * as React from 'react';
import { ChevronRight, FileAudio } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { Decision } from '@/types/mdt';
import { AiTag } from './AiBlock';
import { JobProgress } from './JobProgress';

/**
 * AI zapisovatel (BON-3): z nahrávky nebo přepisu diskuse AI navrhne znění závěru a úkoly do draftu.
 * Návrh je v editoru označený „AI návrh“, předseda ho upraví a potvrdí; potvrzený závěr se nepřepíše.
 */
export function ScribePanel({ caseId, dirty, onDraft }: { caseId: string; dirty: boolean; onDraft: (decision: Decision) => void }) {
  const [open, setOpen] = React.useState(false);
  const [audio, setAudio] = React.useState<File | null>(null);
  const [transcript, setTranscript] = React.useState('');
  const [jobId, setJobId] = React.useState<number | null>(null);
  const [starting, setStarting] = React.useState(false);
  const bodyId = React.useId();

  const start = async () => {
    setStarting(true);
    try {
      const { job_id } = await mdtApi.scribe(caseId, audio ? { audio } : { transcript });
      setJobId(job_id);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Zapisovatele se nepodařilo spustit.'));
    } finally {
      setStarting(false);
    }
  };
  const onDone = React.useCallback(async () => {
    setJobId(null);
    try {
      onDraft(await mdtApi.getDecision(caseId));
      toast.success('Návrh závěru od AI je v editoru', { description: 'Části od AI jsou označené. Zkontrolujte je, upravte a potvrďte.' });
      setOpen(false);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Návrh se nepodařilo načíst.'));
    }
  }, [caseId, onDraft]);
  const onError = React.useCallback((message: string) => {
    setJobId(null);
    toast.error(message);
  }, []);

  const ready = Boolean(audio) || transcript.trim().length > 20;

  return (
    <section className="rounded-xl border border-border bg-card" aria-labelledby="scribe-title">
      <h2 id="scribe-title" className="text-sm font-semibold">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={bodyId}
          className="flex w-full items-center gap-2 rounded-xl px-4 py-3 text-left hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRight className={cn('size-4 text-muted-foreground transition-transform motion-reduce:transition-none', open && 'rotate-90')} aria-hidden />
          <span className="flex-1">AI zapisovatel: návrh závěru z diskuse</span>
          <AiTag />
        </button>
      </h2>
      {open && (
        <div id={bodyId} className="flex flex-col gap-4 border-t border-border px-4 py-4">
          <p className="text-[13px] text-muted-foreground">
            Nahrajte záznam diskuse nebo vložte přepis. AI navrhne znění závěru a úkoly do draftu, každou část označí jako
            AI návrh. Nic se nestane oficiálním záznamem bez potvrzení předsedou.
          </p>
          {jobId !== null ? (
            <JobProgress jobId={jobId} onDone={onDone} onError={onError} label="Přepisuji diskusi a navrhuji závěr…" />
          ) : (
            <>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="scribe-audio" className="text-[13px] font-medium">Nahrávka diskuse (do 20 MB)</label>
                <div className="flex items-center gap-2">
                  <input
                    id="scribe-audio"
                    type="file"
                    accept="audio/*"
                    onChange={(e) => setAudio(e.target.files?.[0] ?? null)}
                    className="text-sm file:mr-3 file:rounded-md file:border file:border-border file:bg-card file:px-2.5 file:py-1 file:text-sm file:font-medium hover:file:bg-muted"
                  />
                  {audio && <FileAudio className="size-4 text-muted-foreground" aria-hidden />}
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="scribe-transcript" className="text-[13px] font-medium">nebo přepis diskuse</label>
                <Textarea
                  id="scribe-transcript"
                  rows={5}
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                  placeholder="Předseda: Projednáváme P03… Chirurg: …"
                  disabled={Boolean(audio)}
                />
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Button onClick={start} isLoading={starting} disabled={!ready || dirty}>
                  Navrhnout závěr z diskuse
                </Button>
                {dirty && <span className="text-xs text-muted-foreground">Nejdřív uložte rozepsaný draft, návrh AI ho doplní.</span>}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
