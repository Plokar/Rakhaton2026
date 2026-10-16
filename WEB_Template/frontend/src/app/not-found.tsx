'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import {
  Zap,
  Home,
  LayoutDashboard,
  ArrowLeft,
  Bot,
  Terminal,
  ShieldCheck,
  Search,
  Compass,
} from 'lucide-react';

export default function NotFound() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground relative overflow-hidden">
      {/* Background ambient lighting */}
      <div className="absolute -top-40 left-1/2 -translate-x-1/2 h-96 w-96 rounded-full bg-primary/20 blur-[120px] pointer-events-none" />
      <div className="absolute -bottom-40 right-10 h-96 w-96 rounded-full bg-cyan-500/15 blur-[120px] pointer-events-none" />

      {/* Subtle grid */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,var(--border)_1px,transparent_1px),linear-gradient(to_bottom,var(--border)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,#000_70%,transparent_100%)] opacity-25 pointer-events-none" />

      {/* Header */}
      <header className="relative z-10 w-full border-b border-border bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-indigo-500/30">
              <Zap className="h-5 w-5 fill-current" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight">Hackathon OS</span>
              <span className="text-[10px] font-mono text-muted-foreground">Error 404</span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link href="/dashboard">
              <Button size="sm" variant="outline" className="gap-1.5 text-xs">
                <LayoutDashboard className="h-3.5 w-3.5" /> Dashboard
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-16 sm:px-6 lg:px-8">
        <div className="w-full max-w-2xl text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 rounded-full border border-destructive/30 bg-destructive/10 px-3.5 py-1 text-xs font-semibold text-destructive mb-6 animate-in fade-in slide-in-from-top-3">
            <Compass className="h-3.5 w-3.5 animate-spin text-destructive" style={{ animationDuration: '8s' }} />
            404 • Stránka nenalezena
          </div>

          {/* Glowing 404 text */}
          <div className="relative my-2 select-none">
            <span className="text-8xl sm:text-9xl font-extrabold tracking-widest text-transparent bg-clip-text bg-gradient-to-b from-primary via-indigo-500 to-transparent opacity-80">
              404
            </span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-foreground mt-2">
            Ztraceno v digitálním prostoru
          </h1>

          <p className="mt-3 text-sm sm:text-base text-muted-foreground max-w-md mx-auto leading-relaxed">
            Stránka, kterou hledáte, neexistuje, byla přesunuta nebo ještě nebyla doprogramována
          </p>

          {/* Actions */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={() => router.back()}
              className="gap-2 text-xs sm:text-sm"
            >
              <ArrowLeft className="h-4 w-4" /> Vrátit se zpět
            </Button>
            <Link href="/">
              <Button size="lg" className="gap-2 text-xs sm:text-sm shadow-md shadow-indigo-500/20">
                <Home className="h-4 w-4" /> Domovská stránka
              </Button>
            </Link>
          </div>


        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 py-6 text-center text-xs text-muted-foreground border-t border-border">
        <div className="mx-auto max-w-7xl px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Hackathon OS v2.0 • 404 Handler</span>
          <div className="flex items-center gap-4">
            <Link href="/privacy" className="hover:text-foreground transition">Zásady soukromí</Link>
            <Link href="/terms" className="hover:text-foreground transition">Podmínky užití</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
