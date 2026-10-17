'use client';

import * as React from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { FileJson, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ApiError } from '@/lib/api';
import { mdtApi, type PatientDraft, type PatientDraftEdits } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys } from '@/lib/queries';

const SELECT = 'h-9 w-full rounded-lg border border-input bg-card px-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring';
const DRAFTS_KEY = ['patient-drafts'] as const;

const fieldErrors = (err: unknown): Record<string, string> | null =>
  err instanceof ApiError && err.status === 400 && err.data && typeof err.data === 'object'
    ? Object.fromEntries(Object.entries(err.data as Record<string, unknown>).map(([k, v]) => [k, Array.isArray(v) ? String(v[0]) : String(v)]))
    : null;

const isJson = (f: File) => /\.json$/i.test(f.name) || f.type === 'application/json' || f.type === 'application/fhir+json';

/**
 * Nový pacient z rodného čísla (T-323, `/api/mdt/patient-drafts/`): RČ + text nebo soubory (PDF, TXT) → návrh
 * s předvyplněnou nominací a citacemi → lékař doplní a potvrdí → jedna transakce do IRIS, případ na boardu.
 * Nebo FHIR JSON (bundle jednoho pacienta, T-335): RČ nepovinné, nominace ze strukturovaných dat souboru.
 * V aplikaci je pacient jen pod pseudonymem Pxx (D-018); RČ server nevrací.
 */
export function NewPatientForm({ sessionId, onCreated, onCancel }: { sessionId?: number; onCreated: (patientId: string) => void; onCancel: () => void }) {
  const [draft, setDraft] = React.useState<PatientDraft | null>(null);
  return draft ? (
    <DraftReview key={`${draft.id}:${draft.documents.length}`} draft={draft} onChange={setDraft} onConfirmed={onCreated} onDiscarded={() => setDraft(null)} onCancel={onCancel} />
  ) : (
    <DraftStart sessionId={sessionId} onDraft={setDraft} onExisting={onCreated} onCancel={onCancel} />
  );
}

/** Text a soubory podkladů; sdílí založení návrhu i „Přidat podklad“. */
function DocumentInputs({ text, onText, files, onFiles, error, allowJson = false }: { text: string; onText: (v: string) => void; files: File[]; onFiles: (f: File[]) => void; error?: string; allowJson?: boolean }) {
  const fileRef = React.useRef<HTMLInputElement>(null);
  const jsonRef = React.useRef<HTMLInputElement>(null);
  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium">Text zprávy nebo nominace</span>
        <Textarea value={text} onChange={(e) => onText(e.target.value)} rows={6} placeholder={'Dg.: C34.1 adenokarcinom horního laloku pravé plíce.\n\nOtázka pro MDT: lobektomie, nebo chemoradioterapie?'} />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={fileRef}
          type="file"
          multiple
          accept="application/pdf,.pdf,text/plain,.txt,.md"
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(e) => {
            onFiles([...files, ...Array.from(e.target.files ?? [])]);
            e.target.value = '';
          }}
        />
        <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
          <FileText aria-hidden /> Přidat soubory (PDF, TXT)
        </Button>
        {allowJson && (
          <>
            <input
              ref={jsonRef}
              type="file"
              accept="application/json,application/fhir+json,.json"
              className="sr-only"
              tabIndex={-1}
              aria-hidden
              onChange={(e) => {
                const picked = e.target.files?.[0];
                if (picked) onFiles([...files.filter((f) => !isJson(f)), picked]);
                e.target.value = '';
              }}
            />
            <Button type="button" variant="outline" size="sm" onClick={() => jsonRef.current?.click()}>
              <FileJson aria-hidden /> Nahrát FHIR JSON
            </Button>
          </>
        )}
        {files.map((f, i) => (
          <span key={`${f.name}-${i}`} className="text-xs text-muted-foreground">
            {f.name}{' '}
            <button type="button" className="underline" onClick={() => onFiles(files.filter((_, j) => j !== i))} aria-label={`Odebrat ${f.name}`}>
              odebrat
            </button>
          </span>
        ))}
      </div>
      {error && <p role="alert" className="text-xs font-medium text-destructive">{error}</p>}
    </div>
  );
}

