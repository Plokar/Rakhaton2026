'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { ListChecks } from 'lucide-react';
import { Page } from '@/components/layout/Page';
import { formatDate } from '@/components/mdt/format';
import { can, useMe } from '@/components/mdt/me';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import type { MdtTask, TaskStatus } from '@/types/mdt';

const STATUS_LABEL: Record<TaskStatus, string> = {
  requested: 'Zadáno',
  'in-progress': 'Probíhá',
  completed: 'Hotovo',
};

// Klíč = verze (po změně stavu se seznam načte znovu z IRIS).
const fetchTasks = () => mdtApi.getTasks();

const isOverdue = (t: MdtTask, today: string) => t.status !== 'completed' && !!t.due_date && t.due_date < today;

/** Úkoly po zasedání (FR-P3): úkoly z potvrzených závěrů (FHIR Task v IRIS), stav, termíny a re-MDT. */
export default function MdtTasksPage() {
  return (
    <Page>
      <TasksContent />
    </Page>
  );
}

function TasksContent() {
  const me = useMe();
  const [version, setVersion] = React.useState(0);
  const [statusFilter, setStatusFilter] = React.useState<TaskStatus | 'open' | ''>('open');
  const [patientFilter, setPatientFilter] = React.useState('');
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const { data: tasks, error, loading } = useApiData(fetchTasks, String(version));
  const today = new Date().toISOString().slice(0, 10);

  const patients = [...new Set((tasks ?? []).map((t) => t.patient_id))].sort();
  const shown = (tasks ?? []).filter(
    (t) =>
      (!patientFilter || t.patient_id === patientFilter) &&
      (statusFilter === '' || (statusFilter === 'open' ? t.status !== 'completed' : t.status === statusFilter)),
  );
  const overdue = (tasks ?? []).filter((t) => isOverdue(t, today)).length;
  // Re-MDT po pacientech (z CarePlanu), jen jedno datum na záznam MDT.
  const reMdt = [...new Map((tasks ?? []).filter((t) => t.re_mdt?.date).map((t) => [t.mdt_record, t])).values()];

  const changeStatus = async (task: MdtTask, status: TaskStatus) => {
    setSaveError(null);
    try {
      await mdtApi.updateTask(task.id, status);
      setVersion((v) => v + 1);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Stav úkolu se nepodařilo uložit.');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">Úkoly po zasedání</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Úkoly z potvrzených závěrů komise, jejich stav a termíny opětovného projednání.
          {overdue > 0 && <strong className="ml-1 text-destructive">Po termínu: {overdue}.</strong>}
        </p>
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <label className="flex items-center gap-2">
          Stav
          <select
            className="rounded-md border border-border bg-background px-2 py-1"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as TaskStatus | 'open' | '')}
          >
            <option value="open">Nedokončené</option>
            <option value="">Všechny</option>
            {Object.entries(STATUS_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2">
          Pacient
          <select
            className="rounded-md border border-border bg-background px-2 py-1"
            value={patientFilter}
            onChange={(e) => setPatientFilter(e.target.value)}
          >
            <option value="">Všichni</option>
            {patients.map((pid) => (
              <option key={pid} value={pid}>
                {pid}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <Skeleton className="h-40 w-full" />}
      {error && <p className="text-sm text-destructive">{error}</p>}
      {saveError && <p className="text-sm text-destructive">{saveError}</p>}

      {reMdt.length > 0 && (
        <section aria-label="Plánovaná re-MDT" className="rounded-xl border border-border bg-card p-4">
          <h2 className="text-sm font-bold text-foreground">Plánovaná re-MDT</h2>
          <ul className="mt-2 space-y-1 text-sm">
            {reMdt.map((t) => (
              <li key={t.mdt_record}>
                <strong>{t.patient_id}</strong> · {formatDate(t.re_mdt?.date)} {t.re_mdt?.reason && `· ${t.re_mdt.reason}`}
              </li>
            ))}
          </ul>
        </section>
      )}

      {tasks && shown.length === 0 && (
        <EmptyState
          icon={<ListChecks className="h-6 w-6" />}
          title={tasks.length === 0 ? 'Zatím žádné úkoly' : 'Filtru neodpovídá žádný úkol'}
          description="Úkoly vzniknou po potvrzení závěru komise."
        />
      )}

      {shown.length > 0 && (
        <ul className="space-y-2.5" aria-label="Úkoly">
          {shown.map((t) => (
            <li key={t.id} className="rounded-xl border border-border bg-card p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <p className="font-semibold text-foreground">{t.description}</p>
                  <p className="text-xs text-muted-foreground">
                    {t.patient_id} · {t.owner.name}
                    {t.due_date && (
                      <>
                        {' · termín '}
                        <span className={isOverdue(t, today) ? 'font-bold text-destructive' : undefined}>
                          {formatDate(t.due_date)}
                          {isOverdue(t, today) && ' (po termínu)'}
                        </span>
                      </>
                    )}
                    {' · '}
                    {t.case_id ? (
                      <Link className="underline" href={`/dashboard/cases/${t.case_id}/record`}>
                        záznam {t.mdt_record}
                      </Link>
                    ) : (
                      `záznam ${t.mdt_record}`
                    )}
                  </p>
                </div>
                {can.generateBrief(me) ? (
                  <select
                    aria-label={`Stav úkolu ${t.id}`}
                    className="rounded-md border border-border bg-background px-2 py-1 text-sm"
                    value={t.status}
                    onChange={(e) => changeStatus(t, e.target.value as TaskStatus)}
                  >
                    {Object.entries(STATUS_LABEL).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="text-sm font-semibold">{STATUS_LABEL[t.status]}</span>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
