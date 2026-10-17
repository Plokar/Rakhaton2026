'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { Page, PageHeader } from '@/components/layout/Page';
import { PageCrumbs } from '@/components/layout/TopBar';
import { Skeleton } from '@/components/shadcn/skeleton';
import { AddPatientForm } from '@/components/mdt/AddPatientSheet';
import { dayLabel, timeLabel } from '@/components/mdt/dates';
import { can, useMe } from '@/components/mdt/me';
import { apiErrorMessage, useSessionQuery } from '@/lib/queries';

/**
 * Zařazení pacienta jako samostatná stránka (FR-P4): záloha pro přímé odkazy a mobil. Hlavní cesta je
 * „+“ na dlaždici kalendáře nebo „Zařadit“ v jednání (boční panel, NAVRH_UI §6.5).
 */
export default function AddCasePage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = React.use(params);
  const router = useRouter();
  const me = useMe();
  const session = useSessionQuery(sessionId);
  const back = `/dashboard/mdt/${encodeURIComponent(sessionId)}`;

  return (
    <Page className="max-w-3xl">
      {session.data && (
        <PageCrumbs items={[{ label: session.data.title, href: back }, { label: 'Zařadit pacienta' }]} />
      )}
      <PageHeader
        title="Zařadit pacienta"
        meta={session.data ? `${session.data.title}, ${dayLabel(session.data.date)} ${timeLabel(session.data.date)}` : 'Načítám zasedání…'}
      />
      {me && !can.generateBrief(me) && (
        <p className="text-sm text-muted-foreground">Pacienta zařazuje zadávající lékař nebo předseda komise.</p>
      )}
      {session.isLoading ? (
        <Skeleton className="h-64" />
      ) : session.isError || !session.data ? (
        <p role="alert" className="text-sm text-destructive">{apiErrorMessage(session.error, 'Zasedání se nepodařilo načíst.')}</p>
      ) : (
        <AddPatientForm session={session.data} onDone={() => router.push(back)} />
      )}
    </Page>
  );
}
