'use client';

import * as React from 'react';
import { mdtApi, type PatientDraft, type StoredBrief } from '@/lib/mdt-api';
import type { EvidenceId, EvidenceSource } from '@/types/mdt';
import { BriefView } from './BriefView';
import type { BriefDataSource } from './data-source';
import { CaseQuickViewNarrow, staticQuickViewSources } from './quick-view';

/**
 * Zdroj citace v náhledu návrhu: podklady návrhu (`Pxx-impNN`) z textu návrhu, guidelines a studie z IRIS.
 * Údaje ze souboru FHIR a nominace v IRIS ještě nejsou, ukáže se jen vysvětlení.
 */
function draftLoader(draft: PatientDraft) {
  return async (id: EvidenceId): Promise<EvidenceSource> => {
    const docId = id.split('#')[0];
    const doc = draft.documents.find((d) => d.id === docId);
    if (doc) {
      return { evidence_id: id, kind: 'paragraph', title: doc.title, text: doc.text ?? null, resource_type: 'DocumentReference',
        resource_id: doc.id, patient_id: draft.patient_id, date: doc.date };
    }
    if (!id.startsWith(`${draft.patient_id}-`)) return mdtApi.getEvidence(id);
    return { evidence_id: id, kind: 'resource', title: id, patient_id: draft.patient_id,
      text: 'Údaj návrhu nového pacienta. Plné znění zdroje bude k dispozici po zápisu do IRIS.' };
  };
}

/**
 * Náhledy návrhu nového pacienta (T-323): úzký pás pro projektor (hlavička D-018, klíčové údaje šablony,
 * varování, semafor) a celý podklad. Počítá je server bez LLM nad návrhem; po uložení úprav se obnoví.
 */
export function DraftPreview({ draft }: { draft: PatientDraft }) {
  const preview = draft.preview;
  const loadSource = React.useMemo(() => draftLoader(draft), [draft]);
  const dataSource = React.useMemo<BriefDataSource>(
    () => ({ loadSource, loadTimeline: async () => [], loadObservations: async () => [] }),
    [loadSource],
  );
  if (!preview) return null;
  const sources = staticQuickViewSources({
    patientId: draft.patient_id,
    brief: preview.narrow as StoredBrief,
    options: preview.detail.decision_support?.treatment_options ?? [],
    intake: preview.intake,
    template: preview.template,
    loadSource,
  });
  return (
    <div className="flex flex-col gap-2">
      <details className="group rounded-lg border border-border" open>
        <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
          Náhled úzkého pásu <span className="font-normal text-muted-foreground">(okno pro projektor, tak ho uvidí komise)</span>
        </summary>
        <div className="border-t border-border p-3">
          <div className="mx-auto h-[560px] w-full max-w-[380px] overflow-hidden rounded-lg border border-border shadow-sm">
            <CaseQuickViewNarrow sources={sources} caseId={null} />
          </div>
        </div>
      </details>
      <details className="rounded-lg border border-border">
        <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
          Detailní náhled podkladu <span className="font-normal text-muted-foreground">(bez AI, z údajů návrhu)</span>
        </summary>
        <div className="border-t border-border p-3">
          <BriefView brief={preview.detail} dataSource={dataSource} />
        </div>
      </details>
    </div>
  );
}
