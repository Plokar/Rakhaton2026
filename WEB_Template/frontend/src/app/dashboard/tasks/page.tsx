'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { ListChecks } from 'lucide-react';
import { Page, PageHeader } from '@/components/layout/Page';
import { Skeleton } from '@/components/shadcn/skeleton';
import { ToggleGroup, ToggleGroupItem } from '@/components/shadcn/toggle-group';
import { formatDate } from '@/components/mdt/format';
import { useMe } from '@/components/mdt/me';
import { todayPrague } from '@/components/mdt/dates';
import { EmptyState } from '@/components/ui/empty-state';
import { isOverdue, TASK_STATUS_LABEL as STATUS_LABEL, useCanChangeTask, useChangeTaskStatus } from '@/components/mdt/MyTasks';
import { apiErrorMessage, useMyTasksQuery, useTasksQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { TaskStatus } from '@/types/mdt';

type Filter = 'open' | 'all' | TaskStatus;
type Whose = 'mine' | 'all';

/** Úkoly po zasedání (FR-P3): úkoly z potvrzených závěrů (FHIR Task v IRIS), stav, termíny a re-MDT. */
export default function MdtTasksPage() {
  const me = useMe();
  const everyone = useTasksQuery();
  const mine = useMyTasksQuery(null, Boolean(me?.practitioner_id));
  const [filter, setFilter] = React.useState<Filter>('open');
  // T-328: lékař začíná u svých úkolů (i z návrhu závěru), předseda u všech
  const [whoseChoice, setWhose] = React.useState<Whose | null>(null);
  const whose: Whose = whoseChoice ?? (me?.role === 'mdt_admin' || !me?.practitioner_id ? 'all' : 'mine');
  const tasks = whose === 'mine' ? mine : everyone;
  const [patient, setPatient] = React.useState('');
  const today = todayPrague();
  const canChange = useCanChangeTask();
  const changeStatus = useChangeTaskStatus();

  const all = tasks.data ?? [];
  const patients = [...new Set(all.map((t) => t.patient_id))].sort();
  const shown = all
    .filter((t) => (!patient || t.patient_id === patient) && (filter === 'all' || (filter === 'open' ? t.status !== 'completed' : t.status === filter)))
    .toSorted((a, b) => (a.due_date ?? '9999').localeCompare(b.due_date ?? '9999'));
  const overdue = all.filter((t) => isOverdue(t, today)).length;
  // Re-MDT po pacientech (z CarePlanu), jen jedno datum na záznam MDT.
  const reMdt = [...new Map(all.filter((t) => t.re_mdt?.date && t.mdt_record).map((t) => [t.mdt_record, t])).values()];

  return (
    <Page className="max-w-5xl">
      <PageHeader
        title="Úkoly po zasedání"
        meta={
          <>
            Úkoly z potvrzených závěrů komise a termíny opětovného projednání.
            {overdue > 0 && <span className="ml-1 font-medium text-destructive">Po termínu: {overdue}.</span>}
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        {me?.practitioner_id && (
          <ToggleGroup value={[whose]} onValueChange={(v) => v[0] && setWhose(v[0] as Whose)} variant="outline" spacing={0} aria-label="Čí úkoly">
            <ToggleGroupItem value="mine">Moje</ToggleGroupItem>
            <ToggleGroupItem value="all">Všech</ToggleGroupItem>
          </ToggleGroup>
        )}
        <ToggleGroup value={[filter]} onValueChange={(v) => v[0] && setFilter(v[0] as Filter)} variant="outline" spacing={0} aria-label="Stav úkolů">
          <ToggleGroupItem value="open">Nedokončené</ToggleGroupItem>
          <ToggleGroupItem value="completed">Hotové</ToggleGroupItem>
          <ToggleGroupItem value="all">Všechny</ToggleGroupItem>
        </ToggleGroup>
        {patients.length > 1 && (
          <label className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Pacient</span>
            <select className="h-8 rounded-lg border border-input bg-card px-2 text-sm" value={patient} onChange={(e) => setPatient(e.target.value)}>
              <option value="">Všichni</option>
              {patients.map((pid) => <option key={pid} value={pid}>{pid}</option>)}
            </select>
          </label>
        )}
      </div>

      {tasks.isLoading && <Skeleton className="h-40" />}
      {tasks.isError && <p role="alert" className="text-sm text-destructive">{apiErrorMessage(tasks.error, 'Úkoly se nepodařilo načíst.')}</p>}

      {tasks.data && shown.length === 0 && (
        <EmptyState
          icon={<ListChecks aria-hidden />}
          title={all.length === 0 ? 'Zatím žádné úkoly' : 'Filtru neodpovídá žádný úkol'}
          description={whose === 'mine'
            ? 'Úkoly, které vám komise přidělí v závěru, se tu objeví hned (návrh) a po potvrzení se zapíšou do IRIS.'
            : 'Úkoly vzniknou po potvrzení závěru komise a zapíšou se do IRIS.'}
        />
      )}

      {shown.length > 0 && (
        <ul className="divide-y divide-border overflow-hidden rounded-xl border border-border bg-card" aria-label="Úkoly">
          {shown.map((t) => {
            const late = isOverdue(t, today);
            return (
              <li key={t.id} className="grid gap-x-4 gap-y-1 px-4 py-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{t.description}</p>
                  <p className="text-[13px] text-muted-foreground">
                    <span translate="no" className="font-medium text-foreground">{t.patient_id}</span> · {t.owner.name}
                    {t.due_date && (
                      <>
                        {' · termín '}
                        <span className={cn('tabular-nums', late && 'font-medium text-destructive')}>
                          {formatDate(t.due_date)}
                          {late && ' (po termínu)'}
                        </span>
                      </>
                    )}
                    {' · '}
                    {t.case_id ? (
                      <Link className="underline underline-offset-4 hover:text-foreground" href={`/dashboard/cases/${t.case_id}/record`}>
                        {t.mdt_record ? `záznam ${t.mdt_record}` : 'návrh záznamu'}
                      </Link>
                    ) : (
                      `záznam ${t.mdt_record}`
                    )}
                    {t.draft && <span> · návrh závěru, čeká na potvrzení</span>}
                  </p>
                </div>
                {canChange(t) ? (
                  <select
                    aria-label={`Stav úkolu: ${t.description}`}
                    className="h-8 w-fit rounded-lg border border-input bg-card px-2 text-sm"
                    value={t.status}
                    onChange={(e) => changeStatus(t, e.target.value as TaskStatus)}
                  >
                    {Object.entries(STATUS_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                  </select>
                ) : (
                  <span className="text-sm text-muted-foreground">{STATUS_LABEL[t.status]}</span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {reMdt.length > 0 && (
        <section aria-labelledby="re-mdt" className="flex flex-col gap-2">
          <h2 id="re-mdt" className="text-base font-semibold">Plánovaná re-MDT</h2>
          <ul className="flex flex-col gap-1 text-sm">
            {reMdt.map((t) => (
              <li key={t.mdt_record}>
                <span translate="no" className="font-medium">{t.patient_id}</span>{' '}
                <span className="tabular-nums">{formatDate(t.re_mdt?.date)}</span>
                {t.re_mdt?.reason && <span className="text-muted-foreground"> · {t.re_mdt.reason}</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </Page>
  );
}
