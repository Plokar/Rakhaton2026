'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { Page } from '@/components/layout/Page';
import { CitationProvider } from '@/components/mdt/citations';
import { apiDataSource } from '@/components/mdt/data-source';
import { IntakeForm, type IntakeResult } from '@/components/mdt/IntakeForm';
import { can, useMe } from '@/components/mdt/me';
import { SourceDrawer } from '@/components/mdt/SourceDrawer';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import { cn } from '@/lib/utils';
import type { EvidenceId, IntakePrefill } from '@/types/mdt';

const fetchPatients = () => mdtApi.getPatients();
const fetchIntake = (pid: string): Promise<IntakePrefill | null> => (pid ? mdtApi.getIntake(pid) : Promise.resolve(null));

/** Zařazení pacienta do boardu (FR-P4, ARCH §7.1): výběr pacienta z IRIS a formulář s kontrolou úplnosti. */
export default function AddCasePage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = React.use(params);
  return (
    <Page>
      <AddCaseContent sessionId={sessionId} />
    </Page>
  );
}

function AddCaseContent({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const me = useMe();
  const [patientId, setPatientId] = React.useState('');
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const close = React.useCallback(() => setOpenId(null), []);
  const patients = useApiData(fetchPatients, '');
  const intake = useApiData(fetchIntake, patientId);

  const submit = async (r: IntakeResult) => {
    if (!intake.data || !me) return;
    setSubmitting(true);
    setError(null);
    const at = new Date().toISOString();
    try {
      await mdtApi.createCase({
        session: Number(sessionId),
        patient_id: patientId,
        service_request_id: intake.data.service_request_id,
        ecog: r.ecog,
        intent: r.intent,
        imaging_recent_checked: r.imaging_recent_checked,
        skipped_fields: r.skipped_fields,
        acknowledged_warnings: r.acknowledged.map((id) => ({ id, by: me.user_id, at })),
        acknowledge: r.acknowledged,
        status: 'nominated',
      });
      router.push(`/dashboard/mdt/${encodeURIComponent(sessionId)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Zařazení se nepodařilo.');
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Link
        href={`/dashboard/mdt/${encodeURIComponent(sessionId)}`}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Agenda
      </Link>
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Zařadit pacienta</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Údaje se předvyplní z IRIS s citací zdroje. Chybějící údaj doplňte, nebo přeskočte; varování můžete vzít na vědomí.
        </p>
      </div>

      {me && !can.generateBrief(me) && (
        <p className="rounded-lg border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground">
          Pacienta zařazuje zadávající lékař nebo předseda komise.
        </p>
      )}

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="mb-2 text-sm font-semibold text-foreground">Pacient</h2>
        {patients.loading && <Skeleton className="h-20 w-full" />}
        {patients.error && <p className="text-sm text-destructive">{patients.error}</p>}
        <ul className="grid gap-2 sm:grid-cols-2">
          {(patients.data ?? []).map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => setPatientId(p.id)}
                aria-pressed={patientId === p.id}
                className={cn(
                  'w-full rounded-lg border px-3 py-2 text-left transition',
                  patientId === p.id ? 'border-primary bg-primary/10' : 'border-border hover:bg-accent',
                )}
              >
                <span className="block text-sm font-semibold text-foreground">{p.display_name}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {p.diagnosis ? `${p.diagnosis.icd10} ${p.diagnosis.text}` : 'bez onkologické diagnózy'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>

      {patientId && (
        <CitationProvider order={[]} activeId={openId} onOpen={setOpenId}>
          <section className="rounded-xl border border-border bg-card p-4">
            {intake.loading && <Skeleton className="h-64 w-full" />}
            {intake.error && <p className="text-sm text-destructive">{intake.error}</p>}
            {intake.data && (
              <IntakeForm key={patientId} prefill={intake.data} submitting={submitting} onSubmit={submit} />
            )}
            {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
          </section>
          <SourceDrawer evidenceId={openId} loadSource={apiDataSource.loadSource} onClose={close} />
        </CitationProvider>
      )}
    </div>
  );
}
