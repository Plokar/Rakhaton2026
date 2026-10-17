'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, CalendarDays, LayoutGrid, ListChecks, MonitorUp } from 'lucide-react';
import { dayLabel, pragueDay, timeLabel, todayPrague } from '@/components/mdt/dates';
import { openProjectorWindow } from '@/components/mdt/projector';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarRail,
} from '@/components/shadcn/sidebar';
import { useMe } from '@/components/mdt/me';
import { isOverdue } from '@/components/mdt/MyTasks';
import { useMyTasksQuery, useSessionsQuery, useTasksQuery } from '@/lib/queries';

const NAV = [
  { href: '/dashboard', label: 'Přehled', icon: LayoutGrid, exact: true },
  { href: '/dashboard/mdt', label: 'Zasedání', icon: CalendarDays },
  { href: '/dashboard/tasks', label: 'Úkoly', icon: ListChecks },
] as const;

/** Postranní panel (NAVRH_UI §5.1): navigace, nejbližší zasedání jedním klikem, okno projektoru. Bez dev služeb. */
export function AppSidebar() {
  const pathname = usePathname();
  const sessions = useSessionsQuery();
  const tasks = useTasksQuery();
  const today = todayPrague();

  const overdue = (tasks.data ?? []).filter((t) => isOverdue(t, today)).length;
  // T-328: lékař vidí počet svých nedokončených úkolů (i z návrhu závěru), předseda dál úkoly po termínu
  const me = useMe();
  const mine = useMyTasksQuery(null, Boolean(me?.practitioner_id));
  const myOpen = (mine.data ?? []).filter((t) => t.status !== 'completed');
  const myLate = myOpen.filter((t) => isOverdue(t, today)).length;
  const upcoming = (sessions.data ?? [])
    .filter((s) => s.status !== 'closed' && pragueDay(s.date) >= today)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(0, 5);
  const byDay = upcoming.reduce<{ day: string; label: string; items: typeof upcoming }[]>((groups, s) => {
    const day = pragueDay(s.date);
    const last = groups.at(-1);
    if (last && last.day === day) last.items.push(s);
    else groups.push({ day, label: dayLabel(s.date), items: [s] });
    return groups;
  }, []);

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/dashboard" />} tooltip="MedTeam">
              <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Activity className="size-4" aria-hidden />
              </span>
              <span className="flex min-w-0 flex-col leading-tight">
                <span translate="no" className="truncate text-sm font-semibold">MedTeam</span>
                <span className="truncate text-xs text-muted-foreground">Onkologická komise</span>
              </span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV.map((item) => {
                const active = 'exact' in item && item.exact ? pathname === item.href : pathname.startsWith(item.href);
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton render={<Link href={item.href} />} isActive={active} tooltip={item.label}>
                      <item.icon aria-hidden />
                      <span>{item.label}</span>
                    </SidebarMenuButton>
                    {item.href === '/dashboard/tasks' && myOpen.length > 0 ? (
                      <SidebarMenuBadge
                        aria-label={`Vašich úkolů: ${myOpen.length}${myLate ? `, po termínu ${myLate}` : ''}`}
                        className={myLate ? 'text-amber-700 dark:text-amber-400' : 'text-primary'}
                      >
                        {myOpen.length}
                      </SidebarMenuBadge>
                    ) : (
                      item.href === '/dashboard/tasks' && overdue > 0 && (
                        <SidebarMenuBadge aria-label={`${overdue} po termínu`} className="text-amber-700 dark:text-amber-400">
                          {overdue}
                        </SidebarMenuBadge>
                      )
                    )}
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="group-data-[collapsible=icon]:hidden">
          <SidebarGroupLabel>Nejbližší zasedání</SidebarGroupLabel>
          <SidebarGroupContent>
            {sessions.isLoading ? (
              <SidebarMenu>
                {[0, 1, 2].map((i) => <SidebarMenuItem key={i}><SidebarMenuSkeleton /></SidebarMenuItem>)}
              </SidebarMenu>
            ) : byDay.length === 0 ? (
              <p className="px-2 py-1 text-xs text-muted-foreground">Žádné naplánované zasedání.</p>
            ) : (
              byDay.map((group) => (
                <div key={group.day} className="mb-2 last:mb-0">
                  <p className="px-2 pb-1 text-xs text-muted-foreground">{group.day === today ? `dnes · ${group.label}` : group.label}</p>
                  <SidebarMenu>
                    {group.items.map((s) => (
                      <SidebarMenuItem key={s.id}>
                        <SidebarMenuButton
                          render={<Link href={`/dashboard/mdt/${s.id}`} />}
                          isActive={pathname === `/dashboard/mdt/${s.id}`}
                          className="h-auto py-1.5 pr-8"
                          title={s.title}
                        >
                          <span className="w-10 shrink-0 text-xs tabular-nums text-muted-foreground">{timeLabel(s.date)}</span>
                          <span className="truncate">{s.title}</span>
                        </SidebarMenuButton>
                        <SidebarMenuBadge className="tabular-nums" aria-label={`${s.patients.length} pacientů`}>
                          {s.patients.length}
                        </SidebarMenuBadge>
                      </SidebarMenuItem>
                    ))}
                  </SidebarMenu>
                </div>
              ))
            )}
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton tooltip="Okno pro projektor" onClick={() => openProjectorWindow(null)}>
              <MonitorUp aria-hidden />
              <span>Okno pro projektor</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
