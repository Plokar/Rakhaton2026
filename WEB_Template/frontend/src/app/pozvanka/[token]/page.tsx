'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { CircleAlert, Eye, EyeOff } from 'lucide-react';
import { ROLE_META } from '@/components/mdt/roles';
import { MDT_ROLE_LABEL } from '@/components/mdt/me';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { useAuth } from '@/contexts/AuthContext';
import { ApiError } from '@/lib/api';
import { mdtApi } from '@/lib/mdt-api';
import { fieldErrorMessage } from '@/lib/queries';

/**
 * Pozvánka od správce MDT (T-356, D-027): lékař přes jednorázový odkaz nastaví přihlášení. Jméno, profese,
 * nemocnice a komise jsou z pozvánky. Pak pokračuje průvodcem nastavení (`/dashboard/vitejte`).
 */
export default function InvitationPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = React.use(params);
  return (
    <div className="flex min-h-dvh flex-col bg-background px-5 py-4 sm:px-10">
      <div className="flex items-center justify-between gap-3">
        <Link href="/login" className="flex items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <Image src="/icon-192.png" alt="" width={36} height={36} className="size-9 rounded-lg" aria-hidden />
          <span translate="no" className="text-base font-semibold tracking-tight">MDTcore</span>
        </Link>
        <ThemeToggle />
      </div>
      <main className="mx-auto my-auto w-full max-w-md py-8">
        <InvitationForm token={token} />
      </main>
    </div>
  );
}

function InvitationForm({ token }: { token: string }) {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const invitation = useQuery({ queryKey: ['invitation', token], queryFn: () => mdtApi.getPublicInvitation(token), retry: false });
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [password2, setPassword2] = React.useState('');
  const [show, setShow] = React.useState(false);
  const [error, setError] = React.useState('');
  const [saving, setSaving] = React.useState(false);

  if (invitation.isLoading) return <p className="text-sm text-muted-foreground" aria-busy="true">Načítám pozvánku…</p>;
  if (invitation.isError || !invitation.data) {
    const gone = invitation.error instanceof ApiError && [404, 410].includes(invitation.error.status);
    return (
      <div className="text-center">
        <h1 className="text-xl font-semibold">Pozvánka neplatí</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          {gone && invitation.error instanceof ApiError ? invitation.error.message : 'Pozvánku se nepodařilo načíst. Zkuste to znovu.'}
        </p>
        <Link href="/login" className="mt-4 inline-block text-sm font-medium text-primary hover:underline">Přejít na přihlášení</Link>
      </div>
    );
  }
  const inv = invitation.data;
  const name = [inv.title_before, inv.first_name, inv.last_name].filter(Boolean).join(' ') + (inv.title_after ? `, ${inv.title_after}` : '');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username.trim()) return setError('Vyplňte uživatelské jméno.');
    if (password.length < 8) return setError('Heslo musí mít aspoň 8 znaků.');
    if (password !== password2) return setError('Zadaná hesla se neshodují.');
    setSaving(true);
    try {
      await mdtApi.acceptInvitation(token, { username: username.trim(), password, password2 });
      await refreshUser();
      router.push('/dashboard/vitejte');
    } catch (err) {
      setError(fieldErrorMessage(err, 'Účet se nepodařilo založit.'));
      setSaving(false);
    }
  };

  return (
    <>
      <p className="text-xs font-medium text-muted-foreground">Pozvánka od správce MDT</p>
      <h1 className="text-2xl font-semibold tracking-tight">Vítejte, {name}</h1>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 rounded-lg border border-border bg-card p-3 text-sm">
        <dt className="text-muted-foreground">Profese</dt><dd>{ROLE_META[inv.specialty]?.label ?? inv.specialty}</dd>
        <dt className="text-muted-foreground">Role</dt><dd>{MDT_ROLE_LABEL[inv.role]}</dd>
        {inv.is_external && <><dt className="text-muted-foreground">Nemocnice</dt><dd>{inv.organization}</dd></>}
        {inv.committees.length > 0 && <><dt className="text-muted-foreground">Komise</dt><dd>{inv.committees.map((c) => c.name).join(', ')}</dd></>}
      </dl>
      <p className="mt-3 text-sm text-muted-foreground">
        Nastavte si přihlášení. Potom si v krátkém průvodci nastavíte, co chcete vidět na projektoru (PVW), co od kolegů
        vyžadujete a své normy pro řešení.
      </p>
      {error && (
        <p role="alert" className="mt-4 flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
          <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden /> {error}
        </p>
      )}
      <form onSubmit={submit} noValidate className="mt-5 flex flex-col gap-4">
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Uživatelské jméno
          <Input autoComplete="username" autoCapitalize="none" spellCheck={false} value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Heslo (aspoň 8 znaků)
          <Input type={show ? 'text' : 'password'} autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} required
            rightIcon={
              <button type="button" onClick={() => setShow(!show)} aria-label={show ? 'Skrýt heslo' : 'Zobrazit heslo'} className="text-muted-foreground hover:text-foreground">
                {show ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
              </button>
            } />
        </label>
        <label className="flex flex-col gap-1.5 text-sm font-medium">
          Heslo znovu
          <Input type={show ? 'text' : 'password'} autoComplete="new-password" value={password2} onChange={(e) => setPassword2(e.target.value)} required />
        </label>
        <Button type="submit" size="lg" className="mt-1 w-full" isLoading={saving}>Založit účet a pokračovat</Button>
        <p className="text-center text-xs text-muted-foreground">
          Odkaz platí do {new Date(inv.expires_at).toLocaleString('cs-CZ', { dateStyle: 'medium', timeStyle: 'short' })} a jen jednou.
        </p>
      </form>
    </>
  );
}
