'use client';

import * as React from 'react';
import Link from 'next/link';
import { ChevronRight, FileArchive, FileDown, FileJson, UsersRound } from 'lucide-react';
import { buttonVariants } from '@/components/shadcn/button';
import { exportUrl } from '@/lib/mdt-api';
import { cn } from '@/lib/utils';
import type { BoardRecord, BoardRecordAttendee, BoardRecordCase } from '@/types/mdt';
import { dayLabel, timeLabel } from './dates';
import { formatDate } from './format';
import { ROLE_META } from './roles';

const roleLabel = (role: BoardRecordAttendee['role']) =>
  role === 'chair' ? 'předseda' : role && role in ROLE_META ? ROLE_META[role].label.toLowerCase() : null;

/** Kdo je pacient pro předsedu: jméno z IRIS, jinak maskované RČ, jinak hlavička bez identity. */
const identity = (c: BoardRecordCase) => c.name ?? c.rc ?? c.display_name;

function DecisionState({ c }: { c: BoardRecordCase }) {
  if (c.decision?.status === 'confirmed') {
    return (
      <span className="text-emerald-800 dark:text-emerald-300">
        potvrzeno{c.decision.confirmed_at ? ` ${formatDate(c.decision.confirmed_at.slice(0, 16))}` : ''}
      </span>
    );
  }
  if (c.decision) return <span className="text-amber-800 dark:text-amber-300">závěr nepotvrzen (návrh)</span>;
  return <span className="text-muted-foreground">bez závěru</span>;
}

/**
 * Pacienti boardu se stažením výstupů (T-333): na řádku ID, jméno nebo maskované RČ, diagnóza, stav závěru,
 * PDF a FHIR document Bundle. FHIR jen u potvrzeného závěru, PDF i u návrhu.
 */
