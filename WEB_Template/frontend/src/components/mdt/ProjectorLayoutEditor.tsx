'use client';

import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Plus, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/shadcn/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/shadcn/dialog';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, queryKeys, useIntakeQuery, useObservationsQuery } from '@/lib/queries';
import { cn } from '@/lib/utils';
import type { EvidenceId, MdtCase, ProjectorExtra, ProjectorLayout } from '@/types/mdt';
import { AiTag } from './AiBlock';
import { CitationProvider, Citations } from './citations';
import { FactIcon } from './FactIcon';
import { FactLayoutEditor } from './FactLayoutEditor';
import { AREA_LABEL, areaForIcd10, hasLayout, templateKey, type LayoutItem } from './fact-layout';
import { buildKeyFacts } from './key-facts';
import { useMe } from './me';
import { MAX_EXTRA, PatientChatDialog, PatientChatFocus } from './PatientChatDialog';
import { shortPatient } from './patient';
import { CaseQuickViewProjector, useQuickViewSources } from './quick-view';
import { SourceDrawer } from './SourceDrawer';

/**
 * Úprava okna pro projektor u případu (T-333): kategorie a údaje skrýt nebo přeskládat (T-338). Skrývá se jen
 * v projektoru, podklad i detail zůstávají celé (D-019). Bez úpravy platí šablona zadávajícího lékaře.
 * „Doplnit z karty“ (T-345): chatbot nad kartou pacienta, nalezené tvrzení se zdrojem jde do okna. Při zařazení je
 * chatbot vedle formuláře (tlačítko do něj skočí), jinak se otevře v dialogu uprostřed.
 */
export function ProjectorLayoutEditor({
  patientId,
  value,
  onChange,
}: {
  patientId: string;
  value: ProjectorLayout;
  onChange: (next: ProjectorLayout) => void;
}) {
  const intake = useIntakeQuery(patientId);
  const observations = useObservationsQuery(patientId);
  const items = React.useMemo<LayoutItem[]>(
    () =>
      buildKeyFacts(intake.data, observations.data).facts.map((fact) => ({
        key: fact.id,
        abbr: fact.abbr,
        label: fact.label,
        category: fact.category,
        detail: (
          <>
            <FactIcon status={fact.status} className="size-3.5 shrink-0" />
            <span className="truncate">{(fact.value ?? fact.label).replace(new RegExp(`^${fact.abbr.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}: `), '')}</span>
          </>
        ),
      })),
    [intake.data, observations.data],
  );
  const [asking, setAsking] = React.useState(false);
  const focusChat = React.useContext(PatientChatFocus);
  const extra = value.extra ?? [];
  const setExtra = (next: ProjectorExtra[]) => onChange({ ...value, extra: next });
  return (
    <>
      <FactLayoutEditor
        items={items}
        value={value}
        onChange={onChange}
        blocks
        hideVerb="Skrýt v okně pro projektor"
        loading={intake.isLoading || observations.isLoading}
        addon={extra.length > 0 && <ExtraList items={extra} onRemove={(id) => setExtra(extra.filter((x) => x.id !== id))} />}
        actions={
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              if (!focusChat?.()) setAsking(true);
            }}
            title="Najít údaj v kartě pacienta (chatbot) a doplnit ho do okna pro projektor"
          >
            <Plus aria-hidden /> Doplnit z karty
          </Button>
        }
      />
      <PatientChatDialog
        patientId={patientId}
        open={asking}
        onOpenChange={setAsking}
        extra={extra}
        onAdd={(item) => {
          setExtra([...extra, item]);
          toast.success('Doplněno do okna pro projektor', { description: item.text });
        }}
      />
    </>
  );
}

