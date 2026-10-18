import type * as React from 'react';
import type { FactCategory, ProjectorLayout, TemplateArea } from '@/types/mdt';
import type { KeyFact } from './key-facts';

/**
 * Kategorie klíčových údajů a rozložení podle šablony lékaře (T-338, docs/SABLONY_LEKARE.md, D-024, D-025).
 *
 * - Kategorie určuje systém (pole `category` z API); šablona mění jen pořadí a viditelnost.
 * - Skrytý údaj se neztratí (D-019): je ve skupině „skryté“, o klik dál.
 * - Závažný údaj se ukáže, i když ho šablona skrývá (`forced`).
 * - Údaj, který šablona nezná (nový), je viditelný na konci své kategorie.
 */
export const CATEGORY_META: { id: FactCategory; label: string }[] = [
  { id: 'staging', label: 'Diagnóza a staging' },
  { id: 'molecular', label: 'Molekulární genetika a biomarkery' },
  { id: 'imaging', label: 'Zobrazení a invazivní vyšetření' },
  { id: 'function', label: 'Funkční stav a výkonnost' },
  { id: 'history', label: 'Anamnéza a dosavadní léčba' },
  { id: 'lab', label: 'Laboratoř' },
  { id: 'patient', label: 'Pacient: dotazníky a preference' },
  { id: 'alerts', label: 'Upozornění a chybějící údaje' },
];
export const CATEGORY_LABEL = Object.fromEntries(CATEGORY_META.map((c) => [c.id, c.label])) as Record<FactCategory, string>;

export const AREA_LABEL: Record<TemplateArea, string> = { PLI: 'Plíce', PRS: 'Prs', KRC: 'Kolorektum', OBC: 'Ostatní diagnózy' };

/** Oblast šablony podle MKN-10 (stejné pravidlo jako sada guidelines na serveru). */
export function areaForIcd10(icd10: string | null | undefined): TemplateArea {
  const code = (icd10 ?? '').toUpperCase();
  if (code.startsWith('C34')) return 'PLI';
  if (code.startsWith('C50')) return 'PRS';
  if (/^C(18|19|20)/.test(code)) return 'KRC';
  return 'OBC';
}

/** Klíč údaje v šabloně bez ID pacienta: `alert:RF-LAB:P04-lab05-cea` → `alert:RF-LAB`. */
export function templateKey(fact: Pick<KeyFact, 'id'>): string {
  if (!fact.id.startsWith('alert:')) return fact.id;
  return `alert:${fact.id.slice('alert:'.length).split(':')[0]}`;
}

const hasKey = (set: Set<string>, fact: KeyFact) => set.has(fact.id) || set.has(templateKey(fact));

export interface FactGroupView {
  category: FactCategory;
  label: string;
  /** Viditelné v pořadí šablony (bez šablony podle stavu: závažné, mimo normu, chybí…). */
  facts: KeyFact[];
  /** Skryté šablonou (údaj nebo celá kategorie). */
  hidden: KeyFact[];
  /** ID údajů ukázaných přes skrytí, protože jsou závažné. */
  forced: Set<string>;
  /** Celá kategorie je v šabloně skrytá. */
  categoryHidden: boolean;
}

export function hasLayout(layout: ProjectorLayout | null | undefined): layout is ProjectorLayout {
  return Boolean(layout && (layout.categories || layout.facts?.order?.length || layout.facts?.hidden?.length || layout.blocks));
}

/** Údaje do kategorií podle šablony. `statusOrder` = výchozí pořadí uvnitř kategorie (priorita stavu). */
export function arrangeFacts(
  facts: KeyFact[],
  layout: ProjectorLayout | null | undefined,
  statusOrder: (facts: KeyFact[]) => KeyFact[],
): { groups: FactGroupView[]; hiddenCount: number } {
  const known = CATEGORY_META.map((c) => c.id);
  const order = [...new Set([...(layout?.categories?.order ?? []).filter((c) => known.includes(c)), ...known])];
  const hiddenCategories = new Set(layout?.categories?.hidden ?? []);
  const factOrder = layout?.facts?.order ?? [];
  const hiddenFacts = new Set(layout?.facts?.hidden ?? []);
  const rank = (fact: KeyFact) => {
    const byId = factOrder.indexOf(fact.id);
    const byKey = factOrder.indexOf(templateKey(fact));
    const found = [byId, byKey].filter((i) => i >= 0);
    return found.length ? Math.min(...found) : Number.POSITIVE_INFINITY;
  };
  let hiddenCount = 0;
  const groups: FactGroupView[] = [];
  for (const category of order) {
    const inCategory = facts.filter((f) => f.category === category);
    if (!inCategory.length) continue;
    const base = statusOrder(inCategory);
    const sorted = factOrder.length
      ? base.map((fact, i) => ({ fact, r: rank(fact), i })).sort((a, b) => a.r - b.r || a.i - b.i).map((x) => x.fact)
      : base;
    const categoryHidden = hiddenCategories.has(category);
    const visible: KeyFact[] = [];
    const hidden: KeyFact[] = [];
    const forced = new Set<string>();
    for (const fact of sorted) {
      const hide = categoryHidden || hasKey(hiddenFacts, fact);
      if (!hide) visible.push(fact);
      else if (fact.status === 'critical') {
        visible.push(fact);
        forced.add(fact.id);
      } else hidden.push(fact);
    }
    hiddenCount += hidden.length;
    groups.push({ category, label: CATEGORY_LABEL[category], facts: visible, hidden, forced, categoryHidden });
  }
  return { groups, hiddenCount };
}


/** Položka editoru rozložení: údaj pacienta (úprava u případu) nebo údaj z katalogu (šablona lékaře). */
export interface LayoutItem {
  key: string;
  abbr: string;
  label: string;
  category: FactCategory;
  detail?: React.ReactNode;
}

/** Kategorie a údaje v pořadí rozložení včetně skrytých (pro editor; žádné vynucení závažných). */
export function editorGroups(items: LayoutItem[], layout: ProjectorLayout) {
  const known = CATEGORY_META.map((c) => c.id);
  const order = [...new Set([...(layout.categories?.order ?? []).filter((c) => known.includes(c)), ...known])];
  const hiddenCategories = new Set(layout.categories?.hidden ?? []);
  const factOrder = layout.facts?.order ?? [];
  const hiddenFacts = new Set(layout.facts?.hidden ?? []);
  const rank = (key: string) => {
    const i = factOrder.indexOf(key);
    return i === -1 ? Number.POSITIVE_INFINITY : i;
  };
  return order
    .map((category) => ({
      category,
      label: CATEGORY_LABEL[category],
      hidden: hiddenCategories.has(category),
      items: items
        .filter((it) => it.category === category)
        .map((item, i) => ({ item, i }))
        .sort((a, b) => rank(a.item.key) - rank(b.item.key) || a.i - b.i)
        .map(({ item }) => ({ item, hidden: hiddenFacts.has(item.key) })),
    }))
    .filter((g) => g.items.length > 0);
}
