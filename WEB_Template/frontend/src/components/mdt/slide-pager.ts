'use client';

import * as React from 'react';

/**
 * Stránkování okna projektoru na slidy (T-348): obsah se neposouvá, ale skládá do slidů podle výšky okna.
 * Jednotky (skupina údajů, pár postupů, anamnéza) se změří v neviditelné vrstvě stejné šířky jako sloupec slidu
 * a po pořadí se plní sloupce: když se jednotka nevejde, pokračuje v dalším sloupci nebo na dalším slidu.
 * Jednotky stejného bloku za sebou tvoří jednu kartu s nadpisem bloku (karta stojí `chrome[block]` výšky).
 */

export interface SlideUnit<B extends string = string> {
  key: string;
  block: B;
  node: React.ReactNode;
}

export interface SlideSegment<B extends string = string> {
  block: B;
  units: SlideUnit<B>[];
  /** Blok začal na předchozím slidu nebo ve sloupci vlevo: nadpis dostane „pokračování“. */
  continued: boolean;
}

export interface SlidePage<B extends string = string> {
  columns: SlideSegment<B>[][];
  /** Jednotka vyšší než celý slide (dlouhá anamnéza): jen tento slide smí posouvat. */
  overflow: boolean;
}

export const UNIT_GAP = 6;        // gap-1.5 mezi jednotkami v kartě
export const CARD_GAP = 8;        // gap-2 mezi kartami
export const COLUMN_GAP = 8;
export const WIDE_FROM = 768;     // 48rem: od této šířky dva sloupce vedle sebe (projektor, široké okno)

export function paginate<B extends string>(
  units: SlideUnit<B>[],
  heights: Record<string, number>,
  chrome: Partial<Record<B, number>>,
  available: number,
  columns: number,
): SlidePage<B>[] {
  const pages: SlidePage<B>[] = [];
  let page: SlidePage<B> = { columns: [[]], overflow: false };
  let used = 0;
  const started = new Set<B>();
  const column = () => page.columns[page.columns.length - 1];
  const nextColumn = () => {
    if (page.columns.length < columns) page.columns.push([]);
    else {
      pages.push(page);
      page = { columns: [[]], overflow: false };
    }
    used = 0;
  };
  for (const unit of units) {
    const h = heights[unit.key] ?? 0;
    const last = column().at(-1);
    const joins = last?.block === unit.block;
    let cost = joins ? UNIT_GAP + h : (used ? CARD_GAP : 0) + (chrome[unit.block] ?? 0) + h;
    if (used > 0 && used + cost > available) {
      nextColumn();
      cost = (chrome[unit.block] ?? 0) + h;
    }
    const segment = column().at(-1);
    if (segment?.block === unit.block && used > 0) segment.units.push(unit);
    else column().push({ block: unit.block, units: [unit], continued: started.has(unit.block) });
    started.add(unit.block);
    used += cost;
    if (used > available) page.overflow = true;
  }
  if (column().length || pages.length === 0) pages.push(page);
  return pages;
}

/**
 * Změří jednotky (`data-unit` v `measureRef`) a nadpisy karet (`data-chrome`) a vrátí slidy pro aktuální velikost
 * okna. Přepočítá se při změně velikosti okna i obsahu (načtení dat, rozbalení textu v měřicí vrstvě).
 */
export function useSlidePages<B extends string>(
  units: SlideUnit<B>[],
  viewportRef: React.RefObject<HTMLElement | null>,
  measureRef: React.RefObject<HTMLElement | null>,
): { pages: SlidePage<B>[]; columns: number; columnWidth: number | null } {
  const [size, setSize] = React.useState<{ width: number; height: number } | null>(null);
  const [measured, setMeasured] = React.useState<{ heights: Record<string, number>; chrome: Partial<Record<B, number>> }>({
    heights: {},
    chrome: {},
  });

  React.useLayoutEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const read = () => setSize({ width: viewport.clientWidth, height: viewport.clientHeight });
    read();
    const observer = new ResizeObserver(read);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, [viewportRef]);

  const columns = size && size.width >= WIDE_FROM ? 2 : 1;
  const columnWidth = size ? Math.floor((size.width - COLUMN_GAP * (columns - 1)) / columns) : null;

  React.useLayoutEffect(() => {
    const layer = measureRef.current;
    if (!layer || columnWidth == null) return;
    const read = () => {
      const heights: Record<string, number> = {};
      layer.querySelectorAll<HTMLElement>('[data-unit]').forEach((el) => {
        heights[el.dataset.unit!] = el.getBoundingClientRect().height;
      });
      // karta bez jednotek: vnitřní okraje + nadpis bloku + mezera pod nadpisem (anamnéza nadpis nemá)
      const chrome: Partial<Record<B, number>> = {};
      layer.querySelectorAll<HTMLElement>('[data-chrome]').forEach((card) => {
        const style = getComputedStyle(card);
        const title = card.querySelector<HTMLElement>('[data-chrome-title]')?.getBoundingClientRect().height ?? 0;
        chrome[card.dataset.chrome as B] =
          parseFloat(style.paddingTop) + parseFloat(style.paddingBottom) + title + (title ? UNIT_GAP : 0);
      });
      setMeasured((prev) => (same(prev.heights, heights) && same(prev.chrome, chrome) ? prev : { heights, chrome }));
    };
    read();
    const observer = new ResizeObserver(read);
    observer.observe(layer);
    return () => observer.disconnect();
  }, [measureRef, columnWidth, units]);

  const pages = React.useMemo(
    () => (size ? paginate(units, measured.heights, measured.chrome, size.height, columns) : [{ columns: [units.length ? [{ block: units[0].block, units, continued: false }] : []], overflow: false }]),
    [units, measured, size, columns],
  );
  return { pages, columns, columnWidth };
}

function same(a: Partial<Record<string, number>>, b: Partial<Record<string, number>>) {
  const ka = Object.keys(a);
  return ka.length === Object.keys(b).length && ka.every((k) => Math.abs((a[k] ?? 0) - (b[k] ?? -1)) < 0.5);
}

/** Popisek slidu: bloky na něm v pořadí („Klíčové údaje · Léčebné postupy“). */
export function pageBlocks<B extends string>(page: SlidePage<B> | undefined): B[] {
  return [...new Set((page?.columns ?? []).flat().map((s) => s.block))];
}