export function BoardOutputs({ record, className }: { record: BoardRecord; className?: string }) {
  if (record.cases.length === 0) {
    return <p className={cn('text-sm text-muted-foreground', className)}>Na boardu nebyl žádný pacient.</p>;
  }
  return (
    <ul className={cn('divide-y divide-border rounded-lg border border-border bg-card', className)}>
      {record.cases.map((c) => (
        <li key={c.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-3 py-2.5">
          <div className="min-w-0 flex-1 basis-56">
            <p className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <Link href={`/dashboard/cases/${c.id}`} translate="no" className="font-semibold hover:underline hover:underline-offset-4">
                {c.patient_id}
              </Link>
              <span className="font-medium">{identity(c)}</span>
              {c.name && c.rc && <span className="text-xs tabular-nums text-muted-foreground">RČ {c.rc}</span>}
            </p>
            <p className="truncate text-xs text-muted-foreground">
              {c.diagnosis ? <span translate="no">{c.diagnosis.icd10}</span> : null}
              {c.diagnosis ? ` ${c.diagnosis.text} · ` : ''}
              <DecisionState c={c} />
              {c.decision?.record_id && <span translate="no"> · {c.decision.record_id}</span>}
            </p>
          </div>
          <div className="flex shrink-0 gap-1.5">
            {c.exports.pdf ? (
              <a href={exportUrl.pdf(c.id)} className={buttonVariants({ variant: 'outline' })} aria-label={`PDF závěru ${c.patient_id}`}>
                <FileDown aria-hidden /> PDF
              </a>
            ) : (
              <span className={cn(buttonVariants({ variant: 'outline' }), 'pointer-events-none opacity-45')} title="Pacient nemá závěr" aria-disabled="true">
                <FileDown aria-hidden /> PDF
              </span>
            )}
            {c.exports.fhir ? (
              <a href={exportUrl.fhir(c.id)} className={buttonVariants({ variant: 'outline' })} aria-label={`FHIR záznam ${c.patient_id}`}>
                <FileJson aria-hidden /> FHIR
              </a>
            ) : (
              <span
                className={cn(buttonVariants({ variant: 'outline' }), 'pointer-events-none opacity-45')}
                title="FHIR záznam vzniká potvrzením závěru"
                aria-disabled="true"
              >
                <FileJson aria-hidden /> FHIR
              </span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Stáhnout všechna PDF a FHIR boardu jedním souborem. */
export function ZipLink({ record, variant = 'default' }: { record: BoardRecord; variant?: 'default' | 'outline' }) {
  const any = record.cases.some((c) => c.exports.pdf);
  if (!any) return null;
  return (
    <a href={exportUrl.zip(record.id)} className={buttonVariants({ variant, size: 'lg' })}>
      <FileArchive aria-hidden /> Stáhnout vše (ZIP)
    </a>
  );
}

/** Přítomní lékaři: rozbalovací seznam (z `Decision.attendees`, u koho byli uvedení). */
function Attendees({ record }: { record: BoardRecord }) {
  const [open, setOpen] = React.useState(false);
  const bodyId = React.useId();
  const people = record.attendees;
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-controls={bodyId}
        disabled={people.length === 0}
        className="inline-flex items-center gap-1.5 rounded-md py-1 text-sm font-medium hover:underline hover:underline-offset-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:text-muted-foreground disabled:no-underline"
      >
        <ChevronRight className={cn('size-4 text-muted-foreground transition-transform motion-reduce:transition-none', open && 'rotate-90')} aria-hidden />
        <UsersRound className="size-4 text-muted-foreground" aria-hidden />
        {people.length ? `Přítomní lékaři (${people.length})` : 'Přítomní lékaři nejsou v závěrech uvedení'}
      </button>
      {open && (
        <ul id={bodyId} className="mt-1.5 grid gap-x-6 gap-y-1 pl-6 text-[13px] sm:grid-cols-2">
          {people.map((a) => (
            <li key={a.id ?? a.name} className="min-w-0">
              <span className="font-medium">{a.name}</span>
              {roleLabel(a.role) && <span className="text-muted-foreground"> · {roleLabel(a.role)}</span>}
              {record.cases.length > 1 && (
                <span className="block text-xs text-muted-foreground" translate="no">{a.patients.join(', ')}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** Velká karta boardu v záznamu (T-333): název, datum, počet pacientů, přítomní a výstupy pacientů. */
export function BoardRecordCard({ record }: { record: BoardRecord }) {
  const [open, setOpen] = React.useState(false);
  const listId = React.useId();
  return (
    <article className="flex flex-col gap-4 rounded-xl border border-border bg-card px-5 py-4" aria-labelledby={`board-${record.id}`}>
      <header className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <div className="min-w-0">
          <h2 id={`board-${record.id}`} className="text-lg font-semibold tracking-tight">
            <Link href={`/dashboard/mdt/${record.id}`} className="hover:underline hover:underline-offset-4">{record.title}</Link>
          </h2>
          <p className="text-[13px] tabular-nums text-muted-foreground">
            {dayLabel(record.date)} {timeLabel(record.date)}
            {record.chair && <> · předseda {record.chair.name}</>}
          </p>
        </div>
        <dl className="flex gap-6 text-sm">
          <div>
            <dt className="text-xs text-muted-foreground">Pacientů</dt>
            <dd className="text-2xl font-semibold tabular-nums">{record.counts.patients}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Potvrzených závěrů</dt>
            <dd className="text-2xl font-semibold tabular-nums">{record.counts.confirmed}</dd>
          </div>
        </dl>
      </header>
      <Attendees record={record} />
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-controls={listId}
          className={buttonVariants({ variant: 'outline', size: 'lg' })}
        >
          <ChevronRight className={cn('transition-transform motion-reduce:transition-none', open && 'rotate-90')} aria-hidden />
          {open ? 'Skrýt pacienty' : `Pacienti a výstupy (${record.counts.patients})`}
        </button>
        <ZipLink record={record} variant="outline" />
      </div>
      {open && <div id={listId}><BoardOutputs record={record} /></div>}
    </article>
  );
}
