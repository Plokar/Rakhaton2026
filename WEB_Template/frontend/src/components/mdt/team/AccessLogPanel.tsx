'use client';

import * as React from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, useAllUsersQuery } from '@/lib/queries';
import type { AccessAction, AccessLogFilters } from '@/types/mdt';
import { formatDate } from '../format';

const ACTION_LABEL: Record<AccessAction, string> = {
  view: 'zobrazení', export: 'export', write: 'zápis', ai: 'dotaz na AI',
};
const selectClass = 'h-9 rounded-lg border border-input bg-card px-2 text-sm';

/**
 * Záznam přístupů k pacientům (T-370): kdo kdy otevřel kterého pacienta, stáhl export nebo zapsal.
 * Jen správce MDT; ukládají se jen ID (Pxx, případ), nikdy jméno ani RČ. Zobrazení stejného pacienta
 * stejným lékařem se zapisuje nejvýš jednou za 5 minut.
 */
export function AccessLogPanel() {
  const [filters, setFilters] = React.useState<AccessLogFilters>({ patient: '', user: '', action: '', page: 1 });
  const [patientInput, setPatientInput] = React.useState('');
  const users = useAllUsersQuery(true);
  const log = useQuery({
    queryKey: ['access-log', filters],
    queryFn: () => mdtApi.getAccessLog(filters),
    placeholderData: keepPreviousData,
  });
  const set = (next: Partial<AccessLogFilters>) => setFilters((f) => ({ ...f, ...next, page: next.page ?? 1 }));
  const pages = log.data ? Math.max(1, Math.ceil(log.data.count / log.data.page_size)) : 1;

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">
        Kdo kdy otevřel kterého pacienta, stáhl export nebo zapsal. Opakované zobrazení stejného pacienta se zapisuje
        nejvýš jednou za 5 minut. Záznam nejde upravit ani smazat.
      </p>
      <form
        className="flex flex-wrap items-end gap-2"
        onSubmit={(e) => { e.preventDefault(); set({ patient: patientInput.trim() }); }}
      >
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Pacient
          <Input value={patientInput} onChange={(e) => setPatientInput(e.target.value)} placeholder="P03" className="h-9 w-28" />
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Lékař
          <select className={selectClass} value={filters.user ?? ''}
            onChange={(e) => set({ user: e.target.value ? Number(e.target.value) : '' })}>
            <option value="">všichni</option>
            {users.data?.map((u) => <option key={u.user_id} value={u.user_id}>{u.name}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-muted-foreground">
          Akce
          <select className={selectClass} value={filters.action ?? ''}
            onChange={(e) => set({ action: e.target.value as AccessAction | '' })}>
            <option value="">všechny</option>
            {(Object.keys(ACTION_LABEL) as AccessAction[]).map((a) => <option key={a} value={a}>{ACTION_LABEL[a]}</option>)}
          </select>
        </label>
        <Button type="submit" variant="outline" size="sm" className="h-9">Filtrovat</Button>
      </form>

      {log.isLoading ? (
        <div className="flex flex-col gap-2" aria-busy="true">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-10" />)}</div>
      ) : log.isError ? (
        <p role="alert" className="text-sm text-destructive">{apiErrorMessage(log.error, 'Záznam přístupů se nepodařilo načíst.')}</p>
      ) : !log.data?.results.length ? (
        <p className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
          Pro tento výběr zatím žádné přístupy.
        </p>
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-border bg-card">
            <table className="w-full min-w-[44rem] text-sm">
              <caption className="sr-only">Záznam přístupů k pacientům</caption>
              <thead>
                <tr className="border-b border-border text-left text-xs text-muted-foreground">
                  <th scope="col" className="px-4 py-2.5 font-medium">Kdy</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Lékař</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Pacient</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Akce</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Výsledek</th>
                  <th scope="col" className="px-4 py-2.5 font-medium">Adresa</th>
                </tr>
              </thead>
              <tbody>
                {log.data.results.map((e) => (
                  <tr key={e.id} className="border-b border-border last:border-0">
                    <td className="whitespace-nowrap px-4 py-2 tabular-nums">{formatDate(e.created_at)}</td>
                    <td className="px-4 py-2">{e.user_name || e.username || '—'}</td>
                    <td className="px-4 py-2 font-medium">
                      {e.patient_id || (e.session_id ? `zasedání ${e.session_id}` : '—')}
                    </td>
                    <td className="px-4 py-2">{ACTION_LABEL[e.action]}</td>
                    <td className={e.status >= 400 ? 'px-4 py-2 text-destructive' : 'px-4 py-2 text-muted-foreground'}>
                      {e.status === 403 ? 'odmítnuto' : e.status >= 400 ? `chyba ${e.status}` : 'ok'}
                    </td>
                    <td className="max-w-[16rem] truncate px-4 py-2 font-mono text-xs text-muted-foreground" title={e.path}>{e.path}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between gap-2 text-sm text-muted-foreground">
            <span>{log.data.count} záznamů · strana {log.data.page} z {pages}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={log.data.page <= 1} onClick={() => set({ page: log.data.page - 1 })}>
                Novější
              </Button>
              <Button variant="outline" size="sm" disabled={log.data.page >= pages} onClick={() => set({ page: log.data.page + 1 })}>
                Starší
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
