/**
 * Rodné číslo v poli hledání pacienta (T-356): formát při psaní a kontrola jako `services/rc.py` na backendu.
 * `RRMMDD/XXXX` od roku 1954 (dělitelné 11, výjimka do 1985: zbytek 10 a kontrolní 0), `RRMMDD/XXX` do roku 1953.
 * Ženy mají měsíc +50, od roku 2004 smí být měsíc ještě +20.
 */

/** Dotaz začíná číslicí → píše se RČ (ne jméno ani Pxx). */
export const isRcInput = (value: string) => /^\s*\d/.test(value);

/** Jen číslice (nejvýš 10) a lomítko za šestou: „6553151234“ → „655315/1234“. */
export function formatRc(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 10);
  return digits.length > 6 ? `${digits.slice(0, 6)}/${digits.slice(6)}` : digits;
}

/** Chyba česky, nebo null, když je RČ platné. Neúplné RČ (méně než 9 číslic) vrací `incomplete`. */
export function validateRc(value: string, today = new Date()): string | 'incomplete' | null {
  const digits = value.replace(/\D/g, '');
  if (digits.length < 9) return 'incomplete';
  if (digits.length > 10) return 'Rodné číslo má nejvýš 10 číslic.';
  const yy = Number(digits.slice(0, 2));
  const mm = Number(digits.slice(2, 4));
  const dd = Number(digits.slice(4, 6));
  let year: number;
  if (digits.length === 9) {
    if (yy >= 54) return 'Devítimístné rodné číslo mají jen lidé narození do roku 1953.';
    year = 1900 + yy;
  } else {
    year = yy < 54 ? 2000 + yy : 1900 + yy;
    // 10 číslic se do Number vejde přesně (< 2^53)
    const mod = Number(digits) % 11;
    const legacy = Number(digits.slice(0, 9)) % 11 === 10 && digits[9] === '0' && year < 1986;
    if (mod !== 0 && !legacy) return 'Rodné číslo nemá platnou kontrolní číslici (není dělitelné 11).';
  }
  let month = mm > 50 ? mm - 50 : mm;
  if (month > 20 && year >= 2004) month -= 20;
  const born = new Date(year, month - 1, dd);
  if (month < 1 || month > 12 || born.getMonth() !== month - 1 || born.getDate() !== dd) {
    return 'Rodné číslo neobsahuje platné datum narození.';
  }
  if (born > today) return 'Datum narození z rodného čísla je v budoucnosti.';
  return null;
}
