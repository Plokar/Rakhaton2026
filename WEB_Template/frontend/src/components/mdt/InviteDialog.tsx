'use client';

import * as React from 'react';
import { Check, Copy } from 'lucide-react';
import { Button } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';

/**
 * Pozvání kolegy: přihlášený předseda se na /register nedostane (proxy ho vrátí na dashboard), proto
 * mu dáme odkaz, který pošle kolegovi. Roli a odbornost pak upraví v Týmu komise (T-319).
 */
export function InviteDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [copy, setCopy] = React.useState<'idle' | 'done' | 'failed'>('idle');
  const link = typeof window === 'undefined' ? '/register' : `${window.location.origin}/register`;
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(link);
      setCopy('done');
    } catch {
      setCopy('failed');     // schránka bez HTTPS nebo bez oprávnění: odkaz zůstane k ručnímu zkopírování
    }
  };
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Pozvat kolegu</DialogTitle>
          <DialogDescription>
            Pošlete kolegovi odkaz na registraci. Při registraci si vybere odbornost a má přístup člena komise; roli
            předsedy nebo zadávajícího lékaře mu pak nastavíte v Týmu komise.
          </DialogDescription>
        </DialogHeader>
        <p className="select-all rounded-md bg-muted px-3 py-2 text-sm">{link}</p>
        <p role="status" className="sr-only">{copy === 'done' ? 'Odkaz na registraci je ve schránce.' : ''}</p>
        {copy === 'failed' && <p role="alert" className="text-sm">Odkaz se nepodařilo zkopírovat, označte ho ručně.</p>}
        <DialogFooter>
          <Button variant="outline" size="lg" onClick={onClose}>Zavřít</Button>
          <Button size="lg" onClick={copyLink}>
            {copy === 'done' ? <Check aria-hidden /> : <Copy aria-hidden />}
            {copy === 'done' ? 'Zkopírováno' : 'Zkopírovat odkaz'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
