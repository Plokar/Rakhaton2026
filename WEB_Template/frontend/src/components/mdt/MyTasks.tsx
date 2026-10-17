'use client';

import * as React from 'react';
import Link from 'next/link';
import { useQueryClient } from '@tanstack/react-query';
import { ListChecks } from 'lucide-react';
import { toast } from 'sonner';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys, useMyTasksQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtTask, TaskStatus } from '@/types/mdt';
import { todayPrague } from './dates';
import { formatDate } from './format';
import { useMe } from './me';

export const TASK_STATUS_LABEL: Record<TaskStatus, string> = {
  requested: 'Zadáno',
  'in-progress': 'Probíhá',
  completed: 'Hotovo',
};

export const isOverdue = (t: MdtTask, today: string) =>
  t.status !== 'completed' && !!t.due_date && t.due_date.slice(0, 10) < today;

/** Smí měnit stav úkolu: předseda, lékař, nebo ten, komu je úkol přiřazený (T-328). Návrh závěru ne. */
export function useCanChangeTask() {
  const me = useMe();
  return (t: MdtTask) =>
    !t.draft && (me?.role === 'mdt_admin' || me?.role === 'mdt_doctor' || (!!t.owner.id && t.owner.id === me?.practitioner_id));
}

/** Změna stavu úkolu v IRIS + obnovení všech seznamů úkolů (sidebar, Úkoly, náhled pacienta). */
export function useChangeTaskStatus() {
  const client = useQueryClient();
  return async (task: MdtTask, status: TaskStatus) => {
    try {
      await mdtApi.updateTask(task.id, status);
      await client.invalidateQueries({ queryKey: queryKeys.tasks });
      toast(`Úkol: ${TASK_STATUS_LABEL[status].toLowerCase()}`, { description: task.description });
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Stav úkolu se nepodařilo uložit.'));
    }
  };
}

/**
 * Vaše úkoly u pacienta (T-328): co komise přidělila přihlášenému lékaři, i z dosud nepotvrzeného závěru.
 * Bez přiřazených úkolů se nic nezobrazí.
 */
export function MyTasks({ patientId }: { patientId: string | null | undefined }) {
  const me = useMe();
  const tasks = useMyTasksQuery(patientId, Boolean(patientId && me?.practitioner_id));
  const canChange = useCanChangeTask();
  const changeStatus = useChangeTaskStatus();
  const today = todayPrague();
  const open = (tasks.data ?? []).filter((t) => t.status !== 'completed');
  if (!open.length) return null;

  return (
    <section aria-labelledby="moje-ukoly" className="rounded-xl border border-primary/30 bg-primary/5 p-3">
      <h3 id="moje-ukoly" className="mb-2 flex items-center gap-1.5 text-sm font-semibold">
        <ListChecks className="h-4 w-4 text-primary" aria-hidden /> Vaše úkoly u pacienta ({open.length})
      </h3>
      <ul className="flex flex-col gap-2">
        {open.map((t) => {
          const late = isOverdue(t, today);
          return (
            <li key={t.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
              <span className="min-w-0 flex-1">
                {t.description}
                <span className="block text-xs text-muted-foreground">
                  {t.due_date && (
                    <span className={cn('tabular-nums', late && 'font-medium text-destructive')}>
                      termín {formatDate(t.due_date)}{late && ' (po termínu)'}
                    </span>
                  )}
                  {t.draft && <span>{t.due_date ? ' · ' : ''}návrh závěru, čeká na potvrzení předsedou</span>}
                  {t.case_id && (
                    <>
                      {' · '}
                      <Link className="underline underline-offset-4 hover:text-foreground" href={`/dashboard/cases/${t.case_id}/record`}>
                        {t.mdt_record ? `záznam ${t.mdt_record}` : 'návrh záznamu'}
                      </Link>
                    </>
                  )}
                </span>
              </span>
              {canChange(t) ? (
                <select
                  aria-label={`Stav úkolu: ${t.description}`}
                  className="h-8 w-fit rounded-lg border border-input bg-card px-2 text-sm"
                  value={t.status}
                  onChange={(e) => changeStatus(t, e.target.value as TaskStatus)}
                >
                  {Object.entries(TASK_STATUS_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
              ) : (
                <span className="text-xs text-muted-foreground">{TASK_STATUS_LABEL[t.status]}</span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
