'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ApiError } from '@/lib/api';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { MdtRole, ProjectorLayout, RoleId, TemplateArea } from '@/types/mdt';
import { TemplateAreasEditor } from './FactLayoutEditor';
import { MDT_ROLE_LABEL } from './me';
import { ROLE_META } from './roles';

const SPECIALTIES = (Object.keys(ROLE_META) as RoleId[]).filter((r) => r !== 'patient');
const ROLES: MdtRole[] = ['mdt_doctor', 'mdt_viewer', 'mdt_admin'];

/** Chyby po polích z API → jedna věta. */
function fieldMessage(err: unknown): string {
  if (err instanceof ApiError && err.data && typeof err.data === 'object') {
    const parts = Object.values(err.data as Record<string, unknown>).flatMap((v) => (Array.isArray(v) ? v : [v])).filter((v): v is string => typeof v === 'string');
    if (parts.length) return parts.join(' ');
  }
  return apiErrorMessage(err, 'Lékaře se nepodařilo založit.');
}

/**
 * Předseda zakládá lékaře (T-338, docs/SABLONY_LEKARE.md R5): 1) profil (jméno, tituly, profese, role, přihlášení),
 * 2) šablona klíčových údajů předvyplněná podle profese. Lékař ji později upraví v Nastavení.
 */
export function NewDoctorDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const client = useQueryClient();
  const [step, setStep] = React.useState<1 | 2>(1);
  const [form, setForm] = React.useState({ username: '', email: '', password: '', first_name: '', last_name: '', title_before: '', title_after: '' });
  const [specialty, setSpecialty] = React.useState<RoleId | ''>('');
  const [role, setRole] = React.useState<MdtRole>('mdt_doctor');
  const [templates, setTemplates] = React.useState<Partial<Record<TemplateArea, ProjectorLayout>>>({});
  const [preset, setPreset] = React.useState<string | undefined>();
  const [error, setError] = React.useState('');
  const [saving, setSaving] = React.useState(false);
  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value });
  const onTemplates = React.useCallback((next: Partial<Record<TemplateArea, ProjectorLayout>>, presetId?: string) => {
    setTemplates(next);
    if (presetId) setPreset(presetId);
  }, []);

  const reset = () => {
    setStep(1);
    setForm({ username: '', email: '', password: '', first_name: '', last_name: '', title_before: '', title_after: '' });
    setSpecialty('');
    setRole('mdt_doctor');
    setTemplates({});
    setPreset(undefined);
    setError('');
  };
  const close = () => {
    reset();
    onClose();
  };

  const next = () => {
    setError('');
    if (!form.last_name.trim()) return setError('Vyplňte příjmení.');
    if (!specialty) return setError('Vyberte profesi (odbornost).');
    if (!form.username.trim()) return setError('Vyplňte uživatelské jméno.');
    if (form.password.length < 8) return setError('Dočasné heslo musí mít aspoň 8 znaků.');
    setStep(2);
  };

  const create = async (withTemplate: boolean) => {
    if (!specialty) return;
    setSaving(true);
    setError('');
    const chosen = Object.fromEntries(Object.entries(templates).filter(([, l]) => l && Object.keys(l).length));
    try {
      const doctor = await mdtApi.createUser({
        ...form,
        username: form.username.trim(),
        specialty,
        role,
        ...(withTemplate && Object.keys(chosen).length ? { templates: chosen, preset } : {}),
      });
      await client.invalidateQueries({ queryKey: queryKeys.users });
      toast.success(`Založen: ${doctor.name}`, { description: `${MDT_ROLE_LABEL[doctor.role]} · přihlášení ${doctor.username}` });
      close();
    } catch (err) {
      setError(fieldMessage(err));
      if (err instanceof ApiError && err.data && typeof err.data === 'object' && !('templates' in (err.data as object))) setStep(1);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !saving && close()}>
      <DialogContent className={cn(step === 2 ? 'sm:max-w-3xl' : 'sm:max-w-lg')}>
        <DialogHeader>
          <DialogTitle>Přidat lékaře · krok {step} ze 2</DialogTitle>
          <DialogDescription>
            {step === 1
              ? 'Jméno, tituly, profese a role v komisi. Přihlašovací údaje předáte lékaři, heslo si pak změní v Nastavení.'
              : 'Šablona údajů předvyplněná podle profese. Upravte, co má lékař u pacienta vidět; jde přeskočit.'}
          </DialogDescription>
        </DialogHeader>
        {error && <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
        {step === 1 ? (
          <div className="flex flex-col gap-3">
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
            <label className="flex flex-col gap-1 text-sm font-medium">
              Role v komisi
              <select className="h-9 rounded-lg border border-input bg-card px-2 text-sm" value={role} onChange={(e) => setRole(e.target.value as MdtRole)}>
                {ROLES.map((r) => <option key={r} value={r}>{MDT_ROLE_LABEL[r]}</option>)}
              </select>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="flex flex-col gap-1 text-sm font-medium">Uživatelské jméno<Input value={form.username} onChange={set('username')} autoCapitalize="none" spellCheck={false} autoComplete="off" /></label>
              <label className="flex flex-col gap-1 text-sm font-medium">E-mail<Input type="email" value={form.email} onChange={set('email')} autoComplete="off" /></label>
            </div>
            <label className="flex flex-col gap-1 text-sm font-medium">Dočasné heslo (aspoň 8 znaků)<Input type="text" value={form.password} onChange={set('password')} autoComplete="new-password" /></label>
          </div>
        ) : (
          <div className="max-h-[60vh] overflow-y-auto pr-1">
            <TemplateAreasEditor value={templates} onChange={onTemplates} specialty={specialty || null} initFromPresets />
          </div>
        )}
        <DialogFooter className="gap-2">
          {step === 1 ? (
            <>
              <Button variant="outline" onClick={close}>Zrušit</Button>
              <Button onClick={next}>Pokračovat na šablonu</Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setStep(1)} disabled={saving}>Zpět</Button>
              <Button variant="ghost" onClick={() => void create(false)} disabled={saving}>Založit bez šablony</Button>
              <Button onClick={() => void create(true)} isLoading={saving}>Založit lékaře</Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
