'use client';

import { MonitorUp } from 'lucide-react';
import { EmptyState } from '@/components/ui/empty-state';
import { cn } from '@/lib/utils';
import type { ProjectorSelection } from './projector';
import { CaseQuickViewNarrow, useQuickViewSources } from './quick-view';

/**
 * Úzký panel pro projektor vedle snímku z PACS (T-512, FR-U2). Obsah je společný rychlý přehled
 * (`CaseQuickViewNarrow`), případ vybírá jednání komise přes BroadcastChannel.
 */
export function ProjectorPanel({
  selection,
  className,
  titleAs = 'h1',
}: {
  selection: ProjectorSelection | null;
  className?: string;
  titleAs?: 'h1' | 'h2';
}) {
  const sources = useQuickViewSources({
    sessionId: selection?.board ?? null,
    caseId: selection?.caseId ?? null,
    patientId: selection?.patient ?? null,
  });

  if (!selection) {
    return (
      <div className={cn('flex h-full items-center justify-center p-6', className)}>
        <EmptyState
          className="w-full border-0"
          icon={<MonitorUp aria-hidden />}
          title="Čeká se na výběr pacienta"
          description="Otevřete jednání komise a vyberte pacienta. Panel se přepne sám."
        />
      </div>
    );
  }
  return <CaseQuickViewNarrow sources={sources} caseId={selection.caseId} titleAs={titleAs} className={className} />;
}
