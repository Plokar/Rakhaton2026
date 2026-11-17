'use client';

import * as React from 'react';
import QRCode from 'qrcode';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ShieldCheck } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Input } from '@/components/shadcn/input';
import { apiFetch } from '@/lib/api';
import { apiErrorMessage } from '@/lib/queries';

type State = { enabled: boolean; required: boolean };
const KEY = ['auth', '2fa'] as const;

const post = <T,>(path: string, body?: unknown) =>
  apiFetch<T>(`/api/auth/2fa/${path}`, { method: 'POST', ...(body ? { body: JSON.stringify(body) } : {}) });

/**
 * Dvoufázové přihlášení (T-383): QR kód pro aplikaci Authenticator, potvrzení kódem, vypnutí heslem a kódem.
 * Správce MDT ho má povinné (`required`), vypnout ho nemůže.
 */
export function TwoFactorCard() {
  const client = useQueryClient();
  const state = useQuery({ queryKey: KEY, queryFn: () => apiFetch<State>('/api/auth/2fa/') });
  const [setup, setSetup] = React.useState<{ secret: string; svg: string } | null>(null);
  const [code, setCode] = React.useState('');
  const [password, setPassword] = React.useState('');

  const start = useMutation({
    mutationFn: () => post<{ secret: string; otpauth_uri: string }>('setup/'),
    onSuccess: async ({ secret, otpauth_uri }) => {
      const svg = await QRCode.toString(otpauth_uri, { type: 'svg', margin: 1 });
      setSetup({ secret, svg });
      setCode('');
    },
    onError: (err) => toast.error(apiErrorMessage(err, 'Nastavení se nepodařilo spustit.')),
  });
  const confirm = useMutation({
    mutationFn: () => post<State>('confirm/', { code: code.replace(/\s/g, '') }),
    onSuccess: (next) => {
      client.setQueryData(KEY, next);
      setSetup(null);
      toast.success('Dvoufázové přihlášení je zapnuté.');
    },
    onError: (err) => toast.error(apiErrorMessage(err, 'Kód nesedí.')),
  });
  const disable = useMutation({
    mutationFn: () => post<State>('disable/', { password, code: code.replace(/\s/g, '') }),
    onSuccess: (next) => {
      client.setQueryData(KEY, next);
      setPassword('');
      setCode('');
      toast('Dvoufázové přihlášení je vypnuté.');
    },
    onError: (err) => toast.error(apiErrorMessage(err, 'Vypnutí se nepodařilo.')),
  });

  const data = state.data;
  return (
    <section id="zabezpeceni" aria-labelledby="zabezpeceni-nadpis" className="scroll-mt-20 rounded-xl border border-border bg-card p-5">
      <h2 id="zabezpeceni-nadpis" className="flex items-center gap-2 text-base font-semibold">
        <ShieldCheck className="size-4 text-primary" aria-hidden /> Dvoufázové přihlášení
      </h2>
      <p className="mb-4 mt-1 text-sm text-muted-foreground">
        Kromě hesla se při přihlášení zadá kód z aplikace v telefonu (Google nebo Microsoft Authenticator).
        {data?.required && ' Jako správce MDT ho máte povinné.'}
      </p>
      {!data ? null : data.enabled ? (
        <div className="space-y-3">
          <p className="text-sm font-medium text-emerald-700 dark:text-emerald-400">Zapnuto.</p>
          {!data.required && (
            <form
              className="flex flex-wrap items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                disable.mutate();
              }}
            >
              <Input type="password" autoComplete="current-password" placeholder="Heslo" value={password}
                onChange={(e) => setPassword(e.target.value)} aria-label="Heslo" className="w-44" />
              <Input inputMode="numeric" autoComplete="one-time-code" placeholder="Kód" value={code} maxLength={7}
                onChange={(e) => setCode(e.target.value)} aria-label="Kód z aplikace" className="w-28" />
              <Button type="submit" variant="outline" disabled={!password || !code || disable.isPending}>Vypnout</Button>
            </form>
          )}
        </div>
      ) : setup ? (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            confirm.mutate();
          }}
        >
          <p className="text-sm">1. V aplikaci Authenticator přidejte účet načtením kódu:</p>
          <div
            className="size-48 rounded-lg bg-white p-1 ring-1 ring-border [&_svg]:h-full [&_svg]:w-full"
            role="img"
            aria-label="QR kód pro aplikaci Authenticator"
            // SVG vytvořila knihovna qrcode z adresy otpauth od serveru
            dangerouslySetInnerHTML={{ __html: setup.svg }}
          />
          <p className="text-[13px] text-muted-foreground">
            Nejde načíst? Zadejte klíč ručně: <code translate="no" className="break-all font-mono text-foreground">{setup.secret}</code>
          </p>
          <label htmlFor="twofa-code" className="block text-sm">2. Opište šestimístný kód z aplikace:</label>
          <div className="flex gap-2">
            <Input id="twofa-code" inputMode="numeric" autoComplete="one-time-code" maxLength={7} value={code}
              onChange={(e) => setCode(e.target.value)} className="w-32" placeholder="123 456" />
            <Button type="submit" disabled={code.replace(/\s/g, '').length !== 6 || confirm.isPending}>Zapnout</Button>
          </div>
        </form>
      ) : (
        <Button onClick={() => start.mutate()} disabled={start.isPending}>Nastavit dvoufázové přihlášení</Button>
      )}
    </section>
  );
}
