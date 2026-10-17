'use client';

import * as React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Label } from '@/components/shadcn/label';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { SessionInput } from '@/lib/mdt-api';
import { apiErrorMessage } from '@/lib/queries';
import type { MdtSession } from '@/types/mdt';
import { localInputValue } from './dates';

/**
 * Založení nebo úprava boardu (FR-P1, jen předseda). Změna termínu přepíše datum zasedání
 * v `Task` všech zařazených pacientů v IRIS, proto to dialog výslovně říká.
 */
export function BoardDialog({
  open,
  session,
  defaultDay,
  onClose,
  onSubmit,
}: {
  open: boolean;
  session?: MdtSession;
  /** Předvyplněný den nového boardu z kalendáře („2026-10-21“), čas 14:00. */
  defaultDay?: string;
  onClose: () => void;
  onSubmit: (input: SessionInput) => Promise<void>;
}) {
  const [title, setTitle] = React.useState(session?.title ?? '');
  const [date, setDate] = React.useState(session ? localInputValue(session.date) : defaultDay ? `${defaultDay}T14:00` : '');
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
      setError(apiErrorMessage(err, 'Board se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => !next && !saving && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{session ? 'Upravit board' : 'Nový board'}</DialogTitle>
          <DialogDescription>
            {session
              ? 'Změna termínu se zapíše do nominací všech pacientů v agendě (IRIS).'
              : 'Board je jedno zasedání komise s termínem a agendou pacientů.'}
          </DialogDescription>
        </DialogHeader>
        <form id="board-form" onSubmit={submit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="board-title">Komise</Label>
            <Input
              id="board-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="např. GIT – kolorektální karcinom / hepatobiliární…"
              autoComplete="off"
              autoFocus
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="board-date">Termín zasedání</Label>
            <Input id="board-date" type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} />
          </div>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
            Zrušit
          </Button>
          <Button type="submit" form="board-form" isLoading={saving}>
            {session ? 'Uložit' : 'Založit board'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
