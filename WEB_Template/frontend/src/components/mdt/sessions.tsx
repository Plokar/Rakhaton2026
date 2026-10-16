import Link from 'next/link';
import { CalendarDays, ChevronRight, FileText, PanelRightOpen, UserRound } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MdtCase, MdtSession, MdtSessionListItem } from '@/types/mdt';
import { formatDate } from './format';

export const SESSION_STATUS: Record<MdtSession['status'], string> = {
  planned: 'Plánováno',
  in_progress: 'Probíhá',
  closed: 'Uzavřeno',
};

export const CASE_STATUS: Record<MdtCase['status'], string> = {
  nominated: 'Nominován',
  ready: 'Připraven',
  in_discussion: 'Projednává se',
  decided: 'Rozhodnuto',
  confirmed: 'Potvrzeno',
  returned: 'Vrácen k doplnění',
};

/** Boardy seřazené od nejbližšího termínu. */
export function sortSessions<T extends MdtSession>(sessions: T[]): T[] {
  return [...sessions].sort((a, b) => a.date.localeCompare(b.date));
}

/** Board = zasedání MDT (FR-P1): termín, komise, předseda a zařazení pacienti. */
export function SessionCard({ session }: { session: MdtSessionListItem }) {
  return (
    <Link
      href={`/dashboard/mdt/${session.id}`}
      className="group flex items-start gap-3 rounded-xl border border-border bg-card p-4 transition hover:border-primary/60 hover:bg-muted/30"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <CalendarDays className="h-5 w-5" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-foreground">{session.title}</p>
        <p className="text-xs text-muted-foreground">
          {formatDate(session.date)} · {SESSION_STATUS[session.status]}
          {session.chair && <> · předseda {session.chair.name}</>}
        </p>
        <p className="mt-1.5 flex flex-wrap gap-1">
          {session.patients.length === 0 ? (
            <span className="text-xs text-muted-foreground">Zatím bez pacientů</span>
          ) : (
            session.patients.map((pid) => (
              <span key={pid} className="rounded-md border border-border px-1.5 py-0.5 font-mono text-[11px] text-foreground">
                {pid}
              </span>
            ))
          )}
        </p>
      </div>
      <ChevronRight className="mt-2 h-4 w-4 shrink-0 text-muted-foreground transition group-hover:translate-x-0.5" aria-hidden />
    </Link>
  );
}

/** Případ v agendě zasedání: hlavička pacienta z IRIS, otázka, stav a odkaz na podklad. */
export function AgendaItem({ item }: { item: MdtCase }) {
  const patient = item.patient;
  return (
    <li className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted font-mono text-xs font-semibold text-muted-foreground">
          {item.order ?? '–'}
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <p className="text-sm font-bold text-foreground">{patient?.display_name ?? item.patient_id}</p>
            <span
              className={cn(
                'rounded-full border px-2 py-0.5 text-[10px] font-semibold',
                item.status === 'returned'
                  ? 'border-destructive/40 text-destructive'
                  : 'border-border text-muted-foreground',
              )}
            >
              {CASE_STATUS[item.status]}
            </span>
            {item.ecog !== null && (
              <span className="text-[11px] text-muted-foreground">ECOG {item.ecog}</span>
            )}
            {item.intent && <span className="text-[11px] font-semibold text-foreground">{item.intent}</span>}
          </div>
          {patient?.diagnosis && (
            <p className="text-xs text-muted-foreground">
              {patient.diagnosis.text} <span className="font-mono">{patient.diagnosis.icd10}</span>
            </p>
          )}
          {(item.question ?? patient?.mdt_question) && (
            <p className="line-clamp-2 text-sm text-foreground">{item.question ?? patient?.mdt_question}</p>
          )}
          {item.created_by && (
            <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <UserRound className="h-3 w-3" aria-hidden /> zařadil {item.created_by.name}
            </p>
          )}
        </div>
      </div>
      {item.id !== undefined && (
        <div className="mt-3 flex flex-wrap gap-2 pl-10">
          <Link
            href={`/dashboard/cases/${item.id}`}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
          >
            <FileText className="h-3.5 w-3.5" aria-hidden /> Podklad
          </Link>
          <a
            href={`/brief/${item.id}`}
            target="_blank"
            rel="noopener"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <PanelRightOpen className="h-3.5 w-3.5" aria-hidden /> Úzké okno
          </a>
        </div>
      )}
    </li>
  );
}
