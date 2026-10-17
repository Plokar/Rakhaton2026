'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Activity,
  ArrowRight,
  CircleAlert,
  CircleCheck,
  CircleDot,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  OctagonAlert,
  User,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { CompatibilityLight } from '@/components/mdt/CompatibilityLight';
import { ROLE_META } from '@/components/mdt/roles';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { ApiError } from '@/lib/api';
import { cn } from '@/lib/utils';
import type { Light, RoleId } from '@/types/mdt';

// Demo účty zakládá `seed_mdt` (T-501) nad fiktivními daty. 1-click přihlášení heslo záměrně zveřejňuje;
// na produkci se musí shodovat s MDT_DEMO_PASSWORD backendu.
const DEMO_PASSWORD = process.env.NEXT_PUBLIC_DEMO_PASSWORD || 'demo123456';

/** Odbornost = barevný štítek (D-017), role v komisi = text vedle. */
const DEMO_ACCOUNTS: { username: string; specialty: RoleId; role: string; note?: string }[] = [
  { username: 'predseda', specialty: 'oncologist', role: 'Předseda komise', note: 'spravuje boardy a termíny' },
  { username: 'onkolog', specialty: 'oncologist', role: 'Zadávající lékař' },
  { username: 'pneumolog', specialty: 'pulmonologist', role: 'Zadávající lékař', note: 'pacient P04' },
  { username: 'chirurg', specialty: 'surgeon', role: 'Člen komise' },
  { username: 'radiolog', specialty: 'radiologist', role: 'Člen komise' },
  { username: 'patolog', specialty: 'pathologist', role: 'Člen komise' },
  { username: 'radioterapeut', specialty: 'radiation_oncologist', role: 'Člen komise' },
];

/** Přesměrování po přihlášení jen v rámci aplikace (žádné externí URL z parametru). */
function safeRedirect(value: string | null): string {
  return value && value.startsWith('/') && !value.startsWith('//') ? value : '/dashboard';
}

