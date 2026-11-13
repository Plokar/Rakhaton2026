/** Datum z FHIR (i částečné „2019-03“) v českém formátu. */
export function formatDate(value: string | null | undefined): string {
  if (!value) return '';
  const [datePart, timePart] = value.split('T');
  const [year, month, day] = datePart.split('-');
  if (!month) return year;
  if (!day) return `${Number(month)}/${year}`;
  const date = `${Number(day)}. ${Number(month)}. ${year}`;
  return timePart ? `${date} ${timePart.slice(0, 5)}` : date;
}

/** ISO data uvnitř textu tvrzení („2026-09-08 · MR prostaty“) česky jako jinde v aplikaci; text podkladu se nemění. */
export function formatDatesInText(text: string): string {
  return text.replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, (_, y: string, m: string, d: string) => `${Number(d)}. ${Number(m)}. ${y}`);
}
