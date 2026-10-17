/** Data zasedání v pražském čase (Intl), sdílené kalendářem, sidebarem a jednáním. */
const TZ = 'Europe/Prague';

const DAY = new Intl.DateTimeFormat('cs-CZ', { weekday: 'short', day: 'numeric', month: 'numeric', timeZone: TZ });
const DAY_LONG = new Intl.DateTimeFormat('cs-CZ', { weekday: 'long', day: 'numeric', month: 'numeric', year: 'numeric', timeZone: TZ });
const TIME = new Intl.DateTimeFormat('cs-CZ', { hour: '2-digit', minute: '2-digit', timeZone: TZ });
const ISO_DAY = new Intl.DateTimeFormat('en-CA', { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: TZ });

/** „st 21. 10.“ */
export const dayLabel = (iso: string | Date) => DAY.format(new Date(iso)).replace(/\s+/g, ' ');
/** „středa 21. 10. 2026“ */
export const dayLabelLong = (iso: string | Date) => DAY_LONG.format(new Date(iso));
/** „14:00“ */
export const timeLabel = (iso: string | Date) => TIME.format(new Date(iso));
/** Den zasedání v Praze jako „2026-10-21“ (klíč buňky kalendáře). */
export const pragueDay = (iso: string | Date) => ISO_DAY.format(new Date(iso));
/** Dnešek v Praze („2026-10-17“). */
export const todayPrague = () => pragueDay(new Date());

/** Český tvar „1 pacient / 2 pacienti / 5 pacientů“. */
export function patientsLabel(n: number): string {
  if (n === 1) return '1 pacient';
  if (n >= 2 && n <= 4) return `${n} pacienti`;
  return `${n} pacientů`;
}
