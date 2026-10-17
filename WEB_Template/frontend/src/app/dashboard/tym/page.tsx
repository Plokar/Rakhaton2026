'use client';

import * as React from 'react';
import { UserPlus } from 'lucide-react';
import { toast } from 'sonner';
import { Page, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/shadcn/button';
import { Skeleton } from '@/components/shadcn/skeleton';
import { InviteDialog } from '@/components/mdt/InviteDialog';
import { can, MDT_ROLE_LABEL, useMe } from '@/components/mdt/me';
import { ROLE_META } from '@/components/mdt/roles';
import { apiErrorMessage, useUpdateUser, useUsersQuery } from '@/lib/queries';
import type { MdtRole, Me, RoleId } from '@/types/mdt';

const ROLES: MdtRole[] = ['mdt_admin', 'mdt_doctor', 'mdt_viewer'];
const SPECIALTIES = (Object.keys(ROLE_META) as RoleId[]).filter((r) => r !== 'patient');

const selectClass = 'h-8 rounded-lg border border-input bg-card px-2 text-sm disabled:opacity-60';

/**
 * Tým komise (T-319, PROGRESS Q26): předseda vidí členy, mění jejich roli (předseda, zadávající lékař,
 * člen komise) a odbornost, a posílá odkaz na registraci. Role omezují jen úpravy, číst smí každý.
 */
export default function TeamPage() {
  const me = useMe();
  const chair = can.manageBoards(me);
  const users = useUsersQuery(chair);
  const update = useUpdateUser();
  const [inviting, setInviting] = React.useState(false);

  const change = (user: Me, input: { role?: MdtRole; specialty?: RoleId }) =>
    update.mutate(
      { userId: user.user_id, input },
      {
        onSuccess: (saved) =>
          toast(`${saved.name} · ${MDT_ROLE_LABEL[saved.role]}${saved.specialty ? `, ${ROLE_META[saved.specialty].label.toLowerCase()}` : ''}`),
        onError: (err) => toast.error(apiErrorMessage(err, 'Změnu se nepodařilo uložit.')),
      },
    );

  return (
    <Page className="max-w-4xl">
      <PageHeader
        title="Tým komise"
        meta="Role určuje, kdo smí zařazovat pacienty a spravovat zasedání. Odbornost řadí podklad „pro mě“."
        actions={
          chair && (
            <Button size="lg" onClick={() => setInviting(true)}>
              <UserPlus aria-hidden /> Pozvat kolegu
            </Button>
          )
        }
      />

      {!me ? (
        <Skeleton className="h-40" />
      ) : !chair ? (
        <p className="text-sm text-muted-foreground">Členy týmu a jejich role spravuje předseda komise.</p>
      ) : users.isLoading ? (
        <div className="flex flex-col gap-2" aria-busy="true">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14" />)}
        </div>
      ) : users.isError ? (
        <p role="alert" className="text-sm text-destructive">{apiErrorMessage(users.error, 'Tým se nepodařilo načíst.')}</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border bg-card">
          <table className="w-full min-w-[36rem] text-sm">
            <caption className="sr-only">Členové týmu, jejich role a odbornost</caption>
            <thead>
              <tr className="border-b border-border text-left text-xs text-muted-foreground">
                <th scope="col" className="px-4 py-2.5 font-medium">Lékař</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Role v komisi</th>
                <th scope="col" className="px-4 py-2.5 font-medium">Odbornost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {(users.data ?? []).map((u) => {
                const self = u.user_id === me.user_id;
                return (
                  <tr key={u.user_id}>
                    <td className="px-4 py-2.5">
                      <span className="block font-medium">{u.name || u.username}{self && <span className="font-normal text-muted-foreground"> (vy)</span>}</span>
                      <span className="block text-xs text-muted-foreground">{u.username}</span>
                    </td>
                    <td className="px-4 py-2.5">
                      <select
                        aria-label={`Role: ${u.name || u.username}`}
                        className={selectClass}
                        value={u.role}
                        disabled={self || update.isPending}
                        title={self ? 'Sám sobě roli předsedy odebrat nejde' : undefined}
                        onChange={(e) => change(u, { role: e.target.value as MdtRole })}
                      >
                        {ROLES.map((r) => <option key={r} value={r}>{MDT_ROLE_LABEL[r]}</option>)}
                      </select>
                    </td>
                    <td className="px-4 py-2.5">
                      <select
                        aria-label={`Odbornost: ${u.name || u.username}`}
                        className={selectClass}
                        value={u.specialty ?? ''}
                        disabled={update.isPending}
                        onChange={(e) => e.target.value && change(u, { specialty: e.target.value as RoleId })}
                      >
                        {!u.specialty && <option value="">Nevyplněno</option>}
                        {SPECIALTIES.map((r) => <option key={r} value={r}>{ROLE_META[r].label}</option>)}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <InviteDialog open={inviting} onClose={() => setInviting(false)} />
    </Page>
  );
}
