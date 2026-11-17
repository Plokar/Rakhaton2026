'use client';

import * as React from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ThumbsDown, ThumbsUp, Vote } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Textarea } from '@/components/shadcn/textarea';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { Decision, RoleId } from '@/types/mdt';
import { ROLE_META } from './roles';

/**
 * Souhlas přítomných s návrhem závěru (T-381). Hlasuje každý člen komise z mobilu nebo webu; rozhoduje předseda,
 * hlas se jen zapíše do záznamu MDT. Stav se obnovuje po 10 s, dokud je návrh otevřený.
 */
export const votesKey = (caseId: number) => ['case', String(caseId), 'votes'] as const;

export function useVotes(caseId: number | null) {
  return useQuery({
    queryKey: votesKey(caseId ?? 0),
    queryFn: () => mdtApi.getVotes(caseId!),
    enabled: caseId != null,
    refetchInterval: (query) => (query.state.data?.open ? 10_000 : false),
  });
}

function useVote(caseId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (input: { vote: 'agree' | 'disagree'; comment?: string } | null) =>
      input ? mdtApi.putVote(caseId, input) : mdtApi.deleteVote(caseId),
    onSuccess: (state) => client.setQueryData(votesKey(caseId), state),
    onError: (err) => toast.error(apiErrorMessage(err, 'Hlas se nepodařilo uložit.')),
  });
}

/** Karta pro člena komise (mobil, „Živě na MDT“): návrh závěru krátce a souhlasím / nesouhlasím s důvodem. */
export function VoteCard({ caseId, patientId, className }: { caseId: number; patientId: string; className?: string }) {
  const votes = useVotes(caseId);
  const draft = useQuery({ queryKey: ['case', String(caseId), 'decision'], queryFn: () => mdtApi.getDecision(String(caseId)) });
  const vote = useVote(caseId);
  const [disagreeing, setDisagreeing] = React.useState(false);
  const [comment, setComment] = React.useState('');
  const state = votes.data;
  if (!state || !draft.data || state.decision === null) return null;
  const chosen = draft.data.sections.options_considered?.find((o) => o.chosen)?.title;
  const conclusion = draft.data.sections.conclusion?.text;
  const mine = state.mine;
  return (
    <section aria-labelledby={`vote-${caseId}`} className={cn('rounded-lg border border-border bg-card p-4', className)}>
      <h2 id={`vote-${caseId}`} className="flex items-center gap-2 text-sm font-semibold">
        <Vote className="size-4 text-primary" aria-hidden />
        {state.decision === 'confirmed' ? 'Závěr je potvrzený' : 'Návrh závěru'}{' '}
        <span translate="no" className="font-normal text-muted-foreground">{patientId}</span>
      </h2>
      {(chosen || conclusion) && (
        <div className="mt-2 space-y-1 text-sm">
          {chosen && <p><span className="text-muted-foreground">Zvolený postup:</span> {chosen}</p>}
          {conclusion && <p className="line-clamp-4">{conclusion}</p>}
        </div>
      )}
      <p className="mt-2 text-[13px] text-muted-foreground" aria-live="polite">
        Souhlasí {state.agree}, nesouhlasí {state.disagree}
        {mine && <> · váš hlas: <span className="font-medium text-foreground">{mine.vote === 'agree' ? 'souhlasím' : 'nesouhlasím'}</span></>}
      </p>
      {state.open && !disagreeing && (
        <div className="mt-3 flex flex-wrap gap-2">
          <Button size="sm" variant={mine?.vote === 'agree' ? 'default' : 'outline'} disabled={vote.isPending}
            onClick={() => vote.mutate({ vote: 'agree' })}>
            <ThumbsUp aria-hidden /> Souhlasím
          </Button>
          <Button size="sm" variant={mine?.vote === 'disagree' ? 'default' : 'outline'} disabled={vote.isPending}
            onClick={() => {
              setComment(mine?.vote === 'disagree' ? mine.comment : '');
              setDisagreeing(true);
            }}>
            <ThumbsDown aria-hidden /> Nesouhlasím
          </Button>
          {mine && (
            <Button size="sm" variant="ghost" disabled={vote.isPending} onClick={() => vote.mutate(null)}>
              Stáhnout hlas
            </Button>
          )}
        </div>
      )}
      {state.open && disagreeing && (
        <form
          className="mt-3 space-y-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (!comment.trim()) return;
            vote.mutate({ vote: 'disagree', comment: comment.trim() }, { onSuccess: () => setDisagreeing(false) });
          }}
        >
          <label htmlFor={`vote-reason-${caseId}`} className="text-[13px] font-medium">Proč nesouhlasíte (zapíše se do záznamu MDT)</label>
          <Textarea id={`vote-reason-${caseId}`} value={comment} onChange={(e) => setComment(e.target.value)} rows={2} maxLength={1000}
            placeholder="Např. chybí restaging, preferuji konverzní chemoterapii…" />
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={!comment.trim() || vote.isPending}>Uložit nesouhlas</Button>
            <Button type="button" size="sm" variant="ghost" onClick={() => setDisagreeing(false)}>Zrušit</Button>
          </div>
        </form>
      )}
    </section>
  );
}

