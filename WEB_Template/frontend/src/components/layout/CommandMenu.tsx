'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { CalendarDays, Keyboard, LayoutGrid, ListChecks, MonitorUp, Moon, Settings, Sun, UserRound, UsersRound } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { dayLabel, pragueDay, timeLabel, todayPrague } from '@/components/mdt/dates';
import { openProjectorWindow } from '@/components/mdt/projector';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/shadcn/command';
import { useSessionsWithCases } from '@/lib/queries';

const ALL_SESSIONS = () => true;

/** Ctrl K: pacienti (rovnou na případ), zasedání, navigace a akce (NAVRH_UI §5.2). */
export function CommandMenu({
  open,
  onOpenChange,
  onShowShortcuts,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onShowShortcuts: () => void;
}) {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const { sessions, detail } = useSessionsWithCases(ALL_SESSIONS);

  const run = (action: () => void) => {
    onOpenChange(false);
    action();
  };

  // Nadcházející zasedání nahoře (od nejbližšího), minulá pod nimi.
  const today = todayPrague();
  const upcoming = [...sessions].sort((a, b) => {
    const pastA = pragueDay(a.date) < today;
    const pastB = pragueDay(b.date) < today;
    return pastA === pastB ? (pastA ? b.date.localeCompare(a.date) : a.date.localeCompare(b.date)) : pastA ? 1 : -1;
  });
  const cases = upcoming.flatMap((s) => (detail.get(s.id)?.cases ?? []).map((c) => ({ c, session: s })));

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange} title="Hledat" description="Pacient, zasedání nebo akce" className="sm:max-w-xl">
      <Command loop>
      <CommandInput placeholder="Hledat pacienta (P03), diagnózu, komisi…" />
      <CommandList>
        <CommandEmpty>Nic nenalezeno.</CommandEmpty>
        {cases.length > 0 && (
          <CommandGroup heading="Pacienti">
            {cases.map(({ c, session }) => (
              <CommandItem
                key={c.id}
                value={`${c.patient_id} ${c.patient?.display_name ?? ''} ${c.patient?.diagnosis?.icd10 ?? ''} ${c.patient?.diagnosis?.text ?? ''} ${session.title}`}
                onSelect={() => run(() => router.push(`/dashboard/cases/${c.id}`))}
              >
                <UserRound aria-hidden />
                <span className="truncate">{c.patient?.display_name ?? c.patient_id}</span>
                <span className="ml-auto shrink-0 text-right text-xs text-muted-foreground">
                  {c.patient?.diagnosis?.icd10} · {session.title.split('–')[0].trim()}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        {upcoming.length > 0 && (
          <CommandGroup heading="Zasedání">
            {upcoming.map((s) => (
              <CommandItem key={s.id} value={`zasedání ${s.title} ${dayLabel(s.date)}`} onSelect={() => run(() => router.push(`/dashboard/mdt/${s.id}`))}>
                <CalendarDays aria-hidden />
                <span className="truncate">{s.title}</span>
                <span className="ml-auto shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                  {dayLabel(s.date)} {timeLabel(s.date)}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        <CommandSeparator />
        <CommandGroup heading="Přejít">
          <CommandItem value="přehled kalendář" onSelect={() => run(() => router.push('/dashboard'))}>
            <LayoutGrid aria-hidden /> Přehled
          </CommandItem>
          <CommandItem value="zasedání seznam" onSelect={() => run(() => router.push('/dashboard/mdt'))}>
            <CalendarDays aria-hidden /> Všechna zasedání
          </CommandItem>
          <CommandItem value="úkoly" onSelect={() => run(() => router.push('/dashboard/tasks'))}>
            <ListChecks aria-hidden /> Úkoly
          </CommandItem>
          <CommandItem value="nastavení" onSelect={() => run(() => router.push('/dashboard/settings'))}>
            <Settings aria-hidden /> Nastavení
          </CommandItem>
          <CommandItem value="tým komise členové role odbornost" onSelect={() => run(() => router.push('/dashboard/tym'))}>
            <UsersRound aria-hidden /> Tým komise
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="Akce">
          <CommandItem value="okno projektor" onSelect={() => run(() => openProjectorWindow(null))}>
            <MonitorUp aria-hidden /> Otevřít okno pro projektor
          </CommandItem>
          <CommandItem
            value="tmavý světlý režim projektor"
            onSelect={() => run(() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark'))}
          >
            {resolvedTheme === 'dark' ? <Sun aria-hidden /> : <Moon aria-hidden />}
            {resolvedTheme === 'dark' ? 'Světlý režim' : 'Tmavý režim (projektor)'}
          </CommandItem>
          <CommandItem value="klávesové zkratky nápověda" onSelect={() => run(onShowShortcuts)}>
            <Keyboard aria-hidden /> Klávesové zkratky
          </CommandItem>
        </CommandGroup>
      </CommandList>
      </Command>
    </CommandDialog>
  );
}
