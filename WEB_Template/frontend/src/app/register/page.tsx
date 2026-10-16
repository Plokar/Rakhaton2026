'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import {
  Zap,
  Eye,
  EyeOff,
  User,
  Mail,
  Lock,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

export default function RegisterPage() {
  const router = useRouter();
  const { register, user } = useAuth();

  const [username, setUsername] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [firstName, setFirstName] = React.useState('');
  const [lastName, setLastName] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [password2, setPassword2] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);

  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (user) {
      router.push('/dashboard');
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== password2) {
      setError('Zadaná hesla se neshodují.');
      return;
    }

    if (password.length < 8) {
      setError('Heslo musí mít minimálně 8 znaků.');
      return;
    }

    setLoading(true);

    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
        password2,
        first_name: firstName.trim(),
        last_name: lastName.trim(),
      });
      router.push('/dashboard');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Registrace se nezdařila. Zkontrolujte vyplněná pole.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      {/* Left side: Hero showcase (desktop only) */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between border-r border-border bg-card p-12 relative overflow-hidden">
        <div className="absolute -left-20 -top-20 h-96 w-96 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute right-0 bottom-0 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-indigo-500/30">
            <Zap className="h-5 w-5 fill-current" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight">Hackathon OS</span>
            <span className="block text-xs font-mono text-muted-foreground">Vytvořte si vývojářský účet</span>
          </div>
        </div>

        <div className="space-y-6 max-w-md">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <Sparkles className="h-3.5 w-3.5" /> Okamžitý start týmu
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight">
            Připoj se k projektu <br />
            a začněte vyvíjet.
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Každý nový uživatel získá přístup k projektovému dashboardu, sdílenému Kanbanu úkolů,
            AI Studiu a real-time WebSocket komunikačnímu kanálu.
          </p>

          <div className="space-y-2 pt-4 border-t border-border text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Automatické přihlášení a nastavení JWT tokenu</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              <span>Plný přístup k API a WebSocket endpointům</span>
            </div>
          </div>
        </div>

        <div className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} Hackathon OS • Django 4.2 &amp; Next.js 16
        </div>
      </div>

      {/* Right side: Register form */}
      <div className="flex flex-1 flex-col justify-between p-6 sm:p-12 lg:p-16">
        <div className="flex items-center justify-between">
          <Link href="/" className="lg:hidden flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Zap className="h-4 w-4 fill-current" />
            </div>
            <span className="font-bold text-sm">Hackathon OS</span>
          </Link>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>

        <div className="mx-auto w-full max-w-md my-auto">
          <div className="mb-6">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Vytvořit nový účet</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Zaregistrujte se a vyzkoušejte Hackathon OS v plné parádě.
            </p>
          </div>

          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive font-medium animate-in fade-in">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Jméno
                </label>
                <Input
                  type="text"
                  placeholder="Petr"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">
                  Příjmení
                </label>
                <Input
                  type="text"
                  placeholder="Novák"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Uživatelské jméno *
              </label>
              <Input
                type="text"
                placeholder="petr_dev"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                leftIcon={<User className="h-4 w-4" />}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                E-mailová adresa *
              </label>
              <Input
                type="email"
                placeholder="petr@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail className="h-4 w-4" />}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Heslo (min. 8 znaků) *
              </label>
              <Input
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock className="h-4 w-4" />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Potvrzení hesla *
              </label>
              <Input
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password2}
                onChange={(e) => setPassword2(e.target.value)}
                leftIcon={<Lock className="h-4 w-4" />}
                required
              />
            </div>

            <Button type="submit" className="w-full mt-2" isLoading={loading} size="lg">
              Zaregistrovat se a pokračovat <ArrowRight className="h-4 w-4" />
            </Button>

            <p className="text-[11px] text-muted-foreground text-center leading-relaxed pt-1">
              Registrací souhlasíte s našimi{' '}
              <Link href="/terms" className="text-primary hover:underline font-medium">
                Podmínkami užití
              </Link>{' '}
              a berete na vědomí{' '}
              <Link href="/privacy" className="text-primary hover:underline font-medium">
                Zásady ochrany soukromí
              </Link>.
            </p>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Už máte účet?{' '}
            <Link href="/login" className="font-semibold text-primary hover:underline">
              Přihlaste se zde
            </Link>
          </p>
        </div>

        <div className="text-center text-xs text-muted-foreground">
          Hackathon OS v2.0 • Django 4.2 REST + Next.js 16
        </div>
      </div>
    </div>
  );
}
