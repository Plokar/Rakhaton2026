'use client';

import * as React from 'react';
import Link from 'next/link';
import { BellRing, CircleCheck, ClipboardCheck } from 'lucide-react';
import { toast } from 'sonner';
import { buttonVariants } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Button } from '@/components/ui/button';
import { apiErrorMessage, useCaseDoctorRules, useCheckReview, useMyReviewsQuery, useReadinessQuery, useReviewQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { CaseReview, MyReview, ReviewStatus } from '@/types/mdt';
import { dayLabel, timeLabel } from './dates';
import { RequirementsPanel } from './DoctorRules';
import { formatDate } from './format';

/**
 * Kontrola před zasedáním (T-349). 48 h před zasedáním dostane zadávající lékař upozornění: co přibylo od zařazení
 * (laboratoř, zobrazení, zprávy) a co v podkladu chybí. Potvrdí kontrolu, nebo údaje doplní. Když na kontrolu
 * zapomene, pacient zůstává na MDT, jen je podsvícený, aby to komise věděla.
 */

/** Pacient, kterého je třeba podsvítit (čeká na kontrolu, nebo zasedání začalo bez ní). */
export const needsReview = (status: ReviewStatus | undefined) => status === 'due' || status === 'missed';

/** Podbarvení řádku nebo čipu pacienta bez kontroly (žlutá jako „k dokončení“, ne barva semaforu). */
export const REVIEW_ROW = 'bg-amber-50 ring-1 ring-inset ring-amber-300/70 dark:bg-amber-400/10 dark:ring-amber-400/30';

export function reviewText(review: Pick<CaseReview, 'status' | 'unseen_count'>): string {
  const base = review.status === 'missed' ? 'Kontrola neproběhla' : 'Čeká na kontrolu';
  return review.unseen_count ? `${base} · ${newCount(review.unseen_count)}` : base;
}

function newCount(n: number) {
  return n === 1 ? '1 nový výsledek' : n < 5 ? `${n} nové výsledky` : `${n} nových výsledků`;
}

/** Potřebuje pacient podsvítit? (sdílená cache s `ReviewMark`, jeden dotaz na případ) */
export function useNeedsReview(caseId: number | null | undefined): boolean {
  return needsReview(useReviewQuery(caseId).data?.status);
}

/** Štítek u pacienta (kalendář, agenda, projektor); bez kontroly nic nezobrazí. */
export function ReviewMark({ caseId, className, short = false }: { caseId: number; className?: string; short?: boolean }) {
  const { data } = useReviewQuery(caseId);
  if (!data || !needsReview(data.status)) return null;
  const text = reviewText(data);
  return (
    <span
      title={`${text}. Zadávající lékař před zasedáním nepotvrdil, že viděl, co přibylo od zařazení.`}
      className={cn('inline-flex items-center gap-1 text-xs font-medium text-amber-800 dark:text-amber-300', className)}
    >
      <BellRing className="size-3.5 shrink-0" aria-hidden />
      {short ? (data.status === 'missed' ? 'bez kontroly' : 'ke kontrole') : text}
      {short && <span className="sr-only">. {text}</span>}
    </span>
  );
}

/** Dialog kontroly: nové výsledky od zařazení, chybějící údaje a potvrzení. */
export function ReviewDialog({
  caseId,
  patient,
  session,
  open,
  onOpenChange,
}: {
  caseId: number;
  patient: string;
  session?: { title: string; date: string } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const review = useReviewQuery(open ? caseId : null);
  const readiness = useReadinessQuery(open ? caseId : null);
  const doctorRules = useCaseDoctorRules(open ? caseId : null);
  const check = useCheckReview();
  const data = review.data;
  const missing = readiness.data?.unresolved.filter((f) => f.status !== 'skipped') ?? [];

  const confirm = () =>
    check.mutate(caseId, {
      onSuccess: () => {
        toast(`${patient}: kontrola před zasedáním potvrzena`);
        onOpenChange(false);
      },
      onError: (err) => toast.error(apiErrorMessage(err, 'Kontrolu se nepodařilo uložit.')),
    });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Kontrola před zasedáním · {patient}</DialogTitle>
          <DialogDescription>
            {session ? `${session.title}, ${dayLabel(session.date)} ${timeLabel(session.date)}. ` : ''}
            Zkontrolujte, co přibylo od zařazení, a doplňte, co chybí. Pacient na zasedání zůstane i bez kontroly, jen bude
            podsvícený.
          </DialogDescription>
        </DialogHeader>

        <section aria-labelledby="review-new" className="flex flex-col gap-1.5">
          <h3 id="review-new" className="text-sm font-semibold">
            Nové od zařazení{data ? ` (${formatDate(data.since)})` : ''}
          </h3>
          {review.isLoading ? (
            <p className="text-sm text-muted-foreground">Načítám výsledky z IRIS…</p>
          ) : review.isError ? (
            <p role="alert" className="text-sm text-destructive">{apiErrorMessage(review.error, 'Výsledky se nepodařilo načíst.')}</p>
          ) : !data?.new_results.length ? (
            <p className="text-sm text-muted-foreground">Od zařazení v dokumentaci nic nového nepřibylo.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-border rounded-lg border border-border">
              {data.new_results.map((n) => (
                <li key={n.citation} className={cn('flex items-baseline gap-3 px-3 py-2 text-sm', n.unseen && 'bg-amber-50/70 dark:bg-amber-400/5')}>
                  <span className="w-20 shrink-0 tabular-nums text-muted-foreground">{formatDate(n.date)}</span>
                  <span className="min-w-0 flex-1">
                    <span className="font-medium">{n.label}</span>
                    {n.value && <span className="text-muted-foreground"> · {n.value}</span>}
                    <span translate="no" className="ml-1.5 font-mono text-[11px] text-muted-foreground">{n.citation}</span>
                  </span>
                  {n.unseen && <span className="shrink-0 text-xs font-medium text-amber-800 dark:text-amber-300">nové</span>}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section aria-labelledby="review-missing" className="flex flex-col gap-1.5">
          <h3 id="review-missing" className="text-sm font-semibold">Chybí v podkladu</h3>
          {readiness.isLoading ? (
            <p className="text-sm text-muted-foreground">Načítám…</p>
          ) : missing.length ? (
            <p className="text-sm">
              {missing.slice(0, 6).map((f) => f.label).join(', ')}
              {missing.length > 6 && ` a dalších ${missing.length - 6}`}
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Povinné údaje jsou doplněné nebo přeskočené.</p>
          )}
        </section>

        {/* T-364: co vyžadují pozvaní lékaři; rozhoduje zadávající lékař (může kontrolu potvrdit) */}
        <RequirementsPanel rules={doctorRules.data} loading={doctorRules.isLoading} error={doctorRules.error}
          caseId={caseId} canDecide={data?.can_check !== false} />

        {data?.checked_at && (
          <p className="text-xs text-muted-foreground">
            Naposledy zkontroloval {data.checked_by?.name ?? 'lékař'} {formatDate(data.checked_at)}.
          </p>
        )}
        <DialogFooter>
          <Link href={`/dashboard/cases/${caseId}`} className={buttonVariants({ variant: 'outline', size: 'lg' })} onClick={() => onOpenChange(false)}>
            Doplnit údaje
          </Link>
          {data?.can_check !== false && (
            <Button size="lg" onClick={confirm} isLoading={check.isPending} disabled={!data}>
              <ClipboardCheck aria-hidden /> Zkontrolováno
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Upozornění nahoře v aplikaci: moji pacienti, kteří se do 48 h projednávají a čekají na kontrolu. */
export function ReviewBanner() {
  const { data } = useMyReviewsQuery();
  const [open, setOpen] = React.useState<MyReview | null>(null);
  if (!data?.length) return null;
  return (
    <>
      <div role="status" className="flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b border-amber-300/60 bg-amber-50 px-4 py-2 text-sm text-amber-950 sm:px-6 dark:border-amber-400/20 dark:bg-amber-400/10 dark:text-amber-100">
        <BellRing className="size-4 shrink-0" aria-hidden />
        <span className="font-medium">
          {data.length === 1 ? 'Před zasedáním zkontrolujte pacienta' : `Před zasedáním zkontrolujte ${data.length} pacienty`}
        </span>
        <ul className="flex flex-wrap items-center gap-1.5">
          {data.map((r) => (
            <li key={r.case_id}>
              <button
                type="button"
                onClick={() => setOpen(r)}
                className="inline-flex items-center gap-1.5 rounded-md bg-white/70 px-2 py-0.5 text-[13px] ring-1 ring-amber-300/70 transition-colors hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring dark:bg-white/5 dark:ring-amber-400/30 dark:hover:bg-white/10"
              >
                <span translate="no" className="font-semibold">{r.patient_id}</span>
                <span className="text-amber-900/80 dark:text-amber-100/80">
                  {r.session.title}, {dayLabel(r.session.date)} {timeLabel(r.session.date)}
                </span>
                {r.unseen_count > 0 && <span className="font-medium">· {newCount(r.unseen_count)}</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>
      {open && (
        <ReviewDialog
          caseId={open.case_id}
          patient={open.patient_id}
          session={open.session}
          open
          onOpenChange={(next) => !next && setOpen(null)}
        />
      )}
    </>
  );
}

/** Pruh v detailu a v jednání: stav kontroly a tlačítko dialogu (jen když kontrola čeká nebo neproběhla). */
export function ReviewNotice({ caseId, patient, session, className }: { caseId: number; patient: string; session?: { title: string; date: string } | null; className?: string }) {
  const { data } = useReviewQuery(caseId);
  const [open, setOpen] = React.useState(false);
  if (!data || data.status === 'upcoming') return null;
  if (data.status === 'checked') {
    return (
      <p className={cn('flex items-center gap-2 text-[13px] text-muted-foreground', className)}>
        <CircleCheck className="size-4 text-emerald-700 dark:text-emerald-400" aria-hidden />
        Zkontrolováno před zasedáním{data.checked_by ? ` (${data.checked_by.name}, ${formatDate(data.checked_at!)})` : ''}
      </p>
    );
  }
  return (
    <>
      <div className={cn('flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg px-3 py-2 text-sm text-amber-950 dark:text-amber-100', REVIEW_ROW, className)}>
        <BellRing className="size-4 shrink-0" aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="font-medium">{reviewText(data)}.</span>{' '}
          {data.status === 'missed'
            ? 'Zadávající lékař před zasedáním nepotvrdil, že viděl, co přibylo od zařazení.'
            : data.can_check
              ? 'Podívejte se, co přibylo od zařazení, případně doplňte údaje a kontrolu potvrďte.'
              : 'Zadávající lékař ještě nepotvrdil, že viděl, co přibylo od zařazení.'}
        </span>
        <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
          {data.can_check ? 'Zkontrolovat' : 'Co přibylo'}
        </Button>
      </div>
      {open && <ReviewDialog caseId={caseId} patient={patient} session={session} open onOpenChange={setOpen} />}
    </>
  );
}
