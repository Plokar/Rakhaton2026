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
import type { MdtSession, MdtSessionListItem, PatientListItem } from '@/types/mdt';
import { CitationProvider } from './citations';
import { dayLabel, timeLabel } from './dates';
import { ImportReportSheet } from './ImportReportSheet';
import { IntakeForm, type IntakeResult } from './IntakeForm';
import { useMe } from './me';
import { NewPatientForm } from './NewPatientForm';
import { SourceDrawer } from './SourceDrawer';

const OPEN_SESSIONS = (s: MdtSessionListItem) => s.status !== 'closed';

/**
 * Zařazení pacienta z kalendáře nebo z jednání (NAVRH_UI §6.5): výběr pacienta z IRIS, pak formulář
 * s kontrolou úplnosti (`IntakeForm`: Doplnit / Přeskočit, varování, ECOG + C/P). Otázku pro MDT
 * přeskočit nejde (OBC-1.1).
 */
export function AddPatientSheet({ session, onClose }: { session: MdtSession | null; onClose: () => void }) {
  const [shown, setShown] = React.useState(session);
  if (session && session !== shown) setShown(session);
  return (
    <Sheet open={session !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full gap-0 p-0 data-[side=right]:sm:max-w-xl">
        {shown && (
          <>
            <SheetHeader className="border-b border-border px-5 py-4 pr-12">
              <SheetTitle className="text-base font-semibold">Zařadit pacienta</SheetTitle>
              <SheetDescription>
                {shown.title}, {dayLabel(shown.date)} {timeLabel(shown.date)}
              </SheetDescription>
            </SheetHeader>
            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
              <AddPatientForm key={shown.id} session={shown} onDone={onClose} />
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

/** Výběr pacienta a formulář zařazení; sdílí ho boční panel i stránka `/dashboard/mdt/[id]/add`. */
export function AddPatientForm({ session, onDone }: { session: MdtSession; onDone: () => void }) {
  const me = useMe();
  const [patientId, setPatientId] = React.useState<string | null>(null);
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

  const onBoard = new Set((board.data?.cases ?? []).map((c) => c.patient_id));
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
    const at = new Date().toISOString();
    create.mutate(
      {
        session: session.id,
        patient_id: patientId,
        service_request_id: intake.data.service_request_id,
        ecog: r.ecog,
        intent: r.intent,
        imaging_recent_checked: r.imaging_recent_checked,
        skipped_fields: r.skipped_fields,
        acknowledged_warnings: r.acknowledged.map((id) => ({ id, by: me.user_id, at })),
        acknowledge: r.acknowledged,
        status: 'nominated',
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
                <IntakeForm key={patientId} prefill={intake.data} submitting={create.isPending} onSubmit={submit} patientId={patientId ?? undefined} />
              ) : null}
              <SourceDrawer evidenceId={sourceId} loadSource={mdtApi.getEvidence} onClose={() => setSourceId(null)} />
            </CitationProvider>
            {create.isError && (
              <p role="alert" className="text-sm text-destructive">{apiErrorMessage(create.error, 'Pacienta se nepodařilo zařadit.')}</p>
            )}
          </div>
        )}
    </>
  );
}

function PatientOption({
  patient,
  onBoard,
  elsewhere,
  onSelect,
}: {
  patient: PatientListItem;
  onBoard: boolean;
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
          {!onBoard && elsewhere && (
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
