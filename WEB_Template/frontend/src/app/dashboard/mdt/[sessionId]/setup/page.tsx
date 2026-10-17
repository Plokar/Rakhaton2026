'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw, Save } from 'lucide-react';
import { Page } from '@/components/layout/Page';
import { CitationProvider } from '@/components/mdt/citations';
import { apiDataSource } from '@/components/mdt/data-source';
import { formatDate } from '@/components/mdt/format';
import { can, useMe } from '@/components/mdt/me';
import { requiredRoles, SectionConfigurator } from '@/components/mdt/SectionConfigurator';
import { SourceDrawer } from '@/components/mdt/SourceDrawer';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { mdtApi } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import type { BriefConfig, EvidenceId } from '@/types/mdt';

// Klíč „sessionId|verze“: po uložení se board i konfigurace načtou znovu.
const fetchSetup = async (key: string) => {
  const [session, configs] = await Promise.all([mdtApi.getSession(key.split('|')[0]), mdtApi.getConfigs()]);
  return { session, configs };
};

/** Konfigurátor podkladu boardu (FR-R1, ARCH §7.1): nastavuje předseda, ostatní vidí nastavení. */
export default function SetupPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = React.use(params);
  return (
    <Page>
      <SetupContent sessionId={sessionId} />
    </Page>
  );
}

function SetupContent({ sessionId }: { sessionId: string }) {
  const me = useMe();
  const editable = can.manageBoards(me);
  const [version, setVersion] = React.useState(0);
  const { data, error, loading } = useApiData(fetchSetup, `${sessionId}|${version}`);
  const [draft, setDraft] = React.useState<BriefConfig | null>(null);
  const [busy, setBusy] = React.useState(false);
  const [message, setMessage] = React.useState<{ kind: 'error' | 'info'; text: string } | null>(null);
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const close = React.useCallback(() => setOpenId(null), []);

  const session = data?.session;
  const configs = data?.configs ?? [];
  const boardConfig = configs.find((c) => Number(c.id) === session?.config_id);
  const current = draft ?? boardConfig ?? configs.find((c) => c.is_preset) ?? null;
  const requirements = React.useMemo(() => requiredRoles(session?.cases ?? []), [session]);
  const defaultName = session ? `${session.title} – ${formatDate(session.date)}` : '';

  const save = async (): Promise<BriefConfig | null> => {
    if (!current || !session) return null;
    setBusy(true);
    setMessage(null);
    try {
      // Kopie presetu se uloží jako nastavení boardu (vlastní název), preset sám zůstává beze změny.
      const presetNames = new Set(configs.filter((c) => c.is_preset).map((c) => c.name));
      const name = !current.name.trim() || presetNames.has(current.name.trim()) ? defaultName : current.name.trim();
      const saved =
        current.id && !current.is_preset && Number(current.id) === session.config_id
          ? await mdtApi.updateConfig(current.id, { ...current, name })
          : await mdtApi.createConfig({ ...current, id: undefined, is_preset: false, name });
      if (Number(saved.id) !== session.config_id) await mdtApi.updateSession(session.id, { config_id: Number(saved.id) });
      setDraft(null);
      setVersion((v) => v + 1);
      setMessage({ kind: 'info', text: 'Nastavení boardu uloženo. Nové podklady se vygenerují podle něj.' });
      return saved;
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Uložení se nepodařilo.' });
      return null;
    } finally {
      setBusy(false);
    }
  };

  const regenerate = async () => {
    const saved = draft ? await save() : current;
    if (!saved?.id || !session) return;
    setBusy(true);
    try {
      const cases = session.cases.filter((c) => c.id !== undefined);
      await Promise.all(cases.map((c) => mdtApi.generateBrief(String(c.id), { config_id: saved.id })));
      setMessage({ kind: 'info', text: `Spuštěno generování ${cases.length} podkladů podle nastavení „${saved.name}“.` });
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Generování se nepodařilo spustit.' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Link
        href={`/dashboard/mdt/${encodeURIComponent(sessionId)}`}
        className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" /> Agenda
      </Link>
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Nastavení podkladu</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {session ? `${session.title} · ${formatDate(session.date)}` : ''}
          {editable ? '' : ' · nastavuje předseda komise, bloky si můžete sbalit u sebe v podkladu'}
        </p>
      </div>

      {loading && <Skeleton className="h-96 w-full" />}
      {error && (
        <p className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      )}
      {message && (
        <p
          className={
            message.kind === 'error'
              ? 'rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive'
              : 'rounded-lg border border-border bg-muted/50 px-3 py-2 text-sm text-muted-foreground'
          }
        >
          {message.text}
        </p>
      )}

      {current && session && (
        <CitationProvider order={[]} activeId={openId} onOpen={setOpenId}>
          <section className="space-y-5 rounded-xl border border-border bg-card p-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 text-xs font-semibold text-foreground">
                <span className="block">Preset</span>
                <select
                  className="h-9 w-full rounded-lg border border-input bg-background px-2 text-sm font-normal disabled:opacity-70"
                  value={current.id ?? ''}
                  disabled={!editable}
                  onChange={(e) => {
                    const picked = configs.find((c) => c.id === e.target.value);
                    if (picked) setDraft({ ...picked });
                  }}
                >
                  {configs.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                      {c.is_preset ? ' (preset)' : Number(c.id) === session.config_id ? ' (board)' : ''}
                    </option>
                  ))}
                </select>
              </label>
              <label className="space-y-1 text-xs font-semibold text-foreground">
                <span className="block">Název nastavení boardu</span>
                <Input
                  value={current.name}
                  placeholder={defaultName}
                  disabled={!editable}
                  onChange={(e) => setDraft({ ...current, name: e.target.value })}
                />
              </label>
            </div>
            <SectionConfigurator
              config={current}
              onChange={setDraft}
              readOnly={!editable}
              requirements={requirements}
            />
            {editable && (
              <div className="flex flex-wrap justify-end gap-2 border-t border-border pt-4">
                <Button variant="outline" onClick={save} isLoading={busy} disabled={!draft} className="gap-1.5">
                  <Save className="h-4 w-4" /> Uložit pro board
                </Button>
                <Button onClick={regenerate} isLoading={busy} className="gap-1.5">
                  <RefreshCw className="h-4 w-4" /> Uložit a přegenerovat podklady ({session.cases.length})
                </Button>
              </div>
            )}
          </section>
          <SourceDrawer evidenceId={openId} loadSource={apiDataSource.loadSource} onClose={close} />
        </CitationProvider>
      )}
    </div>
  );
}
