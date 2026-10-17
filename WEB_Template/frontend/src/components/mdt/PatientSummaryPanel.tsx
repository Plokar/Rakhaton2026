'use client';

import * as React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import type { Decision } from '@/types/mdt';
import { AiBlock } from './AiBlock';
import { ClaimList } from './ClaimList';
import { formatDate } from './format';
import { JobProgress } from './JobProgress';

type Summary = NonNullable<Decision['patient_summary']>;

/**
 * Shrnutí závěru pro pacienta (BON-4): AI ho vytvoří z potvrzeného závěru laickým jazykem, každá věta
 * s citací. Uloží se jako `DocumentReference` a je i v PDF exportu; před předáním ho zkontroluje lékař.
 */
export function PatientSummaryPanel({ caseId, initial, canCreate }: { caseId: string; initial?: Summary | null; canCreate: boolean }) {
  const client = useQueryClient();
  const summary = useQuery({
    queryKey: ['case', caseId, 'patient-summary'],
    queryFn: () =>
      mdtApi.getPatientSummary(caseId).catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }),
    initialData: initial ?? undefined,
  });
  const [jobId, setJobId] = React.useState<number | null>(null);
  const [starting, setStarting] = React.useState(false);

  const start = async () => {
    setStarting(true);
    try {
      const { job_id } = await mdtApi.generatePatientSummary(caseId);
      setJobId(job_id);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Shrnutí se nepodařilo spustit.'));
    } finally {
      setStarting(false);
    }
  };
  const onDone = React.useCallback(() => {
    setJobId(null);
    void client.invalidateQueries({ queryKey: ['case', caseId, 'patient-summary'] });
    toast.success('Shrnutí pro pacienta je připravené', { description: 'Zkontrolujte ho před předáním pacientovi.' });
  }, [client, caseId]);
  const onError = React.useCallback((message: string) => {
    setJobId(null);
    toast.error(message);
  }, []);

  if (summary.isLoading) return <Skeleton className="h-24" />;
  if (summary.data) {
    return (
      <AiBlock title="Shrnutí pro pacienta" headingLevel="h2" defaultOpen>
        <ClaimList claims={summary.data.items} />
        <p className="mt-3 text-xs text-muted-foreground">
          Laický jazyk, z potvrzeného závěru, vytvořeno {formatDate(summary.data.generated_at?.slice(0, 16))}. Je součástí PDF
          exportu (<span translate="no">{summary.data.document_reference}</span>). Před předáním pacientovi ho zkontroluje lékař.
        </p>
      </AiBlock>
    );
  }
  return (
    <section className="flex flex-col items-start gap-2 rounded-xl border border-dashed border-border px-4 py-4" aria-labelledby="summary-title">
      <h2 id="summary-title" className="text-sm font-semibold">Shrnutí pro pacienta</h2>
      <p className="text-[13px] text-muted-foreground">
        AI z potvrzeného závěru připraví srozumitelné shrnutí laickým jazykem, každou větu s odkazem na závěr. Před předáním ho
        zkontroluje lékař.
      </p>
      {jobId !== null ? (
        <JobProgress jobId={jobId} onDone={onDone} onError={onError} label="Připravuji shrnutí pro pacienta…" />
      ) : canCreate ? (
        <Button variant="outline" onClick={start} isLoading={starting}>
          Vytvořit shrnutí pro pacienta
        </Button>
      ) : (
        <p className="text-xs text-muted-foreground">Shrnutí vytváří předseda, zadávající nebo přizvaný lékař.</p>
      )}
    </section>
  );
}
