'use client';

import * as React from 'react';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Button } from '@/components/ui/button';
import { useMyLive } from '@/components/mdt/live/use-live';
import { IDLE_MINUTES, useIdleLogout } from '@/hooks/useIdleLogout';

const MEETING = /^\/dashboard\/mdt\/(\d+)$/;

/**
 * Odhlášení při nečinnosti v shellu aplikace (T-373): sdílený počítač na oddělení nesmí zůstat přihlášený.
 * Výjimka: jednání a „Živě na MDT“, dokud zasedání probíhá (promítá se bez dotyku). Okno projektoru
 * a úzký panel jsou mimo shell, těch se to netýká.
 */
export function IdleLogout() {
  const pathname = usePathname();
  const { logout } = useAuth();
  const { data: live } = useMyLive(IDLE_MINUTES > 0);
  const running = live?.sessions.filter((s) => s.status === 'in_progress') ?? [];
  const meetingId = MEETING.exec(pathname)?.[1];
  const exempt = meetingId
    ? running.some((s) => String(s.id) === meetingId)
    : pathname.startsWith('/dashboard/live') && running.length > 0;

  const onLogout = React.useCallback(() => {
    const login = new URL('/login', window.location.origin);
    login.searchParams.set('redirect', window.location.pathname + window.location.search);
    login.searchParams.set('duvod', 'necinnost');
    void logout().finally(() => window.location.replace(login.href));
  }, [logout]);
  const { secondsLeft, unsaved, stay } = useIdleLogout({ exempt, onLogout });

  if (secondsLeft === null) return null;
  return (
    <Dialog open onOpenChange={(open) => !open && stay()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Jste ještě tady?</DialogTitle>
          <DialogDescription>
            {unsaved
              ? `Aplikace je ${IDLE_MINUTES} minut bez aktivity. Máte neuložené změny, proto vás neodhlásíme. Uložte je, nebo se odhlaste.`
              : `Aplikace je ${IDLE_MINUTES} minut bez aktivity. Kvůli ochraně údajů pacientů vás za ${secondsLeft} s odhlásíme.`}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onLogout}>Odhlásit</Button>
          <Button onClick={stay} autoFocus>Zůstat přihlášen</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
