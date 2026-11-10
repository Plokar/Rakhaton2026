'use client';

import * as React from 'react';
import { hasUnsaved } from '@/lib/unsaved';

/** Nečinnost v minutách, po které se uživatel odhlásí (sdílené počítače na oddělení). `0` = vypnuto. */
export const IDLE_MINUTES = Number(process.env.NEXT_PUBLIC_IDLE_MINUTES ?? 30) || 0;
export const WARNING_SECONDS = 60;

const STORAGE_KEY = 'mdt-last-activity';
const EVENTS = ['pointerdown', 'pointermove', 'keydown', 'wheel', 'touchstart'] as const;

function readShared(): number {
  try {
    return Number(window.localStorage.getItem(STORAGE_KEY)) || 0;
  } catch {
    return 0;
  }
}

function writeShared(at: number): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, String(at));
  } catch {
    /* soukromé okno: nečinnost se hlídá jen v této záložce */
  }
}

/**
 * Odhlášení při nečinnosti (T-373). Po `IDLE_MINUTES` bez myši, klávesnice a dotyku vrátí `secondsLeft`
 * (dialog „Budete odhlášeni“), po dalších `WARNING_SECONDS` zavolá `onLogout`.
 *
 * - Aktivita v jedné záložce platí pro všechny (čas poslední aktivity je v localStorage).
 * - `exempt` (promítání živého zasedání) se počítá jako aktivita.
 * - S neuloženou prací (`hasUnsaved`) se neodhlašuje: dialog zůstane, dokud uživatel neodpoví (`unsaved`).
 */
export function useIdleLogout({ exempt, onLogout }: { exempt: boolean; onLogout: () => void }) {
  const [secondsLeft, setSecondsLeft] = React.useState<number | null>(null);
  const [unsaved, setUnsaved] = React.useState(false);
  const lastLocal = React.useRef(0);
  const lastWrite = React.useRef(0);
  const loggedOut = React.useRef(false);
  const logoutRef = React.useRef(onLogout);
  const exemptRef = React.useRef(exempt);
  React.useEffect(() => {
    logoutRef.current = onLogout;
    exemptRef.current = exempt;
  }, [onLogout, exempt]);

  const touch = React.useCallback(() => {
    const now = Date.now();
    lastLocal.current = now;
    if (now - lastWrite.current > 5000) {
      lastWrite.current = now;
      writeShared(now);
    }
  }, []);

  /** „Zůstat přihlášen“: zapíše aktivitu hned (i pro ostatní záložky) a zavře dialog. */
  const stay = React.useCallback(() => {
    lastWrite.current = 0;
    touch();
    setSecondsLeft(null);
    setUnsaved(false);
  }, [touch]);

  React.useEffect(() => {
    if (!IDLE_MINUTES) return;
    const limit = IDLE_MINUTES * 60_000;
    lastWrite.current = 0;
    touch();
    EVENTS.forEach((name) => window.addEventListener(name, touch, { passive: true }));
    const timer = window.setInterval(() => {
      if (loggedOut.current) return;
      if (exemptRef.current) touch();
      const idle = Date.now() - Math.max(lastLocal.current, readShared());
      if (idle < limit) {
        setSecondsLeft(null);
        setUnsaved(false);
        return;
      }
      const left = Math.ceil((limit + WARNING_SECONDS * 1000 - idle) / 1000);
      if (hasUnsaved()) {
        setUnsaved(true);
        setSecondsLeft(Math.max(0, left));
        return;
      }
      if (left > 0) {
        setSecondsLeft(left);
        return;
      }
      loggedOut.current = true;
      logoutRef.current();
    }, 1000);
    return () => {
      EVENTS.forEach((name) => window.removeEventListener(name, touch));
      window.clearInterval(timer);
    };
  }, [touch]);

  return { secondsLeft, unsaved, stay };
}
