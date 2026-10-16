'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  ClipboardList,
  FileText,
  Plus,
  ShieldCheck,
  Stethoscope,
  UsersRound,
} from 'lucide-react';
import { BoardDialog } from '@/components/mdt/BoardDialog';
import { CitationProvider, Citations, collectCitations } from '@/components/mdt/citations';
import { CompatibilityLight } from '@/components/mdt/CompatibilityLight';
import { SourceDrawer } from '@/components/mdt/SourceDrawer';
import { useMe, can } from '@/components/mdt/me';
import { mdtApi, type SessionInput, type StoredBrief } from '@/lib/mdt-api';
import { useApiData } from '@/lib/use-api-data';
import type { IntakeField, IntakePrefill, IntakeWarning, MdtCase, MdtSessionDetail } from '@/types/mdt';
import { cn } from '@/lib/utils';
import { DashboardLayout } from '@/components/layout/DashboardLayout';

const fetchBrief = async (id: string): Promise<StoredBrief | null> => (id ? mdtApi.getBrief(id) : null);
const fetchIntake = async (id: string): Promise<IntakePrefill | null> => (id ? mdtApi.getIntake(id) : null);
const fetchSession = async (id: string): Promise<MdtSessionDetail | null> => (id ? mdtApi.getSession(id) : null);
const fetchSessions = () => mdtApi.getSessions();

const formatMeeting = (iso: string) =>
  new Intl.DateTimeFormat('cs-CZ', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Prague',
  }).format(new Date(iso));

export function AdminBoardWorkspace() {
  return <DashboardLayout><AdminBoardContent /></DashboardLayout>;
}

