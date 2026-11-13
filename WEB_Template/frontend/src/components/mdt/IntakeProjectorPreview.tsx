'use client';

import { MonitorUp } from 'lucide-react';
import { useMyTemplateLayout, useSessionQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { IntakePrefill, MdtCase, MdtSession, PatientListItem, ProjectorLayout } from '@/types/mdt';
import { areaForIcd10 } from './fact-layout';
import type { IntakeChoice } from './IntakeForm';
import { useMe } from './me';
import { CaseQuickViewProjector, useQuickViewSources } from './quick-view';

/** Případ, který ještě neexistuje: záporné ID se s žádným skutečným nepotká. */
const DRAFT_CASE = -1;

/**
 * Živý náhled okna pro projektor při zařazení (T-345): tak, jak ho uvidí komise. Bere ECOG, záměr C/P a rozložení
 * z formuláře; bez úpravy platí šablona zadávajícího (moje, u dokončení nominace toho, kdo nominoval). Údaje jsou
 * z IRIS jako v okně; semafor postupů a anamnéza se doplní až u případu (soulad i podklad se počítají u něj).
 */
export function IntakeProjectorPreview({
  session,
  patient,
  intake,
  choice,
  layout,
  className,
}: {
  session: MdtSession;
  patient: PatientListItem;
  intake: IntakePrefill;
  /** `null` = ECOG ani záměr lékař ještě neměnil: předvyplnění z IRIS. */
  choice: IntakeChoice | null;
  /** Okno pro projektor z formuláře (i údaje doplněné z karty). */
  layout: ProjectorLayout;
  className?: string;
}) {
  const me = useMe();
  const board = useSessionQuery(session.id);
  const pending = board.data?.cases.find((c) => c.patient_id === patient.id && (c.status === 'nominated' || c.status === 'returned')) ?? null;
  const base = useQuickViewSources({ sessionId: session.id, caseId: pending?.id ?? null, patientId: patient.id });
  const mine = useMyTemplateLayout(areaForIcd10(patient.diagnosis?.icd10));
  const caseId = pending?.id ?? DRAFT_CASE;

  let sources = base;
  if (board.data) {
    const item: MdtCase = {
      ...(pending ?? {}),
      id: caseId,
      session: session.id,
      patient_id: patient.id,
      service_request_id: intake.service_request_id,
      ecog: choice ? choice.ecog : intake.ecog_physician?.value ?? null,
      intent: choice ? choice.intent : intake.intent_prefill ?? null,
      imaging_recent_checked: pending?.imaging_recent_checked ?? false,
      skipped_fields: pending?.skipped_fields ?? [],
      acknowledged_warnings: pending?.acknowledged_warnings ?? [],
      status: pending?.status ?? 'nominated',
      question: pending?.question ?? patient.mdt_question ?? undefined,
      patient: pending?.patient ?? patient,
      projector_layout: layout,
      requester_layout: pending ? pending.requester_layout ?? null : mine ?? null,
      created_by: pending?.created_by ?? (me ? { user_id: me.user_id, name: me.name } : undefined),
    };
    const cases = [...board.data.cases.filter((c) => c.id !== pending?.id), item];
    sources = { ...base, session: { ...base.session, data: { ...board.data, cases } } };
  }

  return (
    <aside
      aria-label="Náhled okna pro projektor"
      className={cn('flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-background shadow-[0_12px_32px_-12px_rgb(15_23_42/0.25)]', className)}
    >
      <header className="flex shrink-0 items-start gap-2 border-b border-border bg-card px-3 py-2">
        <MonitorUp className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
        <div className="min-w-0">
          <h2 className="text-[13px] font-semibold leading-tight">Náhled okna pro projektor</h2>
          <p className="text-xs text-muted-foreground">Tak ho uvidí komise. Mění se s ECOG, záměrem C/P a úpravou okna.</p>
        </div>
      </header>
      <CaseQuickViewProjector sources={sources} caseId={caseId} titleAs="h2" className="min-h-0 flex-1" />
    </aside>
  );
}