function DraftStart({ sessionId, onDraft, onExisting, onCancel }: { sessionId?: number; onDraft: (d: PatientDraft) => void; onExisting: (pid: string) => void; onCancel: () => void }) {
  const [rc, setRc] = React.useState('');
  const [synthetic, setSynthetic] = React.useState(false);
  const [text, setText] = React.useState('');
  const [files, setFiles] = React.useState<File[]>([]);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [existing, setExisting] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const drafts = useQuery({ queryKey: DRAFTS_KEY, queryFn: () => mdtApi.getPatientDrafts() });
  const json = files.find(isJson);

  const open = async (id: number) => {
    try {
      onDraft(await mdtApi.getPatientDraft(id));
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Návrh se nepodařilo načíst.'));
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setErrors({});
    setExisting(null);
    const body = new FormData();
    body.append('rc', rc.trim());
    body.append('synthetic', String(synthetic));
    if (text.trim()) body.append('text', text.trim());
    for (const f of files) body.append('files', f);
    if (sessionId) body.append('session', String(sessionId));
    try {
      onDraft(await mdtApi.createPatientDraft(body));
    } catch (err) {
      const data = err instanceof ApiError && err.status === 409 ? (err.data as { patient_id?: string; draft_id?: number }) : null;
      if (data?.draft_id) {
        toast.info('Pro toto rodné číslo už rozpracovaný návrh je, otevírám ho.');
        await open(data.draft_id);
      } else if (data?.patient_id) {
        setExisting(data.patient_id);
      } else {
        const fields = fieldErrors(err);
        if (fields) setErrors(fields);
        else toast.error(apiErrorMessage(err, 'Návrh pacienta se nepodařilo vytvořit.'));
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <p className="text-[13px] text-muted-foreground">
        Z rodného čísla se odvodí pohlaví a věk, ze zpráv diagnóza, TNM, ECOG a otázka pro MDT (každý údaj s citací).
        Pacienta jde načíst i z FHIR JSON (bundle jednoho pacienta). V IRIS se nic nezapíše, dokud návrh nepotvrdíte.
        V aplikaci bude pacient jen pod pseudonymem Pxx.
      </p>
      {(drafts.data ?? []).length > 0 && (
        <div className="flex flex-col gap-1 text-sm">
          <span className="font-medium">Rozpracované návrhy</span>
          {drafts.data!.map((d) => (
            <button key={d.id} type="button" onClick={() => void open(d.id)} className="self-start text-left text-[13px] underline-offset-2 hover:underline">
              <span translate="no">{d.patient_id}</span> · podklady: {d.documents}
            </button>
          ))}
        </div>
      )}
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium">
          Rodné číslo{json && <span className="font-normal text-muted-foreground"> (nepovinné u FHIR JSON, ověří se proti pohlaví a roku narození)</span>}
        </span>
        <Input value={rc} onChange={(e) => setRc(e.target.value)} placeholder="585123/1234" inputMode="numeric" autoComplete="off" error={errors.rc} required={!json} />
      </label>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-0.5 size-4 accent-ai" checked={synthetic} onChange={(e) => setSynthetic(e.target.checked)} />
        <span>
          Testovací pacient (fiktivní data)
          <span className="block text-xs text-muted-foreground">Jen u fiktivních dat smí podklady číst AI (D-021). U skutečného pacienta předvyplní údaje jen pravidla.</span>
        </span>
      </label>
      <DocumentInputs text={text} onText={setText} files={files} onFiles={setFiles} error={errors.files ?? errors.text} allowJson />
      {json && (
        <p className="flex items-start gap-1.5 rounded-lg bg-muted px-3 py-2 text-[13px]">
          <FileJson className="mt-0.5 size-4 shrink-0" aria-hidden />
          <span>
            {json.name}: pacient se načte ze strukturovaných dat souboru (diagnózy, TNM, ECOG, nominace, lékaři). ID se
            přečíslují na volné Pxx, reference a RČ se zkontrolují.
          </span>
        </p>
      )}
      {existing && (
        <p role="alert" className="text-sm">
          Pacient s tímto rodným číslem už v IRIS je jako <span translate="no">{existing}</span>.{' '}
          <button type="button" className="font-medium underline" onClick={() => onExisting(existing)}>Zařadit jeho</button>
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" isLoading={saving} disabled={!rc.trim() && !json}>Vytvořit návrh</Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={saving}>Zpět</Button>
      </div>
    </form>
  );
}

function DraftReview({
  draft,
  onChange,
  onConfirmed,
  onDiscarded,
  onCancel,
}: {
  draft: PatientDraft;
  onChange: (d: PatientDraft) => void;
  onConfirmed: (pid: string) => void;
  onDiscarded: () => void;
  onCancel: () => void;
}) {
  const client = useQueryClient();
  const f = draft.fields;
  const dg = f?.diagnoses[0];
  const initial = { question: f?.question?.text ?? '', code: dg?.code ?? '', diagnosis: dg?.text ?? '', tnm: f?.tnm?.text ?? '', ecog: f?.ecog ? String(f.ecog.value) : '' };
  const [form, setForm] = React.useState(initial);
  const [text, setText] = React.useState('');
  const [files, setFiles] = React.useState<File[]>([]);
  const [errors, setErrors] = React.useState<Record<string, string>>({});
  const [busy, setBusy] = React.useState<'save' | 'docs' | 'delete' | null>(null);
  const set = (field: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }));

  /** Jen změněná pole: odeslané pole server bere jako upravené lékařem (bez citace podkladu). */
  const edits = (): PatientDraftEdits | null => {
    const out: PatientDraftEdits = {};
    if (form.question !== initial.question) out.question = form.question;
    if (form.tnm !== initial.tnm) out.tnm = form.tnm;
    if (form.ecog !== initial.ecog) out.ecog = form.ecog === '' ? null : Number(form.ecog);
    if (form.code !== initial.code || form.diagnosis !== initial.diagnosis) {
      const rest = (f?.diagnoses ?? []).slice(1).map((d) => ({ code: d.code, text: d.text }));
      out.diagnoses = form.code.trim() ? [{ code: form.code.trim(), text: form.diagnosis.trim() }, ...rest] : rest;
    }
    return Object.keys(out).length ? out : null;
  };

  const run = async (kind: 'save' | 'docs' | 'delete', action: () => Promise<void>) => {
    setBusy(kind);
    setErrors({});
    try {
      await action();
    } catch (err) {
      const fields = fieldErrors(err);
      if (fields && !('missing' in fields)) setErrors(fields);
      else toast.error(apiErrorMessage(err, 'Akce se nepovedla.'));
    } finally {
      setBusy(null);
    }
  };

  const saved = async () => {
    const changes = edits();
    return changes ? mdtApi.updatePatientDraft(draft.id, changes) : draft;
  };

  const confirm = () =>
    run('save', async () => {
      const current = await saved();
      if (current.missing_for_confirm?.length) {
        onChange(current);
        return;
      }
      const done = await mdtApi.confirmPatientDraft(draft.id);
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.patients }),
        client.invalidateQueries({ queryKey: queryKeys.sessions }),
        ...(draft.session ? [client.invalidateQueries({ queryKey: queryKeys.session(draft.session.id) })] : []),
        client.invalidateQueries({ queryKey: DRAFTS_KEY }),
      ]);
      toast.success(`${done.patient_id} zapsán do IRIS`, { description: `${done.fhir_written.length} záznamů jednou transakcí s Provenance.` });
      onConfirmed(done.patient_id);
    });

  const addDocuments = () =>
    run('docs', async () => {
      await saved();
      const body = new FormData();
      if (text.trim()) body.append('text', text.trim());
      for (const file of files) body.append('files', file);
      onChange(await mdtApi.addPatientDraftDocuments(draft.id, body));
    });

  const discard = () =>
    run('delete', async () => {
      await mdtApi.deletePatientDraft(draft.id);
      await client.invalidateQueries({ queryKey: DRAFTS_KEY });
      onDiscarded();
    });

  const p = draft.patient;
  const values = draft.values?.length ?? 0;
  const imported = draft.import ?? null;
  return (
    <div className="flex flex-col gap-4">
      <div>
        <p className="text-sm font-semibold">
          <span translate="no">{draft.patient_id}</span>
          {p && ` · ${p.sex === 'female' ? 'žena' : 'muž'} · ${p.age} let${p.rc_masked ? ` · RČ ${p.rc_masked}` : ' · bez RČ'}`}
        </p>
        <p className="text-[13px] text-muted-foreground">
          {draft.synthetic ? 'Testovací pacient (fiktivní data)' : 'Skutečný pacient'}
          {draft.session && ` · po zápisu na ${draft.session.title}`}
        </p>
      </div>
      {imported && (
        <div className="rounded-lg border border-border bg-card px-3 py-2 text-[13px]">
          <p className="flex items-center gap-1.5 font-medium">
            <FileJson className="size-4" aria-hidden /> {imported.file}: {imported.total} záznamů FHIR
            {imported.renamed_from && (
              <span className="font-normal text-muted-foreground">
                {' '}· přečíslováno <span translate="no">{imported.renamed_from}</span> → <span translate="no">{draft.patient_id}</span>
              </span>
            )}
          </p>
          <p className="mt-0.5 text-muted-foreground">
            {Object.entries(imported.counts).sort((a, b) => b[1] - a[1]).map(([type, n]) => `${type} ${n}`).join(' · ')}
          </p>
          {imported.practitioners.length > 0 && (
            <p className="mt-0.5 text-muted-foreground">
              Lékaři do IRIS: <span translate="no">{imported.practitioners.join(', ')}</span>
            </p>
          )}
        </div>
      )}
      <ul className="flex flex-col gap-1 text-[13px]">
        {draft.documents.map((d) => (
          <li key={d.id}>
            <span translate="no" className="font-medium">{d.id}</span> {d.title}
            {d.source && <span className="text-muted-foreground"> · {d.source}</span>}
          </li>
        ))}
      </ul>
      {(!imported || draft.documents.length > 0) && <p className="text-xs text-muted-foreground">
        {draft.ai?.used
          ? `AI vytěžila ${values} ${values === 1 ? 'hodnotu' : 'hodnot'} ověřených proti odstavci zprávy${draft.rejected?.length ? `, ${draft.rejected.length} neověřených odmítla` : ''}.`
          : draft.ai?.reason ?? 'Údaje předvyplnila pravidla z textu.'}
      </p>}
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium">Otázka pro MDT</span>
        <Textarea value={form.question} onChange={set('question')} rows={3} />
        {f?.question?.citation && form.question === initial.question && <span translate="no" className="text-xs text-muted-foreground">zdroj {f.question.citation}</span>}
      </label>
      {imported ? (
        <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
          <dt className="font-medium">Diagnózy</dt>
          <dd>
            {(f?.diagnoses ?? []).length === 0
              ? <span className="text-destructive">v souboru není onkologická diagnóza s kódem MKN-10</span>
              : f!.diagnoses.map((d) => (
                <span key={d.code} className="block">
                  {d.code} {d.text} {d.citation && <span translate="no" className="text-xs text-muted-foreground">({d.citation})</span>}
                </span>
              ))}
          </dd>
          <dt className="font-medium">TNM</dt>
          <dd>
            {f?.tnm ? <>{f.tnm.text} <span translate="no" className="text-xs text-muted-foreground">({f.tnm.citation})</span></> : <span className="text-muted-foreground">neuvedeno</span>}
          </dd>
          <dt className="font-medium">ECOG</dt>
          <dd>
            {f?.ecog ? <>{f.ecog.value} <span translate="no" className="text-xs text-muted-foreground">({f.ecog.citation})</span></> : <span className="text-muted-foreground">neuvedeno</span>}
          </dd>
          <dd className="col-span-2 text-xs text-muted-foreground">Údaje jsou ze souboru FHIR. Opravují se v souboru, tady jde upravit otázka pro MDT.</dd>
        </dl>
      ) : (
      <>
      <div className="grid grid-cols-[8rem_minmax(0,1fr)] gap-3">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">MKN-10</span>
          <Input value={form.code} onChange={set('code')} placeholder="C34.1" autoCapitalize="characters" error={errors.diagnoses} />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">Diagnóza</span>
          <Input value={form.diagnosis} onChange={set('diagnosis')} placeholder="Adenokarcinom horního laloku pravé plíce" />
        </label>
      </div>
      {(f?.diagnoses.length ?? 0) > 1 && (
        <p className="text-xs text-muted-foreground">Další diagnózy: {f!.diagnoses.slice(1).map((d) => `${d.code} ${d.text}`).join('; ')}</p>
      )}
      <div className="grid grid-cols-[minmax(0,1fr)_7rem] gap-3">
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">TNM <span className="font-normal text-muted-foreground">(nepovinné)</span></span>
          <Input value={form.tnm} onChange={set('tnm')} placeholder="cT2a cN1 cM0" />
        </label>
        <label className="flex flex-col gap-1.5 text-sm">
          <span className="font-medium">ECOG</span>
          <select className={SELECT} value={form.ecog} onChange={set('ecog')}>
            <option value="">neuvedeno</option>
            {[0, 1, 2, 3, 4].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>
      </>
      )}
      {draft.missing_for_confirm && draft.missing_for_confirm.length > 0 && (
        <p role="alert" className="text-sm text-destructive">K zápisu chybí: {draft.missing_for_confirm.join(', ')}.</p>
      )}
      <details className="rounded-lg border border-border p-3">
        <summary className="cursor-pointer text-sm font-medium">Přidat další podklad</summary>
        <div className="mt-3 flex flex-col gap-2">
          <DocumentInputs text={text} onText={setText} files={files} onFiles={setFiles} error={errors.files ?? errors.text} />
          <Button type="button" variant="outline" size="sm" className="self-start" onClick={() => void addDocuments()} isLoading={busy === 'docs'} disabled={busy !== null || (!text.trim() && files.length === 0)}>
            Přidat podklad
          </Button>
        </div>
      </details>
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => void confirm()} isLoading={busy === 'save'} disabled={busy !== null}>Zapsat do IRIS</Button>
        <Button variant="outline" onClick={onCancel} disabled={busy !== null}>Zpět (návrh zůstane)</Button>
        <Button variant="ghost" onClick={() => void discard()} isLoading={busy === 'delete'} disabled={busy !== null}>Zahodit návrh</Button>
      </div>
    </div>
  );
}
