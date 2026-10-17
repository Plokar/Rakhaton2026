'use client';

import * as React from 'react';
import { CaseDetail } from '@/components/mdt/detail/CaseDetail';

/** Detail pacienta (NAVRH_UI §8). Totéž bez navigace v úzkém okně: `/brief/[caseId]`. */
export default function CaseBriefPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = React.use(params);
  return <CaseDetail key={caseId} caseId={caseId} />;
}
