'use client';

import * as React from 'react';
import Link from 'next/link';
import { Bot, CalendarClock, ExternalLink, MonitorUp, Radio, Search, UsersRound } from 'lucide-react';
import { PageCrumb } from '@/components/layout/TopBar';
import { Button, buttonVariants } from '@/components/shadcn/button';
import { Command, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/shadcn/command';
import { Sheet, SheetContent, SheetTitle } from '@/components/shadcn/sheet';
import { Skeleton } from '@/components/shadcn/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { agendaOrder, apiErrorMessage, usePatientsQuery, useSessionQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtCase, MyLive } from '@/types/mdt';
import { dayLabel, timeLabel } from '../dates';
import { ChatbotPanel } from '../meeting/ChatbotPanel';
import { useChatbot } from '../meeting/use-chatbot';
import { PatientChatPanel } from '../PatientChatDialog';
import { CaseQuickViewWide, useQuickViewSources } from '../quick-view';
import { useLiveSession, useMyLive, usePresence } from './use-live';

type Session = MyLive['sessions'][number];
type Case = MdtCase & { id: number };
/** Vybraný pacient: z agendy (případ), jinak jen karta pacienta z IRIS (chatbot nad kartou, T-345). */
type Pick = { kind: 'case'; caseId: number } | { kind: 'patient'; patientId: string };

const REASON: Record<Session['reasons'][number], string> = {
  chair: 'předsedáte',
  requester: 'zařadil(a) jste pacienta',
  collaborator: 'jste přizván(a)',
};

/**
 * Živé zasedání (T-354) pro mobil i web: lékař se přihlásí svým účtem, aplikace najde zasedání, kde má být
 * (nebo kde už je), ohlásí ho jako přítomného a ukáže pacienta, který je právě na projektoru. Během jednání
 * sáhne po mobilu, když ho zajímá něco, co na projektoru není: detail pacienta, celá karta a dotaz na AI.
 * Ptát se jde i na jiného pacienta z agendy nebo z nemocnice; „Zpět na projektor“ vrátí sledování.
 */
export function LiveView({ initialSession }: { initialSession: number | null }) {
  const mine = useMyLive();
  const [chosen, setChosen] = React.useState<number | null>(initialSession);
  const sessions = mine.data?.sessions ?? [];
  const sessionId = chosen ?? mine.data?.current ?? null;
  const item = sessions.find((s) => s.id === sessionId) ?? null;

  if (mine.isLoading) return <LiveSkeleton />;
  if (mine.isError) {
    return (
      <p role="alert" className="p-6 text-sm text-destructive">
        {apiErrorMessage(mine.error, 'Zasedání se nepodařilo načíst.')}
      </p>
    );
  }
  if (sessionId == null) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <PageCrumb>Živě na MDT</PageCrumb>
        <EmptyState
          className="w-full max-w-lg"
          icon={<CalendarClock aria-hidden />}
          title="Dnes právě neprobíhá žádné zasedání"
          description="Jakmile předseda zahájí jednání, uvidíte tu pacienta, který je na projektoru."
          action={
            <Link href="/dashboard/mdt" className={buttonVariants({ variant: 'outline' })}>
              Kalendář zasedání
            </Link>
          }
        />
      </div>
    );
  }
  return (
    <LiveSession
      key={sessionId}
      sessionId={sessionId}
      item={item}
      others={sessions.filter((s) => s.id !== sessionId)}
      onSwitch={setChosen}
    />
  );
}

