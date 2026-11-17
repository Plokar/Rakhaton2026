'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { ProjectorPanel } from '@/components/mdt/ProjectorPanel';
import { JoinQr } from '@/components/mdt/live/JoinQr';
import { parseSelection, useProjectorQr, useProjectorSelection, type ProjectorSelection } from '@/components/mdt/projector';

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
  const [qr, setQr] = useProjectorQr(selection?.board ?? null);
  // Titulek okna (Next metadata mají přednost před <title> v klientské stránce): okno jde najít na liště.
  React.useEffect(() => {
    document.title = selection ? `${selection.patient} · projektor · MDTcore` : 'Projektor · MDTcore';
  }, [selection]);
  return (
    // Celá šířka okna (T-343): úzké okno vedle PACS má karty pod sebou, široké okno nebo projektor je skládá do sloupců.
    <div className="relative h-dvh bg-background">
      <ProjectorPanel key={selection ? `${selection.board}:${selection.caseId}` : 'empty'} selection={selection} />
      {/* T-380: QR pro příchod lékařů z mobilu (klávesa Q nebo tlačítko v jednání), klik nebo Esc skryje */}
      {qr && selection && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-background/85 backdrop-blur-sm" onClick={() => setQr(false)}>
          <div className="rounded-2xl bg-card p-6 shadow-xl ring-1 ring-border">
            <p className="mb-3 text-center text-lg font-semibold">Připojte se ze svého mobilu</p>
            <JoinQr sessionId={selection.board} size={280} />
          </div>
        </div>
      )}
    </div>
  );
}
