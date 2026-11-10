'use client';

import * as React from 'react';
import Link from 'next/link';
import { TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PILOT_FEEDBACK_URL } from '@/lib/pilot';

/**
 * Chybová obrazovka (T-374): pád komponenty nesmí skončit bílou stránkou. Bez technických detailů;
 * kód chyby (`digest`) jen pro hlášení koordinátorovi. Data pacienta se nezměnila, stačí zkusit znovu.
 */
export function ErrorScreen({ error, retry, fullPage = false }: { error: Error & { digest?: string }; retry: () => void; fullPage?: boolean }) {
  React.useEffect(() => {
    console.error(error);
  }, [error]);
  const external = PILOT_FEEDBACK_URL && !PILOT_FEEDBACK_URL.startsWith('mailto:');

  return (
    <div role="alert" className={fullPage ? 'flex min-h-dvh items-center justify-center bg-background px-4' : 'flex flex-1 items-center justify-center px-4 py-16'}>
      <div className="max-w-md text-center">
        <TriangleAlert className="mx-auto size-8 text-amber-600" aria-hidden />
        <h1 className="mt-4 text-xl font-semibold text-foreground">Něco se pokazilo</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Tuhle obrazovku se nepodařilo zobrazit. Uložená data se nezměnila. Zkuste to znovu; když to nepomůže, vraťte se na přehled.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button onClick={() => retry()}>Zkusit znovu</Button>
          <Link href="/dashboard">
            <Button variant="outline">Zpět na přehled</Button>
          </Link>
        </div>
        {PILOT_FEEDBACK_URL && (
          <p className="mt-6 text-sm">
            <a href={PILOT_FEEDBACK_URL} className="font-medium text-primary underline underline-offset-4"
              {...(external ? { target: '_blank', rel: 'noreferrer' } : {})}>
              Nahlásit problém
            </a>
          </p>
        )}
        {error.digest && <p className="mt-3 text-xs text-muted-foreground">Kód chyby pro hlášení: {error.digest}</p>}
      </div>
    </div>
  );
}
