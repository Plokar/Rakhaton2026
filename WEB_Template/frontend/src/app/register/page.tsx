'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Activity, CircleAlert, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { TemplateAreasEditor } from '@/components/mdt/FactLayoutEditor';
import { ROLE_META } from '@/components/mdt/roles';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { ApiError, type RegisterData } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { ProjectorLayout, TemplateArea } from '@/types/mdt';

type Specialty = RegisterData['specialty'];

/** Odbornosti pro registraci (RoleId bez „patient“, T-319); barva štítku podle D-017. */
const SPECIALTIES = (Object.keys(ROLE_META) as (keyof typeof ROLE_META)[]).filter((r): r is Specialty => r !== 'patient');

/** České chyby registrace: DRF vrací chyby po polích. */
function registerError(err: unknown): string {
  if (err instanceof ApiError && err.data && typeof err.data === 'object') {
    const messages = Object.values(err.data as Record<string, unknown>)
      .flatMap((v) => (Array.isArray(v) ? v : [v]))
      .filter((v): v is string => typeof v === 'string');
    if (messages.length) return messages.join(' ');
  }
  if (err instanceof ApiError) return `Server vrátil chybu ${err.status}. Zkuste to prosím znovu.`;
  return 'Server neodpovídá. Zkontrolujte připojení a zkuste to znovu.';
}

/**
 * Registrace kolegy (T-319, T-338) ve dvou krocích: 1) profil (jméno, tituly, profese, přihlášení),
 * 2) šablona klíčových údajů předvyplněná podle profese (pneumolog = výběr pro plíce), jde upravit i přeskočit.
 * Nový účet je člen komise; roli předsedy nebo zadávajícího lékaře nastaví předseda v Týmu komise.
 */
