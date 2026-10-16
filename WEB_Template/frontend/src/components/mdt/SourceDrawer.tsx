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
      <div className="absolute inset-0 bg-black/40 backdrop-blur-[1px]" onClick={onClose} aria-hidden />
      <aside className="relative flex h-full w-full flex-col border-l border-border bg-card shadow-2xl sm:max-w-md">
        <div className="flex items-start gap-2 border-b border-border px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="font-mono text-xs text-muted-foreground">{evidenceId}</p>
            <p className="text-sm font-semibold text-foreground">
              {current?.source?.title ?? (current?.error ? 'Zdroj nenalezen' : 'Načítám zdroj…')}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
            aria-label="Zavřít zdroj"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-3">
          {!current && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden /> Načítám…
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
    <div className="space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-1.5 text-xs">
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-semibold',
            source.kind === 'external'
              ? 'border-dashed border-foreground/40 text-foreground'
              : 'border-border bg-muted text-muted-foreground',
          )}
        >
          <Icon className="h-3 w-3" aria-hidden /> {KIND_LABEL[source.kind]}
        </span>
        {source.date && <span className="text-muted-foreground">{formatDate(source.date)}</span>}
        {source.criterion_kind && (
          <span className="text-muted-foreground">
            {source.criterion_kind === 'inclusion' ? 'kritérium zařazení' : 'kritérium vyřazení'}
          </span>
        )}
      </div>

      {(source.department || source.author) && (
        <dl className="space-y-0.5 text-xs text-muted-foreground">
          {source.department && <dd>{source.department.trim()}</dd>}
          {source.author && <dd>{source.author.text}</dd>}
        </dl>
      )}

      {source.value && (
        <div className="rounded-lg border border-border bg-background p-3">
          <p className="text-2xl font-bold text-foreground">
            {source.value.text}
            {source.value.interpretation && (
              <span className="ml-2 rounded bg-muted px-1.5 py-0.5 align-middle text-xs font-semibold text-muted-foreground">
                {source.value.interpretation === 'H' ? 'nad normou' : source.value.interpretation === 'L' ? 'pod normou' : source.value.interpretation}
              </span>
            )}
          </p>
          {(source.value.ref_low !== null || source.value.ref_high !== null) && (
            <p className="text-xs text-muted-foreground">
              Referenční rozsah: {source.value.ref_low ?? '–'} – {source.value.ref_high ?? '–'} {source.value.unit ?? ''}
            </p>
          )}
        </div>
      )}

      {source.text && <SourceText text={source.text} highlight={source.highlight} markRef={markRef} />}

      {(source.source || source.region) && (
        <p className="text-xs text-muted-foreground">
          Zdroj: {source.source}
          {source.region && <> · {source.region}</>}
        </p>
      )}

      {source.derived_from && source.derived_from.length > 0 && (
        <div className="space-y-2">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Zdrojový dokument</p>
          {source.derived_from.map((doc) => (
            <div key={doc.evidence_id} className="rounded-lg border border-border p-3">
              <p className="text-xs font-semibold text-foreground">
                {doc.title} <span className="font-mono font-normal text-muted-foreground">{doc.evidence_id}</span>
              </p>
              {doc.date && <p className="text-[11px] text-muted-foreground">{formatDate(doc.date)}</p>}
              {doc.text && <p className="mt-1 whitespace-pre-wrap text-xs text-foreground">{doc.text}</p>}
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
    return <p className="whitespace-pre-wrap leading-relaxed text-foreground">{text}</p>;
  }
  return (
    <p className="whitespace-pre-wrap leading-relaxed text-muted-foreground">
      {text.slice(0, highlight.start)}
      <mark ref={markRef} className="rounded bg-yellow-200 px-0.5 text-foreground dark:bg-yellow-500/30">
        {text.slice(highlight.start, highlight.end)}
      </mark>
      {text.slice(highlight.end)}
    </p>
  );
}
