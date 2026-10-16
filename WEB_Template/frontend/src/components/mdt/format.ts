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
