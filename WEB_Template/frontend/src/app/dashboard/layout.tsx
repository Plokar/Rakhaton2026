'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { CommandMenu } from '@/components/layout/CommandMenu';
import { ShortcutsDialog } from '@/components/layout/ShortcutsDialog';
import { CrumbSlotProvider, TopBar } from '@/components/layout/TopBar';
import { MeProvider } from '@/components/mdt/me';
import { SidebarInset, SidebarProvider } from '@/components/shadcn/sidebar';

/**
 * Sdílený shell /dashboard (NAVRH_UI §4–5): sidebar se při navigaci nepřemontuje, Ctrl K hledání
 * a nápověda ke zkratkám. Cache dat, URL stav a toasty jsou v `app/providers.tsx`.
 */
export default function DashboardShell({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}

function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  React.useEffect(() => {
    if (!isLoading && !user) router.push('/login');
  }, [user, isLoading, router]);

  if (isLoading || !user) return <ShellLoading />;
  return (
    <MeProvider userId={user.id}>
      <Shell>{children}</Shell>
    </MeProvider>
  );
}

function ShellLoading() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-background" aria-busy="true">
      <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent motion-reduce:animate-none" />
      <span className="sr-only">Načítám…</span>
    </div>
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
          <main id="obsah" className="flex min-h-0 min-w-0 flex-1 flex-col">
            <React.Suspense fallback={null}>{children}</React.Suspense>
          </main>
        </SidebarInset>
      </SidebarProvider>
      {searchOpen && (
        <CommandMenu open={searchOpen} onOpenChange={setSearchOpen} onShowShortcuts={() => setShortcutsOpen(true)} />
      )}
      <ShortcutsDialog open={shortcutsOpen} onOpenChange={setShortcutsOpen} />
    </CrumbSlotProvider>
  );
}
