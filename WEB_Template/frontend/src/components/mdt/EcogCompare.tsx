import { TriangleAlert } from 'lucide-react';
import type { BriefHeader } from '@/types/mdt';

type Ecog = BriefHeader['ecog'];

export function ecogDifference(ecog: Ecog): number | null {
  return ecog.physician && ecog.patient ? Math.abs(ecog.physician.value - ecog.patient.value) : null;
}

/**
 * Rozdíl ECOG lékaře a pacienta (PROMs) ≥ 1 je varovný signál (OBC-1.3): ikona a text, ne jen barva.
 * Hodnoty samotné ukazuje hlavička (FR-A2, D-018).
 */
export function EcogDifference({ ecog }: { ecog: Ecog }) {
  const diff = ecogDifference(ecog);
  if (diff === null || diff < 1) return null;
  return (
    <p className="flex items-start gap-2 rounded-lg bg-amber-50 px-3 py-2 text-[13px] leading-snug text-amber-950 dark:bg-amber-400/10 dark:text-amber-100">
      <TriangleAlert className="mt-0.5 size-4 shrink-0 text-amber-700 dark:text-amber-400" aria-hidden />
      <span>
        <span className="font-medium">ECOG lékaře {ecog.physician?.value} a pacienta {ecog.patient?.value} se liší o {diff}</span> (OBC-1.3).
        {ecog.patient?.answer_text && <> Pacient uvádí: „{ecog.patient.answer_text}“</>}
      </span>
    </p>
  );
}
