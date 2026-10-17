'use client';

import * as React from 'react';
import { Stethoscope, UserRound } from 'lucide-react';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/shadcn/command';
import { Skeleton } from '@/components/shadcn/skeleton';
import { apiErrorMessage, usePractitionersQuery } from '@/lib/queries';
import type { Practitioner } from '@/types/mdt';

/** Bez diakritiky a velikosti písmen: „radiacni“ najde „radiační“. */
const plain = (text: string) => text.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();

/** Všechna slova hledání musí být v textu položky (jméno, odbornost, ID). */
function matches(value: string, search: string): number {
  const words = plain(search).split(/\s+/).filter(Boolean);
  const haystack = plain(value);
  return words.every((w) => haystack.includes(w)) ? 1 : 0;
}

/**
 * Výběr lékaře nemocnice (T-328): popup se všemi lékaři z IRIS (FHIR Practitioner) a vyhledáváním.
 * Používá se všude, kde se přidává lékař (přítomní, vlastník úkolu). Lékaři s účtem v aplikaci jsou nahoře.
 */
export function PractitionerPicker({
  open,
  onOpenChange,
  onSelect,
  title = 'Vybrat lékaře',
  description = 'Lékaři nemocnice z IRIS. Hledejte podle jména, odbornosti nebo kódu.',
  excludeIds = [],
  withUserOnly = false,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (practitioner: Practitioner) => void;
  title?: string;
  description?: string;
  /** Lékaři, kteří už jsou vybraní (nezobrazí se znovu). */
  excludeIds?: string[];
  /** Jen lékaři s účtem v aplikaci (např. přizvání ke spolupráci). */
  withUserOnly?: boolean;
}) {
  const directory = usePractitionersQuery(open);
  const excluded = new Set(excludeIds);
  const items = (directory.data ?? []).filter((p) => !excluded.has(p.id) && (!withUserOnly || p.user));
  const withAccount = items.filter((p) => p.user);
  const others = items.filter((p) => !p.user);

  const pick = (p: Practitioner) => {
    onSelect(p);
    onOpenChange(false);
  };

  const row = (p: Practitioner) => (
    <CommandItem key={p.id} value={`${p.name} ${p.specialty} ${p.id}`} onSelect={() => pick(p)}>
      {p.user ? <UserRound aria-hidden /> : <Stethoscope aria-hidden />}
      <span className="min-w-0 flex-1">
        <span className="block truncate">{p.name}</span>
        {p.specialty && <span className="block truncate text-xs text-muted-foreground">{p.specialty}</span>}
      </span>
      {p.user && <span className="shrink-0 text-xs text-muted-foreground">účet v aplikaci</span>}
    </CommandItem>
  );

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title={title} description={description} className="sm:max-w-lg">
      <Command loop filter={matches}>
        <CommandInput placeholder="Hledat lékaře: jméno, odbornost, kód…" autoFocus />
        <CommandList className="max-h-96">
          {directory.isLoading ? (
            <div className="flex flex-col gap-2 p-2" aria-busy="true">
              {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-9" />)}
            </div>
          ) : directory.isError ? (
            <p role="alert" className="p-3 text-sm text-destructive">
              {apiErrorMessage(directory.error, 'Seznam lékařů se nepodařilo načíst.')}
            </p>
          ) : (
            <>
              <CommandEmpty>Žádný lékař neodpovídá hledání.</CommandEmpty>
              {withAccount.length > 0 && <CommandGroup heading="S účtem v aplikaci">{withAccount.map(row)}</CommandGroup>}
              {others.length > 0 && <CommandGroup heading="Další lékaři nemocnice">{others.map(row)}</CommandGroup>}
            </>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