function loginErrorMessage(err: unknown, demo: boolean): string {
  if (err instanceof ApiError) {
    if (err.status === 400 || err.status === 401) {
      return demo
        ? 'Demo účet se nepodařilo přihlásit. Ověřte, že backend má založené demo účty (seed_mdt).'
        : 'Nesprávné uživatelské jméno nebo heslo.';
    }
    if (err.status === 429) return 'Příliš mnoho pokusů o přihlášení. Zkuste to za minutu.';
    return `Server vrátil chybu ${err.status}. Zkuste to prosím znovu.`;
  }
  return 'Server neodpovídá. Zkontrolujte připojení a zkuste to znovu.';
}

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, user } = useAuth();

  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [error, setError] = React.useState('');
  /** Co se právě přihlašuje: 'form', nebo uživatelské jméno demo účtu. */
  const [pending, setPending] = React.useState<string | null>(null);
  const usernameRef = React.useRef<HTMLInputElement>(null);
  const passwordRef = React.useRef<HTMLInputElement>(null);

  const redirectUrl = safeRedirect(searchParams.get('redirect'));

  React.useEffect(() => {
    if (user) router.push(redirectUrl);
  }, [user, router, redirectUrl]);

  const signIn = async (name: string, secret: string, source: string) => {
    setError('');
    setPending(source);
    try {
      await login(name, secret);
      router.push(redirectUrl);
    } catch (err: unknown) {
      setError(loginErrorMessage(err, source !== 'form'));
      setPending(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Vyplňte uživatelské jméno i heslo.');
      (username.trim() ? passwordRef : usernameRef).current?.focus();
      return;
    }
    void signIn(username.trim(), password, 'form');
  };

  return (
    <div className="flex min-h-dvh bg-background">
      <aside
        aria-label="O aplikaci MedTeam"
        className="hidden min-h-dvh flex-1 flex-col justify-between gap-8 border-r border-border bg-muted/40 p-8 lg:flex xl:p-14"
      >
        <Brand subtitle />
        <div className="flex flex-col gap-8 xl:flex-row xl:items-center xl:gap-14">
          <div className="max-w-md">
            <p className="text-3xl font-semibold leading-tight tracking-tight text-balance text-foreground xl:text-4xl">
              Celý případ pro komisi na jednom úzkém panelu
            </p>
            {/* Pod 1280 px (projektor 1024 × 768) mluví za odstavec sama ukázka. */}
            <p className="mt-4 hidden text-base leading-relaxed text-pretty text-muted-foreground xl:block">
              Vedle snímku z PACS. Data pacienta z InterSystems IRIS, citace u každého tvrzení a semafor léčby
              počítaný pravidly. Rozhoduje vždy lékař.
            </p>
          </div>
          <ProductPreview />
        </div>
        <p className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} MedTeam · podklady pro multidisciplinární onkologickou komisi
        </p>
      </aside>

      <main className="flex w-full flex-col px-5 py-4 sm:px-10 lg:w-[480px] lg:shrink-0 lg:px-12 xl:w-[520px]">
        <div className="flex items-center justify-between gap-3">
          <Brand className="lg:hidden" />
          <ThemeToggle className="ml-auto" />
        </div>

        <div className="mx-auto my-auto w-full max-w-sm py-6">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Přihlášení</h1>
          <p className="mt-1 text-sm text-muted-foreground">Pro ukázku vyberte roli. Vlastním účtem se přihlásíte níže.</p>

          <section aria-labelledby="demo-accounts" className="mt-5">
            <div className="flex items-baseline justify-between gap-3">
              <h2 id="demo-accounts" className="text-sm font-medium text-foreground">Demo účty</h2>
              <p className="text-xs text-muted-foreground">syntetická data hackathonu</p>
            </div>
            <ul className="mt-2 divide-y divide-border overflow-hidden rounded-xl border border-border bg-card">
              {DEMO_ACCOUNTS.map((account) => (
                <li key={account.username}>
                  <DemoAccountButton
                    account={account}
                    pending={pending === account.username}
                    disabled={pending !== null}
                    onSelect={() => {
                      setUsername(account.username);
                      setPassword(DEMO_PASSWORD);
                      void signIn(account.username, DEMO_PASSWORD, account.username);
                    }}
                  />
                </li>
              ))}
            </ul>
          </section>

          <div className="my-5 flex items-center gap-3 text-xs text-muted-foreground" aria-hidden>
            <span className="h-px flex-1 bg-border" />
            nebo vlastním účtem
            <span className="h-px flex-1 bg-border" />
          </div>

          {error && (
            <p
              role="alert"
              className="mb-4 flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2.5 text-sm text-destructive"
            >
              <CircleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
              {error}
            </p>
          )}

          <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <label htmlFor="login-username" className="text-sm font-medium text-foreground">
                Uživatelské jméno
              </label>
              <Input
                ref={usernameRef}
                id="login-username"
                name="username"
                autoComplete="username"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="např. predseda…"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                aria-invalid={Boolean(error) && !username.trim()}
                leftIcon={<User className="size-4" aria-hidden />}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex items-baseline justify-between gap-3">
                <label htmlFor="login-password" className="text-sm font-medium text-foreground">
                  Heslo
                </label>
                <Link
                  href="/forgot-password"
                  className="rounded-sm text-xs font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  Zapomenuté heslo?
                </Link>
              </div>
              <Input
                ref={passwordRef}
                id="login-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                aria-invalid={Boolean(error) && !password}
                leftIcon={<Lock className="size-4" aria-hidden />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    aria-label={showPassword ? 'Skrýt heslo' : 'Zobrazit heslo'}
                    aria-pressed={showPassword}
                    className="rounded-sm text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    {showPassword ? <EyeOff className="size-4" aria-hidden /> : <Eye className="size-4" aria-hidden />}
                  </button>
                }
              />
            </div>

            <Button type="submit" size="lg" className="mt-1 w-full" disabled={pending !== null}>
              {pending === 'form' ? (
                <>
                  <Loader2 className="size-4 animate-spin motion-reduce:animate-none" aria-hidden />
                  Přihlašuji…
                </>
              ) : (
                <>
                  Přihlásit se
                  <ArrowRight className="size-4" aria-hidden />
                </>
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            Nemáte účet?{' '}
            <Link
              href="/register"
              className="rounded-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              Zaregistrujte se
            </Link>
          </p>
        </div>

        {process.env.NODE_ENV === 'development' && (
          <p className="text-center text-xs text-muted-foreground">
            Lokální e-maily:{' '}
            <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="text-foreground underline underline-offset-2">
              Mailhog :8025
            </a>
          </p>
        )}
      </main>
    </div>
  );
}

function Brand({ className, subtitle = false }: { className?: string; subtitle?: boolean }) {
  return (
    <div className={cn('flex items-center gap-2.5', className)}>
      <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Activity className="size-5" aria-hidden />
      </span>
      <span>
        <span translate="no" className="block text-lg font-bold leading-tight tracking-tight text-foreground">MedTeam</span>
        {subtitle && <span className="block text-xs text-muted-foreground">Podklady pro onkologickou komisi</span>}
      </span>
    </div>
  );
}

function DemoAccountButton({
  account,
  pending,
  disabled,
  onSelect,
}: {
  account: (typeof DEMO_ACCOUNTS)[number];
  pending: boolean;
  disabled: boolean;
  onSelect: () => void;
}) {
  const specialty = ROLE_META[account.specialty];
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      className="group flex w-full items-center gap-3 px-3 py-2 text-left transition-colors hover:bg-muted/70 focus-visible:bg-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-60"
    >
      <span className="sr-only">Přihlásit jako </span>
      <span className={cn('w-34 shrink-0 truncate rounded-md border px-2 py-0.5 text-center text-xs font-semibold', specialty.className)}>
        {specialty.label}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium text-foreground">{account.role}</span>
        {account.note && <span className="block truncate text-xs text-muted-foreground">{account.note}</span>}
      </span>
      {pending ? (
        <Loader2 className="size-4 shrink-0 animate-spin text-primary motion-reduce:animate-none" aria-label="Přihlašuji…" />
      ) : (
        <ArrowRight
          className="size-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-foreground motion-reduce:transition-none"
          aria-hidden
        />
      )}
    </button>
  );
}

