'use client';

import Link from 'next/link';
import { TriangleAlert } from 'lucide-react';
import { toast } from 'sonner';
import { Button, buttonVariants } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Skeleton } from '@/components/shadcn/skeleton';
import { apiErrorMessage, useSessionRecordQuery, useSessionStatus } from '@/lib/queries';
import type { MdtSessionDetail } from '@/types/mdt';
import { BoardOutputs, ZipLink } from './BoardRecord';
import { isDiscussed } from './patient';

/**
 * Ukončení boardu (T-333, jen předseda): potvrzení s počtem projednaných a potvrzených závěrů. Board se
 * uzavře (stav `closed`) a hned se nabídne stažení výstupů.
 */
export function CloseBoardDialog({
  board,
  open,
  onOpenChange,
  onClosed,
}: {
  board: MdtSessionDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onClosed: () => void;
}) {
  const status = useSessionStatus();
  const count = board.cases.length;
  const discussed = board.cases.filter(isDiscussed).length;
  const confirmed = board.cases.filter((c) => c.status === 'confirmed').length;
  const unconfirmed = count - confirmed;

  const close = () =>
    status.mutate(
      { id: board.id, status: 'closed' },
      {
        onSuccess: () => {
          onOpenChange(false);
          onClosed();
        },
        onError: (err) => toast.error(apiErrorMessage(err, 'Board se nepodařilo ukončit.')),
      },
    );

  return (
    <Dialog open={open} onOpenChange={(next) => !status.isPending && onOpenChange(next)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Ukončit board?</DialogTitle>
          <DialogDescription>
            {board.title}: projednáno {discussed} z {count}, potvrzených závěrů {confirmed}. Board se uloží do Záznamu
            boardů a pacienty už do něj zařadit nepůjde.
          </DialogDescription>
        </DialogHeader>
        {unconfirmed > 0 && (
          <p className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-[13px] text-amber-950 dark:bg-amber-400/10 dark:text-amber-200">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
            {unconfirmed === 1 ? '1 pacient nemá' : `${unconfirmed} pacientů nemá`} potvrzený závěr. PDF bude jen návrh a FHIR
            záznam nevznikne, dokud závěr nepotvrdíte (jde i po ukončení).
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={status.isPending}>
            Zrušit
          </Button>
          <Button onClick={close} disabled={status.isPending}>
            Ukončit board
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Nabídka stažení výstupů po ukončení boardu (a později z hlavičky uzavřeného boardu). */
export function BoardOutputsDialog({
  sessionId,
  open,
  onOpenChange,
  justClosed = false,
}: {
  sessionId: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  justClosed?: boolean;
}) {
  const record = useSessionRecordQuery(sessionId, open);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[calc(100dvh-2rem)] grid-rows-[auto_minmax(0,1fr)_auto] sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{justClosed ? 'Board je ukončený. Stáhnout výstupy?' : 'Výstupy boardu'}</DialogTitle>
          <DialogDescription>
            PDF závěru a FHIR záznam (document Bundle z IRIS) pro každého pacienta. Najdete je i později v{' '}
            <Link href="/dashboard/zaznamy" className="font-medium text-foreground underline underline-offset-4">Záznamu boardů</Link>.
          </DialogDescription>
        </DialogHeader>
        <div className="min-h-0 overflow-y-auto">
          {record.isLoading ? (
            <div className="flex flex-col gap-2" aria-busy="true">
              {[0, 1, 2].map((i) => <Skeleton key={i} className="h-14" />)}
            </div>
          ) : record.isError || !record.data ? (
            <p role="alert" className="text-sm text-destructive">{apiErrorMessage(record.error, 'Výstupy se nepodařilo načíst.')}</p>
          ) : (
            <BoardOutputs record={record.data} />
          )}
        </div>
        <DialogFooter className="items-center">
          <Button variant="ghost" size="lg" onClick={() => onOpenChange(false)}>
            {justClosed ? 'Teď ne' : 'Zavřít'}
          </Button>
          <Link href="/dashboard/zaznamy" className={buttonVariants({ variant: 'outline', size: 'lg' })}>
            Záznam boardů
          </Link>
          {record.data && <ZipLink record={record.data} />}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
