'use client';

import * as React from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/shadcn/skeleton';
import { Input } from '@/components/ui/input';
import { mdtApi } from '@/lib/mdt-api';
import { apiErrorMessage, useMyTemplates, useSaveTemplate } from '@/lib/queries';
import type { ProjectorLayout, TemplateArea } from '@/types/mdt';
import { AREAS, TemplateAreasEditor } from './FactLayoutEditor';
import { AREA_LABEL } from './fact-layout';
import { useMe } from './me';
import { ROLE_META } from './roles';

type Drafts = Partial<Record<TemplateArea, ProjectorLayout>>;
const same = (a: unknown, b: unknown) => JSON.stringify(a ?? {}) === JSON.stringify(b ?? {});

/**
 * Nastavení → Moje šablona údajů (T-338, docs/SABLONY_LEKARE.md R2, R5): tituly a šablona klíčových údajů po
 * oblastech. Platí v mém detailu a přehledech a jako výchozí okno projektoru u pacientů, které zařazuji.
 */
export function MyTemplateCard() {
  const me = useMe();
  const templates = useMyTemplates();
  const save = useSaveTemplate();
  const [drafts, setDrafts] = React.useState<Drafts | null>(null);
  const [preset, setPreset] = React.useState<string | undefined>();
  const [titles, setTitles] = React.useState<{ title_before: string; title_after: string } | null>(null);

  const saved = React.useMemo(() => {
    const out: Drafts = {};
    for (const t of templates.data?.templates ?? []) if (t.layout) out[t.area] = t.layout;
    return out;
  }, [templates.data]);
  const current = drafts ?? saved;
  const changed = AREAS.filter((a) => !same(current[a], saved[a]));
  const titleValue = titles ?? { title_before: me?.title_before ?? '', title_after: me?.title_after ?? '' };

  const saveAll = async () => {
    try {
      for (const area of changed) {
        const layout = current[area];
        await save.mutateAsync({ area, layout: layout && Object.keys(layout).length ? layout : null, preset });
      }
      setDrafts(null);
      toast.success('Šablona uložena', { description: changed.map((a) => AREA_LABEL[a]).join(', ') });
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Šablonu se nepodařilo uložit.'));
    }
  };

  const saveTitles = async () => {
    try {
      const updated = await mdtApi.updateMyTitles(titleValue);
      toast.success(`Uloženo: ${updated.name}`, { description: 'Nové jméno se ukáže po obnovení stránky.' });
      setTitles(null);
    } catch (err) {
      toast.error(apiErrorMessage(err, 'Tituly se nepodařilo uložit.'));
    }
  };

  return (
    <section id="sablona" aria-labelledby="sablona-nadpis" className="scroll-mt-20 rounded-xl border border-border bg-card p-5">
      <h2 id="sablona-nadpis" className="text-base font-semibold">Lékař a moje šablona údajů</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Co chcete u pacienta vidět a v jakém pořadí. Platí ve vašem detailu a přehledech a jako výchozí okno pro projektor
        u pacientů, které zařazujete. U konkrétního pacienta ho můžete upravit. Skryté údaje nezmizí, závažný údaj se ukáže vždy.
      </p>

      <div className="mt-4 grid max-w-xl grid-cols-[1fr_1fr_auto] items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-semibold">
          Titul před jménem
          <Input value={titleValue.title_before} onChange={(e) => setTitles({ ...titleValue, title_before: e.target.value })} placeholder="MUDr." maxLength={40} />
        </label>
        <label className="flex flex-col gap-1 text-xs font-semibold">
          Titul za jménem
          <Input value={titleValue.title_after} onChange={(e) => setTitles({ ...titleValue, title_after: e.target.value })} placeholder="Ph.D." maxLength={40} />
        </label>
        <Button type="button" variant="outline" onClick={() => void saveTitles()} disabled={!titles}>Uložit tituly</Button>
      </div>
      {me && (
        <p className="mt-2 text-xs text-muted-foreground">
          Profese: {me.specialty ? ROLE_META[me.specialty].label : 'nevyplněno'} (mění předseda v Týmu komise).
        </p>
      )}

      <div className="mt-5">
        {templates.isLoading ? (
          <Skeleton className="h-64" />
        ) : templates.isError ? (
          <p role="alert" className="text-sm text-destructive">{apiErrorMessage(templates.error, 'Šablonu se nepodařilo načíst.')}</p>
        ) : (
          <TemplateAreasEditor
            value={current}
            specialty={me?.specialty}
            onChange={(next, presetId) => {
              setDrafts(next);
              if (presetId) setPreset(presetId);
            }}
          />
        )}
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-border pt-4">
        <Button type="button" onClick={() => void saveAll()} disabled={!changed.length || save.isPending} isLoading={save.isPending}>
          Uložit šablonu{changed.length ? ` (${changed.map((a) => AREA_LABEL[a]).join(', ')})` : ''}
        </Button>
        {changed.length > 0 && (
          <Button type="button" variant="ghost" onClick={() => setDrafts(null)}>Zahodit změny</Button>
        )}
        {!changed.length && <span className="text-xs text-muted-foreground">Vše uloženo.</span>}
      </div>
    </section>
  );
}
