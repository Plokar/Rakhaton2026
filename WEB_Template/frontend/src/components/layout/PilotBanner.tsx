'use client';

import { FlaskConical } from 'lucide-react';
import { PILOT_FEEDBACK_URL, PILOT_MODE } from '@/lib/pilot';

/**
 * Pruh pilotního provozu nad obsahem (T-355): připomíná, že v aplikaci jsou jen fiktivní pacienti, a nabízí
 * nahlášení problému. Na okně projektoru není (to má vlastní layout bez shellu).
 */
export function PilotBanner() {
  if (!PILOT_MODE) return null;
  return (
    <div
      role="note"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-[13px] text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/40 dark:text-amber-100"
    >
      <span className="inline-flex items-center gap-1.5 font-medium">
        <FlaskConical className="size-4" aria-hidden />
        Pilotní provoz
      </span>
      <span>Jen fiktivní pacienti. Nezadávejte ani nenahrávejte skutečné údaje pacientů.</span>
      {PILOT_FEEDBACK_URL && (
        <a
          href={PILOT_FEEDBACK_URL}
          target={PILOT_FEEDBACK_URL.startsWith('mailto:') ? undefined : '_blank'}
          rel="noreferrer"
          className="ml-auto font-medium underline underline-offset-2 hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        >
          Nahlásit problém nebo nápad
        </a>
      )}
    </div>
  );
}
