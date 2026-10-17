'use client';

import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { MessageSquareWarning } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';
import { mdtApi } from '@/lib/mdt-api';
import type { FeedbackSection } from '@/types/mdt';

const SECTION_LABEL: Record<FeedbackSection, string> = {
  anamnesis: 'Anamnéza',
  key_facts: 'Klíčové údaje',
  treatment: 'Léčebné postupy',
  warning: 'Varování',
  other: 'Jiné',
};

export function ProjectorFeedback({ caseId }: { caseId: number }) {
  const [open, setOpen] = React.useState(false);
  const [section, setSection] = React.useState<FeedbackSection>('anamnesis');
  const [message, setMessage] = React.useState('');
  const [correction, setCorrection] = React.useState('');
  const [guideAi, setGuideAi] = React.useState(true);
  const [shareAsHint, setShareAsHint] = React.useState(false);
  const [formError, setFormError] = React.useState('');
  const queryClient = useQueryClient();
  const queryKey = ['mdt', 'feedback', caseId];
  const feedbackQuery = useQuery({ queryKey, queryFn: () => mdtApi.getFeedback(caseId) });
  const saveFeedback = useMutation({
    mutationFn: () => mdtApi.sendFeedback(caseId, {
      section, message, correction, guide_ai: guideAi, share_as_hint: shareAsHint,
    }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey });
      setMessage('');
      setCorrection('');
      setGuideAi(true);
      setShareAsHint(false);
      setFormError('');
      setOpen(false);
    },
    onError: (error) => setFormError(error instanceof Error ? error.message : 'Zpětnou vazbu se nepodařilo uložit.'),
  });

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError('');
    saveFeedback.mutate();
  };

  return (
    <section aria-labelledby="projector-feedback-title" className="rounded-[20px] bg-card p-4">
      <div className="flex items-start gap-3">
        <MessageSquareWarning aria-hidden className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <h2 id="projector-feedback-title" className="text-sm font-semibold">Zpětná vazba k AI</h2>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
            Opravy se ukládají k případu. Sdílené opravy se nabídnou lékařům u podobné diagnózy jako neověřená nápověda.
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={() => setOpen(true)}>
          Nahlásit chybu
        </Button>
      </div>

      {feedbackQuery.isError && (
        <p role="alert" className="mt-3 text-xs text-destructive">Nápovědy a zpětnou vazbu se nepodařilo načíst.</p>
      )}
      {(feedbackQuery.data?.hints.length ?? 0) > 0 && (
        <div className="mt-3 flex flex-col gap-2 border-t border-border pt-3">
          <p className="text-xs font-medium">Zkušenosti týmu u podobné diagnózy</p>
          {feedbackQuery.data?.hints.map((hint, index) => (
            <div key={`${hint.section}-${index}`} className="rounded-lg bg-muted/60 px-3 py-2">
              <div className="mb-1 flex flex-wrap items-center gap-1.5">
                <Badge variant="secondary">{SECTION_LABEL[hint.section]}</Badge>
                <span className="text-[11px] text-muted-foreground">{hint.label}</span>
              </div>
              <p className="text-xs leading-relaxed">{hint.correction}</p>
            </div>
          ))}
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Nápověda není údaj o tomto pacientovi ani doporučení. Ověřte ji proti jeho dokumentaci a guidelines.
          </p>
        </div>
      )}
      {(feedbackQuery.data?.feedback.length ?? 0) > 0 && (
        <details className="mt-3 border-t border-border pt-3">
          <summary className="cursor-pointer text-xs font-medium">
            Uložená zpětná vazba k tomuto případu ({feedbackQuery.data?.feedback.length})
          </summary>
          <ul className="mt-2 flex flex-col gap-2">
            {feedbackQuery.data?.feedback.map((item) => (
              <li key={item.id} className="rounded-lg bg-muted/60 px-3 py-2 text-xs">
                <p className="font-medium">{SECTION_LABEL[item.section]}</p>
                <p className="mt-1">{item.message}</p>
                {item.correction && <p className="mt-1 text-muted-foreground">Oprava: {item.correction}</p>}
                {item.share_as_hint && <Badge className="mt-2" variant="secondary">Sdíleno jako nápověda</Badge>}
              </li>
            ))}
          </ul>
        </details>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <form onSubmit={submit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Nahlásit chybu v podkladu AI</DialogTitle>
            <DialogDescription>
            Zpráva se uloží k případu. Pokud zvolíte vodítko pro AI, při další generaci tohoto podkladu se předá jako neověřená instrukce; současný výstup se nezmění.
            </DialogDescription>
          </DialogHeader>
          <label className="flex flex-col gap-1.5 text-sm font-medium" htmlFor="feedback-section">
            Část podkladu
            <select
              id="feedback-section"
              value={section}
              onChange={(event) => setSection(event.target.value as FeedbackSection)}
              className="h-10 rounded-md border border-input bg-background px-3 text-sm font-normal focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {Object.entries(SECTION_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label className="flex items-start gap-2 text-xs leading-relaxed">
            <input
              type="checkbox"
              checked={guideAi}
              onChange={(event) => setGuideAi(event.target.checked)}
              className="mt-0.5 size-4 shrink-0 accent-primary"
            />
            <span>Použít tuto zprávu jako vodítko pro AI při dalších generacích podkladu tohoto případu. AI ji musí ověřit proti dokumentaci; zpráva není zdrojem faktů ani citací.</span>
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium" htmlFor="feedback-message">
            Co je chybně nebo neúplné?
            <Textarea
              id="feedback-message"
              required
              maxLength={1000}
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Popište chybu v návrhu AI."
              className="min-h-20 bg-background"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm font-medium" htmlFor="feedback-correction">
            Jak to má být? <span className="font-normal text-muted-foreground">(volitelné)</span>
            <Textarea
              id="feedback-correction"
              maxLength={2000}
              value={correction}
              onChange={(event) => setCorrection(event.target.value)}
              placeholder="Doplňte opravu nebo upřesnění."
              className="min-h-20 bg-background"
            />
          </label>
          <label className="flex items-start gap-2 text-xs leading-relaxed">
            <input
              type="checkbox"
              checked={shareAsHint}
              onChange={(event) => setShareAsHint(event.target.checked)}
              className="mt-0.5 size-4 shrink-0 accent-primary"
            />
            <span>
              Sdílet opravu jako nápovědu pro lékaře u podobné diagnózy. Nápověda nebude obsahovat ID případu ani autora,
              ale může ji ovlivnit zadaný text. Neuvádějte jména, rodná čísla ani jiné identifikující údaje.
            </span>
          </label>
          {formError && <p role="alert" className="text-sm text-destructive">{formError}</p>}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Zrušit</Button>
            <Button type="submit" disabled={saveFeedback.isPending || !message.trim()}>
              {saveFeedback.isPending ? 'Ukládám…' : 'Uložit zpětnou vazbu'}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </section>
  );
}
