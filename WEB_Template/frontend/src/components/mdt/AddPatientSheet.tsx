'use client';

import * as React from 'react';
import { ArrowLeft, FilePlus2, Search, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/shadcn/sheet';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Input } from '@/components/ui/input';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, useCreateCase, useIntakeQuery, usePatientsQuery, useSessionQuery, useSessionsWithCases } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtCase, MdtSession, MdtSessionListItem, PatientListItem, ProjectorExtra, ProjectorLayout } from '@/types/mdt';
import { CitationProvider } from './citations';
import { dayLabel, timeLabel } from './dates';
import { ImportReportSheet } from './ImportReportSheet';
import { IntakeForm, type IntakeChoice, type IntakeResult } from './IntakeForm';
import { IntakeProjectorPreview } from './IntakeProjectorPreview';
import { useMe } from './me';
import { NewPatientForm } from './NewPatientForm';
import { PatientChatFocus, PatientChatPanel } from './PatientChatDialog';
import { SourceDrawer } from './SourceDrawer';

const OPEN_SESSIONS = (s: MdtSessionListItem) => s.status !== 'closed';

/** Zařazení čeká na dokončení (T-339): nominace bez kontroly úplnosti, nebo vrácené k doplnění (OBC-1.1). */
export const intakePending = (c: Pick<MdtCase, 'status'>) => c.status === 'nominated' || c.status === 'returned';

/**
 * Zařazení pacienta z kalendáře nebo z jednání (NAVRH_UI §6.5): výběr pacienta z IRIS, pak formulář
 * s kontrolou úplnosti (`IntakeForm`: Doplnit / Přeskočit, varování, ECOG + C/P). Otázku pro MDT
 * přeskočit nejde (OBC-1.1). Na širokém displeji je úplně vlevo živý náhled okna pro projektor a mezi ním a panelem
 * chatbot nad kartou pacienta, kde se lékař doptává (T-345); od 1024 px jen náhled, chatbot pak v dialogu.
 */
export function AddPatientSheet({ session, onClose, patientId }: { session: MdtSession | null; onClose: () => void; patientId?: string | null }) {
  const [shown, setShown] = React.useState(session);
  if (session && session !== shown) setShown(session);
  return (
    <Sheet open={session !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 data-[side=right]:sm:max-w-xl">
        {shown && (
          <>
            <SheetHeader className="border-b border-border px-5 py-4 pr-12">
              <SheetTitle className="text-base font-semibold">{patientId ? `Dokončit zařazení · ${patientId}` : 'Zařadit pacienta'}</SheetTitle>
              <SheetDescription>
                {shown.title}, {dayLabel(shown.date)} {timeLabel(shown.date)}
              </SheetDescription>
            </SheetHeader>
            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
              <AddPatientForm
                key={`${shown.id}:${patientId ?? ''}`}
                session={shown}
                onDone={onClose}
                initialPatientId={patientId ?? null}
                // celá plocha vlevo od panelu (36rem), mimo jeho posuvník: obsahující blok je panel (fixed), ne posuvná oblast
                asideClassName="absolute inset-y-3 right-[calc(100%+0.75rem)] hidden w-[calc(100vw-36rem-1.5rem)] gap-3 lg:flex"
              />
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

/** Výběr pacienta a formulář zařazení; sdílí ho boční panel i stránka `/dashboard/mdt/[id]/add`. */
export function AddPatientForm({
  session,
  onDone,
  initialPatientId = null,
  asideClassName,
}: {
  session: MdtSession;
  onDone: () => void;
  initialPatientId?: string | null;
  /** Umístění náhledu okna pro projektor a chatbotu vedle formuláře (T-345); bez něj se neukážou. */
  asideClassName?: string;
}) {
  const me = useMe();
  const [patientId, setPatientIdState] = React.useState<string | null>(initialPatientId);
  const [choice, setChoice] = React.useState<IntakeChoice | null>(null);
  const [layout, setLayout] = React.useState<ProjectorLayout>({});
  const chatInput = React.useRef<HTMLTextAreaElement>(null);
  const setPatientId = (next: string | null) => {
    setPatientIdState(next);
    setChoice(null);                                // jiný pacient začíná z předvyplnění a s výchozím oknem
    setLayout({});
  };
  // „+ Doplnit z karty“ skočí do chatbotu vedle formuláře; na užším displeji (chatbot skrytý) otevře editor dialog
  const focusChat = React.useCallback(() => {
    const input = chatInput.current;
    if (!input || input.getClientRects().length === 0) return false;
    input.focus();
    return true;
  }, []);
  const addExtra = (item: ProjectorExtra) => {
    setLayout((prev) => ({ ...prev, extra: [...(prev.extra ?? []), item] }));
    toast.success('Doplněno do okna pro projektor', { description: item.text });
  };
  const [query, setQuery] = React.useState('');
  const [creating, setCreating] = React.useState(false);
  const [importing, setImporting] = React.useState(false);
  const [sourceId, setSourceId] = React.useState<string | null>(null);
  const patients = usePatientsQuery();
  const board = useSessionQuery(session.id);
  const { sessions, detail } = useSessionsWithCases(OPEN_SESSIONS);
  const intake = useIntakeQuery(patientId);
  const create = useCreateCase();
  const when = `${dayLabel(session.date)} ${timeLabel(session.date)}`;

  // T-339: pacient na tomto boardu s nedokončeným zařazením (nominace bez kontroly úplnosti) jde vybrat a dokončit
  const onBoard = new Set((board.data?.cases ?? []).filter((c) => !intakePending(c)).map((c) => c.patient_id));
  const pending = new Set((board.data?.cases ?? []).filter(intakePending).map((c) => c.patient_id));
  const elsewhere = new Map<string, MdtSessionListItem>();
  for (const s of sessions) {
    if (s.id === session.id) continue;
    for (const c of detail.get(s.id)?.cases ?? []) elsewhere.set(c.patient_id, s);
  }
  const needle = query.trim().toLocaleLowerCase('cs');
  const list = (patients.data ?? []).filter(
    (p) => !needle || [p.id, p.display_name, p.diagnosis?.icd10, p.diagnosis?.text, p.mdt_question].some((v) => v?.toLocaleLowerCase('cs').includes(needle)),
  );
  const selected = patients.data?.find((p) => p.id === patientId) ?? null;

  const submit = (r: IntakeResult) => {
    if (!intake.data || !me || !patientId) return;
    create.mutate(
      {
        session: session.id,
        patient_id: patientId,
        service_request_id: intake.data.service_request_id,
        ecog: r.ecog,
        intent: r.intent,
        imaging_recent_checked: r.imaging_recent_checked,
        skipped_fields: r.skipped_fields,
        acknowledge: r.acknowledged,
        ...(r.projector_layout ? { projector_layout: r.projector_layout } : {}),
      },
      {
        onSuccess: () => {
          toast.success(`${patientId} zařazen na ${session.title}`, { description: when });
          onDone();
        },
      },
    );
  };

  return (
    <>
      {creating ? (
        <NewPatientForm
          sessionId={session.id}
          onCreated={(pid) => {
            setCreating(false);
            setPatientId(pid);
          }}
          onCancel={() => setCreating(false)}
        />
      ) : !selected ? (
          <div className="flex flex-col gap-3">
            <Button variant="outline" className="self-start" onClick={() => setCreating(true)}>
              <UserPlus aria-hidden /> Nový pacient
            </Button>
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Hledat pacienta (P02), diagnózu, otázku…"
              aria-label="Hledat pacienta"
              leftIcon={<Search className="size-4" aria-hidden />}
              autoFocus
            />
            {patients.isLoading ? (
              <div className="flex flex-col gap-2" aria-busy="true">
                {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}
              </div>
            ) : patients.isError ? (
              <p role="alert" className="text-sm text-destructive">{apiErrorMessage(patients.error, 'Pacienty se nepodařilo načíst.')}</p>
            ) : list.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">Hledání neodpovídá žádný pacient.</p>
            ) : (
              <ul className="-mx-2 flex flex-col">
                {list.map((p) => (
                  <PatientOption
                    key={p.id}
                    patient={p}
                    onBoard={onBoard.has(p.id)}
                    pending={pending.has(p.id)}
                    elsewhere={elsewhere.get(p.id)}
                    onSelect={() => setPatientId(p.id)}
                  />
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <div className="flex items-start gap-3">
              <Button variant="ghost" size="icon-sm" onClick={() => setPatientId(null)} aria-label="Zpět na výběr pacienta">
                <ArrowLeft aria-hidden />
              </Button>
              <div className="min-w-0 flex-1">
                <p translate="no" className="text-sm font-semibold">{selected.display_name}</p>
                <p className="text-[13px] text-muted-foreground">
                  {selected.diagnosis ? `${selected.diagnosis.icd10} ${selected.diagnosis.text}` : 'Bez onkologické diagnózy'}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setImporting(true)}>
                <FilePlus2 aria-hidden /> Vložit zprávu
              </Button>
            </div>
            <ImportReportSheet patientId={selected.id} open={importing} onClose={() => setImporting(false)} />
            <CitationProvider order={[]} activeId={sourceId} onOpen={setSourceId}>
              {intake.isLoading ? (
                <div className="flex flex-col gap-2" aria-busy="true">
                  <Skeleton className="h-5 w-40" />
                  <Skeleton className="h-48" />
                </div>
              ) : intake.isError ? (
                <p role="alert" className="text-sm text-destructive">
                  {apiErrorMessage(intake.error, 'Údaje pacienta se nepodařilo načíst z IRIS.')}
                </p>
              ) : intake.data ? (
                <PatientChatFocus.Provider value={asideClassName ? focusChat : null}>
                  <IntakeForm
                    key={patientId}
                    prefill={intake.data}
                    submitting={create.isPending}
                    onSubmit={submit}
                    patientId={patientId ?? undefined}
                    layout={layout}
                    onLayoutChange={setLayout}
                    onChoiceChange={setChoice}
                  />
                </PatientChatFocus.Provider>
              ) : null}
              <SourceDrawer evidenceId={sourceId} loadSource={mdtApi.getEvidence} onClose={() => setSourceId(null)} />
            </CitationProvider>
            {create.isError && (
              <p role="alert" className="text-sm text-destructive">{apiErrorMessage(create.error, 'Pacienta se nepodařilo zařadit.')}</p>
            )}
            {asideClassName && intake.data && (
              <div className={asideClassName}>
                {/* úplně vlevo náhled okna (od 48rem jako široký projektor), mezi ním a formulářem chatbot */}
                <IntakeProjectorPreview
                  session={session}
                  patient={selected}
                  intake={intake.data}
                  choice={choice}
                  layout={layout}
                  className="min-w-0 flex-1 xl:max-w-[44rem] xl:flex-[1_1_45%]"
                />
                <PatientChatPanel
                  key={selected.id}
                  patientId={selected.id}
                  extra={layout.extra}
                  onAdd={addExtra}
                  inputRef={chatInput}
                  className="hidden min-w-[20rem] flex-[1_1_55%] overflow-hidden rounded-xl border border-border shadow-[0_12px_32px_-12px_rgb(15_23_42/0.25)] xl:flex"
                />
              </div>
            )}
          </div>
        )}
    </>
  );
}

function PatientOption({
  patient,
  onBoard,
  pending = false,
  elsewhere,
  onSelect,
}: {
  patient: PatientListItem;
  onBoard: boolean;
  pending?: boolean;
  elsewhere: MdtSessionListItem | undefined;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        disabled={onBoard}
        className={cn(
          'flex w-full flex-col rounded-lg px-2 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          onBoard ? 'cursor-not-allowed opacity-55' : 'hover:bg-muted',
        )}
      >
        <span className="flex items-baseline gap-2">
          <span translate="no" className="text-sm font-medium">{patient.display_name}</span>
          {onBoard && <span className="text-xs text-muted-foreground">už je na tomto zasedání</span>}
          {pending && <span className="text-xs font-medium text-amber-700 dark:text-amber-400">nedokončené zařazení · dokončit</span>}
          {!onBoard && !pending && elsewhere && (
            <span className="text-xs text-muted-foreground">
              zařazen: {elsewhere.title}, {dayLabel(elsewhere.date)}
            </span>
          )}
        </span>
        <span className="truncate text-[13px] text-muted-foreground">
          {patient.diagnosis ? `${patient.diagnosis.icd10} ${patient.diagnosis.text}` : 'Bez onkologické diagnózy'}
        </span>
        {patient.mdt_question && <span className="line-clamp-1 text-xs text-muted-foreground">{patient.mdt_question}</span>}
      </button>
    </li>
  );
}
