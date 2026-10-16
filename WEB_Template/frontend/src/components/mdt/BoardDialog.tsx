'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogClose, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import type { SessionInput } from '@/lib/mdt-api';
import type { MdtSession } from '@/types/mdt';

/** „2026-10-21T14:00:00+02:00“ → hodnota pro `<input type="datetime-local">`. */
function toLocalInput(iso: string | undefined): string {
  return iso ? iso.slice(0, 16) : '';
}

/**
 * Založení nebo úprava boardu (FR-P1, jen předseda). Změna termínu přepíše datum zasedání
 * v `Task` všech zařazených pacientů v IRIS, proto to dialog výslovně říká.
 */
export function BoardDialog({
  open,
  session,
  onClose,
  onSubmit,
}: {
  open: boolean;
  session?: MdtSession;
  onClose: () => void;
  onSubmit: (input: SessionInput) => Promise<void>;
}) {
  const [title, setTitle] = React.useState(session?.title ?? '');
  const [date, setDate] = React.useState(toLocalInput(session?.date));
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !date) {
      setError('Vyplňte název komise a termín.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({ title: title.trim(), date: `${date}:00` });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Uložení se nepodařilo.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogClose onClick={onClose} />
      <DialogHeader>
        <DialogTitle>{session ? 'Upravit board' : 'Nový board'}</DialogTitle>
        <DialogDescription>
          {session
            ? 'Změna termínu se zapíše do nominací všech pacientů v agendě (IRIS).'
            : 'Board = jedno zasedání komise s termínem a agendou pacientů.'}
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={submit} className="mt-2 space-y-4">
        <div>
          <label htmlFor="board-title" className="mb-1.5 block text-xs font-semibold text-foreground">
            Komise
          </label>
          <Input
            id="board-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="např. GIT – kolorektální karcinom / hepatobiliární"
            autoFocus
          />
        </div>
        <div>
          <label htmlFor="board-date" className="mb-1.5 block text-xs font-semibold text-foreground">
            Termín zasedání
          </label>
          <Input id="board-date" type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Zrušit
          </Button>
          <Button type="submit" isLoading={saving}>
            {session ? 'Uložit' : 'Založit board'}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
