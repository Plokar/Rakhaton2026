'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from '@/contexts/ThemeContext';
import { useAuth } from '@/contexts/AuthContext';
import {
  Search,
  LayoutDashboard,
  FolderKanban,
  Bot,
  HardDrive,
  Radio,
  Settings,
  Sun,
  Moon,
  LogOut,
  ExternalLink,
} from 'lucide-react';

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter();
  const { resolvedTheme, setTheme } = useTheme();
  const { logout } = useAuth();
  const [query, setQuery] = React.useState('');

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onOpenChange(!open);
      }
      if (e.key === 'Escape' && open) {
        onOpenChange(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onOpenChange]);

  if (!open) return null;

  const actions = [
    {
      group: 'Navigace',
      items: [
        { label: 'Přehled Dashboard', icon: <LayoutDashboard className="h-4 w-4" />, href: '/dashboard' },
        { label: 'Projekty & Úkoly', icon: <FolderKanban className="h-4 w-4" />, href: '/dashboard/projects' },
        { label: 'AI Studio Playground', icon: <Bot className="h-4 w-4" />, href: '/dashboard/ai' },
        { label: 'Správce souborů', icon: <HardDrive className="h-4 w-4" />, href: '/dashboard/storage' },
        { label: 'WebSocket Live Monitor', icon: <Radio className="h-4 w-4" />, href: '/dashboard/realtime' },
        { label: 'Nastavení profilu', icon: <Settings className="h-4 w-4" />, href: '/dashboard/settings' },
      ],
    },
    {
      group: 'Systém & Nástroje',
      items: [
        {
          label: resolvedTheme === 'dark' ? 'Přepnout na světlý režim' : 'Přepnout na tmavý režim',
          icon: resolvedTheme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-indigo-500" />,
          action: () => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark'),
        },
        {
          label: 'Swagger UI (:8000/api/docs)',
          icon: <ExternalLink className="h-4 w-4 text-cyan-400" />,
          action: () => window.open('http://localhost:8000/api/docs/', '_blank'),
        },
        {
          label: 'Django Admin (:8000/admin)',
          icon: <ExternalLink className="h-4 w-4" />,
          action: () => window.open('http://localhost:8000/admin/', '_blank'),
        },
        {
          label: 'Mailhog E-maily (:8025)',
          icon: <ExternalLink className="h-4 w-4" />,
          action: () => window.open('http://localhost:8025', '_blank'),
        },
        {
          label: 'Traefik Dashboard (:8080)',
          icon: <ExternalLink className="h-4 w-4" />,
          action: () => window.open('http://localhost:8080', '_blank'),
        },
        {
          label: 'Odhlásit se',
          icon: <LogOut className="h-4 w-4 text-destructive" />,
          action: async () => {
            await logout();
            router.push('/login');
          },
        },
      ],
    },
  ];

  const filteredGroups = actions
    .map((group) => ({
      ...group,
      items: group.items.filter((item) =>
        item.label.toLowerCase().includes(query.toLowerCase())
      ),
    }))
    .filter((group) => group.items.length > 0);

  const handleSelect = (item: { href?: string; action?: () => void }) => {
    onOpenChange(false);
    setQuery('');
    if (item.href) {
      router.push(item.href);
    } else if (item.action) {
      item.action();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 p-4">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={() => onOpenChange(false)}
      />

      {/* Palette Card */}
      <div className="relative z-50 w-full max-w-xl overflow-hidden rounded-2xl border border-border bg-popover shadow-2xl animate-in zoom-in-95 duration-150">
        {/* Search header */}
        <div className="flex items-center border-b border-border px-4 py-3">
          <Search className="h-4 w-4 text-muted-foreground mr-3 shrink-0" />
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Hledat stránky, nástroje a akce... (Esc pro zavření)"
            className="w-full bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          <kbd className="hidden sm:inline-flex items-center rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
            ESC
          </kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto p-2 space-y-3">
          {filteredGroups.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              Žádné výsledky pro dotaz &quot;{query}&quot;
            </p>
          ) : (
            filteredGroups.map((group) => (
              <div key={group.group}>
                <div className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {group.group}
                </div>
                <div className="space-y-0.5">
                  {group.items.map((item) => (
                    <button
                      key={item.label}
                      onClick={() => handleSelect(item)}
                      className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-foreground transition hover:bg-accent hover:text-accent-foreground text-left"
                    >
                      <div className="flex h-6 w-6 items-center justify-center text-muted-foreground">
                        {item.icon}
                      </div>
                      <span className="flex-1">{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="flex items-center justify-between border-t border-border bg-muted/30 px-4 py-2 text-[11px] text-muted-foreground">
          <span>Stiskni ↵ pro potvrzení</span>
          <span>Tip: zmáčkni Ctrl+K kdykoliv</span>
        </div>
      </div>
    </div>
  );
}
