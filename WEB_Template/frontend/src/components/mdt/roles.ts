import type { RoleId } from '@/types/mdt';

/**
 * Odbornosti a jejich barvy (D-017). Barva odbornosti se nesmí plést se semaforem
 * (zelená, oranžová, červená, šedá) ani s AI (fialová), a vždy je u ní i text.
 */
export const ROLE_META: Record<RoleId, { label: string; className: string }> = {
  surgeon: { label: 'Chirurg', className: 'bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30' },
  oncologist: { label: 'Klinický onkolog', className: 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30' },
  radiation_oncologist: {
    label: 'Radiační onkolog',
    className: 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-500/30',
  },
  radiologist: { label: 'Radiolog', className: 'bg-cyan-500/15 text-cyan-700 dark:text-cyan-300 border-cyan-500/30' },
  pathologist: { label: 'Patolog', className: 'bg-slate-500/15 text-slate-700 dark:text-slate-300 border-slate-500/30' },
  pulmonologist: { label: 'Pneumolog', className: 'bg-stone-500/15 text-stone-700 dark:text-stone-300 border-stone-500/30' },
  cardiologist: { label: 'Kardiolog', className: 'bg-zinc-500/15 text-zinc-700 dark:text-zinc-300 border-zinc-500/30' },
  patient: { label: 'Pacient', className: 'bg-pink-500/15 text-pink-700 dark:text-pink-300 border-pink-500/30' },
};