export default function RegisterPage() {
  const router = useRouter();
  const { register, user } = useAuth();

  const [username, setUsername] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [firstName, setFirstName] = React.useState('');
  const [lastName, setLastName] = React.useState('');
  const [titleBefore, setTitleBefore] = React.useState('');
  const [titleAfter, setTitleAfter] = React.useState('');
  const [step, setStep] = React.useState<1 | 2>(1);
  const [templates, setTemplates] = React.useState<Partial<Record<TemplateArea, ProjectorLayout>>>({});
  const [preset, setPreset] = React.useState<string | undefined>();
  const onTemplates = React.useCallback((next: Partial<Record<TemplateArea, ProjectorLayout>>, presetId?: string) => {
    setTemplates(next);
    if (presetId) setPreset(presetId);
  }, []);
  const [specialty, setSpecialty] = React.useState<Specialty | ''>('');
  const [password, setPassword] = React.useState('');
  const [password2, setPassword2] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (user) router.push('/dashboard');
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!specialty) return setError('Vyberte svou profesi (odbornost).');
    if (!username.trim() || !email.trim()) return setError('Vyplňte uživatelské jméno a e-mail.');
    if (password !== password2) return setError('Zadaná hesla se neshodují.');
    if (password.length < 8) return setError('Heslo musí mít aspoň 8 znaků.');
    if (step === 1) return setStep(2);
    await submit(true);
  };

  const submit = async (withTemplate: boolean) => {
    if (!specialty) return;
    setError('');
    setLoading(true);
    const chosen = Object.fromEntries(Object.entries(templates).filter(([, l]) => l && Object.keys(l).length));
    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
        password2,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        specialty,
        title_before: titleBefore.trim(),
        title_after: titleAfter.trim(),
        ...(withTemplate && Object.keys(chosen).length ? { templates: chosen, preset } : {}),
      });
      router.push('/dashboard');
    } catch (err: unknown) {
      setError(registerError(err));
      setLoading(false);
    }
  };

  return (
    <div
      className="flex min-h-dvh flex-col bg-background px-5 py-4 sm:px-10"
      style={{ paddingBottom: 'calc(1rem + var(--cookie-banner-space, 0px))' }}
    >
      <div className="flex items-center justify-between gap-3">
        <Link href="/login" className="flex items-center gap-2.5 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Activity className="size-5" aria-hidden />
          </span>
          <span translate="no" className="text-base font-semibold tracking-tight">MedTeam</span>
        </Link>
        <ThemeToggle />
      </div>

      <main className={cn('mx-auto my-auto w-full py-8', step === 1 ? 'max-w-md' : 'max-w-3xl')}>
        <p className="text-xs font-medium text-muted-foreground">Krok {step} ze 2 · {step === 1 ? 'profil lékaře' : 'co chcete u pacienta vidět'}</p>
        <h1 className="text-2xl font-semibold tracking-tight">{step === 1 ? 'Registrace do komise' : 'Vaše šablona údajů'}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {step === 1
            ? 'Profese určí, co se vám v podkladu ukáže nahoře, a předvyplní šablonu údajů. Roli předsedy nebo zadávajícího lékaře nastaví předseda komise.'
            : 'Předvyplněno podle vaší profese. Skryjte nebo seřaďte kategorie a údaje; systém si to pamatuje u všech vašich pacientů dané oblasti. Kdykoli změníte v Nastavení.'}
        </p>

        {error && (
          <p role="alert" className="mt-5 flex items-start gap-2 rounded-lg bg-destructive/10 px-3 py-2.5 text-sm text-destructive">
            <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
            {error}
          </p>
        )}

        <form onSubmit={handleSubmit} noValidate className="mt-6 flex flex-col gap-4">
          {step === 2 ? (
            <>
              <TemplateAreasEditor value={templates} onChange={onTemplates} specialty={specialty || null} initFromPresets />
              <div className="flex flex-wrap gap-2 border-t border-border pt-4">
                <Button type="button" variant="outline" onClick={() => setStep(1)} disabled={loading}>Zpět</Button>
                <Button type="submit" isLoading={loading}>Zaregistrovat se se šablonou</Button>
                <Button type="button" variant="ghost" onClick={() => void submit(false)} disabled={loading}>Přeskočit šablonu</Button>
              </div>
            </>
          ) : (
          <>
          <div className="grid grid-cols-2 gap-3">
            <Field id="reg-title-before" label="Titul před jménem">
              <Input id="reg-title-before" autoComplete="honorific-prefix" placeholder="MUDr." maxLength={40} value={titleBefore} onChange={(e) => setTitleBefore(e.target.value)} />
            </Field>
            <Field id="reg-title-after" label="Titul za jménem">
              <Input id="reg-title-after" autoComplete="honorific-suffix" placeholder="Ph.D." maxLength={40} value={titleAfter} onChange={(e) => setTitleAfter(e.target.value)} />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field id="reg-first" label="Jméno">
              <Input id="reg-first" autoComplete="given-name" value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </Field>
            <Field id="reg-last" label="Příjmení">
              <Input id="reg-last" autoComplete="family-name" value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </Field>
          </div>

          <fieldset>
            <legend className="mb-1.5 text-sm font-medium">Profese (odbornost)</legend>
            <div className="flex flex-wrap gap-1.5" role="radiogroup" aria-label="Odbornost">
              {SPECIALTIES.map((r) => (
                <button
                  key={r}
                  type="button"
                  role="radio"
                  aria-checked={specialty === r}
                  onClick={() => setSpecialty(r)}
                  className={cn(
                    'rounded-md border px-2.5 py-1 text-[13px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    specialty === r ? ROLE_META[r].className : 'border-border bg-card text-muted-foreground hover:text-foreground',
                  )}
                >
                  {ROLE_META[r].label}
                </button>
              ))}
            </div>
          </fieldset>

          <Field id="reg-username" label="Uživatelské jméno">
            <Input
              id="reg-username"
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              placeholder="např. novak…"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </Field>
          <Field id="reg-email" label="E-mail">
            <Input id="reg-email" type="email" autoComplete="email" spellCheck={false} value={email} onChange={(e) => setEmail(e.target.value)} required />
          </Field>
          <Field id="reg-password" label="Heslo (aspoň 8 znaků)">
            <Input
              id="reg-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? 'Skrýt heslo' : 'Zobrazit heslo'}
                  className="text-muted-foreground hover:text-foreground"
                >
                  {showPassword ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
                </button>
              }
              required
            />
          </Field>
          <Field id="reg-password2" label="Heslo znovu">
            <Input
              id="reg-password2"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
              required
            />
          </Field>

          <Button type="submit" size="lg" className="mt-2 w-full" isLoading={loading}>
            Pokračovat na šablonu údajů
          </Button>
          <p className="text-center text-xs leading-relaxed text-muted-foreground">
            Registrací souhlasíte s{' '}
            <Link href="/terms" className="underline underline-offset-4 hover:text-foreground">podmínkami užití</Link> a berete na vědomí{' '}
            <Link href="/privacy" className="underline underline-offset-4 hover:text-foreground">zásady ochrany soukromí</Link>. Prototyp pracuje jen se syntetickými pacienty.
          </p>
          </>
          )}
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Už máte účet?{' '}
          <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Přihlásit se
          </Link>
        </p>
      </main>
    </div>
  );
}

function Field({ id, label, children }: { id: string; label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-sm font-medium">
        {label}
      </label>
      {children}
    </div>
  );
}
