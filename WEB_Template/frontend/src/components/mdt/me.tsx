'use client';

import * as React from 'react';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import type { MdtCase, MdtRole, Me } from '@/types/mdt';
import { ROLE_META } from './roles';

/** Role podle oprávnění (FR-U1, D-014). */
export const MDT_ROLE_LABEL: Record<MdtRole, string> = {
  mdt_admin: 'Předseda komise',
  mdt_doctor: 'Zadávající lékař',
  mdt_viewer: 'Člen komise',
};

/** Co smí role v UI (stejně jako backend, ARCH §6.3). Backend je stejně ověří. */
export const can = {
  manageBoards: (me?: Me | null) => me?.role === 'mdt_admin',
  generateBrief: (me?: Me | null) => me?.role === 'mdt_admin' || me?.role === 'mdt_doctor',
  /** Předseda, zadávající lékař, nebo přizvaný ke spolupráci (T-326; i člen komise s rolí jen ke čtení). */
  editCase: (me: Me | null | undefined, c: MdtCase) =>
    me?.role === 'mdt_admin'
    || (me?.role === 'mdt_doctor' && c.created_by?.user_id === me.user_id)
    || Boolean(me && c.collaborators?.some((u) => u.user_id === me.user_id)),
  /** Přizvat ke spolupráci smí předseda nebo zadávající lékař (ne přizvaný). */
  inviteToCase: (me: Me | null | undefined, c: MdtCase) =>
    me?.role === 'mdt_admin' || (Boolean(me) && c.created_by?.user_id === me?.user_id),
};

export function meLabel(me: Me): string {
  const specialty = me.specialty ? ROLE_META[me.specialty].label.toLowerCase() : null;
  return specialty ? `${MDT_ROLE_LABEL[me.role]} · ${specialty}` : MDT_ROLE_LABEL[me.role];
}

const MeContext = React.createContext<Me | null>(null);
const fetchMe = () => mdtApi.getMe();

/** Role a odbornost přihlášeného z `/api/mdt/me/`; dokud se nenačte, je `null` (nic navíc nepovolí). */
export function MeProvider({ userId, children }: { userId: number | string; children: React.ReactNode }) {
  const { data } = useApiData(fetchMe, String(userId));
  return <MeContext.Provider value={data ?? null}>{children}</MeContext.Provider>;
}

export function useMe(): Me | null {
  return React.useContext(MeContext);
}
