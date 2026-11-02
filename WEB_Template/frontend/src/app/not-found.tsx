'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Activity, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { buttonVariants } from '@/components/shadcn/button';
import { ThemeToggle } from '@/components/ui/theme-toggle';

export default function NotFound() {
  const router = useRouter();

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b border-border">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Activity className="size-4" aria-hidden />
            </span>
            <span translate="no" className="text-sm font-semibold">MedTeam</span>
          </Link>
          <ThemeToggle />
        </div>
      </header>

      <main className="flex flex-1 items-center px-4 py-16 sm:px-6">
        <div className="mx-auto w-full max-w-md">
          <p className="font-mono text-sm tabular-nums text-muted-foreground">404</p>
          <h1 className="mt-2 text-2xl font-semibold text-foreground">Stránka neexistuje</h1>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Odkaz je neplatný nebo stránka byla přesunuta. Zasedání a pacienti jsou v přehledu.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link href="/dashboard" className={buttonVariants({ size: 'lg' })}>
              Otevřít přehled
            </Link>
            <Button type="button" variant="ghost" onClick={() => router.back()} className="gap-2">
              <ArrowLeft className="size-4" aria-hidden /> Zpět
            </Button>
          </div>
        </div>
      </main>

      <footer className="border-t border-border py-4 text-xs text-muted-foreground">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-2 px-4 sm:px-6">
          <span translate="no">MedTeam</span>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="transition-colors hover:text-foreground">Zásady soukromí</Link>
            <Link href="/terms" className="transition-colors hover:text-foreground">Podmínky užití</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
