'use client';

import * as React from 'react';
import { MeetingView } from '@/components/mdt/meeting/MeetingView';

/** Jednání komise (NAVRH_UI §7): agenda, 30s přehled pacienta na řadě, zkratky, okno projektoru. */
export default function MdtSessionPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = React.use(params);
  return <MeetingView key={sessionId} sessionId={Number(sessionId)} />;
}
