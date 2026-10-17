'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Input } from '@/components/shadcn/input';
import { Skeleton } from '@/components/shadcn/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys, useUsersQuery } from '@/lib/queries';
import type { MdtCase } from '@/types/mdt';
import { useMe } from './me';
import { shortPatient } from './patient';
import { ROLE_META } from './roles';

const ROLE_LABEL = { mdt_admin: 'předseda', mdt_doctor: 'lékař', mdt_viewer: 'člen komise' } as const;
const plain = (text: string) => text.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();

/**
 * Přizvání ke spolupráci na případu (T-326): přizvaný smí případ upravovat jako zadávající lékař
 * (ECOG, záměr, úplnost, závěr). Přizývá předseda nebo zadávající lékař; backend to ověří znovu.
 */
export function CollaboratorsDialog({ item, open, onOpenChange }: { item: MdtCase; open: boolean; onOpenChange: (open: boolean) => void }) {
  const me = useMe();
  const client = useQueryClient();
  const users = useUsersQuery(open);
  const [selected, setSelected] = React.useState<Set<number>>(() => new Set(item.collaborators?.map((u) => u.user_id)));
  const [saving, setSaving] = React.useState(false);
  const [query, setQuery] = React.useState('');
  const creatorId = item.created_by?.user_id;
  // Předseda smí vše bez přizvání; zadávající lékař právo má.
  // Lékaři s odborností nahoře (účty bez odbornosti jsou z registrace před T-319 nebo z ukázkových dat šablony)
  const team = (users.data ?? [])
    .filter((u) => u.role !== 'mdt_admin' && u.user_id !== creatorId && u.user_id !== me?.user_id)
    .toSorted((a, b) => Number(!a.specialty) - Number(!b.specialty) || a.name.localeCompare(b.name, 'cs'));
  // T-328: vyhledávání jako ve výběru lékaře (bez diakritiky); vybraní zůstávají vidět i mimo hledání
  const words = plain(query).split(/\s+/).filter(Boolean);
  const candidates = team.filter((u) => selected.has(u.user_id) || words.every((w) =>
    plain(`${u.name} ${u.username} ${u.specialty ? ROLE_META[u.specialty].label : ''}`).includes(w)));

  const toggle = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const save = async () => {
    if (item.id === undefined) return;
    setSaving(true);
    try {
      await mdtApi.updateCase(item.id, { collaborators: [...selected] });
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.session(item.session) }),
        client.invalidateQueries({ queryKey: queryKeys.sessions }),
      ]);
      toast.success(selected.size ? `Spolupráce uložena (${selected.size})` : 'Spolupracovníci odebráni');
      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Spolupráci se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(next) => onOpenChange(next)}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Spolupráce · {shortPatient(item)}</DialogTitle>
          <DialogDescription>
            Přizvaný lékař může u pacienta upravovat stejně jako zadávající: ECOG, záměr, úplnost podkladů a závěr.
          </DialogDescription>
        </DialogHeader>
        {users.isLoading ? (
          <div className="flex flex-col gap-2" aria-busy="true">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-9" />)}
          </div>
        ) : users.isError ? (
          <p role="alert" className="text-sm text-destructive">Seznam lékařů se nepodařilo načíst.</p>
        ) : team.length === 0 ? (
          <p className="text-sm text-muted-foreground">V týmu není nikdo další, koho přizvat.</p>
        ) : (
          <>
          <Input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Hledat lékaře: jméno, odbornost…"
            aria-label="Hledat lékaře"
            autoFocus
          />
          {candidates.length === 0 && <p className="text-sm text-muted-foreground">Žádný lékař neodpovídá hledání.</p>}
          <fieldset className="flex max-h-80 flex-col overflow-y-auto rounded-lg border border-border">
            <legend className="sr-only">Lékaři týmu</legend>
            {candidates.map((user) => {
              const id = `collab-${user.user_id}`;
              return (
                <label
                  key={user.user_id}
                  htmlFor={id}
                  className="flex cursor-pointer items-center gap-3 border-b border-border px-3 py-2 last:border-b-0 hover:bg-muted/60"
                >
                  <input
                    id={id}
                    type="checkbox"
                    checked={selected.has(user.user_id)}
                    onChange={() => toggle(user.user_id)}
                    className="size-4 accent-primary"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{user.name}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {user.specialty ? ROLE_META[user.specialty].label : 'bez odbornosti'} · {ROLE_LABEL[user.role]}
                    </span>
                  </span>
                </label>
              );
            })}
          </fieldset>
          </>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Zrušit</Button>
          <Button onClick={save} disabled={saving || users.isLoading}>{saving ? 'Ukládám…' : 'Uložit spolupráci'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
