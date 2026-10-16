'use client';

import * as React from 'react';
import Link from 'next/link';
import { authApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeToggle } from '@/components/ui/theme-toggle';
import { Zap, Mail, ArrowLeft, CheckCircle2, AlertCircle, ExternalLink } from 'lucide-react';

export default function ForgotPasswordPage() {
  const [email, setEmail] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [sent, setSent] = React.useState(false);
  const [error, setError] = React.useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setError('');
    setLoading(true);

    try {
      await authApi.forgotPassword(email.trim());
      setSent(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Požadavek se nepodařilo odeslat.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 sm:p-6 bg-background">
      <div className="absolute top-6 right-6">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md rounded-2xl border border-border bg-card p-6 sm:p-8 shadow-xl">
        <div className="mb-6 text-center">
          <Link href="/" className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground mb-4">
            <Zap className="h-5 w-5 fill-current" />
          </Link>
          <h1 className="text-xl font-bold tracking-tight text-foreground">Obnova zapomenutého hesla</h1>
          <p className="mt-1 text-xs text-muted-foreground">
            Zadejte e-mail přidružený k vašemu účtu. V dev módu se e-mail odešle do Mailhogu.
          </p>
        </div>

        {sent ? (
          <div className="space-y-4 text-center animate-in fade-in">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-500">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <p className="text-sm text-foreground font-medium">
              E-mail s odkazem pro obnovu byl odeslán.
            </p>
            <div className="rounded-xl border border-border bg-muted/40 p-3 text-xs text-muted-foreground text-left space-y-1">
              <p className="font-semibold text-foreground">🔍 Kde najdu e-mail v dev prostředí?</p>
              <p>Otevřete Mailhog webové rozhraní na portu 8025:</p>
              <a
                href="http://localhost:8025"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline font-semibold"
              >
                Otevřít Mailhog (:8025) <ExternalLink className="h-3 w-3" />
              </a>
            </div>
            <Link href="/login" className="block pt-2">
              <Button variant="outline" className="w-full">
                Zpět na přihlášení
              </Button>
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-foreground mb-1.5">
                Váš e-mail
              </label>
              <Input
                type="email"
                placeholder="např. admin@hackathon.local"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail className="h-4 w-4" />}
                required
                autoFocus
              />
            </div>

            <Button type="submit" className="w-full" isLoading={loading} size="lg">
              Odeslat resetovací odkaz
            </Button>

            <Link href="/login" className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground hover:text-foreground pt-2">
              <ArrowLeft className="h-3.5 w-3.5" /> Zpět na přihlášení
            </Link>
          </form>
        )}
      </div>
    </div>
  );
}
