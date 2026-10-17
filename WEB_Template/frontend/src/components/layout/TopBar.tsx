'use client';

import * as React from 'react';
import { createPortal } from 'react-dom';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Moon, Search, Sun } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { UserMenu } from '@/components/layout/UserMenu';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/shadcn/breadcrumb';
import { Kbd, KbdGroup } from '@/components/shadcn/kbd';
import { Separator } from '@/components/shadcn/separator';
import { SidebarTrigger } from '@/components/shadcn/sidebar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/shadcn/tooltip';

/** Slot v drobečkové navigaci: stránka do něj přes portál vloží název boardu nebo pacienta. */
const CrumbSlot = React.createContext<HTMLElement | null>(null);

/** Poslední článek drobečkové navigace (název boardu, pacient); renderuje stránka. */
export function PageCrumb({ children }: { children: React.ReactNode }) {
  const slot = React.useContext(CrumbSlot);
  if (!slot) return null;
  return createPortal(
    <>
      <BreadcrumbSeparator />
      <BreadcrumbItem>
        <BreadcrumbPage className="max-w-[28ch] truncate">{children}</BreadcrumbPage>
      </BreadcrumbItem>
    </>,
    slot,
  );
}

const SECTIONS: { prefix: string; label: string; href: string }[] = [
  { prefix: '/dashboard/mdt', label: 'Zasedání', href: '/dashboard/mdt' },
  { prefix: '/dashboard/cases', label: 'Přehled', href: '/dashboard' },
  { prefix: '/dashboard/tasks', label: 'Úkoly', href: '/dashboard/tasks' },
  { prefix: '/dashboard/settings', label: 'Nastavení', href: '/dashboard/settings' },
];

export function CrumbSlotProvider({ slot, children }: { slot: HTMLElement | null; children: React.ReactNode }) {
  return <CrumbSlot.Provider value={slot}>{children}</CrumbSlot.Provider>;
}

export function TopBar({
  slotRef,
  onSearch,
  onShowShortcuts,
}: {
  slotRef: (el: HTMLElement | null) => void;
  onSearch: () => void;
  onShowShortcuts: () => void;
}) {
  const pathname = usePathname();
  const { resolvedTheme, setTheme } = useTheme();
  const section = SECTIONS.find((s) => pathname.startsWith(s.prefix));
  const isRoot = pathname === '/dashboard';
  const isSectionRoot = section && pathname === section.href;

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b border-border bg-background/90 px-3 backdrop-blur supports-[backdrop-filter]:bg-background/75 sm:px-4">
      <SidebarTrigger className="-ml-1" aria-label="Postranní panel (Ctrl B)" />
      <Separator orientation="vertical" className="mx-1 h-5" />

      <Breadcrumb className="min-w-0 flex-1">
        <BreadcrumbList ref={slotRef} className="flex-nowrap">
          <BreadcrumbItem>
            {isRoot ? <BreadcrumbPage>Přehled</BreadcrumbPage> : <BreadcrumbLink render={<Link href="/dashboard" />}>Přehled</BreadcrumbLink>}
          </BreadcrumbItem>
          {section && section.href !== '/dashboard' && (
            <>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                {isSectionRoot ? (
                  <BreadcrumbPage>{section.label}</BreadcrumbPage>
                ) : (
                  <BreadcrumbLink render={<Link href={section.href} />}>{section.label}</BreadcrumbLink>
                )}
              </BreadcrumbItem>
            </>
          )}
        </BreadcrumbList>
      </Breadcrumb>

      <button
        type="button"
        onClick={onSearch}
        className="hidden h-9 w-64 items-center gap-2 rounded-lg border border-border bg-card px-3 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:flex"
      >
        <Search className="size-4" aria-hidden />
        <span className="flex-1 text-left">Hledat pacienta…</span>
        <KbdGroup>
          <Kbd>Ctrl</Kbd>
          <Kbd>K</Kbd>
        </KbdGroup>
      </button>
      <button
        type="button"
        onClick={onSearch}
        aria-label="Hledat (Ctrl K)"
        className="flex size-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
      >
        <Search className="size-4" aria-hidden />
      </button>

      <Tooltip>
        <TooltipTrigger
          render={
            <button
              type="button"
              onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
              aria-label={resolvedTheme === 'dark' ? 'Světlý režim' : 'Tmavý režim pro projektor'}
              className="flex size-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          }
        >
          {resolvedTheme === 'dark' ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
        </TooltipTrigger>
        <TooltipContent>{resolvedTheme === 'dark' ? 'Světlý režim' : 'Tmavý režim (projektor)'}</TooltipContent>
      </Tooltip>

      <UserMenu onShowShortcuts={onShowShortcuts} />
    </header>
  );
}
