'use client';

import * as React from 'react';
import Link from 'next/link';
import { LayoutList, MonitorUp } from 'lucide-react';
import { Button, buttonVariants } from '@/components/shadcn/button';
import { Sheet, SheetClose, SheetContent, SheetDescription, SheetTitle } from '@/components/shadcn/sheet';
import { Skeleton } from '@/components/shadcn/skeleton';
import { useCaseLocation } from '@/lib/queries';
import { cn } from '@/lib/utils';
import { can, useMe } from './me';
import { openProjectorWindow } from './projector';
import { ProjectorLayoutDialog } from './ProjectorLayoutEditor';
import { CaseQuickViewNarrow, useQuickViewSources } from './quick-view';

/**
 * Rychlý přehled v bočním panelu (NAVRH_UI §6.4): klik na pacienta v kalendáři. Kalendář pod panelem
 * zůstává, panel je v URL (`?pacient=`), takže odkaz jde poslat a Zpět ho zavře.
 */
export function QuickViewSheet({ caseId, onClose }: { caseId: number | null; onClose: () => void }) {
  // Poslední otevřený případ drží obsah i během animace zavírání.
  const [shownId, setShownId] = React.useState(caseId);
  if (caseId !== null && caseId !== shownId) setShownId(caseId);

  const me = useMe();
  const [arranging, setArranging] = React.useState(false);
  const { session, item, loading } = useCaseLocation(shownId);
  const sources = useQuickViewSources({
    sessionId: session?.id ?? null,
    caseId: item?.id ?? null,
    patientId: item?.patient_id ?? null,
  });

  return (
    <Sheet open={caseId !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" showCloseButton={false} className="w-full gap-0 p-0 data-[side=right]:sm:max-w-[440px]">
        <SheetTitle className="sr-only">Rychlý přehled {item?.patient_id ?? ''}</SheetTitle>
        <SheetDescription className="sr-only">
          Klíčové údaje, léčebné postupy se semaforem a otázka pro MDT. Escape panel zavře.
        </SheetDescription>
        {item && session ? (
          <CaseQuickViewNarrow
            sources={sources}
            caseId={item.id ?? null}
            footer={
              <div className="flex shrink-0 items-center gap-2 border-t border-border bg-card px-4 py-3">
                <Link href={`/dashboard/cases/${item.id}`} className={buttonVariants({ size: 'lg' })}>
                  Otevřít detail
                </Link>
                <Link href={`/dashboard/mdt/${session.id}?pacient=${item.id}`} className={buttonVariants({ variant: 'outline', size: 'lg' })}>
                  Jednání
                </Link>
                <Button
                  variant="ghost"
                  size="icon-lg"
                  aria-label="Okno pro projektor"
                  title="Okno pro projektor"
                  onClick={() => openProjectorWindow({ board: session.id, caseId: item.id as number, patient: item.patient_id })}
                >
                  <MonitorUp aria-hidden />
                </Button>
                {can.editCase(me, item) && (
                  <Button
                    variant="ghost"
                    size="icon-lg"
                    aria-label="Upravit okno pro projektor"
                    title="Upravit okno pro projektor: skrýt nebo přeskládat údaje"
                    onClick={() => setArranging(true)}
                  >
                    <LayoutList aria-hidden />
                  </Button>
                )}
                {arranging && <ProjectorLayoutDialog item={item} open onOpenChange={setArranging} />}
                <SheetClose render={<Button variant="ghost" size="lg" className="ml-auto" />}>Zavřít</SheetClose>
              </div>
            }
          />
        ) : (
          <div className="flex flex-1 flex-col gap-3 p-4" aria-busy={loading}>
            {loading ? (
              <>
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-4 w-64" />
                <Skeleton className="mt-4 h-40" />
              </>
            ) : (
              <>
                <p className="text-sm">Případ v žádném zasedání nenacházím. Možná byl mezitím přesunut nebo odebrán.</p>
                <SheetClose render={<Button variant="outline" className={cn('w-fit')} />}>Zavřít</SheetClose>
              </>
            )}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
