'use client';

import { ErrorScreen } from '@/components/layout/ErrorScreen';

/** Chyba obrazovky uvnitř shellu: postranní panel a horní lišta zůstanou, spadne jen obsah (T-374). */
export default function DashboardError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <ErrorScreen error={error} retry={retry} />;
}
