'use client';

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, Columns2, Info, OctagonAlert, TriangleAlert, type LucideIcon } from 'lucide-react';
import { Skeleton } from '@/components/shadcn/skeleton';
import { ToggleGroup, ToggleGroupItem } from '@/components/shadcn/toggle-group';
import { cn } from '@/lib/utils';
import type { EvidenceId, EvidenceSource, RedFlag, Severity } from '@/types/mdt';
import { AiTag } from './AiBlock';
import { CitationChip, Citations } from './citations';
import { useBriefData } from './data-source';
import { formatDate } from './format';

export const SEVERITY_META: Record<Severity, { label: string; icon: LucideIcon; tone: string }> = {
  high: { label: 'vysoká', icon: OctagonAlert, tone: 'text-red-700 dark:text-red-400' },
  moderate: { label: 'střední', icon: TriangleAlert, tone: 'text-amber-700 dark:text-amber-400' },
  low: { label: 'nízká', icon: Info, tone: 'text-slate-600 dark:text-slate-400' },
};

const ORDER: Severity[] = ['high', 'moderate', 'low'];

/**
 * Varovné signály (FR-R2) jako kompaktní seznam (NAVRH_UI §8): řádek = závažnost, název a zdroje,
 * rozbalení ukáže popis, pasáž pravidla a oba zdroje rozporu vedle sebe. Filtr podle závažnosti
 * signály jen skrývá z pohledu, počet zůstává vidět (D-019).
 */
export function RedFlagList({ flags }: { flags: RedFlag[] }) {
  const [filter, setFilter] = React.useState<'all' | Severity>('all');
  const counts = Object.fromEntries(ORDER.map((s) => [s, flags.filter((f) => f.severity === s).length])) as Record<Severity, number>;
  const sorted = flags.toSorted((a, b) => ORDER.indexOf(a.severity) - ORDER.indexOf(b.severity));
  const shown = filter === 'all' ? sorted : sorted.filter((f) => f.severity === filter);

  if (!flags.length) return <p className="text-sm text-muted-foreground">Pravidla nenašla žádný varovný signál.</p>;
  return (
    <div className="flex flex-col gap-3">
      <ToggleGroup
        value={[filter]}
        onValueChange={(value) => setFilter((value[0] as typeof filter | undefined) ?? 'all')}
        variant="outline"
        size="sm"
        spacing={0}
        aria-label="Filtr podle závažnosti"
      >
        <ToggleGroupItem value="all">Vše {flags.length}</ToggleGroupItem>
        {ORDER.filter((s) => counts[s]).map((s) => (
          <ToggleGroupItem key={s} value={s}>
            {SEVERITY_META[s].label} {counts[s]}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <ul className="divide-y divide-border rounded-lg border border-border bg-card">
        {shown.map((flag) => <RedFlagRow key={flag.id} flag={flag} />)}
      </ul>
      <p className="text-xs text-muted-foreground">Deterministická pravidla a kontrola rozporů mezi zdroji. Signál označený AI je návrh k ověření.</p>
    </div>
  );
}

function RedFlagRow({ flag }: { flag: RedFlag }) {
  const [open, setOpen] = React.useState(false);
  const [compare, setCompare] = React.useState(false);
  const meta = SEVERITY_META[flag.severity];
  const Icon = meta.icon;
  const pair = flag.citations.slice(0, 2);
  const bodyId = React.useId();
  return (
    <li>
      <div className="grid grid-cols-[1.5rem_minmax(0,1fr)_auto] items-start gap-x-2 px-3 py-2.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={bodyId}
          aria-label={`${open ? 'Sbalit' : 'Rozbalit'}: ${flag.title}`}
          className="flex size-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <ChevronRight className={cn('size-4 transition-transform motion-reduce:transition-none', open && 'rotate-90')} aria-hidden />
        </button>
        <div className="min-w-0">
          <p className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm leading-6">
            <span className={cn('inline-flex shrink-0 items-center gap-1 self-center text-xs font-medium', meta.tone)}>
              <Icon className="size-4" strokeWidth={2.25} aria-hidden /> {meta.label}
            </span>
            <button type="button" onClick={() => setOpen(!open)} className="min-w-0 text-left font-medium hover:underline hover:underline-offset-4">
              {flag.title}
            </button>
            {flag.rule === 'RF-LLM' && <AiTag className="self-center" />}
            {flag.verification === 'unverified' && <span className="self-center text-xs font-medium text-amber-800 dark:text-amber-300">neověřeno</span>}
          </p>
          {open && (
            <div id={bodyId} className="mt-1 flex flex-col gap-2 pb-1">
              <p className="text-sm leading-relaxed">
                {flag.description}
                <Citations ids={flag.citations} />
              </p>
              {pair.length === 2 && (
                <button
                  type="button"
                  onClick={() => setCompare(!compare)}
                  aria-expanded={compare}
                  className="inline-flex w-fit items-center gap-1.5 rounded-md text-[13px] font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <Columns2 className="size-4" aria-hidden /> {compare ? 'Skrýt srovnání zdrojů' : 'Porovnat oba zdroje vedle sebe'}
                </button>
              )}
              {compare && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {pair.map((id) => <SourcePreview key={id} id={id} hint={flag.description} />)}
                </div>
              )}
            </div>
          )}
        </div>
        <p className="flex items-center gap-1.5 pt-0.5 text-xs text-muted-foreground">
          <span translate="no" className="hidden sm:inline">{flag.rule}</span>
          {flag.guideline && <CitationChip id={flag.guideline} />}
        </p>
      </div>
    </li>
  );
}

function SourcePreview({ id, hint }: { id: EvidenceId; hint: string }) {
  const { loadSource } = useBriefData();
  const source = useQuery({ queryKey: ['evidence', id], queryFn: () => loadSource(id), staleTime: Infinity, retry: false });
  return (
    <div className="rounded-lg bg-muted/60 p-3 text-[13px]">
      <p className="flex items-start gap-2 font-medium">
        <span className="min-w-0 flex-1">{source.data?.title ?? id}</span>
        <CitationChip id={id} />
      </p>
      {source.data?.date && <p className="text-xs tabular-nums text-muted-foreground">{formatDate(source.data.date)}</p>}
      {source.isLoading && <Skeleton className="mt-2 h-12" />}
      {source.isError && <p className="mt-1 text-destructive">Zdroj se nepodařilo načíst.</p>}
      {source.data && <p className="mt-1.5 whitespace-pre-wrap leading-relaxed">{excerpt(source.data, hint)}</p>}
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