/**
 * Přehled pro předsedu v editoru závěru: kdo souhlasí a kdo ne. Nesouhlas jde jedním klikem převzít do
 * „Odlišných stanovisek“ (dissent); do záznamu se souhlas přítomných zapíše sám při potvrzení.
 */
export function VotesSummary({ caseId, decision, onChange, readOnly }: {
  caseId: number;
  decision: Decision;
  onChange: (d: Decision) => void;
  readOnly: boolean;
}) {
  const { data } = useVotes(caseId);
  const recorded = decision.sections.votes ?? [];
  if (!data && !recorded.length) return null;
  const items = data?.votes.length
    ? data.votes.map((v) => ({ name: v.name, role: v.specialty, vote: v.vote, comment: v.comment }))
    : recorded.map((v) => ({ name: v.member, role: v.role as RoleId | null, vote: v.vote, comment: v.comment }));
  if (!items.length) {
    return data?.open ? <p className="text-[13px] text-muted-foreground">Souhlas přítomných: zatím nikdo nehlasoval (hlasuje se z „Živě na MDT“).</p> : null;
  }
  const dissent = decision.sections.dissent ?? [];
  const missingDissent = items.filter((v) => v.vote === 'disagree' && !dissent.some((d) => d.member === v.name && d.text === v.comment));
  return (
    <div className="space-y-1.5 rounded-lg bg-muted/40 p-3 text-sm">
      <p className="font-medium">
        Souhlas přítomných: souhlasí {items.filter((v) => v.vote === 'agree').length}, nesouhlasí {items.filter((v) => v.vote === 'disagree').length}
      </p>
      <ul className="space-y-0.5 text-[13px]">
        {items.map((v) => (
          <li key={`${v.name}-${v.vote}`}>
            {v.vote === 'agree' ? '✓' : '✗'} {v.name}
            {v.role && ROLE_META[v.role as RoleId] ? <span className="text-muted-foreground"> ({ROLE_META[v.role as RoleId].label})</span> : null}
            {v.comment ? <span className="text-muted-foreground">: {v.comment}</span> : null}
          </li>
        ))}
      </ul>
      {!readOnly && missingDissent.length > 0 && (
        <Button
          size="sm"
          variant="outline"
          onClick={() =>
            onChange({
              ...decision,
              sections: {
                ...decision.sections,
                dissent: [
                  ...dissent,
                  ...missingDissent.map((v) => ({ member: v.name, role: (v.role ?? 'oncologist') as RoleId, text: v.comment })),
                ],
              },
            })
          }
        >
          Převzít nesouhlas do odlišných stanovisek ({missingDissent.length})
        </Button>
      )}
      <p className="text-xs text-muted-foreground">Při potvrzení se souhlas přítomných zapíše do záznamu MDT. Závěr potvrzuje předseda.</p>
    </div>
  );
}