/** Údaje doplněné z karty pacienta: v okně pod klíčovými údaji, každý se zdrojem; odebírají se jednotlivě. */
function ExtraList({ items, onRemove }: { items: ProjectorExtra[]; onRemove: (id: string) => void }) {
  return (
    <section>
      <h3 className="text-sm font-semibold">
        Doplněno z karty pacienta <span className="font-normal text-muted-foreground">({items.length} z {MAX_EXTRA})</span>
      </h3>
      <p className="mb-2 text-xs text-muted-foreground">V okně pro projektor pod klíčovými údaji, každý se zdrojem. Podklad se nemění.</p>
      <ul className="flex flex-col gap-1">
        {items.map((x) => (
          <li
            key={x.id}
            className={cn('flex items-start gap-2 rounded-lg border border-border bg-card px-2 py-1.5 text-sm', x.ai && 'border-l-2 border-l-ai/60')}
          >
            <p className="min-w-0 flex-1 leading-snug">
              {x.ai && <AiTag className="mr-1.5 align-baseline" />}
              {x.text}
              <Citations ids={x.citations} />
            </p>
            <button
              type="button"
              onClick={() => onRemove(x.id)}
              aria-label={`Odebrat z okna pro projektor: ${x.text}`}
              title="Odebrat z okna pro projektor"
              className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <X className="size-4" aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Rozložení u případu (přesná ID údajů) → šablona lékaře (klíče bez ID pacienta). */
function asTemplate(layout: ProjectorLayout): ProjectorLayout {
  const keys = (ids: string[] | undefined) => [...new Set((ids ?? []).map((id) => templateKey({ id })))];
  return {
    ...(layout.categories ? { categories: layout.categories } : {}),
    ...(layout.facts ? { facts: { order: keys(layout.facts.order), hidden: keys(layout.facts.hidden) } } : {}),
  };
}

/** Dialog s editorem a živým náhledem okna pro projektor; ukládá zadávající, přizvaný lékař nebo předseda. */
export function ProjectorLayoutDialog({ item, open, onOpenChange }: { item: MdtCase; open: boolean; onOpenChange: (open: boolean) => void }) {
  const client = useQueryClient();
  const me = useMe();
  // Bez úpravy u případu se vychází ze šablony zadávajícího; doplněné z karty pacienta (T-345) zůstávají.
  const caseExtra = item.projector_layout?.extra ?? [];
  const startFrom = hasLayout(item.projector_layout)
    ? item.projector_layout!
    : { ...(item.requester_layout ?? {}), ...(caseExtra.length ? { extra: caseExtra } : {}) };
  const [draft, setDraft] = React.useState<ProjectorLayout>(() => startFrom);
  const [sourceId, setSourceId] = React.useState<EvidenceId | null>(null);
  const [alsoMine, setAlsoMine] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const sources = useQuickViewSources({ sessionId: item.session, caseId: item.id ?? null, patientId: item.patient_id });
  const area = areaForIcd10(item.patient?.diagnosis?.icd10);
  const requester = item.created_by?.name;
  const iAmRequester = Boolean(me && item.created_by && me.user_id === item.created_by.user_id);

  const save = async () => {
    if (item.id === undefined) return;
    setSaving(true);
    try {
      await mdtApi.updateCase(item.id, { projector_layout: draft });
      if (alsoMine) await mdtApi.saveTemplate(area, asTemplate(draft));
      await Promise.all([
        client.invalidateQueries({ queryKey: queryKeys.session(item.session) }),
        client.invalidateQueries({ queryKey: queryKeys.sessions }),
        ...(alsoMine ? [client.invalidateQueries({ queryKey: ['templates'] })] : []),
      ]);
      toast.success('Okno pro projektor uloženo', {
        description: alsoMine ? `Také jako vaše šablona pro ${AREA_LABEL[area].toLowerCase()}.` : 'Otevřené okno se přepne po obnovení dat.',
      });
      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Rozložení se nepodařilo uložit.'));
    } finally {
      setSaving(false);
    }
  };

  const resetToTemplate = async () => {
    if (item.id === undefined) return;
    setSaving(true);
    try {
      await mdtApi.updateCase(item.id, { projector_layout: caseExtra.length ? { extra: caseExtra } : {} });
      await client.invalidateQueries({ queryKey: queryKeys.session(item.session) });
      toast.success(`Okno podle šablony ${iAmRequester ? 'vaší' : 'zadávajícího lékaře'}`);
      onOpenChange(false);
    } catch (error) {
      toast.error(apiErrorMessage(error, 'Rozložení se nepodařilo vrátit.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle>Okno pro projektor · {shortPatient(item)}</DialogTitle>
          <DialogDescription>
            Skryjte, co komise na projektoru nepotřebuje, a přetažením seřaďte kategorie a údaje. Vlevo je náhled.{' '}
            {hasLayout(item.projector_layout)
              ? 'U pacienta je vlastní úprava.'
              : item.requester_layout
                ? `Teď platí šablona ${iAmRequester ? 'vaše' : `zadávajícího lékaře${requester ? ` (${requester})` : ''}`}.`
                : 'Teď platí výchozí pořadí.'}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-5 md:grid-cols-[420px_minmax(0,1fr)]">
          <div className="hidden h-[60vh] overflow-hidden rounded-xl border border-border md:block" aria-label="Náhled okna pro projektor">
            <CaseQuickViewProjector sources={sources} caseId={item.id ?? null} titleAs="h2" layout={draft} />
          </div>
          <div className="max-h-[60vh] overflow-y-auto pr-1">
            <CitationProvider order={[]} activeId={sourceId} onOpen={setSourceId}>
              <ProjectorLayoutEditor patientId={item.patient_id} value={draft} onChange={setDraft} />
              <SourceDrawer evidenceId={sourceId} loadSource={mdtApi.getEvidence} onClose={() => setSourceId(null)} />
            </CitationProvider>
          </div>
        </div>
        <DialogFooter className="flex-wrap items-center gap-2 sm:justify-between">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="size-4 accent-primary" checked={alsoMine} onChange={(e) => setAlsoMine(e.target.checked)} />
            Uložit také jako moji šablonu pro {AREA_LABEL[area].toLowerCase()}
          </label>
          <div className="flex flex-wrap gap-2">
            {hasLayout(item.projector_layout) && (
              <Button variant="ghost" onClick={() => void resetToTemplate()} disabled={saving}>Podle šablony</Button>
            )}
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>Zrušit</Button>
            <Button onClick={save} disabled={saving}>{saving ? 'Ukládám…' : 'Uložit okno pro projektor'}</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
