'use client';

import { useQuery } from '@tanstack/react-query';
import { Skeleton } from '@/components/shadcn/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import { Citations } from './citations';
import { formatDate } from './format';

/**
 * Podobné případy (BONUS B2, T-332): předchozí závěry MDT jiných pacientů s obdobnou diagnózou, anonymizovaně
 * (pohlaví a věková dekáda). Inspirace pro diskusi, ne doporučení; citace otevře celý záznam komise.
 */
export function SimilarCases({ caseId }: { caseId: number }) {
  const query = useQuery({ queryKey: ['case', caseId, 'similar'], queryFn: () => mdtApi.getSimilarCases(caseId), staleTime: 300_000 });
  if (query.isLoading) return <Skeleton className="h-24 w-full" />;
  if (query.isError) return <p role="alert" className="text-sm text-destructive">{apiErrorMessage(query.error, 'Podobné případy se nepodařilo načíst.')}</p>;
  const data = query.data;
  if (!data?.cases.length) {
    return (
      <p className="text-sm text-muted-foreground">
        {data?.diagnosis
          ? `V systému zatím není jiný záznam komise pro ${data.diagnosis.icd10} ani pro kategorii ${data.diagnosis.icd10.slice(0, 3)}.`
          : 'Diagnóza případu chybí, podobné případy nejde hledat.'}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      <ul className="flex flex-col gap-3">
        {data.cases.map((c) => (
          <li key={c.composition_id} className="rounded-xl border border-border p-3">
            <p className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm">
              <span translate="no" className="font-semibold">{c.diagnosis.icd10}</span>
              <span className="text-muted-foreground">{c.patient} · komise {formatDate(c.date)}</span>
              <span className="text-xs text-muted-foreground">{c.match === 'code' ? 'stejný kód MKN-10' : 'stejná kategorie MKN-10'}</span>
              <Citations ids={c.citations} />
            </p>
            {c.question && <p className="mt-1.5 text-[13px] text-muted-foreground"><span className="font-medium text-foreground">Otázka:</span> {c.question}</p>}
            {c.recommendation && <p className="mt-1 line-clamp-3 text-[13px]"><span className="font-medium">Postup:</span> {c.recommendation}</p>}
            {c.conclusion && <p className="mt-1 line-clamp-3 text-[13px]"><span className="font-medium">Závěr:</span> {c.conclusion}</p>}
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">Předchozí závěry komise u jiných pacientů jako inspirace pro diskusi, nejde o doporučení.</p>
    </div>
  );
}
