'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import type { EvidenceId } from '@/types/mdt';

// Klíče kontraktu §8, jejichž hodnota je Evidence ID nebo jejich seznam.
const EVIDENCE_KEYS = new Set([
  'citation', 'citations', 'guideline', 'guideline_citations', 'rule_citation',
  'patient_citations', 'inputs', 'criterion_id', 'required_by',
]);
const PATIENT_FACT = /^P\d{2}(?:-|#|$)/;

/** Citace v pořadí, v jakém se v podkladu objeví (bez duplicit). */
export function collectCitations(node: unknown): EvidenceId[] {
  const seen = new Set<EvidenceId>();
  const walk = (value: unknown, key?: string) => {
    if (Array.isArray(value)) {
      value.forEach((item) => walk(item, key));
    } else if (value && typeof value === 'object') {
      Object.entries(value).forEach(([k, v]) => walk(v, k));
    } else if (typeof value === 'string' && key && EVIDENCE_KEYS.has(key)) {
      seen.add(value);
    }
  };
  walk(node);
  return [...seen];
}

interface CitationContextValue {
  numbers: Map<EvidenceId, number>;
  activeId: EvidenceId | null;
  open: (id: EvidenceId) => void;
}

const CitationContext = React.createContext<CitationContextValue | null>(null);

/**
 * Číslování citací v podkladu (ARCH §7.3: „citace jsou čísla, ne dlouhé odkazy“).
 * Fakta pacienta dostanou pořadové číslo, pasáže guidelines a kritéria studií zůstávají jako ID.
 */
export function CitationProvider({
  order,
  activeId,
  onOpen,
  children,
}: {
  order: EvidenceId[];
  activeId: EvidenceId | null;
  onOpen: (id: EvidenceId) => void;
  children: React.ReactNode;
}) {
  const numbers = React.useMemo(() => {
    const map = new Map<EvidenceId, number>();
    for (const id of order) {
      if (PATIENT_FACT.test(id) && !map.has(id)) map.set(id, map.size + 1);
    }
    return map;
  }, [order]);
  const value = React.useMemo(() => ({ numbers, activeId, open: onOpen }), [numbers, activeId, onOpen]);
  return <CitationContext.Provider value={value}>{children}</CitationContext.Provider>;
}

/** Otevření zdroje citace z libovolné komponenty podkladu (graf, časová osa…). */
export function useCitationOpen(): ((id: EvidenceId) => void) | undefined {
  return React.useContext(CitationContext)?.open;
}

export function CitationChip({ id }: { id: EvidenceId }) {
  const ctx = React.useContext(CitationContext);
  const number = ctx?.numbers.get(id);
  const active = ctx?.activeId === id;
  return (
    <button
      type="button"
      onClick={() => ctx?.open(id)}
      title={`Zdroj ${id}`}
      aria-label={`Otevřít zdroj ${id}`}
      className={cn(
        'inline-flex h-5 min-w-5 items-center justify-center rounded-md border px-1 align-baseline font-mono text-[10px] font-semibold leading-none transition',
        active
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-border bg-muted text-muted-foreground hover:border-primary hover:text-primary',
      )}
    >
      {number ?? id}
    </button>
  );
}

export function Citations({ ids, className }: { ids: EvidenceId[]; className?: string }) {
  if (!ids.length) return null;
  return (
    <span className={cn('ml-1 inline-flex flex-wrap gap-0.5 align-baseline', className)}>
      {ids.map((id) => (
        <CitationChip key={id} id={id} />
      ))}
    </span>
  );
}
