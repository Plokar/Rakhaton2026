'use client';

import * as React from 'react';
import { MessageSquareWarning } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { ToggleGroup, ToggleGroupItem } from '@/components/shadcn/toggle-group';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, useInvalidateCase } from '@/lib/queries';
import type { BriefFeedback, SectionId } from '@/types/mdt';
import { formatDate } from './format';
import { JobProgress } from './JobProgress';

type FeedbackInput = { text: string; sections?: SectionId[] };

/**
 * Vytvoření (nebo přegenerování) podkladu přes job s průběhem (D-004). Smí předseda a zadávající
 * lékař (ARCH §6.3); po dokončení se obnoví podklad i semafor ve sdílené cache. Přegenerování může nést
 * zpětnou vazbu lékaře k předchozí verzi (T-323): jde do promptů vybraných částí.
 */
export function useBriefJob(caseId: number | string) {
  const [jobId, setJobId] = React.useState<number | null>(null);
  const [starting, setStarting] = React.useState(false);
  const invalidate = useInvalidateCase();

  const start = React.useCallback(
    async (feedback?: FeedbackInput) => {
      setStarting(true);
      try {
        const { job_id } = await mdtApi.generateBrief(String(caseId), feedback ? { feedback } : {});
        setJobId(job_id);
      } catch (err) {
        toast.error(apiErrorMessage(err, 'Podklad se nepodařilo spustit.'));
      } finally {
        setStarting(false);
      }
    },
    [caseId],
  );
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
    <Button variant={variant} onClick={() => void job.start()} isLoading={job.starting}>
      {label}
    </Button>
  );
}

/** Části podkladu, ke kterým lze dát připomínku (jedna část = jedno volání LLM). */
const PARTS: { id: SectionId; label: string }[] = [
  { id: 'summary', label: 'Souhrn' },
  { id: 'red_flags', label: 'Varovné signály' },
  { id: 'anamnesis', label: 'Anamnéza' },
  { id: 'role_views', label: 'Odbornosti' },
  { id: 'decision_support', label: 'Léčba a studie' },
];

/**
 * Přegenerování se zpětnou vazbou (T-323): lékař napíše, co AI udělala špatně a na co se má zaměřit,
 * volitelně jen pro některé části. Bez textu se podklad jen vytvoří znovu.
 */
export function RegenerateDialog({
  open,
  onClose,
  onSubmit,
}: {
  open: boolean;
  onClose: () => void;
  onSubmit: (feedback?: FeedbackInput) => void;
}) {
  const [text, setText] = React.useState('');
  const [sections, setSections] = React.useState<string[]>([]);
  const tooShort = text.trim().length > 0 && text.trim().length < 3;

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tooShort) return;
    onSubmit(text.trim() ? { text: text.trim(), sections: sections as SectionId[] } : undefined);
    setText('');
    setSections([]);
    onClose();
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Přegenerovat podklad</DialogTitle>
          <DialogDescription>
            Napište, co AI v podkladu udělala špatně a na co se má zaměřit. Připomínka půjde do zadání vybraných částí
            a zůstane u nového podkladu.
          </DialogDescription>
        </DialogHeader>
        <form id="regenerate-form" onSubmit={submit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium">Co bylo špatně / na co se zaměřit</span>
            <Textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={4}
              maxLength={1000}
              placeholder="Např. Souhrn neuvádí, že CT hrudníku chybí. Zaměř se na resekabilitu jater a FLR."
              aria-invalid={tooShort || undefined}
            />
            <span className="text-xs text-muted-foreground">
              Bez jmen a rodných čísel, text se posílá AI. Bez připomínky se podklad jen vytvoří znovu.
            </span>
          </label>
          <div className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium" id="regenerate-parts">Týká se částí <span className="font-normal text-muted-foreground">(nic = celý podklad)</span></span>
            <ToggleGroup
              value={sections}
              onValueChange={(v) => setSections(v as string[])}
              multiple
              variant="outline"
              size="sm"
              aria-labelledby="regenerate-parts"
              className="flex-wrap"
            >
              {PARTS.map((p) => (
                <ToggleGroupItem key={p.id} value={p.id}>{p.label}</ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>Zrušit</Button>
          <Button type="submit" form="regenerate-form" disabled={tooShort}>Přegenerovat</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Podklad vznikl podle připomínky lékaře: kdo, kdy, co (transparentnost, NFR-4). */
export function FeedbackNote({ feedback }: { feedback: BriefFeedback }) {
  return (
    <p className="flex items-start gap-2 rounded-lg bg-muted px-3 py-2 text-xs text-muted-foreground">
      <MessageSquareWarning className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      <span>
        Přegenerováno podle připomínky {feedback.by} ({formatDate(feedback.at.slice(0, 16))}): „{feedback.text}“
      </span>
    </p>
  );
}
