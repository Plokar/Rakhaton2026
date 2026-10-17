'use client';

import * as React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ChevronLeft, ChevronRight, MonitorUp, MoreHorizontal, NotebookPen, PanelRightOpen, RefreshCw, TriangleAlert, UserRound } from 'lucide-react';
import { PageCrumbs } from '@/components/layout/TopBar';
import { Button, buttonVariants } from '@/components/shadcn/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/shadcn/dropdown-menu';
import { Skeleton } from '@/components/shadcn/skeleton';
import { ToggleGroup, ToggleGroupItem } from '@/components/shadcn/toggle-group';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/shadcn/tooltip';
import { briefP03, timelineP03 } from '@/lib/fixtures';
import { agendaOrder, apiErrorMessage, useBriefQuery, useCaseLocation, useForMeQuery, useTimelineQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { Brief, BriefSection, MdtCase, MdtSessionDetail, SectionId, TimelineEvent } from '@/types/mdt';
import { AiBlock } from '../AiBlock';
import { Citations } from '../citations';
import { ClaimItem, ClaimList, SectionClaims } from '../ClaimList';
import { apiDataSource, BriefDataProvider, fixtureDataSource } from '../data-source';
import { FeedbackNote, GenerateBrief, RegenerateDialog, useBriefJob } from '../GenerateBrief';
import { can, useMe } from '../me';
import { openProjectorWindow } from '../projector';
import { CaseQuickViewBody, fixtureQuickViewSources, quickHeader, useQuickViewSources, type QuickViewSources } from '../quick-view';
import { RedFlagList } from '../RedFlagList';
import { ROLE_META } from '../roles';
import { RoleSection } from '../RoleSection';
import { Timeline } from '../Timeline';
import { TreatmentOptions } from '../TreatmentOptions';
import { TrialScreening } from '../TrialScreening';
import { DetailSection, SectionNav, SectionsProvider, type SectionDef } from './DetailSection';
import { ForMePanel } from './ForMePanel';
import { MyTasks } from '../MyTasks';

/** Případ `demo` = podklad P03 z fixtures, bez backendu (ARCH §7.3). */
export const DEMO_CASE = 'demo';

const briefWindow = (caseId: string) => window.open(`/brief/${encodeURIComponent(caseId)}`, `mdt-brief-${caseId}`, 'popup,width=440,height=960');

/**
 * Detail pacienta (NAVRH_UI §8): první obrazovka odpoví za 30 s (rychlý přehled), vše ostatní je
 * o krok dál a sbalené. Přilepená hlavička, navigace po sekcích, šipky na další pacienty boardu.
 * Celý podklad zůstává dostupný, nic se neskrývá natrvalo (D-019).
 */
export function CaseDetail({ caseId }: { caseId: string }) {
  return caseId === DEMO_CASE ? <DemoCaseDetail /> : <ApiCaseDetail caseId={Number(caseId)} />;
}

function ApiCaseDetail({ caseId }: { caseId: number }) {
  const location = useCaseLocation(caseId);
  const brief = useBriefQuery(caseId);
  const patientId = location.item?.patient_id ?? brief.data?.patient_id ?? null;
  const sources = useQuickViewSources({ sessionId: location.session?.id ?? null, caseId, patientId });
  const timeline = useTimelineQuery(patientId);

  if (brief.isError) {
    return (
      <p role="alert" className="p-6 text-sm text-destructive">
        {apiErrorMessage(brief.error, 'Podklad se nepodařilo načíst.')}{' '}
        <Link href="/dashboard" className="font-medium underline underline-offset-4">Zpět na kalendář</Link>
      </p>
    );
  }
  if (brief.isLoading || (location.loading && !brief.data)) return <DetailSkeleton />;
  if (!patientId) {
    return (
      <p className="p-6 text-sm">
        Případ {caseId} nenacházím v žádném zasedání. <Link href="/dashboard" className="font-medium underline underline-offset-4">Zpět na kalendář</Link>
      </p>
    );
  }
  return (
    <BriefDataProvider value={apiDataSource}>
      <DetailLayout
        caseKey={String(caseId)}
        brief={brief.data ?? null}
        sources={sources}
        session={location.session}
        item={location.item}
        timeline={timeline.data}
      />
    </BriefDataProvider>
  );
}

function DemoCaseDetail() {
  const sources = React.useMemo(() => fixtureQuickViewSources(fixtureDataSource.loadSource), []);
  return (
    <BriefDataProvider value={fixtureDataSource}>
      <p className="border-b border-dashed border-border bg-muted/50 px-4 py-2 text-center text-xs text-muted-foreground">
        Ukázkový podklad pacienta P03 z fixtures (syntetická data, bez backendu).
      </p>
      <DetailLayout caseKey={DEMO_CASE} brief={briefP03} sources={sources} session={null} item={null} timeline={timelineP03} />
    </BriefDataProvider>
  );
}

const sectionsOf = (brief: Brief | null, id: BriefSection['id']) => brief?.sections.filter((s) => s.id === id) ?? [];

/** Kam patří sekce podkladu (`SectionId`) v detailu; otázka pro MDT je v rychlém přehledu. */
const DETAIL_SECTION: Partial<Record<SectionId, string>> = {
  summary: 'souhrn',
  timeline: 'souhrn',
  red_flags: 'varovani',
  anamnesis: 'anamneza',
  role_views: 'odbornosti',
  modalities: 'lecba',
  decision_support: 'lecba',
  trials: 'lecba',
  questions: 'otazky',
};
const DEFAULT_ORDER = ['varovani', 'souhrn', 'anamneza', 'odbornosti', 'lecba', 'pacient', 'otazky'];

/** Rychlý přehled zůstává první (ARCH §7.3), pak podle `sections` (předseda nebo odbornost), pak zbytek. */
function detailOrder(sections: SectionId[], forMe: boolean): string[] {
  const mapped = sections.map((id) => DETAIL_SECTION[id]).filter((id): id is string => Boolean(id));
  return [...new Set(['prehled', ...(forMe ? ['pro-me'] : []), ...mapped, ...DEFAULT_ORDER])];
}

type OrderMode = 'chair' | 'me';
const ORDER_KEY = 'mdt-poradi-podkladu';

function readOrderMode(): OrderMode | null {
  try {
    const v = localStorage.getItem(ORDER_KEY);
    return v === 'chair' || v === 'me' ? v : null;
  } catch {
    return null;
  }
}

function DetailLayout({
  caseKey,
  brief,
  sources,
  session,
  item,
  timeline,
}: {
  caseKey: string;
  brief: Brief | null;
  sources: QuickViewSources;
  session: MdtSessionDetail | null;
  item: MdtCase | null;
  timeline: TimelineEvent[] | undefined;
}) {
  const me = useMe();
  const isDemo = caseKey === DEMO_CASE;
  // T-326: podklad generuje zadávající lékař, přizvaný lékař nebo předseda
  const canGenerate = !isDemo && (item ? can.editCase(me, item) : can.manageBoards(me));
  const hideUnverified = brief?.config.hide_unverified ?? false;
  const forMe = useForMeQuery(isDemo ? null : Number(caseKey), me?.specialty && me.specialty !== 'patient' ? me.specialty : null);
  const view = forMe.data ?? null;
  // Výchozí „pro mě“, když má lékař odbornost a báze k diagnóze pohled; volba se pamatuje v prohlížeči.
  const [stored, setStored] = React.useState<OrderMode | null>(readOrderMode);
  const mode: OrderMode = view ? stored ?? 'me' : 'chair';
  const setMode = (next: OrderMode) => {
    setStored(next);
    try {
      localStorage.setItem(ORDER_KEY, next);
    } catch {
      // bez úložiště platí volba do přenačtení
    }
  };

  const allRoles = sectionsOf(brief, 'role_views').filter((s) => s.role !== 'patient');
  // V režimu „pro mě“ je vlastní pohled role první (T-319).
  const roles = mode === 'me' && view ? allRoles.toSorted((a, b) => Number(b.role === view.role) - Number(a.role === view.role)) : allRoles;
  const patientVoice = sectionsOf(brief, 'role_views').filter((s) => s.role === 'patient');
  const ds = brief?.decision_support;
  const redFlags = brief?.red_flags ?? [];
  const alerts = brief?.header.alerts ?? [];

  const missingBrief = !brief && (
    <div className="flex flex-col items-start gap-2">
      <p className="text-sm text-muted-foreground">
        {canGenerate ? 'Podklad zatím nevznikl. Přehled výše stojí na datech z IRIS a pravidlech.' : 'Podklad připraví předseda nebo zadávající lékař.'}
      </p>
      {canGenerate && <GenerateBrief caseId={caseKey} variant="outline" />}
    </div>
  );

  const blocks: Record<string, { def: SectionDef; node: React.ReactNode } | null> = {
    prehled: {
      def: { id: 'prehled', label: 'Rychlý přehled' },
      node: (
        <DetailSection id="prehled" title="Rychlý přehled">
          <MyTasks patientId={item?.patient_id ?? brief?.patient_id} />
          <CaseQuickViewBody sources={sources} caseId={item?.id ?? null} anamnesisEmpty={missingBrief || undefined} />
        </DetailSection>
      ),
    },
    'pro-me':
      view && mode === 'me'
        ? {
            def: { id: 'pro-me', label: 'Pro vás' },
            node: (
              <DetailSection id="pro-me" title={`Pro vás · ${ROLE_META[view.role].label.toLowerCase()}`}>
                <ForMePanel view={view} />
              </DetailSection>
            ),
          }
        : null,
    varovani: {
      def: { id: 'varovani', label: 'Varovné signály', count: brief ? redFlags.length : undefined },
      node: (
        <DetailSection id="varovani" title="Varovné signály" count={brief ? redFlags.length : undefined}>
          {brief ? (
            <div className="flex flex-col gap-5">
              <RedFlagList flags={redFlags} />
              {alerts.length > 0 && (
                <AiBlock title="Alergie, implantáty a předchozí výkony" status={brief.status} headingLevel="h3">
                  <ul className="flex flex-col gap-1.5">
                    {alerts.map((a) => <li key={a.id}><ClaimItem claim={a} /></li>)}
                  </ul>
                </AiBlock>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Varovné signály z rozporů mezi zdroji vzniknou s podkladem. Varování z kontroly úplnosti jsou v rychlém přehledu.
            </p>
          )}
        </DetailSection>
      ),
    },
    souhrn: {
      def: { id: 'souhrn', label: 'Souhrn a časová osa' },
      node: (
        <DetailSection id="souhrn" title="Souhrn a časová osa">
          <SummaryAndTimeline brief={brief} timeline={timeline} hideUnverified={hideUnverified} />
        </DetailSection>
      ),
    },
    anamneza:
      sectionsOf(brief, 'anamnesis').length || brief?.header.comorbidities.length
        ? {
            def: { id: 'anamneza', label: 'Anamnéza' },
            node: (
              <DetailSection id="anamneza" title="Anamnéza">
                <div className="flex flex-col gap-5">
                  {sectionsOf(brief, 'anamnesis').map((s) => (
                    <AiBlock key={s.title} title={s.title || 'Anamnéza'} status={brief?.status} headingLevel="h3">
                      <SectionClaims section={s} hideUnverified={hideUnverified} />
                    </AiBlock>
                  ))}
                  {brief && brief.header.comorbidities.length > 0 && (
                    <div>
                      <h3 className="mb-1.5 text-sm font-semibold">Komorbidity</h3>
                      <ul className="flex flex-col gap-1 text-sm">
                        {brief.header.comorbidities.map((c) => (
                          <li key={c.citation}>
                            {c.icd10 && <span translate="no" className="mr-1.5 font-medium">{c.icd10}</span>}
                            {c.text}
                            <Citations ids={[c.citation]} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </DetailSection>
            ),
          }
        : null,
    odbornosti:
      roles.length > 0 && brief
        ? {
            def: { id: 'odbornosti', label: 'Odbornosti', count: roles.length },
            node: (
              <DetailSection id="odbornosti" title="Odbornosti" count={roles.length}>
                <div className="flex flex-col gap-5">
                  {roles.map((s) => (
                    <RoleSection
                      key={`${s.role}-${s.title}`}
                      section={s}
                      series={sources.observations.data ?? []}
                      hideUnverified={hideUnverified}
                      status={brief.status}
                      defaultOpen={mode === 'me' && s.role === view?.role}
                    />
                  ))}
                </div>
              </DetailSection>
            ),
          }
        : null,
    lecba:
      brief && (ds || sectionsOf(brief, 'modalities').length)
        ? {
            def: { id: 'lecba', label: 'Léčba a studie' },
            node: (
              <DetailSection id="lecba" title="Léčba a studie">
                <div className="flex flex-col gap-8">
                  {sectionsOf(brief, 'modalities').map((s) => (
                    <AiBlock key={s.title} title={s.title || 'Léčebné metody a odborníci'} status={brief.status} headingLevel="h3">
                      <ClaimList claims={s.items} hideUnverified={hideUnverified} />
                    </AiBlock>
                  ))}
                  {ds && (
                    <>
                      <div>
                        <h3 className="mb-2 text-sm font-semibold">Možnosti léčby a soulad se stavem pacienta</h3>
                        <TreatmentOptions options={ds.treatment_options} />
                      </div>
                      <AiBlock title="Klinické studie (screening RKT)" status={brief.status} headingLevel="h3">
                        <TrialScreening trials={ds.trials} />
                      </AiBlock>
                    </>
                  )}
                </div>
              </DetailSection>
            ),
          }
        : null,
    pacient:
      patientVoice.length > 0 && brief
        ? {
            def: { id: 'pacient', label: 'Hlas pacienta' },
            node: (
              <DetailSection id="pacient" title="Hlas pacienta">
                {patientVoice.map((s) => (
                  <RoleSection key={s.title} section={s} series={sources.observations.data ?? []} hideUnverified={hideUnverified} status={brief.status} />
                ))}
              </DetailSection>
            ),
          }
        : null,
    otazky:
      ds && ds.discussion_questions.length > 0 && brief
        ? {
            def: { id: 'otazky', label: 'Otázky k diskusi', count: ds.discussion_questions.length },
            node: (
              <DetailSection id="otazky" title="Otázky k diskusi" count={ds.discussion_questions.length}>
                <AiBlock title="Otázky pro komisi" status={brief.status} headingLevel="h3">
                  <ol className="flex list-decimal flex-col gap-2 pl-5 text-sm leading-relaxed">
                    {ds.discussion_questions.map((q) => (
                      <li key={q.text}>
                        {q.text}
                        <Citations ids={q.citations} />
                      </li>
                    ))}
                  </ol>
                  <p className="mt-3 text-xs text-muted-foreground">{ds.disclaimer}</p>
                </AiBlock>
              </DetailSection>
            ),
          }
        : null,
  };

  const chairSections = (brief?.config.sections ?? []).filter((s) => s.enabled).toSorted((a, b) => a.order - b.order).map((s) => s.id);
  const order = mode === 'me' && view ? detailOrder(view.sections, true) : detailOrder(chairSections, false);
  const shown = order.map((id) => blocks[id]).filter((b): b is NonNullable<typeof b> => Boolean(b));
  const sections = shown.map((b) => b.def);

  return (
    <SectionsProvider initialOpen={['prehled', 'pro-me', 'varovani']}>
      <PageCrumbs
        items={[
          ...(session ? [{ label: session.title, href: `/dashboard/mdt/${session.id}` }] : []),
          {
            label: item?.patient_id ?? brief?.patient_id ?? sources.patientId,
            href: isDemo ? undefined : `/dashboard/patients/${encodeURIComponent(sources.patientId)}`,
          },
        ]}
      />
      <StickyCaseHeader caseKey={caseKey} sources={sources} session={session} item={item} brief={brief} canGenerate={canGenerate} sections={sections} />

      <div className="mx-auto grid w-full max-w-[1440px] gap-10 px-4 py-6 sm:px-6 lg:px-8 xl:grid-cols-[12rem_minmax(0,1fr)]">
        <aside className="hidden xl:block">
          <div className="sticky top-40 flex flex-col gap-4">
            <SectionNav sections={sections} variant="rail" />
          </div>
        </aside>

        <div className="flex min-w-0 flex-col gap-6">
          {view && (
            <div className="-mb-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
              <span className="text-[13px] text-muted-foreground" id="poradi-label">Pořadí podkladu</span>
              <ToggleGroup
                value={[mode]}
                onValueChange={(v) => v[0] && setMode(v[0] as OrderMode)}
                variant="outline"
                size="sm"
                spacing={0}
                aria-labelledby="poradi-label"
              >
                <ToggleGroupItem value="chair">Předsedy</ToggleGroupItem>
                <ToggleGroupItem value="me">Pro mě · {ROLE_META[view.role].label.toLowerCase()}</ToggleGroupItem>
              </ToggleGroup>
            </div>
          )}

          {shown.map((b) => (
            <React.Fragment key={b.def.id}>{b.node}</React.Fragment>
          ))}

          {brief?.feedback && <FeedbackNote feedback={brief.feedback} />}
          {brief && (
            <p className="border-t border-border pt-4 text-xs text-muted-foreground">
              Podklad připravila AI ({brief.model}). Rozhoduje lékař, oficiálním záznamem se stane až po potvrzení. Tvrzení{' '}
              <span className="tabular-nums">{brief.stats.claims_total}</span>, neověřených <span className="tabular-nums">{brief.stats.claims_unverified}</span>, chybějících
              údajů <span className="tabular-nums">{brief.stats.missing_total}</span>.
            </p>
          )}
        </div>
      </div>
    </SectionsProvider>
  );
}

/** Jedna časová osa s přepínačem AI shrnutí / události z IRIS (NAVRH_UI §8, místo dvou pod sebou). */
function SummaryAndTimeline({ brief, timeline, hideUnverified }: { brief: Brief | null; timeline: TimelineEvent[] | undefined; hideUnverified: boolean }) {
  const ai = [...sectionsOf(brief, 'summary'), ...sectionsOf(brief, 'timeline')];
  const [view, setView] = React.useState<'ai' | 'iris'>(ai.length ? 'ai' : 'iris');
  return (
    <div className="flex flex-col gap-4">
      {ai.length > 0 && (
        <ToggleGroup
          value={[view]}
          onValueChange={(v) => v[0] && setView(v[0] as 'ai' | 'iris')}
          variant="outline"
          size="sm"
          spacing={0}
          aria-label="Zobrazení časové osy"
        >
          <ToggleGroupItem value="ai">AI shrnutí</ToggleGroupItem>
          <ToggleGroupItem value="iris">Události z IRIS</ToggleGroupItem>
        </ToggleGroup>
      )}
      {view === 'ai' && brief ? (
        <div className="flex flex-col gap-5">
          {ai.map((s) => (
            <AiBlock key={`${s.id}-${s.title}`} title={s.title} status={brief.status} headingLevel="h3">
              <ClaimList claims={s.items} hideUnverified={hideUnverified} />
            </AiBlock>
          ))}
        </div>
      ) : timeline === undefined ? (
        <Skeleton className="h-32" />
      ) : timeline.length ? (
        <div>
          <p className="mb-3 text-xs text-muted-foreground">Přímo z dokumentace v IRIS, bez AI.</p>
          <Timeline events={timeline} />
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">V IRIS nejsou pro pacienta žádné události.</p>
      )}
    </div>
  );
}

function StickyCaseHeader({
  caseKey,
  sources,
  session,
  item,
  brief,
  canGenerate,
  sections,
}: {
  caseKey: string;
  sources: QuickViewSources;
  session: MdtSessionDetail | null;
  item: MdtCase | null;
  brief: Brief | null;
  canGenerate: boolean;
  sections: SectionDef[];
}) {
  const router = useRouter();
  const header = quickHeader(sources, item);
  const agenda = agendaOrder(session).filter((c): c is MdtCase & { id: number } => c.id != null);
  const index = item ? agenda.findIndex((c) => c.id === item.id) : -1;
  const prev = index > 0 ? agenda[index - 1] : null;
  const next = index >= 0 && index < agenda.length - 1 ? agenda[index + 1] : null;
  const isDemo = caseKey === DEMO_CASE;
  const highWarnings = header.warnings.filter((w) => w.severity === 'high').length;
  const job = useBriefJob(caseKey);
  const [regenerating, setRegenerating] = React.useState(false);
  const flags = brief?.red_flags.length ?? 0;

  return (
    <div className="sticky top-14 z-20 border-b border-border bg-background/95 backdrop-blur supports-backdrop-filter:bg-background/85">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-2 px-4 py-3 sm:px-6 lg:px-8">
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {session && (
            <Link
              href={`/dashboard/mdt/${session.id}${item ? `?pacient=${item.id}` : ''}`}
              className="inline-flex items-center gap-1 text-[13px] text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="size-4" aria-hidden /> Jednání
            </Link>
          )}
          <div className="min-w-0 flex-1 basis-64">
            <h1 translate="no" className="truncate text-lg font-semibold tracking-tight">{header.displayName}</h1>
            <p className="truncate text-[13px] text-muted-foreground">
              {header.diagnosis ? (
                <>
                  <span translate="no" className="font-medium text-foreground">{header.diagnosis.icd10}</span> {header.diagnosis.text}
                </>
              ) : (
                'Diagnóza v záznamu chybí'
              )}
              {header.tnm && <> · <span translate="no">{header.tnm}</span></>}
            </p>
          </div>
          <dl className="flex items-center gap-4 text-sm">
            <div className="flex items-baseline gap-1.5" title="Performance status (ECOG): lékař, pacient (PROMs)">
              <dt className="text-xs text-muted-foreground">PS</dt>
              <dd className="text-lg font-semibold tabular-nums">{header.physicianPs ?? '–'}</dd>
              <dd className={cn('inline-flex items-center gap-0.5 text-xs tabular-nums', header.psDiffers ? 'font-medium text-amber-800 dark:text-amber-300' : 'text-muted-foreground')}>
                {header.psDiffers && <TriangleAlert className="size-3" aria-hidden />}
                pac. {header.patientPs ?? '–'}
              </dd>
            </div>
            <div className="flex items-baseline gap-1.5" title={`Léčebný záměr: ${header.intentSource}`}>
              <dt className="text-xs text-muted-foreground">C/P</dt>
              <dd className="text-lg font-semibold">{header.intent ?? '–'}</dd>
            </div>
            {(flags > 0 || highWarnings > 0) && (
              <a href="#varovani" className="inline-flex items-center gap-1 text-[13px] font-medium hover:underline hover:underline-offset-4">
                <TriangleAlert className={cn('size-4', highWarnings || brief?.red_flags.some((f) => f.severity === 'high') ? 'text-red-700 dark:text-red-400' : 'text-amber-700 dark:text-amber-400')} aria-hidden />
                <span className="tabular-nums">{flags || header.warnings.length}</span> varování
              </a>
            )}
          </dl>
          <div className="flex items-center gap-1.5">
            {agenda.length > 1 && (
              <div className="flex items-center">
                <NeighbourLink item={prev} direction="prev" />
                <span className="px-1 text-xs tabular-nums text-muted-foreground">{index + 1}/{agenda.length}</span>
                <NeighbourLink item={next} direction="next" />
              </div>
            )}
            {session && item?.id != null && (
              <Button
                variant="outline"
                size="lg"
                onClick={() => openProjectorWindow({ board: session.id, caseId: item.id as number, patient: item.patient_id })}
                title="Okno pro projektor"
              >
                <MonitorUp aria-hidden /> <span className="hidden sm:inline">Projektor</span>
              </Button>
            )}
            {!isDemo && (
              <Link href={`/dashboard/cases/${caseKey}/record`} className={buttonVariants({ size: 'lg' })}>
                <NotebookPen aria-hidden /> Závěr komise
              </Link>
            )}
            <DropdownMenu>
              <DropdownMenuTrigger render={<Button variant="ghost" size="icon-lg" aria-label="Další akce" />}>
                <MoreHorizontal aria-hidden />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                <DropdownMenuItem onClick={() => { if (!briefWindow(caseKey)) router.push(`/brief/${caseKey}`); }}>
                  <PanelRightOpen aria-hidden /> Úzké okno vedle PACS
                </DropdownMenuItem>
                {!isDemo && (
                  <DropdownMenuItem onClick={() => router.push(`/dashboard/patients/${encodeURIComponent(sources.patientId)}`)}>
                    <UserRound aria-hidden /> Karta pacienta, vložit zprávu
                  </DropdownMenuItem>
                )}
                {canGenerate && brief && (
                  <DropdownMenuItem onClick={() => setRegenerating(true)} disabled={job.running || job.starting}>
                    <RefreshCw aria-hidden /> Přegenerovat s připomínkou…
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        {job.progress}
        <RegenerateDialog open={regenerating} onClose={() => setRegenerating(false)} onSubmit={(feedback) => void job.start(feedback)} />
        <div className="xl:hidden">
          <SectionNav sections={sections} variant="tabs" />
        </div>
      </div>
    </div>
  );
}

function NeighbourLink({ item, direction }: { item: (MdtCase & { id: number }) | null; direction: 'prev' | 'next' }) {
  const label = direction === 'prev' ? 'Předchozí pacient' : 'Další pacient';
  const Icon = direction === 'prev' ? ChevronLeft : ChevronRight;
  if (!item) {
    return (
      <span className={cn(buttonVariants({ variant: 'ghost', size: 'icon-lg' }), 'pointer-events-none opacity-40')} aria-hidden>
        <Icon />
      </span>
    );
  }
  return (
    <Tooltip>
      <TooltipTrigger render={<Link href={`/dashboard/cases/${item.id}`} className={buttonVariants({ variant: 'ghost', size: 'icon-lg' })} aria-label={`${label}: ${item.patient_id}`} />}>
        <Icon aria-hidden />
      </TooltipTrigger>
      <TooltipContent>
        {label}: {item.patient_id}
      </TooltipContent>
    </Tooltip>
  );
}

function DetailSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 px-4 py-6 sm:px-6 lg:px-8" aria-busy="true" aria-label="Načítám detail pacienta">
      <Skeleton className="h-6 w-64" />
      <Skeleton className="h-4 w-96" />
      <Skeleton className="mt-6 h-16" />
      <div className="grid gap-8 lg:grid-cols-2">
        <Skeleton className="h-72" />
        <Skeleton className="h-72" />
      </div>
    </div>
  );
}
