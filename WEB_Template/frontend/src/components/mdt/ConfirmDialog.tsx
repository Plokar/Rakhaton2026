'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogClose, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import type { Decision } from '@/types/mdt';

/**
 * Potvrzení závěru předsedou (FR-C3, ARCH §4.3): kdo potvrzuje a co se zapíše do IRIS jako oficiální
 * záznam. Až po potvrzení přestane být obsah od AI návrhem.
 */
export function ConfirmDialog({
  open,
  decision,
  patientId,
  confirmer,
  onClose,
  onConfirm,
}: {
  open: boolean;
  decision: Decision;
  patientId: string;
  confirmer: string;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const aiParts = [
    decision.sections.question, decision.sections.assessment, decision.sections.conclusion,
    ...decision.sections.recommendation, ...decision.tasks,
  ].filter((p) => p.source !== 'human').length;

  const resources = [
    `Composition/${patientId}-mdtNN – Záznam MDT (sekce jako v datasetu)`,
    `CarePlan – léčebný záměr a postup (${decision.sections.recommendation.length} kroků)`,
    `CareTeam – přítomní (${decision.attendees.length})`,
    `Task × ${decision.tasks.length} – úkoly po zasedání`,
    `DetectedIssue × ${decision.red_flags_acknowledged.length} – varovné signály`,
    ...(decision.sections.trial?.study_ids.length ? [`ResearchSubject × ${decision.sections.trial.study_ids.length} – vhodnost do studie`] : []),
    'Provenance – kdo potvrdil, z jakých zdrojů, jakým modelem',
    `ServiceRequest/${patientId}-zad01 a Task – nominace „projednaná“`,
  ];

  const confirm = async () => {
    setBusy(true);
    setError(null);
    try {
      await onConfirm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Potvrzení se nepodařilo.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && !busy && onClose()}>
      <DialogClose onClick={onClose} />
      <DialogHeader>
        <DialogTitle>Potvrdit závěr komise</DialogTitle>
        <DialogDescription>
          Potvrzuje: <strong>{confirmer}</strong>. Závěr se stane oficiálním záznamem a zapíše se do IRIS; potom ho nejde měnit.
        </DialogDescription>
      </DialogHeader>
      <div className="mt-3 space-y-2.5 text-sm">
        {aiParts > 0 && (
          <p className="rounded-lg border border-teal-700/30 bg-teal-50/80 px-3 py-2 text-xs font-medium text-teal-950 dark:border-teal-400/30 dark:bg-teal-950/60 dark:text-teal-200">
            Závěr obsahuje {aiParts} částí předvyplněných AI. Potvrzením je přebíráte jako oficiální rozhodnutí komise.
          </p>
        )}
        <p className="text-xs font-semibold text-foreground">Zapíše se do IRIS (jeden transaction Bundle):</p>
        <ul className="list-disc space-y-0.5 pl-5 font-mono text-[11px] text-muted-foreground">
          {resources.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose} disabled={busy}>
          Zpět k úpravám
        </Button>
        <Button type="button" onClick={confirm} isLoading={busy}>
          Potvrdit a zapsat
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
