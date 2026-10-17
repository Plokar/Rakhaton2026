'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { RefreshCw, Save } from 'lucide-react';
import { Page, PageHeader } from '@/components/layout/Page';
import { PageCrumbs } from '@/components/layout/TopBar';
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
import { useQueries } from '@tanstack/react-query';
import { Citations } from '@/components/mdt/citations';
import { ApiError } from '@/lib/api';
import { queryKeys } from '@/lib/queries';
import { useApiData } from '@/lib/use-api-data';
import type { BriefConfig, CaseTemplate, EvidenceId, MdtSessionDetail } from '@/types/mdt';

// Klíč „sessionId|verze“: po uložení se board i konfigurace načtou znovu.
const fetchSetup = async (key: string) => {
  const [session, configs] = await Promise.all([mdtApi.getSession(key.split('|')[0]), mdtApi.getConfigs()]);
  return { session, configs };
};

/** Konfigurátor podkladu boardu (FR-R1, ARCH §7.1): nastavuje předseda, ostatní vidí nastavení. */
export default function SetupPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = React.use(params);
  return (
    <Page className="max-w-3xl">
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
    <>
      {session && (
        <PageCrumbs items={[{ label: session.title, href: `/dashboard/mdt/${encodeURIComponent(sessionId)}` }, { label: 'Nastavení podkladu' }]} />
      )}
      <PageHeader
        title="Nastavení podkladu"
        meta={session ? `${session.title}, ${formatDate(session.date)}` : 'Načítám zasedání…'}
      />
      <p className="text-sm text-muted-foreground">
        Určuje, jak AI sestaví podklad pro všechny pacienty tohoto boardu: které části obsahuje a v jakém pořadí, jak
        podrobně, kdo sedí u stolu (podle odborností se zvýrazní, co koho zajímá) a jestli skrýt neověřená tvrzení.
        Uloží se pro board a použije se při dalším generování podkladů.
      </p>
      {!editable && (
        <p role="status" className="rounded-lg bg-muted px-3 py-2 text-sm">
          Jen pro čtení: nastavení boardu mění předseda komise. Bloky si můžete sbalit u sebe v podkladu.
        </p>
      )}

      {loading && <Skeleton className="h-96 w-full" />}
      {error && <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>}
      {message && (
        <p
          role={message.kind === 'error' ? 'alert' : 'status'}
          className={
            message.kind === 'error'
              ? 'rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive'
              : 'rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground'
          }
        >
          {message.text}
        </p>
      )}

      {session && (
        <CitationProvider order={[]} activeId={openId} onOpen={setOpenId}>
          <RecommendedTemplates session={session} editable={editable} onUse={(t) => setDraft({ ...t.config, id: t.config_id ?? undefined, is_preset: true })} />
        </CitationProvider>
      )}
      {!loading && !error && session && !current && (
        <p className="text-sm text-muted-foreground">
          Pro board zatím není žádné nastavení podkladu.{editable ? ' Vyjděte z doporučené šablony výše.' : ''}
        </p>
      )}

      {current && session && (
        <CitationProvider order={[]} activeId={openId} onOpen={setOpenId}>
          <section className="flex flex-col gap-5 rounded-xl border border-border bg-card p-5">
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5 text-[13px] font-medium">
                <span className="block">Preset</span>
                <select
                  className="h-9 w-full rounded-lg border border-input bg-card px-2 text-sm font-normal disabled:opacity-70"
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
              <label className="flex flex-col gap-1.5 text-[13px] font-medium">
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
                  <Save aria-hidden /> Uložit pro board
                </Button>
                <Button onClick={regenerate} isLoading={busy} className="gap-1.5">
                  <RefreshCw aria-hidden /> Uložit a přegenerovat podklady ({session.cases.length})
                </Button>
              </div>
            )}
          </section>
          <SourceDrawer evidenceId={openId} loadSource={apiDataSource.loadSource} onClose={close} />
        </CitationProvider>
      )}
    </>
  );
}

/**
 * Doporučená šablona podle diagnózy pacientů na boardu (T-318, báze `data/onko`): „Použít“ ji vezme
 * jako výchozí bod, uloží se jako nastavení boardu (preset sám zůstává beze změny).
 */
function RecommendedTemplates({
  session,
  editable,
  onUse,
}: {
  session: MdtSessionDetail;
  editable: boolean;
  onUse: (template: CaseTemplate) => void;
}) {
  const cases = session.cases.filter((c): c is typeof c & { id: number } => c.id != null);
  const results = useQueries({
    queries: cases.map((c) => ({
      queryKey: queryKeys.template(c.id),
      queryFn: () =>
        mdtApi.getTemplate(c.id).catch((err: unknown) => {
          if (err instanceof ApiError && err.status === 404) return null;
          throw err;
        }),
      staleTime: 5 * 60_000,
    })),
  });
  const byTemplate = new Map<string, { template: CaseTemplate; patients: string[] }>();
  results.forEach((r, i) => {
    if (!r.data) return;
    const entry = byTemplate.get(r.data.template_id) ?? { template: r.data, patients: [] };
    entry.patients.push(cases[i].patient_id);
    byTemplate.set(r.data.template_id, entry);
  });
  if (!byTemplate.size) return null;
  return (
    <section aria-labelledby="doporucene-sablony" className="flex flex-col gap-2">
      <h2 id="doporucene-sablony" className="text-base font-semibold">Doporučená šablona podle diagnózy</h2>
      <ul className="divide-y divide-border rounded-xl border border-border bg-card">
        {[...byTemplate.values()].map(({ template, patients }) => (
          <li key={template.template_id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
            <div className="min-w-0 flex-1 basis-64">
              <p className="text-sm font-medium">
                {template.name}
                <Citations ids={template.sources} />
              </p>
              <p className="text-[13px] text-muted-foreground">
                <span translate="no">{patients.join(', ')}</span> · u stolu: {template.specialties}
              </p>
            </div>
            {editable && (
              <Button variant="outline" size="sm" onClick={() => onUse(template)}>
                Použít
              </Button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
