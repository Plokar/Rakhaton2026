'use client';

import * as React from 'react';
import { UserPlus, UserRoundPlus } from 'lucide-react';
import { Page, PageHeader } from '@/components/layout/Page';
import { Button } from '@/components/shadcn/button';
import { Skeleton } from '@/components/shadcn/skeleton';
import { NewDoctorDialog } from '@/components/mdt/NewDoctorDialog';
import { can, useMe } from '@/components/mdt/me';
import { InviteDoctorDialog } from '@/components/mdt/team/InviteDoctorDialog';
import { CommitteesPanel, DoctorsPanel, InvitationsPanel } from '@/components/mdt/team/TeamPanels';
import { cn } from '@/lib/utils';

type Tab = 'lekari' | 'pozvanky' | 'komise';
const TABS: { id: Tab; label: string }[] = [
  { id: 'lekari', label: 'Lékaři' },
  { id: 'pozvanky', label: 'Pozvánky' },
  { id: 'komise', label: 'Komise' },
];

/**
 * Tým a účty (T-319, T-361, T-362, D-027): jeden správce MDT spravuje všechny účty a komise. Lékaře zve
 * jednorázovým odkazem (i z jiných nemocnic), přiřazuje je do komisí, mění roli a odbornost a blokuje přístup.
 */
export default function TeamPage() {
  const me = useMe();
  const manager = can.manageAccounts(me);
  const [tab, setTab] = React.useState<Tab>('lekari');
  const [inviting, setInviting] = React.useState(false);
  const [adding, setAdding] = React.useState(false);

  return (
    <Page className="max-w-6xl">
      <PageHeader
        title="Tým a účty"
        meta="Správce MDT zve lékaře odkazem, spravuje jejich účty a komise. Role určuje, kdo smí zařazovat pacienty a vést zasedání."
        actions={
          manager && (
            <div className="flex flex-wrap gap-2">
              <Button size="lg" variant="outline" onClick={() => setAdding(true)}>
                <UserRoundPlus aria-hidden /> Založit účet přímo
              </Button>
              <Button size="lg" onClick={() => setInviting(true)}>
                <UserPlus aria-hidden /> Pozvat lékaře
              </Button>
            </div>
          )
        }
      />

      {!me ? (
        <Skeleton className="h-40" />
      ) : !manager ? (
        <p className="text-sm text-muted-foreground">Účty, pozvánky a komise spravuje správce MDT.</p>
      ) : (
        <>
          <div role="tablist" aria-label="Správa týmu" className="mb-4 flex gap-1 border-b border-border">
            {TABS.map((t) => (
              <button key={t.id} type="button" role="tab" id={`tab-${t.id}`} aria-selected={tab === t.id} aria-controls={`panel-${t.id}`}
                onClick={() => setTab(t.id)}
                className={cn('-mb-px border-b-2 px-3 py-2 text-sm font-medium',
                  tab === t.id ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground')}>
                {t.label}
              </button>
            ))}
          </div>
          <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            {tab === 'lekari' && <DoctorsPanel me={me} />}
            {tab === 'pozvanky' && <InvitationsPanel />}
            {tab === 'komise' && <CommitteesPanel />}
          </div>
        </>
      )}
      <InviteDoctorDialog open={inviting} onClose={() => { setInviting(false); setTab('pozvanky'); }} />
      <NewDoctorDialog open={adding} onClose={() => setAdding(false)} />
    </Page>
  );
}
