'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Ban, Pencil, Plus, RotateCw, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { mdtApi } from '@/lib/mdt-api';
import {
  apiErrorMessage, fieldErrorMessage, queryKeys, useAllUsersQuery, useCommitteesQuery, useInvitationsQuery, useUpdateUser,
} from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { Committee, InvitationCreated, InvitationStatus, MdtRole, Me, RoleId } from '@/types/mdt';
import { formatDate } from '../format';
import { MDT_ROLE_LABEL } from '../me';
import { ROLE_META } from '../roles';
import { InvitationLink } from './InviteDoctorDialog';

const ROLES: MdtRole[] = ['mdt_admin', 'mdt_doctor', 'mdt_viewer'];
const SPECIALTIES = (Object.keys(ROLE_META) as RoleId[]).filter((r) => r !== 'patient');
const selectClass = 'h-8 rounded-lg border border-input bg-card px-2 text-sm disabled:opacity-60';

const STATUS_LABEL: Record<InvitationStatus, string> = {
  pending: 'čeká na přijetí', used: 'přijatá', expired: 'vypršela', revoked: 'zrušená',
};

function Loading() {
  return (
    <div className="flex flex-col gap-2" aria-busy="true">
      {[0, 1, 2].map((i) => <Skeleton key={i} className="h-14" />)}
    </div>
  );
}

