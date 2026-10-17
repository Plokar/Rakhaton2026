'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { CircleCheck, FileDown, FileJson, History, Save, ShieldCheck } from 'lucide-react';
import { Page, PageHeader } from '@/components/layout/Page';
import { PageCrumbs } from '@/components/layout/TopBar';
import { buttonVariants } from '@/components/shadcn/button';
import { DEMO_CASE } from '@/components/mdt/detail/CaseDetail';
import { CitationProvider, collectCitations } from '@/components/mdt/citations';
import { ConfirmDialog } from '@/components/mdt/ConfirmDialog';
import { fixtureDataSource, apiDataSource } from '@/components/mdt/data-source';
import { GpReportPanel, PatientSummaryPanel, ScribePanel } from '@/components/mdt/DecisionAi';
import { DecisionEditor, guidelineDeviation } from '@/components/mdt/DecisionEditor';
import { formatDate } from '@/components/mdt/format';
import { can, useMe } from '@/components/mdt/me';
import { ROLE_META } from '@/components/mdt/roles';
import { SourceDrawer } from '@/components/mdt/SourceDrawer';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError, apiUrl } from '@/lib/api';
import { briefP03, decisionP03 } from '@/lib/fixtures';
import { mdtApi } from '@/lib/mdt-api';
import { useCaseLocation } from '@/lib/queries';
import { useApiData } from '@/lib/use-api-data';
import type { Brief, Decision, EvidenceId, Me, ProcedureCompatibility } from '@/types/mdt';

const orNull = <T,>(p: Promise<T>) =>
  p.catch((err: unknown) => {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  });
const fetchDecision = (cid: string): Promise<Decision | null> =>
  cid === DEMO_CASE ? Promise.resolve(decisionP03) : orNull(mdtApi.getDecision(cid));
const fetchBrief = (cid: string): Promise<Brief | null> =>
  cid === DEMO_CASE ? Promise.resolve(briefP03) : orNull(mdtApi.getBrief(cid));
/** Postupy ze semaforu pro „zvažované možnosti“; bez nich editor ukáže jen uložený výběr. */
const fetchOptions = (cid: string): Promise<ProcedureCompatibility[]> =>
  cid === DEMO_CASE ? Promise.resolve([]) : mdtApi.getCompatibility(Number(cid)).catch(() => []);

const nowLabel = () => new Date().toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' });

/** Výchozí draft, když závěr ještě není: otázka z nominace, záměr, přítomní podle rolí podkladu
 * (předseda jako lékař v IRIS, u ostatních rolí se lékař vybere v popupu, T-328/T-329). */
function initialDraft(caseId: string, brief: Brief | null, me: Me | null, nominationQuestion?: string | null): Decision {
  const roles = (brief?.config.roles_present ?? []).filter((r) => r !== 'patient');
  return {
    case_id: caseId,
    status: 'draft',
    mdt_type: 'primarni',
    attendees: [
      ...(me ? [{ user_id: me.practitioner_id ?? String(me.user_id), name: me.name, role: 'chair' as const }] : []),
      ...roles.map((r) => ({ user_id: '', name: ROLE_META[r].label, role: r })),
    ],
    patient_present: false,
    sections: {
      question: { text: brief?.header.mdt_question.text || nominationQuestion || '', source: 'human' },
      assessment: { text: '', source: 'human', citations: [] },
      intent: brief?.header.intent?.code ?? 'odlozeno',
      recommendation: [],
      conclusion: { text: '', source: 'human' },
    },
    tasks: [],
    red_flags_acknowledged: [],
  };
}

/** Zápis závěru komise (FR-C1–C3): editor draftu, uložení a potvrzení předsedou → IRIS. */
export default function DecisionPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = React.use(params);
  return (
    <Page className="max-w-4xl">
      <DecisionContent caseId={caseId} />
    </Page>
  );
}

