'use client';

export const dynamic = 'force-dynamic';

import * as React from 'react';
import { CircleCheck, FileDown, FileJson, Save, ShieldCheck } from 'lucide-react';
import { Page, PageHeader } from '@/components/layout/Page';
import { PageCrumbs } from '@/components/layout/TopBar';
import { buttonVariants } from '@/components/shadcn/button';
import { DEMO_CASE } from '@/components/mdt/detail/CaseDetail';
import { CitationProvider, collectCitations } from '@/components/mdt/citations';
import { ConfirmDialog } from '@/components/mdt/ConfirmDialog';
import { fixtureDataSource, apiDataSource } from '@/components/mdt/data-source';
import { DecisionEditor } from '@/components/mdt/DecisionEditor';
import { formatDate } from '@/components/mdt/format';
import { can, useMe } from '@/components/mdt/me';
import { ROLE_META } from '@/components/mdt/roles';
import { SourceDrawer } from '@/components/mdt/SourceDrawer';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError, apiUrl } from '@/lib/api';
import { briefP03, decisionP03 } from '@/lib/fixtures';
import { mdtApi } from '@/lib/mdt-api';
import { useCaseLocation } from '@/lib/queries';
import { useApiData } from '@/lib/use-api-data';
import type { Brief, Decision, EvidenceId, Me } from '@/types/mdt';

const orNull = <T,>(p: Promise<T>) =>
  p.catch((err: unknown) => {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  });
const fetchDecision = (cid: string): Promise<Decision | null> =>
  cid === DEMO_CASE ? Promise.resolve(decisionP03) : orNull(mdtApi.getDecision(cid));
const fetchBrief = (cid: string): Promise<Brief | null> =>
  cid === DEMO_CASE ? Promise.resolve(briefP03) : orNull(mdtApi.getBrief(cid));

const nowLabel = () => new Date().toLocaleTimeString('cs-CZ', { hour: '2-digit', minute: '2-digit' });

/** Výchozí draft, když závěr ještě není: otázka z nominace, záměr, přítomní podle rolí podkladu. */
function initialDraft(caseId: string, brief: Brief | null, me: Me | null): Decision {
  const roles = (brief?.config.roles_present ?? []).filter((r) => r !== 'patient');
  return {
    case_id: caseId,
    status: 'draft',
    mdt_type: 'primarni',
    attendees: [
      ...(me ? [{ user_id: String(me.user_id), name: me.name, role: 'chair' as const }] : []),
      ...roles.map((r) => ({ user_id: '', name: ROLE_META[r].label, role: r })),
    ],
    patient_present: false,
    sections: {
      question: { text: brief?.header.mdt_question.text ?? '', source: 'human' },
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
  const [draft, setDraft] = React.useState<Decision | null>(null);
  const [savedAt, setSavedAt] = React.useState<string | null>(null);
  const [saving, setSaving] = React.useState(false);
  const [message, setMessage] = React.useState<{ kind: 'error' | 'info'; text: string } | null>(null);
  const [confirming, setConfirming] = React.useState(false);
  const [openId, setOpenId] = React.useState<EvidenceId | null>(null);
  const close = React.useCallback(() => setOpenId(null), []);
  const location = useCaseLocation(isDemo ? null : Number(caseId));

  const loading = decisionData.loading || briefData.loading;
  const brief = briefData.data ?? null;
  const current = draft ?? decisionData.data ?? (loading ? null : initialDraft(caseId, brief, me));
  const confirmed = current?.status === 'confirmed';
  const canEdit = !confirmed && (isDemo || can.generateBrief(me));
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

  const confirm = async () => {
    if (!current?.sections.question.text.trim() || !current.sections.conclusion.text.trim()) {
      throw new Error('Před potvrzením vyplňte projednanou otázku a závěr MDT.');
    }
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
          <p className="flex items-center gap-2 font-semibold">
            <CircleCheck className="size-4 text-emerald-700 dark:text-emerald-400" aria-hidden />
            Potvrzeno: {current.confirmed_by?.name}, {formatDate(current.confirmed_at?.slice(0, 16))}
          </p>
          {current.fhir_ids && (
            <p className="mt-1 text-xs text-muted-foreground">
              Zapsáno do IRIS: <span translate="no" className="font-medium text-foreground">{current.fhir_ids.composition}</span>, CarePlan, CareTeam,{' '}
              {current.fhir_ids.tasks.length} úkolů, {current.fhir_ids.detected_issues.length} varovných signálů, Provenance.
            </p>
          )}
          {!isDemo && (
            <div className="mt-3 flex flex-wrap gap-2">
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

      {!current && (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      )}
      {current && (
        <CitationProvider order={order} activeId={openId} onOpen={setOpenId}>
          <section className="rounded-xl border border-border bg-card p-5">
            <DecisionEditor decision={current} onChange={edit} readOnly={!canEdit} redFlags={brief?.red_flags ?? []} />
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