function LiveSession({
  sessionId,
  item,
  others,
  onSwitch,
}: {
  sessionId: number;
  item: Session | null;
  others: Session[];
  onSwitch: (id: number) => void;
}) {
  const board = useSessionQuery(sessionId);
  const closed = board.data?.status === 'closed';
  usePresence(sessionId, !closed);
  const { live, connected } = useLiveSession(sessionId);
  const cases = agendaOrder(board.data).filter((c): c is Case => c.id != null);

  // null = sleduji projektor; jinak lékař klepl na jiného pacienta
  const [picked, setPicked] = React.useState<Pick | null>(null);
  const following = picked === null;
  const liveCase = live?.case ? (cases.find((c) => c.id === live.case!.id) ?? null) : null;
  const shownCase = picked?.kind === 'case' ? (cases.find((c) => c.id === picked.caseId) ?? null) : following ? liveCase : null;
  const shownPatient = picked?.kind === 'patient' ? picked.patientId : (shownCase?.patient_id ?? null);
  const [searching, setSearching] = React.useState(false);
  const bot = useChatbot(sessionId);

  const sources = useQuickViewSources({
    sessionId: shownCase ? sessionId : null,
    caseId: shownCase?.id ?? null,
    patientId: shownCase?.patient_id ?? null,
  });

  const title = item?.title ?? board.data?.title ?? 'Zasedání';
  const date = item?.date ?? board.data?.date;
  const present = live?.present ?? [];

  return (
    <div className="flex h-[calc(100dvh-3.5rem)] min-h-0 flex-col">
      <PageCrumb>Živě na MDT</PageCrumb>
      {/* Kde jsem: zasedání, stav, přítomní */}
      <header className="shrink-0 border-b border-border bg-card px-4 py-3 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium',
              live?.status === 'in_progress' ? 'bg-emerald-50 text-emerald-800 dark:bg-emerald-400/10 dark:text-emerald-300' : 'bg-muted text-muted-foreground',
            )}
          >
            <Radio className="size-3.5" aria-hidden />
            {live?.status === 'in_progress' ? 'Probíhá' : closed ? 'Uzavřeno' : 'Zatím nezačalo'}
          </span>
          <h1 className="min-w-0 text-base font-semibold">{title}</h1>
          {date && <span className="text-sm text-muted-foreground">{dayLabel(date)} {timeLabel(date)}</span>}
          <Link href={`/dashboard/mdt/${sessionId}`} className="ml-auto text-sm font-medium text-primary underline-offset-4 hover:underline">
            Jednání
          </Link>
        </div>
        <p className="mt-1 flex flex-wrap items-center gap-x-2 text-[13px] text-muted-foreground">
          <UsersRound className="size-3.5" aria-hidden />
          <span>
            {present.length === 0 ? 'Zatím nikdo ohlášený' : `Přítomní (${present.length}): ${present.map((p) => p.name).join(', ')}`}
          </span>
          {item?.reasons.length ? <span>· Máte tu být: {item.reasons.map((r) => REASON[r]).join(', ')}</span> : null}
          {!connected && <span className="text-amber-700 dark:text-amber-400">· připojuji živé změny…</span>}
        </p>
        {others.length > 0 && (
          <p className="mt-1 text-[13px] text-muted-foreground">
            Dnes také:{' '}
            {others.map((s, i) => (
              <React.Fragment key={s.id}>
                {i > 0 && ', '}
                <button type="button" onClick={() => onSwitch(s.id)} className="font-medium text-foreground underline-offset-4 hover:underline">
                  {s.title} {timeLabel(s.date)}
                  {s.status === 'in_progress' ? ' (probíhá)' : ''}
                </button>
              </React.Fragment>
            ))}
          </p>
        )}
      </header>

      {/* Co je na projektoru + výběr pacienta */}
      <div className="shrink-0 border-b border-border bg-background px-4 py-2 sm:px-6">
        <div className="flex items-center gap-2 text-sm">
          <MonitorUp className="size-4 shrink-0 text-primary" aria-hidden />
          {live?.case ? (
            <span className="min-w-0 flex-1">
              Na projektoru <span translate="no" className="font-semibold">{live.case.patient_id}</span>
              {live.case.position ? <span className="text-muted-foreground"> · {live.case.position}. z {live.case.count}</span> : null}
              {live.slide && (
                <span className="text-muted-foreground">
                  {' '}· slide {live.slide.index + 1}/{live.slide.total}
                  {live.slide.label ? ` ${live.slide.label}` : ''}
                </span>
              )}
            </span>
          ) : (
            <span className="min-w-0 flex-1 text-muted-foreground">Projektor zatím neukazuje pacienta</span>
          )}
          {!following && live?.case && (
            <Button size="sm" onClick={() => setPicked(null)}>
              Zpět na projektor
            </Button>
          )}
        </div>
        <div role="group" aria-label="Pacienti v agendě" className="-mx-1 mt-2 flex gap-1.5 overflow-x-auto px-1 pb-1">
          {cases.map((c) => {
            const selected = shownCase?.id === c.id;
            return (
              <button
                key={c.id}
                type="button"
                translate="no"
                aria-pressed={selected}
                onClick={() => setPicked(live?.case?.id === c.id ? null : { kind: 'case', caseId: c.id })}
                className={cn(
                  'inline-flex shrink-0 items-center gap-1 rounded-md border px-2.5 py-1 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  selected ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-card hover:bg-muted',
                )}
              >
                {live?.case?.id === c.id && <MonitorUp className="size-3.5" aria-label="na projektoru" />}
                {c.patient_id}
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => setSearching(true)}
            className={cn(
              'inline-flex shrink-0 items-center gap-1 rounded-md border border-dashed px-2.5 py-1 text-[13px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              picked?.kind === 'patient' ? 'border-primary text-foreground' : 'border-border text-muted-foreground hover:bg-muted',
            )}
          >
            <Search className="size-3.5" aria-hidden />
            {picked?.kind === 'patient' ? <span translate="no">{picked.patientId}</span> : 'Jiný pacient'}
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pb-20">
        {board.isLoading ? (
          <LiveSkeleton />
        ) : shownCase ? (
          <div className="mx-auto w-full max-w-[1200px] px-4 py-4 sm:px-6">
            <CaseQuickViewWide
              key={shownCase.id}
              sources={sources}
              caseId={shownCase.id}
              warningsHref={`/dashboard/cases/${shownCase.id}#varovani`}
              stickyQuestion={false}
              toolbar={
                <div className="flex flex-wrap gap-2 pb-2">
                  <Link href={`/dashboard/cases/${shownCase.id}`} className={buttonVariants({ variant: 'outline', size: 'sm' })}>
                    <ExternalLink aria-hidden /> Celý detail a dokumentace
                  </Link>
                </div>
              }
            />
          </div>
        ) : picked?.kind === 'patient' ? (
          <div className="mx-auto flex w-full max-w-2xl flex-col gap-3 px-4 py-4 sm:px-6">
            <p className="text-sm text-muted-foreground">
              <span translate="no" className="font-semibold text-foreground">{picked.patientId}</span> není v agendě tohoto zasedání.
              Ptejte se AI na jeho kartu v IRIS nebo otevřete kartu pacienta.
            </p>
            <Link href={`/dashboard/patients/${picked.patientId}`} className={cn(buttonVariants({ variant: 'outline', size: 'sm' }), 'self-start')}>
              <ExternalLink aria-hidden /> Karta pacienta
            </Link>
            <PatientChatPanel key={picked.patientId} patientId={picked.patientId} className="h-[32rem] rounded-lg border" />
          </div>
        ) : (
          <div className="flex items-center justify-center p-6">
            <EmptyState
              className="w-full max-w-lg"
              icon={<MonitorUp aria-hidden />}
              title={cases.length ? 'Čeká se, až předseda ukáže prvního pacienta' : 'V agendě zatím nejsou pacienti'}
              description={cases.length ? 'Mezitím si můžete otevřít kteréhokoli pacienta z agendy nahoře.' : 'Pacienta zařazuje zadávající lékař nebo předseda.'}
            />
          </div>
        )}
      </div>

      {/* Dotaz na AI: k pacientovi, kterého právě vidím (z agendy); u pacienta mimo agendu je chat přímo na stránce */}
      {picked?.kind !== 'patient' && (
        <div className="pointer-events-none fixed inset-x-0 bottom-0 z-20 flex justify-end p-4">
          <Button size="lg" className="pointer-events-auto shadow-lg" onClick={() => bot.setOpen(true)}>
            <Bot aria-hidden /> Zeptat se AI{shownPatient ? ` na ${shownPatient}` : ''}
          </Button>
        </div>
      )}
      <Sheet open={bot.open} onOpenChange={bot.setOpen}>
        <SheetContent side="bottom" className="h-[85dvh] gap-0 p-0 sm:mx-auto sm:max-w-2xl sm:rounded-t-xl">
          <ChatbotPanel
            bot={bot}
            current={shownCase ? { id: shownCase.id, patient_id: shownCase.patient_id } : null}
            closed={closed}
            onSelectCase={(caseId) => {
              setPicked(live?.case?.id === caseId ? null : { kind: 'case', caseId });
              bot.setOpen(false);
            }}
            Title={SheetTitle}
          />
        </SheetContent>
      </Sheet>
      <PatientSearch
        open={searching}
        onOpenChange={setSearching}
        agenda={cases}
        onPick={(pid) => {
          const inAgenda = cases.find((c) => c.patient_id === pid);
          setPicked(inAgenda ? (live?.case?.id === inAgenda.id ? null : { kind: 'case', caseId: inAgenda.id }) : { kind: 'patient', patientId: pid });
          setSearching(false);
        }}
      />
    </div>
  );
}

/** Kterýkoli pacient z IRIS: z agendy otevře přehled případu, jinak kartu a chatbot nad kartou. */
function PatientSearch({
  open,
  onOpenChange,
  agenda,
  onPick,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agenda: Case[];
  onPick: (patientId: string) => void;
}) {
  const patients = usePatientsQuery(open);
  const inAgenda = new Set(agenda.map((c) => c.patient_id));
  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Jiný pacient" description="Pacient z agendy nebo z nemocnice">
      <Command loop>
        <CommandInput placeholder="Hledat pacienta (P03), diagnózu…" />
        <CommandList>
          <CommandEmpty>{patients.isLoading ? 'Načítám pacienty…' : 'Nic nenalezeno.'}</CommandEmpty>
          <CommandGroup heading="Pacienti">
            {(patients.data ?? []).map((p) => (
              <CommandItem
                key={p.id}
                value={`${p.display_name} ${p.diagnosis?.icd10 ?? ''} ${p.diagnosis?.text ?? ''}`}
                onSelect={() => onPick(p.id)}
              >
                <span translate="no" className="font-medium">{p.display_name}</span>
                <span className="truncate text-muted-foreground">{p.diagnosis ? `${p.diagnosis.icd10} ${p.diagnosis.text}` : ''}</span>
                {inAgenda.has(p.id) && <span className="ml-auto text-xs text-primary">v agendě</span>}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  );
}

function LiveSkeleton() {
  return (
    <div className="flex flex-col gap-3 p-4 sm:p-6" aria-busy="true">
      <Skeleton className="h-6 w-2/3" />
      <Skeleton className="h-8 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
