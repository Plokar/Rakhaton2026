'use client';

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PatientSummaryDocument } from '@/components/mdt/PatientSummaryDocument';
import { mdtApi } from '@/lib/mdt-api';

/**
 * Veřejná stránka pro pacienta (T-384): shrnutí přes bezpečný odkaz od lékaře, bez přihlášení. Ukazuje jen
 * text shrnutí; neplatný, zrušený nebo prošlý odkaz neprozradí, proč neplatí.
 */
export default function PatientLinkPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = React.use(params);
  const summary = useQuery({ queryKey: ['public-summary', token], queryFn: () => mdtApi.getPublicSummary(token), retry: false });
  return (
    <main className="min-h-dvh bg-background">
      {summary.isLoading ? (
        <p className="p-6 text-sm text-muted-foreground" aria-busy="true">Načítám shrnutí…</p>
      ) : summary.data ? (
        <PatientSummaryDocument title={summary.data.title} mdtDate={summary.data.mdt_date} items={summary.data.items} />
      ) : (
        <div className="mx-auto max-w-xl px-4 py-16 text-center">
          <h1 className="text-xl font-semibold">Odkaz neplatí</h1>
          <p className="mt-2 text-muted-foreground">Platnost odkazu skončila nebo ho lékař zrušil. Požádejte svého lékaře o nový.</p>
        </div>
      )}
    </main>
  );
}
