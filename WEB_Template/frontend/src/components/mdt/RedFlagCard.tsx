'use client';

import * as React from 'react';
import { ChevronDown, Columns2, Cpu, LoaderCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { EvidenceId, EvidenceSource, RedFlag } from '@/types/mdt';
import { CitationChip, Citations } from './citations';
import { useBriefData } from './data-source';
import { formatDate } from './format';

const SEVERITY = {
  high: {
    label: 'Vysoká závažnost',
    border: 'border-l-red-600 dark:border-l-red-500',
    badge: 'bg-red-100 text-red-900 border-red-300 dark:bg-red-950/80 dark:text-red-200 dark:border-red-700/70',
  },
  moderate: {
    label: 'Střední závažnost',
    border: 'border-l-amber-600 dark:border-l-amber-500',
    badge: 'bg-amber-100 text-amber-950 border-amber-300 dark:bg-amber-950/80 dark:text-amber-200 dark:border-amber-700/70',
  },
  low: {
    label: 'Nízká závažnost',
    border: 'border-l-slate-500',
    badge: 'bg-slate-100 text-slate-800 border-slate-300 dark:bg-slate-800 dark:text-slate-200 dark:border-slate-600',
  },
} as const;

/** Varovný signál (FR-R2): závažnost, popis, pasáž guidelines a oba zdroje rozporu vedle sebe. */
export function RedFlagCard({ flag }: { flag: RedFlag }) {
  const [compare, setCompare] = React.useState(false);
  const pair = flag.citations.slice(0, 2);
  const sev = SEVERITY[flag.severity];
  return (
    <li className={cn('rounded-lg border border-border border-l-4 bg-background p-3.5 shadow-2xs', sev.border)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-bold text-foreground">
          {flag.title}
          {flag.rule === 'RF-LLM' && (
            <span className="ml-2 inline-flex items-center gap-1 rounded-md border border-teal-700/30 bg-teal-50 px-1.5 py-0.5 align-middle font-mono text-[10px] font-semibold text-teal-900 dark:border-teal-400/30 dark:bg-teal-950/70 dark:text-teal-200">
              <Cpu className="h-3 w-3" aria-hidden /> AI návrh
            </span>
          )}
        </p>
        <div className="flex items-center gap-1.5">
          <span className={cn('rounded-md border px-2 py-0.5 text-[11px] font-semibold', sev.badge)}>
            {sev.label}
          </span>
          <span className="rounded-md bg-muted px-1.5 py-0.5 font-mono text-[11px] font-medium text-muted-foreground">
            {flag.rule}
          </span>
          {flag.verification === 'unverified' && (
            <span className="rounded-md border border-amber-500/40 bg-amber-500/15 px-1.5 py-0.5 text-[11px] font-semibold text-amber-800 dark:text-amber-200">
              neověřeno
            </span>
          )}
        </div>
      </div>
      <p className="mt-1.5 text-sm leading-relaxed text-foreground">
        {flag.description}
        <Citations ids={[...flag.citations, ...(flag.guideline ? [flag.guideline] : [])]} />
      </p>
      {pair.length === 2 && (
        <button
          type="button"
          onClick={() => setCompare(!compare)}
          aria-expanded={compare}
          className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-semibold text-foreground transition-colors hover:bg-accent"
        >
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', !compare && '-rotate-90')} aria-hidden />
          <Columns2 className="h-3.5 w-3.5 text-primary" aria-hidden /> Porovnat oba zdroje vedle sebe
        </button>
      )}
      {compare && (
        <div className="mt-2.5 grid gap-2.5 sm:grid-cols-2">
          {pair.map((id) => (
            <SourcePreview key={id} id={id} hint={flag.description} />
          ))}
        </div>
      )}
    </li>
  );
}

type Loaded = { id: EvidenceId; source?: EvidenceSource; error?: string };

function SourcePreview({ id, hint }: { id: EvidenceId; hint: string }) {
  const { loadSource } = useBriefData();
  const [loaded, setLoaded] = React.useState<Loaded | null>(null);
  React.useEffect(() => {
    let cancelled = false;
    loadSource(id)
      .then((source) => !cancelled && setLoaded({ id, source }))
      .catch((err: unknown) => !cancelled && setLoaded({ id, error: err instanceof Error ? err.message : 'Zdroj nelze načíst.' }));
    return () => {
      cancelled = true;
    };
  }, [id, loadSource]);

  const source = loaded?.id === id ? loaded.source : undefined;
  return (
    <div className="rounded-md border border-border bg-card p-2 text-xs">
      <p className="flex items-start gap-1 font-semibold text-foreground">
        <span className="min-w-0 flex-1">{source?.title ?? id}</span>
        <CitationChip id={id} />
      </p>
      {source?.date && <p className="text-[11px] text-muted-foreground">{formatDate(source.date)}</p>}
      {!loaded && (
        <p className="mt-1 flex items-center gap-1 text-muted-foreground">
          <LoaderCircle className="h-3 w-3 animate-spin" aria-hidden /> Načítám…
        </p>
      )}
      {loaded?.error && <p className="mt-1 text-destructive">{loaded.error}</p>}
      {source && <p className="mt-1 whitespace-pre-wrap text-foreground">{excerpt(source, hint)}</p>}
    </div>
  );
}

/**
 * Krátká ukázka zdroje: hodnota, zvýrazněný odstavec, nebo řádky textu se slovy z popisu signálu
 * (u dotazníku PROMs tak ukáže odpověď, o kterou jde), jinak začátek textu.
 */
function excerpt(source: EvidenceSource, hint: string): string {
  if (source.value) return source.value.text;
  if (source.text && source.highlight) return source.text.slice(source.highlight.start, source.highlight.end);
  if (!source.text) return '';
  const lines = source.text.split('\n').filter(Boolean);
  const wordsOf = (text: string) => text.toLocaleLowerCase('cs').match(/[a-zà-ž]{5,}/g) ?? [];
  const hintWords = new Set(wordsOf(hint));
  const matching = lines.filter((line) => wordsOf(line).some((w) => hintWords.has(w)));
  const chosen = matching.length ? matching.slice(0, 4) : lines.slice(0, 6);
  return chosen.length < lines.length ? `${chosen.join('\n')}\n…` : chosen.join('\n');
}
