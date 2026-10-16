'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import {
  Zap,
  Eye,
  EyeOff,
  User,
  Lock,
  ArrowRight,
  ShieldCheck,
  AlertCircle,
  Sparkles,
} from 'lucide-react';

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, user } = useAuth();

  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [showPassword, setShowPassword] = React.useState(false);
  const [error, setError] = React.useState('');
  const [loading, setLoading] = React.useState(false);

  const redirectUrl = searchParams.get('redirect') || '/dashboard';

  React.useEffect(() => {
    if (user) {
      router.push(redirectUrl);
    }
  }, [user, router, redirectUrl]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Vyplňte prosím uživatelské jméno i heslo.');
      return;
    }

    setError('');
    setLoading(true);

    try {
      await login(username.trim(), password);
      router.push(redirectUrl);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Přihlášení se nezdařilo. Zkontrolujte údaje.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const fillCredentials = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    setError('');
  };

  return (
    <div className="flex min-h-screen">
      {/* Left side: Hero showcase (desktop only) */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between border-r border-border bg-card p-12 relative overflow-hidden">
        {/* Subtle decorative background gradient */}
        <div className="absolute -left-20 -top-20 h-96 w-96 rounded-full bg-primary/10 blur-3xl pointer-events-none" />
        <div className="absolute right-0 bottom-0 h-96 w-96 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-indigo-500/30">
            <Zap className="h-5 w-5 fill-current" />
          </div>
          <div>
            <span className="text-base font-bold tracking-tight">Hackathon OS</span>
            <span className="block text-xs font-mono text-muted-foreground">Vítej v řídicím centru</span>
          </div>
        </div>

        <div className="space-y-6 max-w-md">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
            <Sparkles className="h-3.5 w-3.5" /> Hackathon Ready Environment
          </div>
          <h2 className="text-3xl font-extrabold tracking-tight">
            Vše nastaveno. <br />
            Můžeš se soustředit na samotný produkt.
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Stateless JWT autentizace s httpOnly cookies, auto-refresh tokeny, WebSocket echo a skupiny,
            připravené AI Studio a seedovaná databáze s projekty a úkoly.
          </p>

          <div className="space-y-3 pt-4 border-t border-border">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Plně kompatibilní s bezpečnostními standardy OWASP</span>
            </div>
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span>Traefik reverzní proxy s automatickým rate-limitingem</span>
            </div>
          </div>
        </div>

        <div className="text-xs text-muted-foreground">
          © {new Date().getFullYear()} Hackathon OS • Django 4.2 &amp; Next.js 16
        </div>
      </div>

      {/* Right side: Login form */}
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

        <div className="mx-auto w-full max-w-sm my-auto">
          <div className="mb-8">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Přihlášení k účtu</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Zadejte své přihlašovací údaje nebo použijte rychlé vyplnění.
            </p>
          </div>

          {/* Quick Fill Buttons for Hackathon Demo */}
          <div className="mb-6 rounded-xl border border-border/80 bg-muted/40 p-3 space-y-2">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              ⚡ Rychlé vyplnění demo účtů:
            </p>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillCredentials('admin', 'admin123456')}
                className="text-xs justify-start h-8 truncate"
              >
                👤 Admin
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fillCredentials('alice', 'demo123456')}
                className="text-xs justify-start h-8 truncate"
              >
                👩 Alice (AI Lead)
              </Button>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-4 flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive font-medium animate-in fade-in">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Uživatelské jméno
              </label>
              <Input
                type="text"
                placeholder="např. admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                leftIcon={<User className="h-4 w-4" />}
                required
                autoFocus
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-foreground">
                  Heslo
                </label>
                <Link
                  href="/forgot-password"
                  className="text-xs text-primary hover:underline font-medium"
                >
                  Zapomenuté heslo?
                </Link>
              </div>
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
                    title={showPassword ? 'Skrýt heslo' : 'Zobrazit heslo'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                }
                required
              />
            </div>

            <Button type="submit" className="w-full mt-2" isLoading={loading} size="lg">
              Přihlásit se <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Nemáte ještě účet?{' '}
            <Link href="/register" className="font-semibold text-primary hover:underline">
              Zaregistrujte se zdarma
            </Link>
          </p>
        </div>

        <div className="text-center text-xs text-muted-foreground">
          Lokální e-maily můžete sledovat na{' '}
          <a href="http://localhost:8025" target="_blank" rel="noreferrer" className="text-foreground underline">
            Mailhog :8025
          </a>
        </div>
      </div>
    </div>
  );
}
