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

// ── Týdny kalendáře ─────────────────────────────────────────────────────────
// Klíč dne „2026-10-21“ se převádí na poledne UTC: přechod letního času ani pásmo prohlížeče den neposunou.

const DAY_MS = 86_400_000;
const atNoon = (day: string) => new Date(`${day}T12:00:00Z`);
const toDay = (date: Date) => date.toISOString().slice(0, 10);

export const addDays = (day: string, n: number) => toDay(new Date(atNoon(day).getTime() + n * DAY_MS));

/** Pondělí týdne, do kterého den patří. */
export function mondayOf(day: string): string {
  const weekday = (atNoon(day).getUTCDay() + 6) % 7;
  return addDays(day, -weekday);
}

/** ISO týden („2026-W43“) podle čtvrtka daného týdne. */
export function isoWeekKey(day: string): string {
  const thursday = addDays(mondayOf(day), 3);
  const year = Number(thursday.slice(0, 4));
  const firstMonday = mondayOf(`${year}-01-04`);
  const week = Math.round((atNoon(thursday).getTime() - atNoon(addDays(firstMonday, 3)).getTime()) / (7 * DAY_MS)) + 1;
  return `${year}-W${String(week).padStart(2, '0')}`;
}

/** „2026-W43“ → pondělí („2026-10-19“); neplatný klíč → `null`. */
export function mondayOfWeekKey(key: string | null | undefined): string | null {
  const match = key?.match(/^(\d{4})-W(\d{2})$/);
  if (!match) return null;
  const week = Number(match[2]);
  if (week < 1 || week > 53) return null;
  return addDays(mondayOf(`${match[1]}-01-04`), (week - 1) * 7);
}

export const weekNumber = (day: string) => Number(isoWeekKey(day).slice(-2));

const SHORT_DAY = new Intl.DateTimeFormat('cs-CZ', { weekday: 'short', timeZone: 'UTC' });
const DAY_MONTH = new Intl.DateTimeFormat('cs-CZ', { day: 'numeric', month: 'numeric', timeZone: 'UTC' });

/** Klíč dne → „st“ a „21. 10.“ zvlášť (nadpis sloupce kalendáře). */
export const weekdayShort = (day: string) => SHORT_DAY.format(atNoon(day));
export const dayMonth = (day: string) => DAY_MONTH.format(atNoon(day)).replace(/\s+/g, ' ');

/** „19.–23. 10. 2026“, přes měsíc „28. 9.–2. 10. 2026“. */
export function rangeLabel(from: string, to: string): string {
  const [fy, fm, fd] = from.split('-').map(Number);
  const [ty, tm, td] = to.split('-').map(Number);
  if (fy === ty && fm === tm) return `${fd}.–${td}. ${tm}. ${ty}`;
  if (fy === ty) return `${fd}. ${fm}.–${td}. ${tm}. ${ty}`;
  return `${fd}. ${fm}. ${fy}–${td}. ${tm}. ${ty}`;
}

/** Datum a čas pro `<input type="datetime-local">` v Praze („2026-10-21T14:00“). */
export function localInputValue(iso: string): string {
  return `${pragueDay(iso)}T${timeLabel(iso)}`;
}
