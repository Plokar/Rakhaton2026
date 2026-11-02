'use client';

import * as React from 'react';
import { Archive, Search } from 'lucide-react';
import { Page, PageHeader } from '@/components/layout/Page';
import { Input } from '@/components/shadcn/input';
import { Skeleton } from '@/components/shadcn/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { BoardRecordCard } from '@/components/mdt/BoardRecord';
import { can, useMe } from '@/components/mdt/me';
import { apiErrorMessage, useRecordsQuery } from '@/lib/queries';
import type { BoardRecord } from '@/types/mdt';

const plain = (text: string) => text.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();
const haystack = (r: BoardRecord) =>
  plain([
    r.title,
    r.date.slice(0, 10),
    ...r.attendees.map((a) => a.name),
    ...r.cases.flatMap((c) => [c.patient_id, c.name ?? '', c.rc ?? '', c.diagnosis?.icd10 ?? '', c.diagnosis?.text ?? '']),
  ].join(' '));

/**
 * Záznam boardů (T-333): uzavřené boardy od nejnovějšího jako velké karty (název, datum, počet pacientů,
 * přítomní lékaři) a u každého pacienta stažení PDF a FHIR záznamu. Jen předseda (správce komise).
 */
export default function RecordsPage() {
  const me = useMe();
  const chair = can.manageBoards(me);
  const records = useRecordsQuery(chair);
  const [query, setQuery] = React.useState('');
  const words = plain(query).split(/\s+/).filter(Boolean);
  const shown = (records.data ?? []).filter((r) => words.every((w) => haystack(r).includes(w)));

  return (
    <Page className="max-w-5xl">
      <PageHeader
        title="Záznam boardů"
        meta="Ukončené boardy s přítomnými lékaři a výstupy pacientů: PDF závěru a FHIR záznam z IRIS."
      />
      {!me ? (
        <Skeleton className="h-40" />
      ) : !chair ? (
        <p className="text-sm text-muted-foreground">Záznam boardů a stahování výstupů má předseda komise.</p>
      ) : records.isLoading ? (
        <div className="flex flex-col gap-4" aria-busy="true">
          {[0, 1].map((i) => <Skeleton key={i} className="h-44 rounded-xl" />)}
        </div>
      ) : records.isError ? (
        <p role="alert" className="text-sm text-destructive">{apiErrorMessage(records.error, 'Záznam boardů se nepodařilo načíst.')}</p>
      ) : (records.data ?? []).length === 0 ? (
        <EmptyState
          icon={<Archive aria-hidden />}
          title="Zatím žádný ukončený board"
          description="Board ukončíte v jednání komise tlačítkem „Ukončit board“. Pak se tady objeví i s výstupy pacientů."
        />
      ) : (
        <>
          <div className="relative max-w-sm">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
            <Input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Board, pacient, jméno, lékař…"
              aria-label="Hledat v záznamu boardů"
              className="h-9 pl-8"
            />
          </div>
          {shown.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nic neodpovídá hledání „{query}“.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {shown.map((r) => <BoardRecordCard key={r.id} record={r} />)}
            </div>
          )}
        </>
      )}
    </Page>
  );
}
