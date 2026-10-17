'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ApiError } from '@/lib/api';
import { mdtApi, type NewPatient } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys } from '@/lib/queries';

const SELECT = 'h-9 w-full rounded-lg border border-input bg-card px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';

/**
 * Nový pacient (T-323): do IRIS jako pseudonym Pxx bez jména a RČ (D-018) s onkologickou diagnózou (MKN-10)
 * a nominací s otázkou pro MDT (OBC-1.1). Zprávy (text, PDF) se nahrají v dalším kroku přes „Vložit zprávu“.
 */
export function NewPatientForm({ sessionId, onCreated, onCancel }: { sessionId?: number; onCreated: (patientId: string) => void; onCancel: () => void }) {
  const client = useQueryClient();
  const [form, setForm] = React.useState({ sex: 'female', birth_year: '', icd10: '', diagnosis: '', stage: '', question: '' });
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [saving, setSaving] = React.useState(false);
  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    try {
      const input: NewPatient = {
        sex: form.sex as NewPatient['sex'], birth_year: Number(form.birth_year), icd10: form.icd10.trim(),
        diagnosis: form.diagnosis.trim(), question: form.question.trim(), ...(form.stage.trim() ? { stage: form.stage.trim() } : {}),
        ...(sessionId ? { session: sessionId } : {}),
      };
      const created = await mdtApi.createPatient(input);
      await client.invalidateQueries({ queryKey: queryKeys.patients });
      toast.success(`${created.patient_id} založen v IRIS`, { description: 'Pacient, diagnóza a nominace s otázkou pro MDT.' });
      onCreated(created.patient_id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 400 && err.data && typeof err.data === 'object') {
        setErrors(Object.fromEntries(Object.entries(err.data as Record<string, unknown>).map(([k, v]) => [k, Array.isArray(v) ? String(v[0]) : String(v)])));
      } else {
        toast.error(apiErrorMessage(err, 'Pacienta se nepodařilo založit.'));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <p className="text-[13px] text-muted-foreground">
        Pacient vznikne v IRIS pod pseudonymem (Pxx), bez jména a rodného čísla. Zprávy a výsledky nahrajete v dalším kroku.
      </p>
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">Pohlaví</span>
          <select className={SELECT} value={form.sex} onChange={set('sex')}>
            <option value="female">žena</option>
            <option value="male">muž</option>
            <option value="other">jiné</option>
          </select>
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">Rok narození</span>
          <Input inputMode="numeric" value={form.birth_year} onChange={set('birth_year')} placeholder="1958" error={errors.birth_year} required />
        </label>
      </div>
      <div className="grid grid-cols-[8rem_minmax(0,1fr)] gap-3">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">MKN-10</span>
          <Input value={form.icd10} onChange={set('icd10')} placeholder="C34.1" autoCapitalize="characters" error={errors.icd10} required />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">Diagnóza</span>
          <Input value={form.diagnosis} onChange={set('diagnosis')} placeholder="Zhoubný novotvar horního laloku plíce" error={errors.diagnosis} required />
        </label>
      </div>
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium">Stadium / TNM <span className="font-normal text-muted-foreground">(nepovinné)</span></span>
        <Input value={form.stage} onChange={set('stage')} placeholder="cT2a cN1 cM0, stadium IIB" />
      </label>
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium">Otázka pro MDT</span>
        <Textarea value={form.question} onChange={set('question')} rows={3} placeholder="Je pacientka kandidátem lobektomie, nebo chemoradioterapie?" required />
        {errors.question && <span className="text-xs font-medium text-destructive">{errors.question}</span>}
      </label>
      {errors.sex && <p role="alert" className="text-xs text-destructive">{errors.sex}</p>}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" isLoading={saving}>Založit pacienta</Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>Zpět</Button>
      </div>
    </form>
  );
}
