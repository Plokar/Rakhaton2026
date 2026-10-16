'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { authApi } from '@/lib/api';
import {
  User,
  Lock,
  Sun,
  Moon,
  Laptop,
  CheckCircle2,
  AlertCircle,
  Key,
} from 'lucide-react';

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const { theme, setTheme } = useTheme();

  // Profile form
  const [firstName, setFirstName] = React.useState(user?.first_name || '');
  const [lastName, setLastName] = React.useState(user?.last_name || '');
  const [email, setEmail] = React.useState(user?.email || '');
  const [profileSaving, setProfileSaving] = React.useState(false);
  const [profileSuccess, setProfileSuccess] = React.useState('');
  const [profileError, setProfileError] = React.useState('');

  // Password form
  const [oldPassword, setOldPassword] = React.useState('');
  const [newPassword, setNewPassword] = React.useState('');
  const [newPassword2, setNewPassword2] = React.useState('');
  const [pwSaving, setPwSaving] = React.useState(false);
  const [pwSuccess, setPwSuccess] = React.useState('');
  const [pwError, setPwError] = React.useState('');

  React.useEffect(() => {
    if (user) {
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
      setEmail(user.email || '');
    }
  }, [user]);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError('');
    setProfileSuccess('');
    setProfileSaving(true);

    try {
      await authApi.updateMe({
        first_name: firstName,
        last_name: lastName,
        email,
      });
      await refreshUser();
      setProfileSuccess('Profil byl úspěšně uložen.');
      setTimeout(() => setProfileSuccess(''), 3000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Uložení profilu selhalo.';
      setProfileError(msg);
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError('');
    setPwSuccess('');

    if (newPassword !== newPassword2) {
      setPwError('Nová hesla se neshodují.');
      return;
    }

    if (newPassword.length < 8) {
      setPwError('Nové heslo musí mít alespoň 8 znaků.');
      return;
    }

    setPwSaving(true);

    try {
      await authApi.changePassword({
        old_password: oldPassword,
        new_password: newPassword,
        new_password2: newPassword2,
      });
      setOldPassword('');
      setNewPassword('');
      setNewPassword2('');
      setPwSuccess('Heslo bylo úspěšně změněno.');
      setTimeout(() => setPwSuccess(''), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Změna hesla selhala.';
      setPwError(msg);
    } finally {
      setPwSaving(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6 max-w-4xl">
        {/* Header */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
            Nastavení profilu
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Správa osobních údajů, hesla a předvoleb vzhledu aplikace.
          </p>
        </div>

        {/* Theme Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Vzhled a motiv</CardTitle>
            <CardDescription>Vyberte si preferovaný vizuální režim rozhraní.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3 max-w-md">
              {[
                { id: 'light', label: 'Světlý', icon: <Sun className="h-5 w-5" /> },
                { id: 'dark', label: 'Tmavý', icon: <Moon className="h-5 w-5" /> },
                { id: 'system', label: 'Systém', icon: <Laptop className="h-5 w-5" /> },
              ].map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setTheme(m.id as 'light' | 'dark' | 'system')}
                  className={`flex flex-col items-center justify-center gap-2 rounded-xl border p-4 text-xs font-semibold transition ${
                    theme === m.id
                      ? 'border-primary bg-primary/10 text-primary shadow-sm'
                      : 'border-border bg-card text-muted-foreground hover:bg-muted/40 hover:text-foreground'
                  }`}
                >
                  {m.icon}
                  <span>{m.label}</span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Personal info */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Osobní údaje</CardTitle>
            <CardDescription>Informace zobrazené členům týmu.</CardDescription>
          </CardHeader>
          <CardContent>
            {profileSuccess && (
              <div className="mb-4 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{profileSuccess}</span>
              </div>
            )}
            {profileError && (
              <div className="mb-4 flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{profileError}</span>
              </div>
            )}

            <form onSubmit={handleProfileSubmit} className="space-y-4 max-w-md">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Uživatelské jméno</label>
                <Input value={user?.username || ''} disabled className="opacity-70 font-mono" />
                <span className="text-[11px] text-muted-foreground mt-0.5 block">Uživatelské jméno nelze měnit.</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">Jméno</label>
                  <Input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-foreground mb-1.5">Příjmení</label>
                  <Input value={lastName} onChange={(e) => setLastName(e.target.value)} />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">E-mail</label>
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </div>

              <Button type="submit" isLoading={profileSaving}>
                Uložit změny
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Change password */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Změna hesla</CardTitle>
            <CardDescription>Změna hesla automaticky invaliduje stávající tokeny na ostatních zařízeních.</CardDescription>
          </CardHeader>
          <CardContent>
            {pwSuccess && (
              <div className="mb-4 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>{pwSuccess}</span>
              </div>
            )}
            {pwError && (
              <div className="mb-4 flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{pwError}</span>
              </div>
            )}

            <form onSubmit={handlePasswordSubmit} className="space-y-4 max-w-md">
              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Stávající heslo</label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Nové heslo (min. 8 znaků)</label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-foreground mb-1.5">Potvrzení nového hesla</label>
                <Input
                  type="password"
                  placeholder="••••••••"
                  value={newPassword2}
                  onChange={(e) => setNewPassword2(e.target.value)}
                  required
                />
              </div>

              <Button type="submit" isLoading={pwSaving}>
                Změnit heslo
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
