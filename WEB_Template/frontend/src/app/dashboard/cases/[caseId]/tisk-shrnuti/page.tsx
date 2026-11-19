'use client';

import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Printer } from 'lucide-react';
import { Button } from '@/components/shadcn/button';
import { PatientSummaryDocument } from '@/components/mdt/PatientSummaryDocument';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, useCaseLocation } from '@/lib/queries';

/** Tisk shrnutí pro pacienta (T-384): v tisku jen dokument, bez navigace aplikace. */
export default function PrintSummaryPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = React.use(params);
  const summary = useQuery({ queryKey: ['case', caseId, 'patient-summary'], queryFn: () => mdtApi.getPatientSummary(caseId) });
  const location = useCaseLocation(Number(caseId));
  return (
    <div className="flex flex-col">
      <style>{'@media print { body * { visibility: hidden } #tisk, #tisk * { visibility: visible } #tisk { position: absolute; inset: 0 } }'}</style>
      <div className="flex justify-end px-4 pt-4 print:hidden">
        <Button onClick={() => window.print()} disabled={!summary.data}>
          <Printer aria-hidden /> Vytisknout
        </Button>
      </div>
      <div id="tisk">
        {summary.isError ? (
          <p role="alert" className="p-6 text-sm text-destructive">{apiErrorMessage(summary.error, 'Shrnutí pro pacienta zatím není.')}</p>
        ) : summary.data ? (
          <PatientSummaryDocument
            title="Shrnutí z multidisciplinární onkologické komise"
            mdtDate={location.session?.date.slice(0, 10) ?? null}
            items={summary.data.items.map((c) => ({ text: c.text }))}
          />
        ) : null}
      </div>
    </div>
  );
}
