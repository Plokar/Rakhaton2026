'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Check, Copy, Mail } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { mdtApi, type InvitationInput } from '@/lib/mdt-api';
import { fieldErrorMessage, queryKeys, useCommitteesQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { InvitationCreated, MdtRole, RoleId } from '@/types/mdt';
import { MDT_ROLE_LABEL } from '../me';
import { ROLE_META } from '../roles';

const SPECIALTIES = (Object.keys(ROLE_META) as RoleId[]).filter((r) => r !== 'patient');
const ROLES: MdtRole[] = ['mdt_doctor', 'mdt_viewer', 'mdt_admin'];
const EMPTY = { title_before: '', first_name: '', last_name: '', title_after: '', email: '', organization: '' };

/** Odkaz pozvánky na adrese, kde správce aplikaci právě používá (backend nezná adresu frontendu). */
export function invitationLink(created: InvitationCreated): string {
  return typeof window === 'undefined' ? created.link : `${window.location.origin}${created.path}`;
}

/** Odkaz s tlačítkem Kopírovat; schránka bez HTTPS nemusí jít, odkaz pak jde označit ručně. */
export function InvitationLink({ created }: { created: InvitationCreated }) {
  const [copy, setCopy] = React.useState<'idle' | 'done' | 'failed'>('idle');
  const link = invitationLink(created);
  return (
    <div className="flex flex-col gap-2">
      <p className="select-all break-all rounded-md bg-muted px-3 py-2 font-mono text-[13px]">{link}</p>
      <div className="flex flex-wrap items-center gap-2">
        <Button type="button" size="sm" onClick={async () => {
          try {
            await navigator.clipboard.writeText(link);
            setCopy('done');
          } catch {
            setCopy('failed');
          }
        }}>
          {copy === 'done' ? <Check aria-hidden /> : <Copy aria-hidden />} {copy === 'done' ? 'Zkopírováno' : 'Zkopírovat odkaz'}
        </Button>
        {created.email_sent && (
          <span className="flex items-center gap-1 text-xs text-muted-foreground"><Mail className="size-3.5" aria-hidden /> Odesláno na {created.email}</span>
        )}
      </div>
      <p role="status" className="sr-only">{copy === 'done' ? 'Odkaz je ve schránce.' : ''}</p>
      {copy === 'failed' && <p role="alert" className="text-sm">Odkaz se nepodařilo zkopírovat, označte ho ručně.</p>}
      <p className="text-xs text-muted-foreground">
        Odkaz platí jednou, do {new Date(created.expires_at).toLocaleString('cs-CZ', { dateStyle: 'medium', timeStyle: 'short' })}.
        Lékař si přes něj nastaví přihlášení a projde průvodce nastavením.
      </p>
    </div>
  );
}

/**
 * Pozvánka od správce MDT (T-361, T-362, D-027): lékař (i z jiné nemocnice) dostane jednorázový odkaz e-mailem
 * a správce ho může zároveň zkopírovat. Externí lékař je člen komise a vidí jen komise, kam je pozvaný.
 */
export function InviteDoctorDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const client = useQueryClient();
  const committees = useCommitteesQuery(open);
  const [form, setForm] = React.useState(EMPTY);
  const [specialty, setSpecialty] = React.useState<RoleId | ''>('');
  const [role, setRole] = React.useState<MdtRole>('mdt_doctor');
  const [external, setExternal] = React.useState(false);
  const [chosen, setChosen] = React.useState<number[]>([]);
  const [sendEmail, setSendEmail] = React.useState(true);
  const [error, setError] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const [created, setCreated] = React.useState<InvitationCreated | null>(null);
  const set = (key: keyof typeof EMPTY) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });

  const close = () => {
    setForm(EMPTY);
    setSpecialty('');
    setRole('mdt_doctor');
    setExternal(false);
    setChosen([]);
    setSendEmail(true);
    setError('');
    setCreated(null);
    onClose();
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.last_name.trim()) return setError('Vyplňte příjmení.');
    if (!specialty) return setError('Vyberte profesi (odbornost).');
    if (external && !form.organization.trim()) return setError('U lékaře z jiné nemocnice vyplňte nemocnici.');
    setSaving(true);
    const input: InvitationInput = {
      ...form, specialty, role: external ? 'mdt_viewer' : role, is_external: external,
      organization: form.organization.trim(), committees: chosen, send_email: sendEmail && Boolean(form.email.trim()),
    };
    try {
      setCreated(await mdtApi.createInvitation(input));
      void client.invalidateQueries({ queryKey: queryKeys.invitations });
    } catch (err) {
      setError(fieldErrorMessage(err, 'Pozvánku se nepodařilo vytvořit.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !saving && close()}>
      <DialogContent className="max-h-[90dvh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{created ? 'Pozvánka je připravená' : 'Pozvat lékaře'}</DialogTitle>
          <DialogDescription>
            {created
              ? `${[created.title_before, created.first_name, created.last_name].filter(Boolean).join(' ')} si přes odkaz založí účet.`
              : 'Lékař dostane jednorázový odkaz. Přes něj si nastaví přihlášení a projde průvodce: svůj PVW, požadavky a normy.'}
          </DialogDescription>
        </DialogHeader>
        {created ? (
          <InvitationLink created={created} />
        ) : (
          <form id="invite-form" onSubmit={submit} className="flex flex-col gap-3" noValidate>
            {error && <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-sm font-medium">Titul před jménem<Input value={form.title_before} onChange={set('title_before')} placeholder="MUDr." maxLength={40} /></label>
              <label className="flex flex-col gap-1 text-sm font-medium">Titul za jménem<Input value={form.title_after} onChange={set('title_after')} placeholder="Ph.D." maxLength={40} /></label>
              <label className="flex flex-col gap-1 text-sm font-medium">Jméno<Input value={form.first_name} onChange={set('first_name')} autoComplete="off" /></label>
              <label className="flex flex-col gap-1 text-sm font-medium">Příjmení<Input value={form.last_name} onChange={set('last_name')} autoComplete="off" /></label>
            </div>
            <fieldset>
              <legend className="mb-1.5 text-sm font-medium">Profese (odbornost)</legend>
              <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Profese">
                {SPECIALTIES.map((r) => (
                  <button key={r} type="button" role="radio" aria-checked={specialty === r} onClick={() => setSpecialty(r)}
                    className={cn('rounded-md border px-2.5 py-1 text-[13px] font-medium', specialty === r ? ROLE_META[r].className : 'border-border bg-card text-muted-foreground hover:text-foreground')}>
                    {ROLE_META[r].label}
                  </button>
                ))}
              </div>
            </fieldset>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-0.5 size-4 accent-primary" checked={external} onChange={(e) => setExternal(e.target.checked)} />
              <span>
                <span className="font-medium">Lékař z jiné nemocnice</span>
                <span className="block text-xs text-muted-foreground">Uvidí jen komise a zasedání, kam ho pozvete; pacienty nezařazuje.</span>
              </span>
            </label>
            {external ? (
              <label className="flex flex-col gap-1 text-sm font-medium">Nemocnice<Input value={form.organization} onChange={set('organization')} placeholder="např. Nemocnice Jih" /></label>
            ) : (
              <label className="flex flex-col gap-1 text-sm font-medium">
                Role v komisi
                <select className="h-9 rounded-lg border border-input bg-card px-2 text-sm" value={role} onChange={(e) => setRole(e.target.value as MdtRole)}>
                  {ROLES.map((r) => <option key={r} value={r}>{MDT_ROLE_LABEL[r]}</option>)}
                </select>
              </label>
            )}
            <fieldset>
              <legend className="mb-1.5 text-sm font-medium">Stálý člen komisí</legend>
              {committees.data?.length ? (
                <div className="flex max-h-40 flex-col gap-1 overflow-y-auto rounded-lg border border-border p-2">
                  {committees.data.map((c) => (
                    <label key={c.id} className="flex items-center gap-2 text-sm">
                      <input type="checkbox" className="size-4 accent-primary" checked={chosen.includes(c.id)}
                        onChange={() => setChosen((prev) => (prev.includes(c.id) ? prev.filter((x) => x !== c.id) : [...prev, c.id]))} />
                      {c.name}
                    </label>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">Zatím žádné komise. Lékaře půjde přizvat na jednotlivá zasedání.</p>
              )}
            </fieldset>
            <label className="flex flex-col gap-1 text-sm font-medium">E-mail<Input type="email" value={form.email} onChange={set('email')} autoComplete="off" /></label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" className="size-4 accent-primary" checked={sendEmail} disabled={!form.email.trim()} onChange={(e) => setSendEmail(e.target.checked)} />
              Poslat odkaz e-mailem (odkaz půjde vždy i zkopírovat)
            </label>
          </form>
        )}
        <DialogFooter className="gap-2">
          {created ? (
            <Button onClick={close}>Hotovo</Button>
          ) : (
            <>
              <Button variant="outline" onClick={close} disabled={saving}>Zrušit</Button>
              <Button type="submit" form="invite-form" isLoading={saving}>Vytvořit pozvánku</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
