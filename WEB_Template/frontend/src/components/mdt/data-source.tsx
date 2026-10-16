'use client';

import * as React from 'react';
import { evidenceP03, observationsP03, timelineP03 } from '@/lib/fixtures';
import { mdtApi } from '@/lib/mdt-api';
import type { EvidenceId, EvidenceSource, ObservationSeries, TimelineEvent } from '@/types/mdt';

/** Odkud podklad bere zdroje citací a data pacienta: z API (IRIS), nebo z fixtures (demo bez backendu). */
export interface BriefDataSource {
  loadSource: (id: EvidenceId) => Promise<EvidenceSource>;
  loadTimeline: (patientId: string) => Promise<TimelineEvent[]>;
  loadObservations: (patientId: string) => Promise<ObservationSeries[]>;
}

export const apiDataSource: BriefDataSource = {
  loadSource: (id) => mdtApi.getEvidence(id),
  loadTimeline: (pid) => mdtApi.getTimeline(pid),
  loadObservations: (pid) => mdtApi.getObservations(pid),
};

export const fixtureDataSource: BriefDataSource = {
  loadSource: async (id) => {
    const source = (await evidenceP03())[id];
    if (!source) throw new Error('Zdroj ve fixtures není.');
    return source;
  },
  loadTimeline: async () => timelineP03,
  loadObservations: async () => observationsP03,
};

const BriefDataContext = React.createContext<BriefDataSource>(apiDataSource);

export function BriefDataProvider({ value, children }: { value: BriefDataSource; children: React.ReactNode }) {
  return <BriefDataContext.Provider value={value}>{children}</BriefDataContext.Provider>;
}

export function useBriefData(): BriefDataSource {
  return React.useContext(BriefDataContext);
}
