'use client';

import * as React from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { CommandPalette } from '@/components/ui/command-palette';
import { Avatar } from '@/components/ui/avatar';
import { Dropdown, DropdownItem, DropdownSeparator } from '@/components/ui/dropdown';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FolderKanban,
  Bot,
  HardDrive,
  Radio,
  Settings,
  Bell,
  Search,
  ChevronLeft,
  ChevronRight,
  Menu,
  ExternalLink,
  LogOut,
  ShieldAlert,
  Zap,
} from 'lucide-react';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, isLoading } = useAuth();
  const [collapsed, setCollapsed] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [cmdOpen, setCmdOpen] = React.useState(false);

  // Ochrana přihlášení
  React.useEffect(() => {
    if (!isLoading && !user) {
      router.push('/login');
    }
  }, [user, isLoading, router]);

  const navItems = [
    {
      title: 'Hlavní',
      items: [
        {
          label: 'Přehled',
          href: '/dashboard',
          icon: <LayoutDashboard className="h-4 w-4" />,
          exact: true,
        },
        {
          label: 'Projekty & Úkoly',
          href: '/dashboard/projects',
          icon: <FolderKanban className="h-4 w-4" />,
        },
        {
          label: 'AI Studio',
          href: '/dashboard/ai',
          icon: <Bot className="h-4 w-4" />,
          badge: 'Live',
        },
        {
          label: 'Úložiště souborů',
          href: '/dashboard/storage',
          icon: <HardDrive className="h-4 w-4" />,
        },
        {
          label: 'WebSocket Monitor',
          href: '/dashboard/realtime',
          icon: <Radio className="h-4 w-4" />,
          badge: 'WS',
        },
      ],
    },
    {
      title: 'Správa',
      items: [
        {
          label: 'Nastavení',
          href: '/dashboard/settings',
          icon: <Settings className="h-4 w-4" />,
        },
      ],
    },
  ];

  const externalLinks = [
    { label: 'Swagger UI (:8000)', href: 'http://localhost:8000/api/docs/' },
    { label: 'Django Admin', href: 'http://localhost:8000/admin/' },
    { label: 'Mailhog (:8025)', href: 'http://localhost:8025' },
    { label: 'Traefik (:8080)', href: 'http://localhost:8080' },
  ];

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <span className="text-xs text-muted-foreground font-mono">Načítám Hackathon OS...</span>
        </div>
      </div>
    );
  }

  const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username;
  const userFallback = (user.first_name?.[0] || user.username[0] || 'U').toUpperCase();

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      {/* Mobile Backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-card transition-all duration-300 ease-in-out lg:static',
          collapsed ? 'w-16' : 'w-64',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        )}
      >
        {/* Sidebar Header */}
        <div className="flex h-16 items-center justify-between border-b border-border px-4">
          <Link href="/dashboard" className="flex items-center gap-2.5 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-indigo-500/30">
              <Zap className="h-5 w-5 fill-current" />
            </div>
            {!collapsed && (
              <div className="flex flex-col">
                <span className="text-sm font-bold tracking-tight text-foreground">Hackathon OS</span>
                <span className="text-[10px] font-mono text-muted-foreground">v2.0 • Django + Next</span>
              </div>
            )}
          </Link>

          {/* Collapse toggle (desktop only) */}
          <button
            type="button"
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex h-7 w-7 items-center justify-center rounded-lg border border-border text-muted-foreground hover:bg-accent hover:text-foreground transition"
            title={collapsed ? 'Rozbalit panel' : 'Sbalit panel'}
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {navItems.map((group) => (
            <div key={group.title} className="space-y-1">
              {!collapsed && (
                <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                  {group.title}
                </div>
              )}
              {group.items.map((item) => {
                const isActive = item.exact
                  ? pathname === item.href
                  : pathname.startsWith(item.href);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all',
                      isActive
                        ? 'bg-primary/10 text-primary font-semibold'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground',
                      collapsed && 'justify-center px-2'
                    )}
                    title={collapsed ? item.label : undefined}
                  >
                    <div className={cn('shrink-0', isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground')}>
                      {item.icon}
                    </div>
                    {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                    {!collapsed && item.badge && (
                      <span className="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold text-primary">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}

          {/* External Dev Services */}
          {!collapsed && (
            <div className="space-y-1 pt-2 border-t border-border/60">
              <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                Dev Služby
              </div>
              {externalLinks.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between rounded-lg px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition"
                >
                  <span>{link.label}</span>
                  <ExternalLink className="h-3 w-3 opacity-60" />
                </a>
              ))}
            </div>
          )}
        </div>

        {/* Sidebar Footer User Info */}
        <div className="border-t border-border p-3">
          <Dropdown
            align="left"
            trigger={
              <div className={cn('flex items-center gap-3 rounded-xl p-2 transition hover:bg-accent cursor-pointer', collapsed && 'justify-center p-1')}>
                <Avatar fallback={userFallback} size={collapsed ? 'sm' : 'default'} />
                {!collapsed && (
                  <div className="flex flex-col text-left overflow-hidden">
                    <span className="text-xs font-semibold text-foreground truncate">{displayName}</span>
                    <span className="text-[11px] text-muted-foreground truncate">{user.email}</span>
                  </div>
                )}
              </div>
            }
          >
            <div className="px-3 py-2 border-b border-border">
              <p className="text-xs font-semibold text-foreground">{displayName}</p>
              <p className="text-[11px] text-muted-foreground truncate">{user.email}</p>
              {user.is_staff && (
                <span className="inline-flex items-center gap-1 mt-1 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                  <ShieldAlert className="h-3 w-3" /> Admin
                </span>
              )}
            </div>
            <DropdownItem onClick={() => router.push('/dashboard/settings')}>
              <Settings className="h-4 w-4" /> Nastavení profilu
            </DropdownItem>
            <DropdownSeparator />
            <DropdownItem
              destructive
              onClick={async () => {
                await logout();
                router.push('/login');
              }}
            >
              <LogOut className="h-4 w-4" /> Odhlásit se
            </DropdownItem>
          </Dropdown>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Navbar */}
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-md sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="lg:hidden flex h-9 w-9 items-center justify-center rounded-xl border border-border text-muted-foreground hover:bg-accent"
            >
              <Menu className="h-5 w-5" />
            </button>

            {/* Quick search button */}
            <button
              type="button"
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-2 rounded-xl border border-border bg-card/60 px-3 py-1.5 text-xs text-muted-foreground hover:bg-accent hover:text-foreground transition sm:w-64 justify-between"
            >
              <div className="flex items-center gap-2">
                <Search className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Hledat v projektu...</span>
                <span className="sm:hidden">Hledat...</span>
              </div>
              <kbd className="hidden sm:inline-flex items-center rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
                Ctrl+K
              </kbd>
            </button>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Quick links to localhost services */}
            <a
              href="http://localhost:8000/api/docs/"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden lg:inline-flex items-center gap-1.5 rounded-lg border border-border bg-card/50 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground transition"
              title="Swagger UI / OpenAPI Dokumentace"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 animate-pulse" />
              Swagger UI
            </a>
            <a
              href="http://localhost:8025"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden md:inline-flex items-center gap-1.5 rounded-lg border border-border bg-card/50 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground transition"
              title="Mailhog e-mail schránka"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Mailhog
            </a>

            {/* Notification bell */}
            <button
              type="button"
              onClick={() => router.push('/dashboard')}
              className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card/60 text-muted-foreground hover:bg-accent hover:text-foreground transition"
              title="Notifikace"
            >
              <Bell className="h-4 w-4" />
              <span className="absolute top-2 right-2 h-2 w-2 rounded-full bg-primary ring-2 ring-background" />
            </button>

            {/* Theme switcher */}
            <ThemeToggle />

            {/* User avatar header */}
            <div className="pl-1">
              <Avatar fallback={userFallback} size="sm" />
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>

      {/* Command Palette Modal */}
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} />
    </div>
  );
}
