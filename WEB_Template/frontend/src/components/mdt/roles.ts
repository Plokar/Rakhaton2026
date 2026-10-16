import type { RoleId } from '@/types/mdt';

/**
 * Odbornosti a jejich barvy (D-017). Barva odbornosti se nesmí plést se semaforem
 * (zelená, oranžová, červená, šedá) ani s AI označením, a vždy je u ní i text.
 */
export const ROLE_META: Record<RoleId, { label: string; className: string }> = {
  surgeon: {
    label: 'Chirurg',
    className: 'bg-sky-100 text-sky-900 border-sky-300 dark:bg-sky-950/70 dark:text-sky-200 dark:border-sky-700/70',
  },
  oncologist: {
    label: 'Klinický onkolog',
    className: 'bg-blue-100 text-blue-900 border-blue-300 dark:bg-blue-950/70 dark:text-blue-200 dark:border-blue-700/70',
  },
  radiation_oncologist: {
    label: 'Radiační onkolog',
    className: 'bg-teal-100 text-teal-900 border-teal-300 dark:bg-teal-950/70 dark:text-teal-200 dark:border-teal-700/70',
  },
  radiologist: {
    label: 'Radiolog',
    className: 'bg-cyan-100 text-cyan-900 border-cyan-300 dark:bg-cyan-950/70 dark:text-cyan-200 dark:border-cyan-700/70',
  },
  pathologist: {
    label: 'Patolog',
    className: 'bg-stone-200/80 text-stone-900 border-stone-400/70 dark:bg-stone-800/80 dark:text-stone-200 dark:border-stone-600',
  },
  pulmonologist: {
    label: 'Pneumolog',
    className: 'bg-slate-200/80 text-slate-900 border-slate-400/70 dark:bg-slate-800/80 dark:text-slate-200 dark:border-slate-600',
  },
  cardiologist: {
    label: 'Kardiolog',
    className: 'bg-rose-100 text-rose-900 border-rose-300 dark:bg-rose-950/60 dark:text-rose-200 dark:border-rose-700/60',
  },
  patient: {
    label: 'Hlas pacienta',
    className: 'bg-amber-100/80 text-amber-950 border-amber-300 dark:bg-amber-950/60 dark:text-amber-200 dark:border-amber-700/60',
  },
};

