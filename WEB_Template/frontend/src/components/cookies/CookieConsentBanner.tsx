'use client';

import * as React from 'react';
import Link from 'next/link';
import { useCookieConsent } from '@/contexts/CookieContext';
import { Button } from '@/components/ui/button';

/**
 * Souhlas s cookies: věcná lišta dole, nic nezakrývá uprostřed obrazovky. Aplikace používá jen
 * nezbytné cookies přihlášení; volitelné jdou zapnout v předvolbách.
 */
export function CookieConsentBanner() {
  const { showBanner, isLoaded, acceptAll, acceptNecessaryOnly, openSettings } = useCookieConsent();

  if (!isLoaded || !showBanner) return null;

  return (
    <div
      role="region"
      aria-label="Souhlas s cookies"
      className="fixed inset-x-3 bottom-3 z-50 rounded-xl border border-border bg-popover p-4 text-popover-foreground shadow-[0_12px_32px_-12px_rgb(15_23_42/0.3)] sm:inset-x-auto sm:right-6 sm:bottom-6 sm:max-w-md"
    >
      <p className="text-sm font-semibold">Cookies</p>
      <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">
        Pro přihlášení a ochranu relace používáme jen nezbytné cookies. Volitelné analytické můžete povolit.{' '}
        <Link href="/privacy" className="font-medium text-foreground underline underline-offset-4">
          Zásady soukromí
        </Link>
      </p>
      <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={openSettings} className="mr-auto">
          Předvolby
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={acceptNecessaryOnly}>
          Jen nezbytné
        </Button>
        <Button type="button" size="sm" onClick={acceptAll}>
          Povolit vše
        </Button>
      </div>
    </div>
  );
}