// ── Ukázka úzkého panelu (syntetický pacient P03 z datasetu, jen ilustrace, nic se nenačítá) ──

const PREVIEW_STATUS: Record<'normal' | 'abnormal' | 'critical' | 'recorded', { icon: LucideIcon; className: string }> = {
  normal: { icon: CircleCheck, className: 'text-emerald-600 dark:text-emerald-400' },
  abnormal: { icon: CircleAlert, className: 'text-amber-600 dark:text-amber-400' },
  critical: { icon: OctagonAlert, className: 'text-red-600 dark:text-red-400' },
  recorded: { icon: CircleDot, className: 'text-muted-foreground' },
};

const PREVIEW_FACTS: { abbr: string; value: string; status: keyof typeof PREVIEW_STATUS }[] = [
  { abbr: 'PNP', value: 'lékař G1, pacient víc', status: 'critical' },
  { abbr: 'MMR/MSI', value: 'nevyšetřeno', status: 'abnormal' },
  { abbr: 'CEA', value: '13,9 µg/l, roste', status: 'abnormal' },
  { abbr: 'Hb', value: '114 g/l', status: 'abnormal' },
  { abbr: 'RAS', value: 'wild-type', status: 'recorded' },
  { abbr: 'Kreat', value: '89 µmol/l', status: 'normal' },
];

