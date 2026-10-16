'use client';

import * as React from 'react';
import { useTheme } from '@/contexts/ThemeContext';
import { Moon, Sun } from 'lucide-react';

export function ThemeToggle({ className }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <button
      type="button"
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
      className={`relative inline-flex h-9 items-center gap-1.5 rounded-lg border border-border bg-card px-2.5 text-xs font-medium text-foreground hover:bg-accent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${className || ''}`}
      aria-label="Přepnout barevný režim"
      title={resolvedTheme === 'dark' ? 'Přepnout na světlý klinický režim' : 'Přepnout na tmavý režim (projektor)'}
      suppressHydrationWarning
    >
      {mounted && resolvedTheme === 'dark' ? (
        <>
          <Sun className="h-4 w-4 text-amber-400" aria-hidden />
          <span className="hidden sm:inline">Světlý</span>
        </>
      ) : (
        <>
          <Moon className="h-4 w-4 text-slate-700 dark:text-slate-300" aria-hidden />
          <span className="hidden sm:inline">Projektor</span>
        </>
      )}
    </button>
  );
}
