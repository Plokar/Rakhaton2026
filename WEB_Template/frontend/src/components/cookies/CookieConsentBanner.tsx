'use client';

import * as React from 'react';
import Link from 'next/link';
import { useCookieConsent } from '@/contexts/CookieContext';
import { Button } from '@/components/ui/button';
import { Cookie, SlidersHorizontal, ShieldCheck, ArrowRight } from 'lucide-react';

export function CookieConsentBanner() {
  const {
    showBanner,
    isLoaded,
    acceptAll,
    acceptNecessaryOnly,
    openSettings,
  } = useCookieConsent();

  if (!isLoaded || !showBanner) {
    return null;
  }

  return (
    <div
      role="region"
      aria-label="Nastavení soukromí a souborů cookies"
      className="fixed bottom-3 left-3 right-3 sm:bottom-6 sm:right-6 sm:left-auto sm:max-w-md md:max-w-lg z-50 animate-in fade-in slide-in-from-bottom-6 duration-300"
    >
      <div className="relative overflow-hidden rounded-2xl border border-primary/20 bg-card/95 p-5 shadow-2xl backdrop-blur-xl ring-1 ring-white/10 dark:ring-black/20">
        {/* Subtle accent glow */}
        <div className="absolute -right-12 -top-12 h-32 w-32 rounded-full bg-primary/15 blur-2xl pointer-events-none" />

        <div className="flex items-start gap-3.5">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary border border-primary/20 shadow-sm">
            <Cookie className="h-5 w-5 fill-current/20" />
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground tracking-tight">
                Soukromí a správa cookies
              </h3>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                <ShieldCheck className="h-3 w-3" /> GDPR Ready
              </span>
            </div>

            <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
              Tento web používá nezbytné cookies pro JWT autentizaci, CSRF ochranu a správu relace.
              Volitelné analytické cookies nám pomáhají zlepšovat odezvu a funkce šablony.
            </p>

            <div className="mt-2 flex items-center gap-3 text-[11px] text-muted-foreground">
              <Link
                href="/privacy"
                className="font-medium text-primary hover:underline inline-flex items-center gap-0.5"
              >
                Zásady soukromí
              </Link>
              <span>•</span>
              <Link
                href="/terms"
                className="font-medium text-primary hover:underline inline-flex items-center gap-0.5"
              >
                Podmínky užití
              </Link>
            </div>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-border flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={openSettings}
            className="text-xs text-muted-foreground hover:text-foreground justify-center gap-1.5 h-8 px-2"
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Upravit předvolby
          </Button>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={acceptNecessaryOnly}
              className="text-xs flex-1 sm:flex-initial h-8 px-3"
            >
              Pouze nezbytné
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={acceptAll}
              className="text-xs flex-1 sm:flex-initial h-8 px-3.5 shadow-sm shadow-indigo-500/20"
            >
              Přijmout vše
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
