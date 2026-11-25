'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Page, PageHeader } from '@/components/layout/Page';
import { PageCrumb } from '@/components/layout/TopBar';
import { Input } from '@/components/shadcn/input';
import { Skeleton } from '@/components/shadcn/skeleton';
import { can, useMe } from '@/components/mdt/me';
import { EmptyState } from '@/components/ui/empty-state';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import type { CommitteeStats, CommitteeStatsBlock } from '@/types/mdt';

const MONTHS = ['led', 'úno', 'bře', 'dub', 'kvě', 'čvn', 'čvc', 'srp', 'zář', 'říj', 'lis', 'pro'];
const monthLabel = (month: string) => `${MONTHS[Number(month.slice(5, 7)) - 1]} ${month.slice(2, 4)}`;
/** 1 den, 2–4 dny, 0 a 5+ dní, desetinné „dne“ (1,5 dne). */
const days = (n: number) =>
  `${n.toLocaleString('cs-CZ')} ${!Number.isInteger(n) ? 'dne' : n === 1 ? 'den' : n >= 2 && n <= 4 ? 'dny' : 'dní'}`;
const percent = (part: number, whole: number) => (whole ? `${Math.round((part / whole) * 100)} %` : '–');

/**
 * Statistiky komise (T-384): kolik pacientů komise projednala, kolik je potvrzených a vrácených k doplnění,
 * jak rychle od zařazení po potvrzení a jak často se závěr odchýlil od guidelines. Jen počty, žádní pacienti.
 */
export default function StatsPage() {
  const me = useMe();
  const [range, setRange] = React.useState<{ from: string; to: string }>({ from: '', to: '' });
  const stats = useQuery({ queryKey: ['stats', range], queryFn: () => mdtApi.getStats(range), enabled: can.manageBoards(me) || Boolean(me?.is_manager) });

  return (
    <Page>
      <PageCrumb>Statistiky</PageCrumb>
      <PageHeader
        title="Statistiky komise"
        meta="Počty případů podle termínu zasedání, bez údajů o pacientech"
        actions={
          <div className="flex flex-wrap items-end gap-2 text-sm">
            <label className="flex flex-col gap-1">
              <span className="text-[13px] text-muted-foreground">Od</span>
              <Input type="date" value={range.from} onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} className="w-40" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[13px] text-muted-foreground">Do</span>
              <Input type="date" value={range.to} onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} className="w-40" />
            </label>
          </div>
        }
      />
      {stats.isLoading ? (
        <div className="grid gap-3 sm:grid-cols-4" aria-busy="true">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24" />)}
        </div>
      ) : stats.isError ? (
        <p role="alert" className="text-sm text-destructive">{apiErrorMessage(stats.error, 'Statistiky se nepodařilo načíst.')}</p>
      ) : !stats.data || stats.data.total.cases === 0 ? (
        <EmptyState title="V tomto období nejsou žádné případy" description="Zkuste jiné období." />
      ) : (
        <StatsBody data={stats.data} />
      )}
    </Page>
  );
}

function Tile({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <p className="text-[13px] text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {note && <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>}
    </div>
  );
}

function StatsBody({ data }: { data: CommitteeStats }) {
  const t = data.total;
  const decided = t.guideline_compliance.compliant + t.guideline_compliance.deviation + t.guideline_compliance.unknown;
  const voted = data.votes.agree + data.votes.disagree;
  return (
    <div className="flex flex-col gap-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Tile label="Projednaní pacienti" value={String(t.cases)} note={`${t.sessions} zasedání`} />
        <Tile label="Potvrzené závěry" value={String(t.confirmed)} note={percent(t.confirmed, t.cases) + ' případů'} />
        <Tile
          label="Od zařazení po potvrzení"
          value={t.median_days_to_confirm === null ? '–' : days(t.median_days_to_confirm)}
          note="medián"
        />
        <Tile
          label="Soulad s guidelines"
          value={percent(t.guideline_compliance.compliant, decided)}
          note={`odchylka ${t.guideline_compliance.deviation}, neuvedeno ${t.guideline_compliance.unknown}`}
        />
        <Tile label="Vráceno k doplnění" value={String(t.returned)} note={percent(t.returned, t.cases) + ' případů'} />
        <Tile label="Souhlas přítomných" value={percent(data.votes.agree, voted)} note={`${data.votes.disagree} nesouhlasů z ${voted} hlasů`} />
      </div>
      {data.by_month.length > 1 && <MonthChart months={data.by_month} />}
      <CommitteeTable rows={data.by_committee} />
    </div>
  );
}

/** Jedna řada (případy za měsíc): jeden odstín, popisek v nadpisu, hodnota při najetí a v tabulce pod grafem. */
function MonthChart({ months }: { months: CommitteeStats['by_month'] }) {
  const max = Math.max(...months.map((m) => m.cases), 1);
  return (
    <section aria-labelledby="mesice-nadpis" className="rounded-xl border border-border bg-card p-4">
      <h2 id="mesice-nadpis" className="text-sm font-semibold">Pacienti podle měsíce zasedání</h2>
      <div className="mt-3 flex h-40 items-end gap-0.5 border-b border-border" role="img" aria-label={months.map((m) => `${monthLabel(m.month)}: ${m.cases}`).join(', ')}>
        {months.map((m) => (
          <div key={m.month} className="group relative flex h-full flex-1 items-end justify-center">
            <div
              className="w-full max-w-10 rounded-t-[4px] bg-primary/80 transition-colors group-hover:bg-primary"
              style={{ height: `${Math.max(2, (m.cases / max) * 100)}%` }}
            />
            <span className="pointer-events-none absolute -top-6 hidden rounded bg-popover px-1.5 py-0.5 text-xs tabular-nums text-popover-foreground shadow ring-1 ring-border group-hover:block">
              {m.cases}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-1 flex gap-0.5">
        {months.map((m) => (
          <span key={m.month} className="flex-1 text-center text-[11px] text-muted-foreground">{monthLabel(m.month)}</span>
        ))}
      </div>
    </section>
  );
}

function CommitteeTable({ rows }: { rows: (CommitteeStatsBlock & { name: string })[] }) {
  return (
    <section aria-labelledby="komise-nadpis" className="overflow-x-auto rounded-xl border border-border bg-card">
      <h2 id="komise-nadpis" className="px-4 pt-4 text-sm font-semibold">Podle komisí</h2>
      <table className="mt-2 w-full min-w-[40rem] text-sm">
        <thead className="text-left text-[13px] text-muted-foreground">
          <tr className="border-b border-border">
            <th className="px-4 py-2 font-medium">Komise</th>
            <th className="px-2 py-2 text-right font-medium">Pacienti</th>
            <th className="px-2 py-2 text-right font-medium">Zasedání</th>
            <th className="px-2 py-2 text-right font-medium">Potvrzeno</th>
            <th className="px-2 py-2 text-right font-medium">Vráceno</th>
            <th className="px-2 py-2 text-right font-medium">Medián dní</th>
            <th className="px-4 py-2 text-right font-medium">Soulad s guidelines</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const decided = r.guideline_compliance.compliant + r.guideline_compliance.deviation + r.guideline_compliance.unknown;
            return (
              <tr key={r.name} className="border-b border-border last:border-0">
                <td className="px-4 py-2">{r.name}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.cases}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.sessions}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.confirmed}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.returned}</td>
                <td className="px-2 py-2 text-right tabular-nums">{r.median_days_to_confirm ?? '–'}</td>
                <td className="px-4 py-2 text-right tabular-nums">{percent(r.guideline_compliance.compliant, decided)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
