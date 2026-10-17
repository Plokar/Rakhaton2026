import type { MdtCase, PatientListItem } from '@/types/mdt';

const SEX_SHORT: Record<PatientListItem['sex'], string> = { male: 'M', female: 'Ž', other: 'J', unknown: '?' };
const SEX_LONG: Record<PatientListItem['sex'], string> = { male: 'muž', female: 'žena', other: 'jiné', unknown: 'neuvedeno' };

/** Zkrácená hlavička čipu „P05 · Ž · 68“ (D-018: bez jména a RČ). */
export function shortPatient(item: Pick<MdtCase, 'patient_id' | 'patient'>): string {
  const p = item.patient;
  if (!p) return item.patient_id;
  return [item.patient_id, SEX_SHORT[p.sex], p.age ?? null].filter((part) => part !== null).join(' · ');
}

/** Pro čtečky a tooltip: „P05, žena, 68 let“. */
export function spokenPatient(item: Pick<MdtCase, 'patient_id' | 'patient'>): string {
  const p = item.patient;
  if (!p) return item.patient_id;
  return [item.patient_id, SEX_LONG[p.sex], p.age !== null ? `${p.age} let` : null].filter(Boolean).join(', ');
}

/** Projednáno = rozhodnuto nebo potvrzeno (jednání komise, NAVRH_UI §7.1). */
export const isDiscussed = (item: Pick<MdtCase, 'status'>) => item.status === 'decided' || item.status === 'confirmed';
