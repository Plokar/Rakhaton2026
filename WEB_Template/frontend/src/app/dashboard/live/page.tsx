'use client';

import * as React from 'react';
import { LiveView } from '@/components/mdt/live/LiveView';

/** Živě na MDT (T-354): pacient na projektoru, jeho detail a dotazy na AI z mobilu; `?zasedani=` vybere zasedání. */
export default function LivePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = React.use(searchParams);
  const raw = Number(Array.isArray(params.zasedani) ? params.zasedani[0] : params.zasedani);
  return <LiveView initialSession={Number.isInteger(raw) && raw > 0 ? raw : null} />;
}
