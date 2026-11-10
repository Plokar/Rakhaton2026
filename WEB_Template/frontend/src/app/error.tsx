'use client';

import { ErrorScreen } from '@/components/layout/ErrorScreen';

/** Chyba mimo shell aplikace (přihlášení, projektor, pozvánka): T-374. */
export default function AppError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  return <ErrorScreen error={error} retry={retry} fullPage />;
}