function DecisionContent({ caseId }: { caseId: string }) {
  const isDemo = caseId === DEMO_CASE;
  const me = useMe();
  const decisionData = useApiData(fetchDecision, caseId);
  const briefData = useApiData(fetchBrief, caseId);
  const optionsData = useApiData(fetchOptions, caseId);
  const [draft, setDraft] = React.useState<Decision | null>(null);
  const [savedAt, setSavedAt] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [message, setMessage] = React.useState<{ kind: 'error' | 'info'; text: string } | null>(null);
  const [confirming, setConfirming] = React.useState(false);
  const [revising, setRevising] = React.useState(false);
  const [reason, setReason] = React.useState('');
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const close = React.useCallback(() => setOpenId(null), []);
  const location = useCaseLocation(isDemo ? null : Number(caseId));

  const loading = decisionData.loading || briefData.loading;
  const brief = briefData.data ?? null;
  const current = draft ?? decisionData.data ?? (loading ? null : initialDraft(caseId, brief, me, location.item?.question));
  const confirmed = current?.status === 'confirmed';
  // T-326: upravuje zadávající lékař, přizvaný lékař nebo předseda (backend to ověří znovu)
  const mayEditCase = location.item ? can.editCase(me, location.item) : can.manageBoards(me);
  const canEdit = !confirmed && (isDemo || mayEditCase);
  const canConfirm = !isDemo && !confirmed && can.manageBoards(me);
  const dirty = draft !== null && savedAt === null;
  const order = React.useMemo(() => collectCitations([current ?? {}, brief?.red_flags ?? []]), [current, brief]);

  const edit = (next: Decision) => {
    setDraft(next);
    setSavedAt(null);
  };

  const save = async (): Promise<Decision | null> => {
    if (!current) return null;
    if (isDemo) {
      setSavedAt(nowLabel());
      setMessage({ kind: 'info', text: 'Ukázka bez backendu: změny zůstávají jen v prohlížeči.' });
      return current;
    }
    setSaving(true);
    setMessage(null);
    try {
      const saved = await mdtApi.saveDecision(caseId, current);
      setDraft(saved);
      setSavedAt(nowLabel());
      return saved;
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Uložení se nepodařilo.' });
      return null;
    } finally {
      setSaving(false);
    }
  };

  /** Draft od zapisovatele je už uložený na serveru, jen ho načíst. */
  const reloadDraft = React.useCallback(() => {
    mdtApi
      .getDecision(caseId)
      .then((fresh) => {
        setDraft(fresh);
        setSavedAt(nowLabel());
        setMessage({ kind: 'info', text: 'Draft připravil AI zapisovatel z přepisu diskuse. Zkontrolujte ho a upravte.' });
      })
      .catch((err: unknown) => setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Draft se nepodařilo načíst.' }));
  }, [caseId]);

  /** Nová verze potvrzeného závěru (T-332): potvrzená verze přejde do auditní stopy s důvodem změny. */
  const revise = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const next = await mdtApi.reviseDecision(caseId, reason);
      setDraft(next);
      setSavedAt(nowLabel());
      setRevising(false);
      setReason('');
      setMessage({ kind: 'info', text: `Založena verze ${next.version}. Po úpravě ji předseda znovu potvrdí; předchozí verze zůstává v auditní stopě.` });
    } catch (err) {
      setMessage({ kind: 'error', text: err instanceof Error ? err.message : 'Novou verzi se nepodařilo založit.' });
    } finally {
      setSaving(false);
    }
  };

  const confirm = async () => {
    if (!current?.sections.question.text.trim() || !current.sections.conclusion.text.trim()) {
      throw new Error('Před potvrzením vyplňte projednanou otázku a závěr MDT.');
    }
    const deviation = guidelineDeviation(current.sections);
    if (deviation) throw new Error(deviation);
    if (!(await save())) throw new Error('Draft se nepodařilo uložit.');
    const result = await mdtApi.confirmDecision(caseId);
    setDraft(result);
    setConfirming(false);
  };

  const patientLabel = location.item?.patient_id ?? brief?.patient_id ?? caseId;
  return (
    <>
      <PageCrumbs
        items={[
          ...(location.session ? [{ label: location.session.title, href: `/dashboard/mdt/${location.session.id}` }] : []),
          { label: patientLabel, href: `/dashboard/cases/${encodeURIComponent(caseId)}` },
          { label: 'Závěr komise' },
        ]}
      />
      <PageHeader
        title="Závěr komise"
        meta={
          <>
            <span translate="no">{brief?.header.display_name ?? patientLabel}</span> · zápis ve struktuře záznamu MDT. Text od AI je
            odlišený, rozhoduje lékař.
          </>
        }
        actions={
          current &&
          !confirmed && (
            <>
              <span className="text-xs text-muted-foreground" aria-live="polite">
                {dirty ? 'Neuložené změny' : savedAt ? `Uloženo v ${savedAt}` : ''}
              </span>
              {canEdit && (
                <Button variant="outline" onClick={save} isLoading={saving}>
                  <Save aria-hidden /> Uložit draft
                </Button>
              )}
              {canConfirm && (
                <Button onClick={() => setConfirming(true)}>
                  <ShieldCheck aria-hidden /> Potvrdit závěr
                </Button>
              )}
            </>
          )
        }
      />

      {isDemo && (
        <p className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
          Ukázkový draft P03 z fixtures. Bez backendu se nic neukládá ani nezapisuje do IRIS.
        </p>
      )}
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
      {(decisionData.error || briefData.error) && (
        <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {decisionData.error ?? briefData.error}
        </p>
      )}

      {confirmed && current && (
        <div className="rounded-xl border border-border bg-card p-4 text-sm">
          <p className="flex flex-wrap items-center gap-2 font-semibold">
            <CircleCheck className="size-4 text-emerald-700 dark:text-emerald-400" aria-hidden />
            Potvrzeno: {current.confirmed_by?.name}, {formatDate(current.confirmed_at?.slice(0, 16))}
            <span className="rounded-md bg-muted px-1.5 py-0.5 text-xs font-medium">verze {current.version ?? 1} · zamčeno</span>
          </p>
          {current.fhir_ids && (
            <p className="mt-1 text-xs text-muted-foreground">
              Zapsáno do IRIS: <span translate="no" className="font-medium text-foreground">{current.fhir_ids.composition}</span>, CarePlan, CareTeam,{' '}
              {current.fhir_ids.tasks.length} úkolů, {current.fhir_ids.detected_issues.length} varovných signálů, Provenance.
            </p>
          )}
          {!isDemo && (
            <div className="mt-3 flex flex-wrap gap-2">
              {/* Export PDF obsahuje i shrnutí pro pacienta, když už vzniklo. */}
              {can.manageBoards(me) && !revising && (
                <Button variant="outline" size="lg" onClick={() => setRevising(true)}>
                  <History aria-hidden /> Upravit (nová verze)
                </Button>
              )}
              <a href={apiUrl(`/api/mdt/cases/${encodeURIComponent(caseId)}/export.pdf`)} className={buttonVariants({ size: 'lg' })}>
                <FileDown aria-hidden /> Export PDF
              </a>
              <a href={apiUrl(`/api/mdt/cases/${encodeURIComponent(caseId)}/export.fhir.json`)} className={buttonVariants({ variant: 'outline', size: 'lg' })}>
                <FileJson aria-hidden /> FHIR document Bundle
              </a>
            </div>
          )}
        </div>
      )}

      {confirmed && revising && (
        <form
          className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4"
          onSubmit={(e) => {
            e.preventDefault();
            void revise();
          }}
        >
          <label htmlFor="revise-reason" className="text-sm font-medium">Proč se potvrzený závěr mění</label>
          <Input
            id="revise-reason"
            value={reason}
            maxLength={500}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Např. doplněno stanovisko HPB chirurga"
          />
          <p className="text-xs text-muted-foreground">Potvrzená verze se nepřepíše: zůstane v auditní stopě i v historii záznamu v IRIS.</p>
          <div className="flex gap-2">
            <Button type="submit" isLoading={saving} disabled={!reason.trim()}>Založit novou verzi</Button>
            <Button type="button" variant="outline" onClick={() => setRevising(false)}>Zrušit</Button>
          </div>
        </form>
      )}
      {current && (current.history?.length ?? 0) > 0 && (
        <section aria-labelledby="history-title" className="rounded-xl border border-border bg-card p-4 text-sm">
          <h2 id="history-title" className="flex items-center gap-2 font-semibold">
            <History className="size-4" aria-hidden /> Auditní stopa verzí (teď verze {current.version ?? 1})
          </h2>
          <ol className="mt-2 flex flex-col gap-1.5">
            {current.history?.map((h) => (
              <li key={h.version} className="text-[13px]">
                <span className="font-medium">Verze {h.version}</span> potvrdil {h.confirmed_by?.name ?? '–'}{' '}
                {formatDate(h.confirmed_at?.slice(0, 16))}; změnu založil {h.revised_by.name} {formatDate(h.revised_at.slice(0, 16))}:{' '}
                <span className="text-muted-foreground">{h.reason}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      {!current && (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
      {current && canEdit && !isDemo && <ScribePanel caseId={caseId} onDraft={reloadDraft} />}
      {current && !confirmed && !canEdit && !isDemo && location.item && (
        <p role="status" className="rounded-lg bg-muted px-3 py-2 text-sm">
          Jen pro čtení: závěr upravuje a audio z diskuse importuje předseda, zadávající lékař
          {location.item.created_by ? ` (${location.item.created_by.name})` : ''} nebo přizvaný lékař. Přizvat vás může
          předseda nebo zadávající lékař v dialogu Spolupráce.
        </p>
      )}

      {current && (
        <CitationProvider order={order} activeId={openId} onOpen={setOpenId}>
          {confirmed && !isDemo && <PatientSummaryPanel caseId={caseId} canGenerate={mayEditCase} />}
          {confirmed && !isDemo && <GpReportPanel caseId={caseId} />}
          <section className="rounded-xl border border-border bg-card p-5">
            <DecisionEditor
              decision={current}
              onChange={edit}
              readOnly={!canEdit}
              redFlags={brief?.red_flags ?? []}
              options={optionsData.data ?? []}
            />
          </section>
          <SourceDrawer
            evidenceId={openId}
            loadSource={(isDemo ? fixtureDataSource : apiDataSource).loadSource}
            onClose={close}
          />
        </CitationProvider>
      )}

      {confirming && current && (
        <ConfirmDialog
          open
          decision={current}
          patientId={brief?.patient_id ?? 'Pxx'}
          confirmer={me?.name ?? 'předseda'}
          onClose={() => setConfirming(false)}
          onConfirm={confirm}
        />
      )}
    </>
  );
}
