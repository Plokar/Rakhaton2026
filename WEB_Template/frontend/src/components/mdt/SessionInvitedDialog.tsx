'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { UserMinus, UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Button } from '@/components/ui/button';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, fieldErrorMessage, queryKeys, useCommitteesQuery, useSessionInvited, useUsersQuery } from '@/lib/queries';
import type { InvitedDoctor } from '@/types/mdt';
import { ROLE_META } from './roles';

const selectClass = 'h-9 min-w-0 flex-1 rounded-lg border border-input bg-card px-2 text-sm';

function who(d: InvitedDoctor) {
  const specialty = d.specialty ? ROLE_META[d.specialty]?.label.toLowerCase() : null;
  return [specialty, d.organization].filter(Boolean).join(' · ');
}

/**
 * Pozvaní na zasedání (T-357, D-027): stálí členové komise bez vyřazených + přizvaní jen na toto zasedání.
 * Podle nich se zadávajícímu lékaři ukážou požadavky a na PVW normy lékařů. Mění předseda nebo správce MDT.
 */
export function SessionInvitedDialog({ sessionId, canEdit, open, onOpenChange }: {
  sessionId: number;
  canEdit: boolean;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const client = useQueryClient();
  const invited = useSessionInvited(open ? sessionId : null);
  const committees = useCommitteesQuery(open && canEdit);
  const users = useUsersQuery(open && canEdit);
  const [adding, setAdding] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const data = invited.data;

  const save = async (input: Parameters<typeof mdtApi.updateSessionInvited>[1]) => {
    setSaving(true);
    try {
      const saved = await mdtApi.updateSessionInvited(sessionId, input);
      client.setQueryData(queryKeys.sessionInvited(sessionId), saved);
      void client.invalidateQueries({ queryKey: queryKeys.session(sessionId) });
      void client.invalidateQueries({ queryKey: ['case'] });       // požadavky a normy u pacientů zasedání
    } catch (err) {
      toast.error(fieldErrorMessage(err, 'Pozvané se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };

  const ids = (list: InvitedDoctor[]) => list.map((d) => d.user_id);
  const attending = new Set(data ? ids(data.attendees) : []);
  const candidates = (users.data ?? []).filter((u) => !attending.has(u.user_id));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Pozvaní lékaři</DialogTitle>
          <DialogDescription>
            Pozvaní jsou stálí členové komise a lékaři přizvaní jen na toto zasedání. Zadávající lékař uvidí, co
            vyžadují, a na projektoru se ukážou jejich normy.
          </DialogDescription>
        </DialogHeader>
        {invited.isLoading ? (
          <p className="text-sm text-muted-foreground">Načítám…</p>
        ) : invited.isError || !data ? (
          <p role="alert" className="text-sm text-destructive">{apiErrorMessage(invited.error, 'Pozvané se nepodařilo načíst.')}</p>
        ) : (
          <div className="flex flex-col gap-4">
            <label className="flex flex-col gap-1 text-sm font-medium">
              Komise
              {canEdit ? (
                <select className={selectClass} value={data.committee?.id ?? ''} disabled={saving}
                  onChange={(e) => void save({ committee_id: e.target.value ? Number(e.target.value) : null })}>
                  <option value="">Bez komise</option>
                  {(committees.data ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              ) : (
                <span className="font-normal">{data.committee?.name ?? 'Bez komise'}</span>
              )}
            </label>

            <section aria-labelledby="invited-members">
              <h3 id="invited-members" className="mb-1.5 text-sm font-semibold">Členové komise ({data.members.length})</h3>
              {data.members.length === 0 ? (
                <p className="text-sm text-muted-foreground">Komise nemá stálé členy.</p>
              ) : (
                <ul className="divide-y divide-border rounded-lg border border-border">
                  {data.members.map((m) => {
                    const out = data.excluded.some((x) => x.user_id === m.user_id);
                    return (
                      <li key={m.user_id} className="flex items-center gap-2 px-3 py-2 text-sm">
                        <span className={out ? 'min-w-0 flex-1 text-muted-foreground line-through' : 'min-w-0 flex-1'}>
                          {m.name} <span className="text-xs text-muted-foreground">{who(m)}</span>
                        </span>
                        {out && <span className="text-xs text-muted-foreground">tentokrát nepřijde</span>}
                        {canEdit && (
                          <Button type="button" size="sm" variant="ghost" disabled={saving}
                            onClick={() => void save({ excluded: out ? ids(data.excluded).filter((id) => id !== m.user_id) : [...ids(data.excluded), m.user_id] })}>
                            {out ? 'Vrátit' : 'Nepřijde'}
                          </Button>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>

            <section aria-labelledby="invited-extra">
              <h3 id="invited-extra" className="mb-1.5 text-sm font-semibold">Přizvaní na toto zasedání ({data.invited.length})</h3>
              {data.invited.length > 0 && (
                <ul className="mb-2 divide-y divide-border rounded-lg border border-border">
                  {data.invited.map((d) => (
                    <li key={d.user_id} className="flex items-center gap-2 px-3 py-2 text-sm">
                      <span className="min-w-0 flex-1">{d.name} <span className="text-xs text-muted-foreground">{who(d)}</span></span>
                      {canEdit && (
                        <Button type="button" size="sm" variant="ghost" disabled={saving} aria-label={`Odebrat ${d.name}`}
                          onClick={() => void save({ invited: ids(data.invited).filter((id) => id !== d.user_id) })}>
                          <UserMinus aria-hidden />
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              {canEdit && (
                <div className="flex gap-2">
                  <select className={selectClass} value={adding} onChange={(e) => setAdding(e.target.value)} aria-label="Lékař k přizvání">
                    <option value="">Vyberte lékaře…</option>
                    {candidates.map((u) => (
                      <option key={u.user_id} value={u.user_id}>
                        {u.name}{u.is_external && u.organization ? ` (${u.organization})` : ''}
                      </option>
                    ))}
                  </select>
                  <Button type="button" variant="outline" disabled={!adding || saving}
                    onClick={() => {
                      void save({ invited: [...ids(data.invited), Number(adding)] });
                      setAdding('');
                    }}>
                    <UserPlus aria-hidden /> Přizvat
                  </Button>
                </div>
              )}
            </section>

            <p className="text-sm">
              <span className="font-medium">Pozvaní celkem: {data.attendees.length}</span>
              {data.attendees.length > 0 && <span className="text-muted-foreground"> · {data.attendees.map((a) => a.name).join(', ')}</span>}
            </p>
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Zavřít</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
