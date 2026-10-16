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
      className={`relative flex h-9 w-9 items-center justify-center rounded-xl border border-border bg-card/60 text-muted-foreground hover:bg-accent hover:text-foreground transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-ring ${className || ''}`}
      aria-label="Přepnout motiv"
      title={resolvedTheme === 'dark' ? 'Přepnout na světlý režim' : 'Přepnout na tmavý režim'}
      suppressHydrationWarning
    >
      {!mounted || resolvedTheme === 'dark' ? (
        <Sun className="h-4 w-4 text-amber-400 transition-transform duration-200 rotate-0 hover:rotate-45" />
      ) : (
        <Moon className="h-4 w-4 text-indigo-600 transition-transform duration-200 rotate-0 hover:-rotate-12" />
      )}
    </button>
  );
}
