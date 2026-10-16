'use client';

import * as React from 'react';
import {
  Activity,
  ClipboardList,
  FileText,
  FlaskConical,
  Microscope,
  Pill,
  ScanLine,
  Stethoscope,
  UsersRound,
  type LucideIcon,
} from 'lucide-react';
import type { TimelineEvent } from '@/types/mdt';
import { Citations } from './citations';
import { formatDate } from './format';

const TYPE_META: Record<TimelineEvent['type'], { label: string; icon: LucideIcon }> = {
  diagnosis: { label: 'Diagnóza', icon: Stethoscope },
  procedure: { label: 'Výkon', icon: Activity },
  medication: { label: 'Léčba', icon: Pill },
  imaging: { label: 'Zobrazení', icon: ScanLine },
  pathology: { label: 'Patologie', icon: Microscope },
  lab: { label: 'Laboratoř', icon: FlaskConical },
  proms: { label: 'Dotazník pacienta', icon: ClipboardList },
  mdt: { label: 'MDT', icon: UsersRound },
  document: { label: 'Zpráva', icon: FileText },
};

type Row = {
  date: string;
  type: TimelineEvent['type'];
  regimen: string | null;
  labels: string[];
  citations: string[];
};

/** „oxaliplatina (FOLFOX + bevacizumab, podání 8 – redukce …)“ → „FOLFOX + bevacizumab, podání 8“. */
const regimenOf = (label: string) => label.match(/\(([^()]*?podání \d+)/)?.[1] ?? null;

/** Podání léků jednoho režimu ve stejný den sloučí do jednoho řádku (FOLFOX + bevacizumab = 4 léky). */
function groupRows(events: TimelineEvent[]): Row[] {
  const rows: Row[] = [];
  for (const e of events) {
    const regimen = e.type === 'medication' ? regimenOf(e.label) : null;
    const last = rows[rows.length - 1];
    if (regimen && last?.regimen === regimen && last.date === e.date) {
      last.labels.push(e.label);
      last.citations.push(e.citation);
    } else {
      rows.push({ date: e.date, type: e.type, regimen, labels: [e.label], citations: [e.citation] });
    }
  }
  return rows;
}

/** Sloučený řádek: režim, počet léků a poznámky k jednotlivým lékům (např. redukce dávky). */
function rowLabel(row: Row): string {
  if (row.labels.length === 1 || !row.regimen) return row.labels.join('; ');
  const count = `${row.labels.length} ${row.labels.length >= 5 ? 'léků' : 'léky'}`;
  const notes = row.labels
    .map((l) => {
      const note = l.match(/podání \d+ – (.+)\)$/)?.[1];
      return note ? `${l.split(' (')[0]}: ${note}` : null;
    })
    .filter(Boolean);
  return `${row.regimen} (${count})${notes.length ? ` · ${notes.join('; ')}` : ''}`;
}

/** Časová osa nemoci a léčby z IRIS (FR-A3): každá událost s citací zdroje. */
export function Timeline({ events }: { events: TimelineEvent[] }) {
  const [showAll, setShowAll] = React.useState(false);
  const rows = React.useMemo(() => groupRows(events), [events]);
  const visible = showAll ? rows : rows.filter((r) => r.type !== 'medication' && r.type !== 'lab');
  const hidden = rows.length - visible.length;

  return (
    <div>
      <ol className="relative space-y-2 border-l border-border pl-4">
        {visible.map((r) => {
          const meta = TYPE_META[r.type];
          const Icon = meta.icon;
          return (
            <li key={`${r.date}-${r.citations[0]}`} className="relative">
              <span className="absolute -left-[1.4rem] top-0.5 flex h-5 w-5 items-center justify-center rounded-full border border-border bg-card">
                <Icon className="h-3 w-3 text-muted-foreground" aria-hidden />
              </span>
              <p className="text-[11px] text-muted-foreground">
                {formatDate(r.date)} · {meta.label}
              </p>
              <p className="text-sm text-foreground">
                {rowLabel(r)}
                <Citations ids={r.citations} />
              </p>
            </li>
          );
        })}
      </ol>
      {(hidden > 0 || showAll) && (
        <button
          type="button"
          onClick={() => setShowAll(!showAll)}
          className="mt-2 text-xs font-medium text-primary hover:underline"
        >
          {showAll ? 'Skrýt léčbu a laboratoř' : `Zobrazit i léčbu a laboratoř (${hidden})`}
        </button>
      )}
    </div>
  );
}
