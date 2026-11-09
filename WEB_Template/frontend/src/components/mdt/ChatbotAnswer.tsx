'use client';

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { CalendarDays, Check, CircleHelp, FileText, Plus, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/shadcn/button';
import { Skeleton } from '@/components/shadcn/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { cn } from '@/lib/utils';
import type { ChatbotMessage, Claim, EvidenceId, EvidenceSource } from '@/types/mdt';
import { AiTag } from './AiBlock';
import { Citations, useCitationOpen } from './citations';
import { Confidence } from './ClaimList';
import { timeLabel } from './dates';
import { formatDate } from './format';
import { MissingData } from './MissingData';

/**
 * Zprávy chatbotu (T-344 u zasedání, T-345 nad kartou pacienta): dotaz lékaře a odpověď AI. Každé tvrzení je
 * v kartě s citací a pod ním je přímo zdroj (datum, oddělení, Evidence ID) a doslovný úryvek textu, kde ho AI
 * našla. Úryvek vybírá kód ze zdroje v IRIS, ne AI.
 */

export type ChatAnswerData = Pick<ChatbotMessage, 'text' | 'claims' | 'uncertain' | 'model' | 'created_at'>;

const QUOTE_LENGTH = 280;
const MAX_SOURCES = 3;              // zdrojů pod jedním tvrzením; zbytek je v citacích tvrzení

export function ChatQuestion({ text, createdAt, tag }: { text: string; createdAt?: string; tag?: React.ReactNode }) {
  return (
    <li className="flex flex-col items-end gap-1 pl-8">
      <p className="flex flex-wrap items-baseline gap-x-1.5 text-xs text-muted-foreground">
        <span className="font-medium text-foreground">Vy</span>
        {createdAt && <time dateTime={createdAt} className="tabular-nums">{timeLabel(createdAt)}</time>}
        {tag}
      </p>
      <p className="max-w-full rounded-lg bg-primary/10 px-3 py-2 text-sm whitespace-pre-wrap wrap-break-word text-foreground">{text}</p>
    </li>
  );
}

/** Odpověď AI: fialový pruh vlevo (D-017) a štítek „AI návrh“, pod každým tvrzením jeho zdroj s úryvkem. */
export function ChatAnswer({
  message,
  patientId,
  onAdd,
  isAdded,
}: {
  message: ChatAnswerData;
  patientId?: string | null;
  /** Doplnit tvrzení do okna pro projektor (T-345); bez něj tlačítko není. `ai` = text napsala AI. */
  onAdd?: (claim: Claim, ai: boolean) => void;
  isAdded?: (claim: Claim) => boolean;
}) {
  const empty = !message.text && message.claims.length === 0 && message.uncertain.length === 0;
  // Odpověď bez jazykového modelu jsou doslovná místa z dokumentace: úryvek pod nimi by jen opakoval text.
  const verbatim = message.model === null && Boolean(message.text);
  return (
    <li className="flex flex-col items-start gap-1 pr-4">
      <p className="flex flex-wrap items-center gap-x-1.5 text-xs text-muted-foreground">
        <AiTag />
        {patientId && <span translate="no" className="font-medium text-foreground">{patientId}</span>}
        <time dateTime={message.created_at} className="tabular-nums">{timeLabel(message.created_at)}</time>
      </p>
      <div className="w-full space-y-2 border-l-2 border-ai/50 pl-3">
        {message.text && <p className="text-sm text-muted-foreground">{message.text}</p>}
        {empty && <p className="text-sm text-muted-foreground">AI neodpověděla.</p>}
        {message.claims.length > 0 && (
          <ul className="flex flex-col gap-3">
            {message.claims.map((claim) => (
              <li key={claim.id}>
                <AnswerClaim
                  claim={claim}
                  verbatim={verbatim}
                  onAdd={onAdd && ((c) => onAdd(c, !verbatim))}
                  added={isAdded?.(claim) ?? false}
                />
              </li>
            ))}
          </ul>
        )}
        {message.uncertain.map((u, i) => (
          <p key={i} className="rounded-md bg-amber-50 px-2.5 py-1.5 text-sm leading-relaxed dark:bg-amber-400/10">
            <span className="mr-1.5 inline-flex items-center gap-1 align-baseline text-xs font-medium text-amber-800 dark:text-amber-300">
              <CircleHelp className="size-3.5 self-center" aria-hidden /> Nejistota AI
            </span>
            {u.text}
            <Citations ids={u.citations} />
          </p>
        ))}
      </div>
    </li>
  );
}

/** Zdroj citace z IRIS; stejný klíč jako SourceDrawer, po prokliku je panel hned plný. */
function useEvidence(id: EvidenceId | undefined) {
  return useQuery({
    queryKey: ['evidence', id],
    queryFn: () => mdtApi.getEvidence(id as EvidenceId),
    enabled: Boolean(id),
    staleTime: Infinity,
    retry: false,
  });
}

/**
 * Tvrzení: nahoře údaj a hodnota („FEV1 = 1,9 l“), pod ním ke každé citaci datum, doslovný text ze zdroje a proklik
 * na zdroj. Bez jazykového modelu je tvrzení doslovný řádek dokumentace: u laboratoře se údaj a hodnota vezmou ze
 * strukturovaného záznamu (kód, ne AI) a řádek jde do úryvku. Neověřené tvrzení je označené a do okna pro projektor nejde.
 */
function AnswerClaim({
  claim,
  verbatim,
  onAdd,
  added,
}: {
  claim: Claim;
  verbatim: boolean;
  onAdd?: (claim: Claim) => void;
  added: boolean;
}) {
  const first = useEvidence(verbatim && claim.kind === 'claim' ? claim.citations[0] : undefined);
  if (claim.kind === 'missing') {
    return <MissingData text={claim.text} expectedSource={claim.expected_source} citations={claim.citations} />;
  }
  const unverified = claim.verification === 'unverified';
  const canAdd = Boolean(onAdd) && !unverified && claim.citations.length > 0;
  const hasConfidence = claim.confidence !== undefined && claim.confidence !== null;
  const measured = first.data?.value ? `${first.data.title} = ${first.data.value.text}` : null;
  const line = claim.text.replace(/^\d{4}-\d{2}-\d{2}:\s*/, '');      // datum je v řádku zdroje
  return (
    <div className="flex flex-col gap-1.5">
      <div
        className={cn(
          'rounded-xl border px-3 py-2',
          unverified ? 'border-amber-300 bg-amber-50 dark:border-amber-400/40 dark:bg-amber-400/10' : 'border-primary/35 bg-card',
        )}
      >
        <p className="text-[15px] font-medium leading-snug">
          {unverified && (
            <span
              className="mr-1.5 inline-flex items-center gap-1 align-baseline text-xs font-medium text-amber-800 dark:text-amber-300"
              title="Grounding validátor tvrzení neověřil proti citovanému zdroji"
            >
              <TriangleAlert className="size-3.5 self-center" aria-hidden /> Neověřeno
            </span>
          )}
          {verbatim ? measured ?? line : claim.text}
          <Citations ids={claim.citations} />
        </p>
        {(hasConfidence || canAdd) && (
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            {hasConfidence && <Confidence value={claim.confidence} />}
            {canAdd &&
              (added ? (
                <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-muted-foreground">
                  <Check className="size-3.5" aria-hidden /> V okně pro projektor
                </span>
              ) : (
                <Button type="button" variant="outline" size="xs" className="ml-auto" onClick={() => onAdd?.(claim)}>
                  <Plus aria-hidden /> Do okna pro projektor
                </Button>
              ))}
          </div>
        )}
      </div>
      {claim.citations.slice(0, MAX_SOURCES).map((id, i) => (
        <ClaimSource
          key={id}
          id={id}
          claim={claim.text}
          // bez LLM je úryvkem sám řádek dokumentace (jen když nahoře není, tj. u laboratoře)
          quote={verbatim ? (i === 0 && measured ? line : null) : undefined}
        />
      ))}
    </div>
  );
}

/**
 * Zdroj tvrzení v pořadí čtení: kdy a kde (datum, oddělení nebo odbornost autora), doslovný text, kde to AI našla,
 * a nakonec proklik na zdroj (boční panel s celým dokumentem a zvýrazněným odstavcem).
 * `quote`: `undefined` = úryvek vybere kód ze zdroje, `null` = bez úryvku, text = tento úryvek.
 */
function ClaimSource({ id, claim, quote }: { id: EvidenceId; claim: string; quote?: string | null }) {
  const open = useCitationOpen();
  const source = useEvidence(id);
  if (source.isLoading) return <Skeleton className="h-16 w-full rounded-lg" />;
  const s = source.data;
  const snippet = quote !== undefined ? quote : s ? sourceQuote(s, claim) : null;
  const where = s ? s.author?.specialty ?? departmentName(s.department) : null;
  const measured = s ? s.resource_type === 'Observation' || Boolean(s.value) : false;
  return (
    <div className="flex flex-col gap-1.5 rounded-lg bg-muted/60 px-3 py-2 text-[13px] leading-snug text-muted-foreground">
      {s && (s.date || where) && (
        <p className="flex items-center gap-1.5">
          <CalendarDays className="size-4 shrink-0" aria-hidden />
          <span>
            {s.date && (
              <>
                {measured ? 'Naměřeno' : 'Ze dne'}{' '}
                <span className="font-medium tabular-nums text-foreground">{formatDate(s.date)}</span>
              </>
            )}
            {s.date && where && ' · '}
            {where}
          </span>
        </p>
      )}
      {snippet && (
        <blockquote className="border-l-2 border-border pl-2.5 leading-relaxed text-foreground/90">
          <Highlighted text={snippet} terms={claimTerms(claim)} />
        </blockquote>
      )}
      <p className="flex items-start gap-1.5">
        <FileText className="mt-px size-4 shrink-0" aria-hidden />
        <span className="min-w-0">
          <button
            type="button"
            onClick={() => open?.(id)}
            className="rounded-sm text-left font-medium text-primary underline underline-offset-4 hover:decoration-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            Otevřít zdroj <span translate="no">{id}</span>
            {s?.title && <> · {s.title}</>}
          </button>
          {source.isError && <> (zdroj se nepodařilo načíst)</>}
        </span>
      </p>
    </div>
  );
}

// ── Úryvek ze zdroje ─────────────────────────────────────────────────────────

/** „RDG – Radiodiagnostické oddělení“ → „Radiodiagnostické oddělení“. */
function departmentName(department: string | null | undefined): string | null {
  const text = department?.trim();
  if (!text) return null;
  return text.split(/\s[–-]\s/).pop()?.trim() || text;
}

const fold = (text: string) => text.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase('cs');
const prefix = (word: string) => word.slice(0, 5);
const STOP = new Set(['jsou', 'byl', 'byla', 'bylo', 'byly', 'pacient', 'pacienta', 'pacientka', 'pacientky', 'hodnota', 'hodnoty',
  'podle', 'ktery', 'ktera', 'ktere', 'dne', 'pro', 'jako', 'maji', 'pri', 'nebo', 'take', 'tato', 'tento', 'tyto', 'pouze', 'jeho', 'jeji'].map(prefix));

/** Slova tvrzení (od 3 znaků, prvních 5 písmen kvůli českým koncovkám) a čísla v přesném tvaru. */
function claimTerms(claim: string): Set<string> {
  const terms = new Set<string>();
  for (const raw of fold(claim).match(/[\p{L}\p{N}]+(?:[,.]\d+)?/gu) ?? []) {
    if (/^\d/.test(raw)) {
      if (raw.length >= 2) terms.add(raw.replace('.', ','));     // jednociferná čísla (den v datu) by svítila všude
    }
    else if (raw.length >= 3 && !STOP.has(prefix(raw))) terms.add(prefix(raw));
  }
  return terms;
}

function matches(word: string, terms: Set<string>): boolean {
  const w = fold(word).replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
  if (!w) return false;
  if (/^\d/.test(w)) return terms.has(w.replace('.', ','));
  return w.length >= 3 && terms.has(prefix(w));
}

/**
 * Úryvek, kde AI tvrzení našla: odstavec z citace `#n`, jinak věty zprávy s nejvíc slovy tvrzení (do 280 znaků),
 * u laboratoře název a hodnota s rozmezím. Doslovně ze zdroje, nic se nepřepisuje.
 */
function sourceQuote(source: EvidenceSource, claim: string): string | null {
  const text = source.text && source.highlight ? source.text.slice(source.highlight.start, source.highlight.end) : source.text;
  if (!text?.trim()) {
    if (!source.value) return null;
    const { ref_low: low, ref_high: high, unit } = source.value;
    const range = low !== null || high !== null ? ` (rozmezí ${low ?? '–'}–${high ?? '–'}${unit ? ` ${unit}` : ''})` : '';
    return `${source.title}: ${source.value.text}${range}`;
  }
  const clean = text.replace(/[ \t]+/g, ' ').trim();
  if (clean.length <= QUOTE_LENGTH) return clean;
  const terms = claimTerms(claim);
  const sentences = clean.split(/(?<=[.!?;])\s+|\n+/).map((x) => x.trim()).filter(Boolean);
  const score = (sentence: string) => sentence.split(/\s+/).filter((word) => matches(word, terms)).length;
  const scores = sentences.map(score);
  const best = scores.indexOf(Math.max(...scores));
  if (best < 0 || scores[best] === 0) return `${clean.slice(0, QUOTE_LENGTH).replace(/\s+\S*$/, '')} …`;
  let [from, to] = [best, best + 1];
  const length = () => sentences.slice(from, to).join(' ').length;
  while (to < sentences.length && length() + sentences[to].length < QUOTE_LENGTH) to += 1;
  while (from > 0 && length() + sentences[from - 1].length < QUOTE_LENGTH) from -= 1;
  let quote = sentences.slice(from, to).join(' ');
  if (quote.length > QUOTE_LENGTH) quote = `${quote.slice(0, QUOTE_LENGTH).replace(/\s+\S*$/, '')} …`;
  return `${from > 0 ? '… ' : ''}${quote}${to < sentences.length && !quote.endsWith('…') ? ' …' : ''}`;
}

/** Slova tvrzení v úryvku zvýrazněná stejně jako odstavec v bočním panelu se zdrojem. */
function Highlighted({ text, terms }: { text: string; terms: Set<string> }) {
  return (
    <>
      {text.split(/(\s+)/).map((part, i) => {
        if (!matches(part, terms)) return <React.Fragment key={i}>{part}</React.Fragment>;
        // zvýrazní jen slovo nebo číslo, ne závorky a interpunkci kolem („(1,9“ → „(“ + 1,9)
        const [, lead, core, trail] = part.match(/^([^\p{L}\p{N}]*)(.*?)([^\p{L}\p{N}]*)$/u) ?? [part, '', part, ''];
        return (
          <React.Fragment key={i}>
            {lead}
            <mark className="rounded-sm bg-amber-200/70 px-0.5 text-foreground dark:bg-amber-400/25">{core}</mark>
            {trail}
          </React.Fragment>
        );
      })}
    </>
  );
}
