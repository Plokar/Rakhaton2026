'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { ProjectorPanel } from '@/components/mdt/ProjectorPanel';
import { parseSelection, useProjectorSelection, type ProjectorSelection } from '@/components/mdt/projector';

/**
 * Druhé okno pro projektor (T-512): úzký panel bez navigace vedle snímku z PACS. Případ vybírá
 * admin okno (`/dashboard/mdt`); výběr přichází přes BroadcastChannel, URL drží výběr pro obnovení.
 * Chráněno v proxy.ts stejně jako /dashboard.
 */
export default function ProjectorPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = React.use(searchParams);
  return <ProjectorWindow initial={parseSelection(params)} />;
}

function ProjectorWindow({ initial }: { initial: ProjectorSelection | null }) {
  const selection = useProjectorSelection(initial);
  // Titulek okna (Next metadata mají přednost před <title> v klientské stránce): okno jde najít na liště.
  React.useEffect(() => {
    document.title = selection ? `${selection.patient} · projektor · MedTeam` : 'Projektor · MedTeam';
  }, [selection]);
  return (
    <div className="flex h-dvh justify-center bg-muted/40">
      <div className="h-full w-full max-w-[420px] border-x border-border bg-background">
        <ProjectorPanel key={selection ? `${selection.board}:${selection.caseId}` : 'empty'} selection={selection} />
      </div>
    </div>
  );
}