function AdminBoardContent() {
  const me = useMe();
  const [refresh, setRefresh] = React.useState(0);
  const [openBoard, setOpenBoard] = React.useState<number | null | undefined>(undefined);
  const [selectedCase, setSelectedCase] = React.useState<MdtCase | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [inviteOpen, setInviteOpen] = React.useState(false);
  const [sourceId, setSourceId] = React.useState<string | null>(null);
  const sessions = useApiData(fetchSessions, String(refresh));
  const boards = sessions.data ?? [];
  const orderedBoards = [...boards].sort((a, b) => a.date.localeCompare(b.date));
  const activeBoardId = openBoard === undefined ? orderedBoards[0]?.id ?? null : openBoard;
  const agenda = useApiData(fetchSession, activeBoardId ? String(activeBoardId) : '');
  const currentCase = agenda.data?.cases.find((item) => item.id === selectedCase?.id)
    ?? agenda.data?.cases[0]
    ?? null;
  const caseId = currentCase?.id ? String(currentCase.id) : '';
  const brief = useApiData(fetchBrief, caseId);
  const intake = useApiData(fetchIntake, currentCase?.patient_id ?? '');
  const loadedBrief = brief.data ?? null;
  const loadedIntake = intake.data ?? null;
  const citationOrder = React.useMemo(() => collectCitations([loadedBrief, loadedIntake]), [loadedBrief, loadedIntake]);

  const createBoard = async (input: SessionInput) => {
    const created = await mdtApi.createSession(input);
    setRefresh((value) => value + 1);
    setOpenBoard(created.id);
    setSelectedCase(null);
  };

  const selectBoard = (boardId: number) => {
    setOpenBoard((value) => (value === boardId ? null : boardId));
    setSelectedCase(null);
  };

  return (
    <CitationProvider order={citationOrder} activeId={sourceId} onOpen={setSourceId}>
      <div className="-m-4 flex min-h-[calc(100vh-4rem)] flex-col overflow-hidden bg-background sm:-m-6 lg:-m-8 lg:flex-row">
        <section className="flex min-h-[36rem] w-full flex-col border-b border-border bg-card lg:min-h-0 lg:w-[min(100%,390px)] lg:shrink-0 lg:border-b-0 lg:border-r" aria-label="Přehled boardů MDT">
          <header className="flex items-center justify-between border-b border-border px-4 py-4">
            <Link href="/dashboard" className="flex items-center gap-2.5" aria-label="MedTeam – přehled">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
                <Activity className="h-5 w-5" aria-hidden />
              </span>
              <span>
                <span className="block text-base font-black tracking-tight text-foreground">MedTeam</span>
                <span className="block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">MDT workspace</span>
              </span>
            </Link>
            {can.manageBoards(me) && (
              <button
                type="button"
                onClick={() => setCreating(true)}
                className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground shadow-sm transition hover:bg-primary/90"
              >
                <Plus className="h-4 w-4" aria-hidden /> Board
              </button>
            )}
          </header>

          <div className="border-b border-border px-4 py-3">
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-muted-foreground">Zasedání komise</p>
            <p className="mt-1 text-xs text-muted-foreground">Rozbalte board a zvolte případ pro klinický přehled.</p>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            {sessions.loading && <div className="space-y-2" aria-busy="true"><div className="h-24 animate-pulse rounded-xl bg-muted" /><div className="h-24 animate-pulse rounded-xl bg-muted" /></div>}
            {sessions.error && <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-xs text-destructive">Boardy se nepodařilo načíst: {sessions.error}</p>}
            {sessions.data?.length === 0 && <div className="rounded-xl border border-dashed border-border p-5 text-center"><CalendarDays className="mx-auto h-6 w-6 text-muted-foreground" /><p className="mt-2 text-sm font-bold">Zatím žádné boardy</p><p className="mt-1 text-xs text-muted-foreground">Založte první zasedání MDT.</p></div>}
            <ul className="space-y-2">
              {orderedBoards.map((board) => {
                const expanded = board.id === activeBoardId;
                return (
                  <li key={board.id} className={cn('overflow-hidden rounded-xl border transition', expanded ? 'border-primary/45 bg-primary/[0.025] shadow-sm' : 'border-border bg-background hover:border-primary/30')}>
                    <button type="button" onClick={() => selectBoard(board.id)} aria-expanded={expanded} className="w-full p-3.5 text-left">
                      <div className="flex items-start justify-between gap-2">
                        <span className="flex min-w-0 items-start gap-2.5">
                          <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary"><CalendarDays className="h-4 w-4" aria-hidden /></span>
                          <span className="min-w-0">
                            <span className="block truncate text-sm font-extrabold text-foreground">{board.title}</span>
                            <span className="mt-1 inline-flex items-center gap-1 text-[11px] font-semibold text-muted-foreground"><UsersRound className="h-3 w-3" aria-hidden />{board.patients.length} {board.patients.length === 1 ? 'případ' : board.patients.length >= 2 && board.patients.length <= 4 ? 'případy' : 'případů'}</span>
                          </span>
                        </span>
                        <span className="flex shrink-0 flex-col items-end gap-1 text-right">
                          <span className="whitespace-nowrap text-[11px] font-bold text-foreground">{formatMeeting(board.date)}</span>
                          <span className="text-[10px] text-muted-foreground">{board.status === 'in_progress' ? 'Probíhá' : board.status === 'closed' ? 'Uzavřeno' : 'Plánováno'}</span>
                        </span>
                      </div>
                      <span className="mt-3 flex items-center justify-between border-t border-border/70 pt-2.5 text-[11px] text-muted-foreground">
                        <span>{board.chair ? `Předseda · ${board.chair.name}` : 'Předseda nepřiřazen'}</span>
                        {expanded ? <ChevronDown className="h-4 w-4" aria-hidden /> : <ChevronRight className="h-4 w-4" aria-hidden />}
                      </span>
                    </button>
                    {expanded && (
                      <div className="border-t border-border/70 px-2.5 py-2">
                        {agenda.loading && <p className="px-2 py-3 text-xs text-muted-foreground">Načítám případy…</p>}
                        {agenda.error && <p role="alert" className="px-2 py-3 text-xs text-destructive">Agendu se nepodařilo načíst.</p>}
                        {agenda.data?.cases.length === 0 && <p className="px-2 py-3 text-xs text-muted-foreground">Board zatím nemá zařazené případy.</p>}
                        <ul className="space-y-1">
                          {agenda.data?.cases.map((item) => (
                            <li key={item.id}>
                              <button type="button" onClick={() => setSelectedCase(item)} className={cn('w-full rounded-lg px-2.5 py-2 text-left transition', currentCase?.id === item.id ? 'bg-primary/10 text-primary ring-1 ring-inset ring-primary/25' : 'hover:bg-muted')}>
                                <span className="flex items-center justify-between gap-2">
                                  <span className="truncate text-xs font-bold">{item.patient?.display_name ?? item.patient_id}</span>
                                  <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{item.ecog !== null ? `PS ${item.ecog}` : 'PS —'} · {item.intent ?? '—'}</span>
                                </span>
                                <span className="mt-1 block truncate text-[10px] text-muted-foreground">{item.patient?.diagnosis?.text ?? 'Diagnóza čeká na podklad'}</span>
                              </button>
                            </li>
                          ))}
                        </ul>
                        <Link href={`/dashboard/mdt/${board.id}`} className="mt-2 flex items-center justify-center gap-1 rounded-lg border border-border px-2 py-2 text-[11px] font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"><ClipboardList className="h-3.5 w-3.5" aria-hidden />Otevřít agendu</Link>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>

          <footer className="border-t border-border bg-muted/20 px-3 py-3">
            <div className="flex items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.13em] text-muted-foreground"><UsersRound className="h-3 w-3" aria-hidden />Tým komise</p>
                <div className="mt-2 flex items-center gap-1.5">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full border border-primary/25 bg-primary/10 text-[10px] font-extrabold text-primary" title={me?.name ?? 'Přihlášený uživatel'}>{(me?.name ?? 'M')[0]}</span>
                  <span className="max-w-[10rem] truncate text-[11px] font-semibold text-foreground">{me?.name ?? 'Přihlášený člen'}</span>
                  <span className="rounded-full border border-border bg-background px-1.5 py-0.5 text-[9px] text-muted-foreground">{me?.specialty ? me.specialty.replaceAll('_', ' ') : 'MDT'}</span>
                </div>
              </div>
              <button type="button" onClick={() => setInviteOpen(true)} aria-label="Přidat uživatele do týmu" title="Přidat uživatele" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-dashed border-primary/50 bg-background text-primary transition hover:bg-primary/10"><Plus className="h-4 w-4" aria-hidden /></button>
            </div>
          </footer>
        </section>

        <main className="min-h-[34rem] min-w-0 flex-1 bg-muted/20 lg:min-h-0" aria-label="Klinický přehled zvoleného případu">
          <div className="ml-auto h-full w-full max-w-[360px] border-x border-border bg-background shadow-sm">
            <ClinicalPanel
              item={currentCase}
              brief={loadedBrief}
              intake={loadedIntake}
              loading={Boolean(currentCase && (brief.loading || intake.loading))}
            />
          </div>
        </main>
      </div>

      {creating && <BoardDialog open onClose={() => setCreating(false)} onSubmit={createBoard} />}
      {inviteOpen && <InviteDialog onClose={() => setInviteOpen(false)} />}
      <SourceDrawer evidenceId={sourceId} loadSource={mdtApi.getEvidence} onClose={() => setSourceId(null)} />
    </CitationProvider>
  );
}

function ClinicalPanel({
  item,
  brief,
  intake,
  loading,
}: {
  item: MdtCase | null;
  brief: StoredBrief | null;
  intake: IntakePrefill | null;
  loading: boolean;
}) {
  const anamnesis = brief?.sections.find((section) => section.id === 'anamnesis');
  const summary = brief?.sections.find((section) => section.id === 'summary');
  const keyClaims = summary?.items.filter((claim) => claim.kind === 'claim').slice(0, 4) ?? [];
  const treatments = brief?.decision_support?.treatment_options ?? [];
  const redFlags = brief?.red_flags ?? [];
  const patient = item?.patient;
  const intakeWarnings = intake?.warnings ?? [];

  if (!item) {
    return <div className="flex h-full min-h-[34rem] flex-col items-center justify-center px-6 text-center"><span className="flex h-12 w-12 items-center justify-center rounded-2xl border border-primary/20 bg-primary/10 text-primary"><Stethoscope className="h-6 w-6" /></span><h2 className="mt-4 text-base font-extrabold">Vyberte případ</h2><p className="mt-1 max-w-[16rem] text-xs leading-relaxed text-muted-foreground">Rozbalte board a zvolte pacienta. Klinický přehled se zobrazí v tomto úzkém panelu vedle snímku.</p></div>;
  }

  return (
    <div className="flex h-full min-h-[34rem] flex-col">
      <header className="border-b border-border bg-card px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">Pacient · anonymizované ID</p>
            <h1 className="mt-0.5 truncate font-mono text-lg font-black tracking-tight text-foreground">{item.patient_id}</h1>
          </div>
          <div className="flex shrink-0 gap-1.5">
            <Metric label="PS / ECOG" value={item.ecog === null ? '—' : String(item.ecog)} />
            <Metric label="C / P" value={item.intent ?? '—'} />
          </div>
        </div>
        <p className="mt-2 text-xs font-semibold leading-snug text-foreground">{patient?.diagnosis?.text ?? 'Diagnóza není v dostupném podkladu.'}</p>
        {patient?.diagnosis && <p className="mt-1 font-mono text-[10px] font-bold text-primary">MKN-10 {patient.diagnosis.icd10}</p>}
      </header>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {loading && <div className="space-y-2" aria-busy="true"><div className="h-20 animate-pulse rounded-xl bg-muted" /><div className="h-28 animate-pulse rounded-xl bg-muted" /></div>}
        {!brief && !loading && <p className="rounded-lg border border-dashed border-border p-3 text-xs leading-relaxed text-muted-foreground">Podklad ještě nebyl vytvořen. Zobrazujeme předvyplněná pole z dokumentace; žádné chybějící hodnoty se nedoplňují odhadem.</p>}

        <PanelCard title="Anamnéza" icon={<FileText className="h-3.5 w-3.5" />}>
          {anamnesis?.items.length ? (
            <ul className="space-y-2">
              {anamnesis.items.map((claim, index) => (
                <li key={`${claim.id}-${index}`} className="flex items-start gap-2 text-[11px] leading-relaxed text-foreground">
                  <ClaimDot kind={claim.kind} verified={claim.verification === 'verified'} />
                  <span className="min-w-0">{claim.text}<Citations ids={claim.citations} /></span>
                </li>
              ))}
            </ul>
          ) : <p className="text-[11px] leading-relaxed text-muted-foreground">{brief ? 'Anamnéza v podkladu chybí.' : 'Anamnéza se zobrazí po vytvoření podkladu.'}</p>}
        </PanelCard>

        <PanelCard title="Klíčové údaje podle diagnózy" icon={<Activity className="h-3.5 w-3.5" />}>
          {intake?.fields.length ? <>
            <ul className="space-y-1.5">
              {intake.fields.map((field) => <IntakeRow key={field.id} field={field} warnings={intakeWarnings} />)}
            </ul>
            <div className="mt-2 border-t border-border pt-2 text-[9px] leading-relaxed text-muted-foreground">Stav pole popisuje úplnost záznamu. Klinickou normalitu označuje jen výslovné varování s citací pravidla.</div>
          </> : <p className="text-[11px] text-muted-foreground">Diagnostická pole nejsou dostupná.</p>}
        </PanelCard>

        {(intakeWarnings.length > 0 || redFlags.length > 0) && <PanelCard title="Varování z pravidel" icon={<AlertTriangle className="h-3.5 w-3.5 text-amber-600" />}>
          <ul className="space-y-2">
            {intakeWarnings.map((warning) => <WarningRow key={warning.id} warning={warning} />)}
            {redFlags.map((flag) => <BriefFlagRow key={flag.id} flag={flag} />)}
          </ul>
        </PanelCard>}

        <PanelCard title="Léčebné postupy" icon={<ShieldCheck className="h-3.5 w-3.5" />}>
          {treatments.length ? <>
            <ul className="space-y-2">
              {treatments.map((option) => <li key={option.id} className="rounded-lg border border-border bg-background p-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-[11px] font-bold leading-snug text-foreground">{option.title}</p>
                  <CompatibilityLight light={option.compatibility.overall} className="px-1.5 py-0.5 text-[9px]" />
                </div>
                <div className="mt-1 text-[10px] text-muted-foreground"><Citations ids={option.guideline_citations} /></div>
                {option.compatibility.rules.slice(0, 2).map((rule) => <p key={rule.rule_id} className="mt-1 text-[10px] leading-relaxed text-muted-foreground">{rule.text}<Citations ids={rule.citations} /></p>)}
              </li>)}
            </ul>
            <p className="mt-2 text-[9px] leading-relaxed text-muted-foreground">Barva znamená pouze soulad s pravidly a dostupnými údaji; nejde o doporučení léčby. Rozhoduje MDT.</p>
          </> : <p className="text-[11px] leading-relaxed text-muted-foreground">Možnosti léčby se zobrazí z podkladu včetně citací pravidel. Nevyhodnocený postup neoznačujeme barvou.</p>}
        </PanelCard>

        {keyClaims.length > 0 && <PanelCard title="Rychlé shrnutí" icon={<ClipboardList className="h-3.5 w-3.5" />}>
          <ul className="space-y-1.5">{keyClaims.map((claim) => <li key={claim.id} className="flex items-start gap-2 text-[11px] leading-relaxed"><ClaimDot kind={claim.kind} verified={claim.verification === 'verified'} /><span>{claim.text}<Citations ids={claim.citations} /></span></li>)}</ul>
        </PanelCard>}
      </div>

      <footer className="border-t-2 border-primary/25 bg-primary/[0.035] px-4 py-3">
        <p className="text-[9px] font-bold uppercase tracking-[0.15em] text-primary">Otázka pro MDT</p>
        <div className="mt-1 flex items-start justify-between gap-2">
          <p className="text-sm font-black leading-snug text-foreground">{item.question ?? patient?.mdt_question ?? 'Otázka pro komisi není v dostupném záznamu.'}</p>
          {patient?.diagnosis?.icd10 && <span className="shrink-0 rounded border border-primary/25 bg-background px-1.5 py-1 font-mono text-[9px] font-bold text-primary">MKN {patient.diagnosis.icd10}</span>}
        </div>
        {patient?.mdt_question_citation && <Citations ids={[patient.mdt_question_citation]} />}
      </footer>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return <span className="min-w-12 rounded-lg border border-border bg-muted/50 px-2 py-1 text-center"><span className="block text-[8px] font-bold uppercase tracking-wider text-muted-foreground">{label}</span><span className="mt-0.5 block font-mono text-base font-black leading-none text-foreground">{value}</span></span>;
}

function PanelCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return <section className="rounded-xl border border-border bg-card p-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)]"><h2 className="mb-2 flex items-center gap-1.5 text-[10px] font-extrabold uppercase tracking-[0.11em] text-muted-foreground">{icon}{title}</h2>{children}</section>;
}

function ClaimDot({ kind, verified }: { kind: string; verified: boolean }) {
  const style = kind === 'missing' ? 'bg-slate-400' : verified ? 'bg-emerald-500' : 'bg-amber-500';
  const label = kind === 'missing' ? 'Údaj chybí' : verified ? 'Tvrzení ověřeno citací' : 'Tvrzení neověřeno';
  return <span aria-label={label} title={label} className={cn('mt-1 h-2 w-2 shrink-0 rounded-full', style)} />;
}

function IntakeRow({ field, warnings }: { field: IntakeField; warnings: IntakeWarning[] }) {
  const warning = warnings.find((entry) => entry.citations.includes(field.citation ?? '') || entry.id.includes(field.id));
  const dotClass = warning ? (warning.severity === 'high' ? 'bg-red-600' : 'bg-amber-500') : field.status === 'present' ? 'bg-emerald-500' : field.status === 'skipped' ? 'bg-slate-400' : 'bg-amber-500';
  const stateLabel = warning ? warning.severity === 'high' ? 'Závažné varování' : 'Upozornění' : field.status === 'present' ? 'Údaj zaznamenán' : field.status === 'skipped' ? 'Přeskočeno' : 'Chybí nebo čeká';
  return <li className="flex items-start gap-2 text-[10px] leading-relaxed"><span title={stateLabel} aria-label={stateLabel} className={cn('mt-1 h-2 w-2 shrink-0 rounded-full', dotClass)} /><span className="min-w-0 flex-1"><span className="font-bold text-foreground">{field.label}: </span><span className="text-muted-foreground">{field.value ?? (field.status === 'skipped' ? 'přeskočeno lékařem' : field.status === 'pending' ? 'vyšetření probíhá' : 'chybí')}</span>{field.citation && <Citations ids={[field.citation]} />}{field.required_by && <Citations ids={[field.required_by]} />}</span></li>;
}

function WarningRow({ warning }: { warning: IntakeWarning }) {
  const color = warning.severity === 'high' ? 'border-l-red-600' : 'border-l-amber-500';
  return <li className={cn('border-l-2 pl-2 text-[10px] leading-relaxed', color)}><p className="font-bold text-foreground">{warning.title}</p><p className="text-muted-foreground">{warning.detail}<Citations ids={warning.citations} /></p></li>;
}

function BriefFlagRow({ flag }: { flag: NonNullable<StoredBrief['red_flags']>[number] }) {
  const color = flag.severity === 'high' ? 'border-l-red-600' : flag.severity === 'moderate' ? 'border-l-amber-500' : 'border-l-slate-400';
  return <li className={cn('border-l-2 pl-2 text-[10px] leading-relaxed', color)}><p className="font-bold text-foreground">{flag.title}</p><p className="text-muted-foreground">{flag.description}<Citations ids={flag.citations} />{flag.guideline && <Citations ids={[flag.guideline]} />}</p></li>;
}

function InviteDialog({ onClose }: { onClose: () => void }) {
  return <div role="dialog" aria-modal="true" aria-labelledby="invite-title" className="fixed inset-0 z-[60] flex items-center justify-center p-4">
    <button type="button" aria-label="Zavřít dialog" onClick={onClose} className="absolute inset-0 bg-black/50" />
    <section className="relative w-full max-w-sm rounded-2xl border border-border bg-card p-5 shadow-2xl">
      <button type="button" onClick={onClose} className="absolute right-4 top-4 rounded-md p-1 text-muted-foreground hover:bg-muted" aria-label="Zavřít"><Plus className="h-4 w-4 rotate-45" /></button>
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary"><UsersRound className="h-4 w-4" /></span>
      <h2 id="invite-title" className="mt-3 text-base font-extrabold">Přidat uživatele</h2>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Vytvořte nový účet přes registraci. Nový účet získá přístup člena komise; přidělení role předsedy nebo lékařské odbornosti vyžaduje oprávnění v uživatelské administraci.</p>
      <Link href="/register" onClick={onClose} className="mt-4 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-primary px-3 text-xs font-bold text-primary-foreground hover:bg-primary/90">Pokračovat k registraci<ChevronRight className="h-3.5 w-3.5" /></Link>
    </section>
  </div>;
}
