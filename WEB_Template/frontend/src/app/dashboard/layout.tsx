'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { QueryClientProvider } from '@tanstack/react-query';
import { NuqsAdapter } from 'nuqs/adapters/next/app';
import { useAuth } from '@/contexts/AuthContext';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { CommandMenu } from '@/components/layout/CommandMenu';
import { ShortcutsDialog } from '@/components/layout/ShortcutsDialog';
import { CrumbSlotProvider, TopBar } from '@/components/layout/TopBar';
import { MeProvider } from '@/components/mdt/me';
import { SidebarInset, SidebarProvider } from '@/components/shadcn/sidebar';
import { Toaster } from '@/components/shadcn/sonner';
import { TooltipProvider } from '@/components/shadcn/tooltip';
import { createQueryClient } from '@/lib/queries';

/**
 * Sdílený shell /dashboard (NAVRH_UI §4–5): sidebar se při navigaci nepřemontuje, jedna cache dat
 * (TanStack Query), stav v URL (nuqs), toasty, Ctrl K a nápověda ke zkratkám.
 */
export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const [queryClient] = React.useState(createQueryClient);
  return (
    <QueryClientProvider client={queryClient}>
      <NuqsAdapter>
        <TooltipProvider delay={300}>
          <AuthGate>{children}</AuthGate>
          <Toaster position="bottom-right" />
        </TooltipProvider>
      </NuqsAdapter>
    </QueryClientProvider>
  );
}

function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  React.useEffect(() => {
    if (!isLoading && !user) router.push('/login');
  }, [user, isLoading, router]);

  if (isLoading || !user) {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background" aria-busy="true">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent motion-reduce:animate-none" />
        <span className="sr-only">Načítám…</span>
      </div>
    );
  }
  return (
    <MeProvider userId={user.id}>
      <Shell>{children}</Shell>
    </MeProvider>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const [slot, setSlot] = React.useState<HTMLElement | null>(null);
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [shortcutsOpen, setShortcutsOpen] = React.useState(false);

  // Jeden globální posluchač: Ctrl/Cmd K hledání, „?“ nápověda (mimo textová pole).
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen((open) => !open);
        return;
      }
      const target = e.target as HTMLElement | null;
      const typing = target && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName));
      if (e.key === '?' && !typing) {
        e.preventDefault();
        setShortcutsOpen(true);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <CrumbSlotProvider slot={slot}>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset className="min-w-0">
          <TopBar slotRef={setSlot} onSearch={() => setSearchOpen(true)} onShowShortcuts={() => setShortcutsOpen(true)} />
          <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">{children}</main>
        </SidebarInset>
      </SidebarProvider>
      {searchOpen && (
        <CommandMenu open={searchOpen} onOpenChange={setSearchOpen} onShowShortcuts={() => setShortcutsOpen(true)} />
      )}
      <ShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </CrumbSlotProvider>
  );
}
