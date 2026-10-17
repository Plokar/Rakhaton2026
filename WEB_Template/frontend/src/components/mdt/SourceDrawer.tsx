'use client';

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ExternalLink } from 'lucide-react';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/shadcn/sheet';
import { Skeleton } from '@/components/shadcn/skeleton';
import { cn } from '@/lib/utils';
import type { EvidenceId, EvidenceSource } from '@/types/mdt';
import { formatDate } from './format';

export type SourceLoader = (id: EvidenceId) => Promise<EvidenceSource>;

const KIND_LABEL: Record<EvidenceSource['kind'], string> = {
  resource: 'Záznam pacienta',
  paragraph: 'Odstavec zprávy',
  guideline: 'Doporučený postup',
  trial_criterion: 'Kritérium studie',
  external: 'Externí zdroj',
};

/**
 * Boční panel se zdrojem citace (FR-R3, ARCH §7.2): text se zvýrazněným odstavcem, hodnota
 * s referenčním rozsahem a zdrojovým dokumentem, znění pasáže nebo kritéria. Obsah stránky se neposouvá.
 */
export function SourceDrawer({
  evidenceId,
  loadSource,
  onClose,
}: {
  evidenceId: EvidenceId | null;
  loadSource: SourceLoader;
  onClose: () => void;
}) {
  // Poslední otevřené ID drží obsah i během animace zavírání.
  const [shownId, setShownId] = React.useState(evidenceId);
  if (evidenceId && evidenceId !== shownId) setShownId(evidenceId);

  const source = useQuery({
    queryKey: ['evidence', shownId],
    queryFn: () => loadSource(shownId as EvidenceId),
    enabled: Boolean(shownId),
    staleTime: Infinity,
    retry: false,
  });

  return (
    <Sheet open={Boolean(evidenceId)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 sm:max-w-lg">
        <SheetHeader className="border-b border-border px-5 py-4 pr-12">
          <SheetDescription className="flex flex-wrap items-center gap-x-2 text-xs">
            <span translate="no" className="font-medium text-foreground">{shownId}</span>
            {source.data && <span>{KIND_LABEL[source.data.kind]}</span>}
            {source.data?.date && <span className="tabular-nums">{formatDate(source.data.date)}</span>}
          </SheetDescription>
          <SheetTitle className="text-base font-semibold leading-snug">
            {source.data?.title ?? (source.isError ? 'Zdroj se nepodařilo najít' : 'Načítám zdroj…')}
          </SheetTitle>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {source.isLoading && (
            <div className="flex flex-col gap-2" aria-busy="true">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          )}
          {source.isError && (
            <p role="alert" className="text-sm text-destructive">
              {source.error instanceof Error ? source.error.message : 'Zdroj se nepodařilo načíst.'} Zkuste citaci otevřít znovu.
            </p>
          )}
          {source.data && <SourceBody source={source.data} />}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function SourceBody({ source }: { source: EvidenceSource }) {
  const markRef = React.useRef<HTMLElement>(null);
  React.useEffect(() => {
    markRef.current?.scrollIntoView({ block: 'center' });
  }, [source]);

  return (
    <div className="flex flex-col gap-4 text-sm">
      {(source.department || source.author || source.criterion_kind) && (
        <dl className="flex flex-col gap-0.5 text-[13px] text-muted-foreground">
          {source.department && <dd className="font-medium text-foreground">{source.department.trim()}</dd>}
          {source.author && <dd>{source.author.text}</dd>}
          {source.criterion_kind && (
            <dd>{source.criterion_kind === 'inclusion' ? 'Kritérium zařazení' : 'Kritérium vyřazení'}</dd>
          )}
        </dl>
      )}

      {source.value && (
        <div className="rounded-lg bg-muted/60 px-4 py-3">
          <p className="flex flex-wrap items-baseline gap-x-2.5 text-2xl font-semibold tabular-nums">
            {source.value.text}
            {source.value.interpretation && (
              <span
                className={cn(
                  'text-sm font-medium',
                  source.value.interpretation === 'H' || source.value.interpretation === 'L'
                    ? 'text-amber-800 dark:text-amber-300'
                    : 'text-muted-foreground',
                )}
              >
                {source.value.interpretation === 'H' ? 'nad normou' : source.value.interpretation === 'L' ? 'pod normou' : source.value.interpretation}
              </span>
            )}
          </p>
          {(source.value.ref_low !== null || source.value.ref_high !== null) && (
            <p className="mt-1 text-[13px] text-muted-foreground">
              Referenční rozsah{' '}
              <span className="font-medium tabular-nums text-foreground">
                {source.value.ref_low ?? '–'}–{source.value.ref_high ?? '–'} {source.value.unit ?? ''}
              </span>
            </p>
          )}
        </div>
      )}

      {source.text && <SourceText text={source.text} highlight={source.highlight} markRef={markRef} />}

      {(source.source || source.region) && (
        <p className="text-[13px] text-muted-foreground">
          Zdroj: <span className="font-medium text-foreground">{source.source}</span>
          {source.region && <>, {source.region}</>}
        </p>
      )}
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          <ExternalLink className="size-4" aria-hidden /> Otevřít původní zdroj
        </a>
      )}

      {source.derived_from && source.derived_from.length > 0 && (
        <section className="flex flex-col gap-3 border-t border-border pt-4" aria-labelledby="source-derived">
          <h3 id="source-derived" className="text-sm font-semibold">Zdrojový dokument</h3>
          {source.derived_from.map((doc) => (
            <div key={doc.evidence_id}>
              <p className="text-[13px] font-medium">
                {doc.title} <span translate="no" className="font-normal text-muted-foreground">{doc.evidence_id}</span>
              </p>
              {doc.date && <p className="text-xs tabular-nums text-muted-foreground">{formatDate(doc.date)}</p>}
              {doc.text && <p className="mt-1.5 whitespace-pre-wrap text-[13px] leading-relaxed">{doc.text}</p>}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}

function SourceText({
  text,
  highlight,
  markRef,
}: {
  text: string;
  highlight?: EvidenceSource['highlight'];
  markRef: React.RefObject<HTMLElement | null>;
}) {
  if (!highlight) return <p className="whitespace-pre-wrap leading-relaxed">{text}</p>;
  return (
    <p className="whitespace-pre-wrap leading-relaxed text-muted-foreground">
      {text.slice(0, highlight.start)}
      <mark ref={markRef} className="rounded-sm bg-amber-200/70 px-0.5 text-foreground dark:bg-amber-400/25">
        {text.slice(highlight.start, highlight.end)}
      </mark>
      {text.slice(highlight.end)}
    </p>
  );
}