const PREVIEW_OPTIONS: { title: string; light: Light; reason: string }[] = [
  { title: 'Resekce jaterních metastáz', light: 'orange', reason: 'chybí CT hrudníku ≤ 6 týdnů' },
  { title: 'Konverzní chemoterapie', light: 'orange', reason: 'neuropatie: lékař G1 × pacient' },
  { title: 'Imunoterapie', light: 'grey', reason: 'MMR/MSI nevyšetřeno' },
];

function ProductPreview() {
  return (
    <figure className="w-[340px] shrink-0">
      <div
        aria-hidden
        inert
        className="select-none overflow-hidden rounded-xl border border-border bg-background text-foreground shadow-[0_16px_40px_-16px_rgb(15_23_42/0.28)]"
      >
        <div className="flex items-start gap-3 border-b border-border bg-card px-4 py-3">
          <div className="min-w-0 flex-1">
            <p className="text-[15px] font-semibold leading-tight">P03 · muž · 67 let</p>
            <p className="mt-1 text-xs leading-snug text-muted-foreground">Adenokarcinom sigmatu · cT3 cN1 cM1a</p>
          </div>
          <PreviewTile term="PS" value="0" note="pac. 1" warn />
          <PreviewTile term="C/P" value="C" note="kurativní" />
        </div>
        <div className="flex flex-col gap-3 px-4 py-3">
          <ul className="grid grid-cols-2 gap-x-3 gap-y-2">
            {PREVIEW_FACTS.map((fact) => {
              const { icon: Icon, className } = PREVIEW_STATUS[fact.status];
              return (
                <li key={fact.abbr} className="flex min-w-0 items-start gap-1.5">
                  <Icon className={cn('mt-0.5 size-3.5 shrink-0', className)} strokeWidth={2.25} />
                  <span className="min-w-0 text-xs leading-snug">
                    <span className="block font-semibold">{fact.abbr}</span>
                    <span className="block truncate text-muted-foreground">{fact.value}</span>
                  </span>
                </li>
              );
            })}
          </ul>
          <ul className="flex flex-col divide-y divide-border border-t border-border">
            {PREVIEW_OPTIONS.map((option) => (
              <li key={option.title} className="flex items-center justify-between gap-2 py-2 last:pb-0">
                <span className="min-w-0 text-xs leading-snug">
                  <span className="block font-semibold">{option.title}</span>
                  <span className="block truncate text-muted-foreground">{option.reason}</span>
                </span>
                <CompatibilityLight light={option.light} className="px-1.5 text-[11px]" />
              </li>
            ))}
          </ul>
        </div>
        <div className="flex items-start gap-3 border-t-2 border-primary/40 bg-card px-4 py-2.5">
          <p className="line-clamp-2 flex-1 text-sm font-bold leading-snug">
            Jsou jaterní metastázy po 8 cyklech FOLFOX + bevacizumab resekabilní?
          </p>
          <p className="shrink-0 text-right leading-tight">
            <span className="block text-[10px] text-muted-foreground">MKN-10</span>
            <span className="text-sm font-bold">C18.7</span>
          </p>
        </div>
      </div>
      <figcaption className="mt-3 text-xs leading-relaxed text-muted-foreground">
        Ukázka úzkého panelu pro projektor · syntetický pacient P03 z datasetu hackathonu
      </figcaption>
    </figure>
  );
}

function PreviewTile({ term, value, note, warn = false }: { term: string; value: string; note: string; warn?: boolean }) {
  return (
    <div className="flex min-w-12 flex-col items-center rounded-lg border border-border bg-background px-2 py-1">
      <span className="text-[10px] font-medium text-muted-foreground">{term}</span>
      <span className="text-xl font-bold leading-none">{value}</span>
      <span className={cn('mt-0.5 text-[10px]', warn ? 'font-medium text-amber-700 dark:text-amber-400' : 'text-muted-foreground')}>{note}</span>
    </div>
  );
}