// ── Lékaři ───────────────────────────────────────────────────────────────────
/** Lékaři: role, odbornost, správce, nemocnice, komise a zablokování (T-319, T-356, T-357). */
export function DoctorsPanel({ me }: { me: Me }) {
  const users = useAllUsersQuery(true);
  const update = useUpdateUser();
  const [committeesOf, setCommitteesOf] = React.useState<Me | null>(null);
  const [orgOf, setOrgOf] = React.useState<Me | null>(null);

  const change = (user: Me, input: Parameters<typeof update.mutate>[0]['input'], message?: string) =>
    update.mutate({ userId: user.user_id, input }, {
      onSuccess: (saved) => toast(message ?? `${saved.name} uloženo`),
      onError: (err) => toast.error(fieldErrorMessage(err, 'Změnu se nepodařilo uložit.')),
    });

  if (users.isLoading) return <Loading />;
  if (users.isError) return <p role="alert" className="text-sm text-destructive">{apiErrorMessage(users.error, 'Tým se nepodařilo načíst.')}</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card">
      <table className="w-full min-w-[56rem] text-sm">
        <caption className="sr-only">Lékaři, jejich role, odbornost, nemocnice a komise</caption>
        <thead>
          <tr className="border-b border-border text-left text-xs text-muted-foreground">
            <th scope="col" className="px-4 py-2.5 font-medium">Lékař</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Role v komisi</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Odbornost</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Nemocnice</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Komise</th>
            <th scope="col" className="px-3 py-2.5 font-medium">Správce</th>
            <th scope="col" className="px-3 py-2.5 font-medium"><span className="sr-only">Přístup</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {(users.data ?? []).map((u) => {
            const self = u.user_id === me.user_id;
            return (
              <tr key={u.user_id} className={cn(!u.is_active && 'text-muted-foreground')}>
                <td className="px-4 py-2.5">
                  <span className="block font-medium">{u.name || u.username}{self && <span className="font-normal text-muted-foreground"> (vy)</span>}</span>
                  <span className="block text-xs text-muted-foreground">
                    {u.username}{!u.is_active && ' · zablokovaný'}{u.onboarding_done === false && ' · nedokončil nastavení'}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  <select aria-label={`Role: ${u.name}`} className={selectClass} value={u.role} disabled={update.isPending || u.is_external}
                    title={u.is_external ? 'Lékař z jiné nemocnice je člen komise' : undefined}
                    onChange={(e) => change(u, { role: e.target.value as MdtRole }, `${u.name} · ${MDT_ROLE_LABEL[e.target.value as MdtRole]}`)}>
                    {ROLES.map((r) => <option key={r} value={r}>{MDT_ROLE_LABEL[r]}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2.5">
                  <select aria-label={`Odbornost: ${u.name}`} className={selectClass} value={u.specialty ?? ''} disabled={update.isPending}
                    onChange={(e) => e.target.value && change(u, { specialty: e.target.value as RoleId })}>
                    {!u.specialty && <option value="">Nevyplněno</option>}
                    {SPECIALTIES.map((r) => <option key={r} value={r}>{ROLE_META[r].label}</option>)}
                  </select>
                </td>
                <td className="px-3 py-2.5">
                  <button type="button" className="rounded px-1 text-left hover:bg-muted" onClick={() => setOrgOf(u)} aria-label={`Nemocnice: ${u.name}`}>
                    {u.is_external ? <span className="font-medium">{u.organization}</span> : <span className="text-muted-foreground">naše</span>}
                  </button>
                </td>
                <td className="px-3 py-2.5">
                  <button type="button" className="flex items-center gap-1 rounded px-1 text-left hover:bg-muted" onClick={() => setCommitteesOf(u)}
                    aria-label={`Komise: ${u.name}`}>
                    {u.committees?.length ? `${u.committees.length}` : <span className="text-muted-foreground">žádná</span>}
                    <Pencil className="size-3 text-muted-foreground" aria-hidden />
                  </button>
                </td>
                <td className="px-3 py-2.5">
                  <input type="checkbox" className="size-4 accent-primary" aria-label={`Správce MDT: ${u.name}`} checked={Boolean(u.is_manager)}
                    disabled={update.isPending || (self && u.is_manager)} title={self ? 'Sám sobě roli správce odebrat nejde' : undefined}
                    onChange={(e) => change(u, { is_manager: e.target.checked }, e.target.checked ? `${u.name} je správce MDT` : `${u.name} už není správce`)} />
                </td>
                <td className="px-3 py-2.5 text-right">
                  {!self && (
                    <Button type="button" size="sm" variant="ghost" disabled={update.isPending}
                      onClick={() => change(u, { is_active: !u.is_active }, u.is_active ? `${u.name}: přístup zablokován` : `${u.name}: přístup obnoven`)}>
                      {u.is_active ? <><Ban aria-hidden /> Zablokovat</> : 'Obnovit přístup'}
                    </Button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {committeesOf && <UserCommitteesDialog user={committeesOf} onClose={() => setCommitteesOf(null)} />}
      {orgOf && <OrganizationDialog user={orgOf} onClose={() => setOrgOf(null)} />}
    </div>
  );
}

function UserCommitteesDialog({ user, onClose }: { user: Me; onClose: () => void }) {
  const committees = useCommitteesQuery(true);
  const update = useUpdateUser();
  const [chosen, setChosen] = React.useState<number[]>((user.committees ?? []).map((c) => c.id));
  const save = () => update.mutate({ userId: user.user_id, input: { committees: chosen } }, {
    onSuccess: () => {
      toast(`${user.name}: komise uloženy`);
      onClose();
    },
    onError: (err) => toast.error(fieldErrorMessage(err, 'Komise se nepodařilo uložit.')),
  });
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Komise · {user.name}</DialogTitle>
          <DialogDescription>Stálý člen je pozvaný na všechna zasedání komise. U zasedání ho jde vyřadit.</DialogDescription>
        </DialogHeader>
        <div className="flex max-h-72 flex-col gap-1 overflow-y-auto">
          {(committees.data ?? []).map((c) => (
            <label key={c.id} className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="size-4 accent-primary" checked={chosen.includes(c.id)}
                onChange={() => setChosen((prev) => (prev.includes(c.id) ? prev.filter((x) => x !== c.id) : [...prev, c.id]))} />
              {c.name}
            </label>
          ))}
          {!committees.data?.length && <p className="text-sm text-muted-foreground">Zatím žádné komise.</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Zrušit</Button>
          <Button onClick={save} isLoading={update.isPending}>Uložit</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function OrganizationDialog({ user, onClose }: { user: Me; onClose: () => void }) {
  const update = useUpdateUser();
  const [external, setExternal] = React.useState(Boolean(user.is_external));
  const [organization, setOrganization] = React.useState(user.organization ?? '');
  const save = () => update.mutate({ userId: user.user_id, input: { is_external: external, organization: organization.trim(), ...(external ? { role: 'mdt_viewer' as const } : {}) } }, {
    onSuccess: () => {
      toast(`${user.name}: nemocnice uložena`);
      onClose();
    },
    onError: (err) => toast.error(fieldErrorMessage(err, 'Nemocnici se nepodařilo uložit.')),
  });
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Nemocnice · {user.name}</DialogTitle>
          <DialogDescription>Lékař z jiné nemocnice vidí jen komise a zasedání, kam je pozvaný, a pacienty nezařazuje.</DialogDescription>
        </DialogHeader>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4 accent-primary" checked={external} onChange={(e) => setExternal(e.target.checked)} />
          Lékař z jiné nemocnice
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium">
          Nemocnice
          <Input value={organization} onChange={(e) => setOrganization(e.target.value)} placeholder={external ? 'např. Nemocnice Jih' : 'nepovinné'} />
        </label>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Zrušit</Button>
          <Button onClick={save} isLoading={update.isPending} disabled={external && !organization.trim()}>Uložit</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Pozvánky ─────────────────────────────────────────────────────────────────
export function InvitationsPanel() {
  const client = useQueryClient();
  const invitations = useInvitationsQuery(true);
  const [resent, setResent] = React.useState<InvitationCreated | null>(null);
  const [busy, setBusy] = React.useState<number | null>(null);
  const refresh = () => client.invalidateQueries({ queryKey: queryKeys.invitations });

  const act = async (id: number, action: () => Promise<unknown>, done?: (result: unknown) => void) => {
    setBusy(id);
    try {
      const result = await action();
      done?.(result);
      await refresh();
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Akci se nepodařilo provést.'));
    } finally {
      setBusy(null);
    }
  };

  if (invitations.isLoading) return <Loading />;
  if (invitations.isError) return <p role="alert" className="text-sm text-destructive">{apiErrorMessage(invitations.error, 'Pozvánky se nepodařilo načíst.')}</p>;
  if (!invitations.data?.length) return <p className="text-sm text-muted-foreground">Zatím žádné pozvánky. Lékaře pozvete tlačítkem Pozvat lékaře.</p>;
  return (
    <>
      <ul className="divide-y divide-border rounded-xl border border-border bg-card">
        {invitations.data.map((i) => (
          <li key={i.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-4 py-3 text-sm">
            <span className="min-w-0 flex-1">
              <span className="block font-medium">
                {[i.title_before, i.first_name, i.last_name].filter(Boolean).join(' ')}{i.title_after && `, ${i.title_after}`}
              </span>
              <span className="block text-xs text-muted-foreground">
                {ROLE_META[i.specialty]?.label ?? i.specialty} · {MDT_ROLE_LABEL[i.role]}
                {i.is_external && ` · ${i.organization}`}
                {i.committees.length > 0 && ` · ${i.committees.map((c) => c.name).join(', ')}`}
                {i.email && ` · ${i.email}`}
              </span>
            </span>
            <span className={cn('text-xs', i.status === 'pending' ? 'font-medium' : 'text-muted-foreground')}>
              {STATUS_LABEL[i.status]}
              {i.status === 'used' && i.used_by && ` (${i.used_by}, ${formatDate(i.used_at)})`}
              {i.status === 'pending' && ` do ${formatDate(i.expires_at)}`}
            </span>
            {i.status !== 'used' && (
              <Button size="sm" variant="outline" disabled={busy === i.id}
                onClick={() => void act(i.id, () => mdtApi.resendInvitation(i.id, Boolean(i.email)), (r) => setResent(r as InvitationCreated))}>
                <RotateCw aria-hidden /> Nový odkaz
              </Button>
            )}
            {i.status === 'pending' && (
              <Button size="sm" variant="ghost" disabled={busy === i.id} onClick={() => void act(i.id, () => mdtApi.revokeInvitation(i.id))}>
                Zrušit
              </Button>
            )}
          </li>
        ))}
      </ul>
      <Dialog open={resent !== null} onOpenChange={(v) => !v && setResent(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Nový odkaz</DialogTitle>
            <DialogDescription>Předchozí odkaz už neplatí.</DialogDescription>
          </DialogHeader>
          {resent && <InvitationLink created={resent} />}
          <DialogFooter><Button onClick={() => setResent(null)}>Hotovo</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ── Komise ───────────────────────────────────────────────────────────────────
export function CommitteesPanel() {
  const client = useQueryClient();
  const committees = useCommitteesQuery(true);
  const [editing, setEditing] = React.useState<Committee | 'new' | null>(null);
  const remove = async (c: Committee) => {
    try {
      await mdtApi.deleteCommittee(c.id);
      await client.invalidateQueries({ queryKey: queryKeys.committees });
      toast(`Komise ${c.name} smazána; zasedání zůstala bez komise`);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Komisi se nepodařilo smazat.'));
    }
  };
  return (
    <div className="flex flex-col gap-3">
      <div>
        <Button variant="outline" onClick={() => setEditing('new')}><Plus aria-hidden /> Nová komise</Button>
      </div>
      {committees.isLoading ? (
        <Loading />
      ) : !committees.data?.length ? (
        <p className="text-sm text-muted-foreground">Zatím žádné komise.</p>
      ) : (
        <ul className="divide-y divide-border rounded-xl border border-border bg-card">
          {committees.data.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center gap-3 px-4 py-3 text-sm">
              <span className="min-w-0 flex-1">
                <span className="block font-medium">{c.name}</span>
                <span className="block text-xs text-muted-foreground">
                  {c.members.length ? c.members.map((m) => m.name).join(', ') : 'bez stálých členů'} · zasedání {c.sessions}
                </span>
              </span>
              <Button size="sm" variant="outline" onClick={() => setEditing(c)}><Pencil aria-hidden /> Upravit</Button>
              <Button size="sm" variant="ghost" aria-label={`Smazat komisi ${c.name}`} onClick={() => void remove(c)}><Trash2 aria-hidden /></Button>
            </li>
          ))}
        </ul>
      )}
      {editing && <CommitteeDialog committee={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function CommitteeDialog({ committee, onClose }: { committee: Committee | null; onClose: () => void }) {
  const client = useQueryClient();
  const users = useAllUsersQuery(true);
  const [name, setName] = React.useState(committee?.name ?? '');
  const [members, setMembers] = React.useState<number[]>(committee?.members.map((m) => m.user_id) ?? []);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState('');
  const save = async () => {
    setSaving(true);
    setError('');
    try {
      if (committee) await mdtApi.updateCommittee(committee.id, { name: name.trim(), members });
      else await mdtApi.createCommittee({ name: name.trim(), members });
      await client.invalidateQueries({ queryKey: queryKeys.committees });
      void client.invalidateQueries({ queryKey: queryKeys.allUsers });
      onClose();
    } catch (err) {
      setError(fieldErrorMessage(err, 'Komisi se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };
  return (
    <Dialog open onOpenChange={(v) => !v && !saving && onClose()}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{committee ? 'Upravit komisi' : 'Nová komise'}</DialogTitle>
          <DialogDescription>Stálí členové jsou pozvaní na všechna zasedání komise.</DialogDescription>
        </DialogHeader>
        {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
        <label className="flex flex-col gap-1 text-sm font-medium">Název<Input value={name} onChange={(e) => setName(e.target.value)} placeholder="např. Hrudní – karcinom plic" /></label>
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium">Stálí členové</legend>
          <div className="flex max-h-60 flex-col gap-1 overflow-y-auto rounded-lg border border-border p-2">
            {(users.data ?? []).filter((u) => u.is_active).map((u) => (
              <label key={u.user_id} className="flex items-center gap-2 text-sm">
                <input type="checkbox" className="size-4 accent-primary" checked={members.includes(u.user_id)}
                  onChange={() => setMembers((prev) => (prev.includes(u.user_id) ? prev.filter((x) => x !== u.user_id) : [...prev, u.user_id]))} />
                {u.name}
                <span className="text-xs text-muted-foreground">
                  {u.specialty ? ROLE_META[u.specialty].label.toLowerCase() : ''}{u.is_external ? ` · ${u.organization}` : ''}
                </span>
              </label>
            ))}
          </div>
        </fieldset>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>Zrušit</Button>
          <Button onClick={() => void save()} isLoading={saving} disabled={!name.trim()}>Uložit</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
