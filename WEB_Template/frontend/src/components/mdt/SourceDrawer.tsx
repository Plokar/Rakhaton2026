'use client';

import * as React from 'react';
import { BookOpen, ExternalLink, FileText, FlaskConical, LoaderCircle, X } from 'lucide-react';
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

type Loaded = { id: EvidenceId; source?: EvidenceSource; error?: string };

/**
 * Boční panel se zdrojem citace (FR-R3, ARCH §7.2): text se zvýrazněným odstavcem,
 * hodnota s referenčním rozsahem a zdrojovým dokumentem, znění pasáže nebo kritéria.
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
  const [loaded, setLoaded] = React.useState<Loaded | null>(null);

  React.useEffect(() => {
    if (!evidenceId) return;
    let cancelled = false;
    loadSource(evidenceId)
      .then((source) => !cancelled && setLoaded({ id: evidenceId, source }))
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : 'Zdroj se nepodařilo načíst.';
        if (!cancelled) setLoaded({ id: evidenceId, error: message });
      });
    return () => {
      cancelled = true;
    };
  }, [evidenceId, loadSource]);

  React.useEffect(() => {
    if (!evidenceId) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [evidenceId, onClose]);

  if (!evidenceId) return null;
  const current = loaded?.id === evidenceId ? loaded : null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label={`Zdroj ${evidenceId}`}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-[2px]" onClick={onClose} aria-hidden />
      <aside className="relative flex h-full w-full flex-col border-l border-border bg-card shadow-2xl sm:max-w-lg">
        <div className="flex items-start gap-3 border-b border-border bg-muted/40 px-5 py-4">
          <div className="min-w-0 flex-1">
            <span className="inline-block rounded border border-primary/30 bg-primary/10 px-2 py-0.5 font-mono text-xs font-bold text-primary">
              {evidenceId}
            </span>
            <p className="mt-1.5 text-base font-bold leading-snug text-foreground">
              {current?.source?.title ?? (current?.error ? 'Zdroj nenalezen' : 'Načítám zdroj…')}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border bg-background p-1.5 text-muted-foreground transition hover:bg-accent hover:text-foreground"
            aria-label="Zavřít zdroj"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {!current && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <LoaderCircle className="h-4 w-4 animate-spin text-primary" aria-hidden /> Načítám…
            </p>
          )}
          {current?.error && <p className="text-sm text-destructive">{current.error}</p>}
          {current?.source && <SourceBody source={current.source} />}
        </div>
      </aside>
    </div>
  );
}

function SourceBody({ source }: { source: EvidenceSource }) {
  const markRef = React.useRef<HTMLElement>(null);
  React.useEffect(() => {
    markRef.current?.scrollIntoView({ block: 'center' });
  }, [source]);

  const Icon = source.kind === 'guideline' ? BookOpen : source.kind === 'trial_criterion' ? FlaskConical : source.kind === 'external' ? ExternalLink : FileText;
  return (
    <div className="space-y-4 text-sm">
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span
          className={cn(
            'inline-flex items-center gap-1.5 rounded-md border px-2.5 py-0.5 font-bold',
            source.kind === 'external'
              ? 'border-dashed border-foreground/40 text-foreground'
              : 'border-border bg-muted text-foreground',
          )}
        >
          <Icon className="h-3.5 w-3.5 text-primary" aria-hidden /> {KIND_LABEL[source.kind]}
        </span>
        {source.date && <span className="font-mono font-medium text-muted-foreground">{formatDate(source.date)}</span>}
        {source.criterion_kind && (
          <span className="rounded bg-muted px-2 py-0.5 font-medium text-muted-foreground">
            {source.criterion_kind === 'inclusion' ? 'kritérium zařazení' : 'kritérium vyřazení'}
          </span>
        )}
      </div>

      {(source.department || source.author) && (
        <dl className="rounded-lg border border-border bg-muted/30 px-3 py-2 space-y-0.5 text-xs text-muted-foreground">
          {source.department && <dd className="font-semibold text-foreground">{source.department.trim()}</dd>}
          {source.author && <dd>{source.author.text}</dd>}
        </dl>
      )}

      {source.value && (
        <div className="rounded-xl border border-border bg-background p-4 shadow-2xs">
          <p className="font-mono text-2xl font-extrabold text-foreground tabular-nums">
            {source.value.text}
            {source.value.interpretation && (
              <span
                className={cn(
                  'ml-2.5 rounded-md border px-2 py-0.5 align-middle font-sans text-xs font-bold',
                  source.value.interpretation === 'H' || source.value.interpretation === 'L'
                    ? 'border-amber-500/40 bg-amber-500/15 text-amber-900 dark:text-amber-200'
                    : 'border-border bg-muted text-muted-foreground',
                )}
              >
                {source.value.interpretation === 'H' ? 'nad normou' : source.value.interpretation === 'L' ? 'pod normou' : source.value.interpretation}
              </span>
            )}
          </p>
          {(source.value.ref_low !== null || source.value.ref_high !== null) && (
            <p className="mt-1 text-xs font-medium text-muted-foreground">
              Referenční rozsah: <span className="font-mono font-semibold text-foreground">{source.value.ref_low ?? '–'} – {source.value.ref_high ?? '–'} {source.value.unit ?? ''}</span>
            </p>
          )}
        </div>
      )}

      {source.text && <SourceText text={source.text} highlight={source.highlight} markRef={markRef} />}

      {(source.source || source.region) && (
        <p className="text-xs font-medium text-muted-foreground">
          Zdroj: <strong className="text-foreground">{source.source}</strong>
          {source.region && <> · {source.region}</>}
        </p>
      )}
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary/20"
        >
          <ExternalLink className="h-3.5 w-3.5" aria-hidden /> Otevřít původní zdroj
        </a>
      )}

      {source.derived_from && source.derived_from.length > 0 && (
        <div className="space-y-2 border-t border-border pt-3">
          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Zdrojový dokument</p>
          {source.derived_from.map((doc) => (
            <div key={doc.evidence_id} className="rounded-lg border border-border bg-background p-3">
              <p className="text-xs font-bold text-foreground">
                {doc.title} <span className="ml-1 font-mono font-normal text-muted-foreground">{doc.evidence_id}</span>
              </p>
              {doc.date && <p className="text-[11px] text-muted-foreground">{formatDate(doc.date)}</p>}
              {doc.text && <p className="mt-1.5 whitespace-pre-wrap text-xs leading-relaxed text-foreground">{doc.text}</p>}
            </div>
          ))}
        </div>
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
  if (!highlight) {
    return (
      <div className="rounded-lg border border-border bg-background p-3.5">
        <p className="whitespace-pre-wrap leading-relaxed text-foreground">{text}</p>
      </div>
    );
  }
  return (
    <div className="rounded-lg border border-border bg-background p-3.5">
      <p className="whitespace-pre-wrap leading-relaxed text-muted-foreground">
        {text.slice(0, highlight.start)}
        <mark
          ref={markRef}
          className="rounded border border-amber-500/40 bg-amber-300/40 px-1 py-0.5 font-medium text-foreground dark:bg-amber-500/30"
        >
          {text.slice(highlight.start, highlight.end)}
        </mark>
        {text.slice(highlight.end)}
      </p>
    </div>
  );
}
