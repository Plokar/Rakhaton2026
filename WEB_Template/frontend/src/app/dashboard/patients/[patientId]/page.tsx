'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { FilePlus2 } from 'lucide-react';
import { Page, PageHeader } from '@/components/layout/Page';
import { PageCrumbs } from '@/components/layout/TopBar';
import { Skeleton } from '@/components/shadcn/skeleton';
import { CitationProvider, Citations } from '@/components/mdt/citations';
import { dayLabel } from '@/components/mdt/dates';
import { EcogDifference } from '@/components/mdt/EcogCompare';
import { formatDate } from '@/components/mdt/format';
import { ImportReportSheet } from '@/components/mdt/ImportReportSheet';
import { can, useMe } from '@/components/mdt/me';
import { SourceDrawer } from '@/components/mdt/SourceDrawer';
import { Timeline } from '@/components/mdt/Timeline';
import { TrendChart, withReadableLabel } from '@/components/mdt/TrendChart';
import { Button } from '@/components/ui/button';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, useObservationsQuery, usePatientQuery, useSessionsWithCases, useTimelineQuery } from '@/lib/queries';
import type { EvidenceId } from '@/types/mdt';

const ALL = () => true;

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-card p-5">
      <h2 className="mb-3 text-[15px] font-semibold">{title}</h2>
      {children}
    </section>
  );
}

/**
 * Karta pacienta (ARCH §7.1): diagnózy, TNM v čase, komorbidity, PS lékař vs. pacient, projednání v komisi,
 * časová osa a řady laboratoře / PROMs, vše přímo z IRIS s citacemi (bez AI). Vložení zprávy (BON-7).
 */
export default function PatientPage({ params }: { params: Promise<{ patientId: string }> }) {
  const { patientId } = React.use(params);
  const me = useMe();
  const patient = usePatientQuery(patientId);
  const timeline = useTimelineQuery(patientId);
  const series = useObservationsQuery(patientId);
  const { sessions, detail } = useSessionsWithCases(ALL);
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const [importing, setImporting] = React.useState(false);
  const close = React.useCallback(() => setOpenId(null), []);

  const cases = sessions.flatMap((s) => (detail.get(s.id)?.cases ?? []).filter((c) => c.patient_id === patientId).map((c) => ({ session: s, item: c })));
  const charts = (series.data ?? []).filter((s) => s.points.length >= 2).map(withReadableLabel);
  const d = patient.data;

  return (
    <Page className="max-w-5xl">
      <PageCrumbs items={[{ label: patientId }]} />
      <PageHeader
        title={<span translate="no">{d?.display_name ?? patientId}</span>}
        meta={d?.diagnosis ? <><span translate="no" className="font-medium text-foreground">{d.diagnosis.icd10}</span> {d.diagnosis.text}</> : 'Data přímo z IRIS, bez AI.'}
        actions={
          can.generateBrief(me) && (
            <Button variant="outline" onClick={() => setImporting(true)}>
              <FilePlus2 aria-hidden /> Vložit zprávu
            </Button>
          )
        }
      />

      {patient.isLoading && <Skeleton className="h-48" />}
      {patient.isError && <p role="alert" className="text-sm text-destructive">{apiErrorMessage(patient.error, 'Pacienta se nepodařilo načíst z IRIS.')}</p>}

      <CitationProvider order={[]} activeId={openId} onOpen={setOpenId}>
        {d && (
          <Block title="Diagnózy a stav">
            <div className="grid gap-5 md:grid-cols-2">
              <div>
                <h3 className="mb-1.5 text-sm font-semibold">Diagnózy</h3>
                <ul className="flex flex-col gap-1 text-sm">
                  {d.diagnoses.map((x) => (
                    <li key={x.citation}>
                      <span translate="no" className="mr-1.5 font-medium">{x.icd10}</span>
                      {x.text}
                      {x.stage && <span className="text-muted-foreground"> · {x.stage}</span>}
                      {x.onset && <span className="text-muted-foreground"> · od {formatDate(x.onset)}</span>}
                      <Citations ids={[x.citation]} />
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="mb-1.5 text-sm font-semibold">TNM v čase</h3>
                {d.tnm.length ? (
                  <ul className="flex flex-col gap-1 text-sm">
                    {d.tnm.map((t) => (
                      <li key={t.citation}>
                        <span className="text-muted-foreground">{formatDate(t.date)}</span> <span translate="no">{t.text}</span>
                        <Citations ids={[t.citation]} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">Údaj chybí v podkladech.</p>
                )}
              </div>
              <div>
                <h3 className="mb-1.5 text-sm font-semibold">Komorbidity</h3>
                {d.comorbidities.length ? (
                  <ul className="flex flex-col gap-1 text-sm">
                    {d.comorbidities.map((c) => (
                      <li key={c.citation}>
                        {c.icd10 && <span translate="no" className="mr-1.5 font-medium">{c.icd10}</span>}
                        {c.text}
                        <Citations ids={[c.citation]} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted-foreground">Bez komorbidit v záznamu.</p>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <h3 className="text-sm font-semibold">Výkonnostní stav (ECOG)</h3>
                <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
                  <div>
                    <dt className="text-xs text-muted-foreground">Lékař</dt>
                    <dd>
                      {d.ecog.physician ? (
                        <>
                          <span className="text-lg font-semibold tabular-nums">{d.ecog.physician.value}</span> {formatDate(d.ecog.physician.date)}
                          <Citations ids={[d.ecog.physician.citation]} />
                        </>
                      ) : 'chybí'}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-muted-foreground">Pacient (PROMs)</dt>
                    <dd>
                      {d.ecog.patient ? (
                        <>
                          <span className="text-lg font-semibold tabular-nums">{d.ecog.patient.value}</span> {formatDate(d.ecog.patient.date)}
                          <Citations ids={[d.ecog.patient.citation]} />
                        </>
                      ) : 'chybí'}
                    </dd>
                  </div>
                </dl>
                <EcogDifference ecog={{ physician: d.ecog.physician ?? undefined, patient: d.ecog.patient ?? undefined }} />
              </div>
            </div>
          </Block>
        )}

        {cases.length > 0 && (
          <Block title="Projednání v komisi">
            <ul className="flex flex-col gap-1 text-sm">
              {cases.map(({ session, item }) => (
                <li key={item.id}>
                  <Link href={`/dashboard/cases/${item.id}`} className="font-medium hover:underline hover:underline-offset-4">
                    {session.title}
                  </Link>{' '}
                  <span className="text-muted-foreground">· {dayLabel(session.date)}</span>
                  {item.question && <p className="text-[13px] text-muted-foreground">{item.question}</p>}
                </li>
              ))}
            </ul>
          </Block>
        )}

        <Block title="Časová osa">
          {timeline.isLoading ? (
            <Skeleton className="h-32" />
          ) : timeline.data?.length ? (
            <Timeline events={timeline.data} />
          ) : (
            <p className="text-sm text-muted-foreground">V IRIS nejsou pro pacienta žádné události.</p>
          )}
        </Block>

        {charts.length > 0 && (
          <Block title="Laboratoř, hmotnost a PROMs">
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {charts.map((s) => <TrendChart key={s.code} series={s} />)}
            </div>
          </Block>
        )}

        <SourceDrawer evidenceId={openId} loadSource={mdtApi.getEvidence} onClose={close} />
      </CitationProvider>

      <ImportReportSheet patientId={patientId} open={importing} onClose={() => setImporting(false)} />
    </Page>
  );
}
