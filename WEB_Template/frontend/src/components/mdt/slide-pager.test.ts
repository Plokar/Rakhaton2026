import { describe, expect, it } from 'vitest';
import { CARD_GAP, paginate, UNIT_GAP, type SlideUnit } from './slide-pager';

const unit = (key: string, block = 'facts'): SlideUnit => ({ key, block, node: null });

describe('paginate (slidy projektoru, T-383)', () => {
  it('vejde-li se vše, je jeden slide', () => {
    const pages = paginate([unit('a'), unit('b')], { a: 100, b: 100 }, { facts: 40 }, 1000, 1);
    expect(pages).toHaveLength(1);
    expect(pages[0].columns[0][0].units.map((u) => u.key)).toEqual(['a', 'b']);
  });

  it('co se nevejde, jde na další slide s „pokračováním“ bloku', () => {
    const h = { a: 300, b: 300, c: 300 };
    const pages = paginate([unit('a'), unit('b'), unit('c')], h, { facts: 40 }, 40 + 300 + UNIT_GAP + 300, 1);
    expect(pages).toHaveLength(2);
    expect(pages[1].columns[0][0].continued).toBe(true);
    expect(pages[1].columns[0][0].units.map((u) => u.key)).toEqual(['c']);
  });

  it('dva sloupce se plní před dalším slidem', () => {
    const pages = paginate([unit('a'), unit('b', 'options')], { a: 500, b: 500 }, { facts: 0, options: 0 }, 500 + CARD_GAP, 2);
    expect(pages).toHaveLength(1);
    expect(pages[0].columns).toHaveLength(2);
  });

  it('jednotka vyšší než slide označí slide k posouvání', () => {
    expect(paginate([unit('long')], { long: 2000 }, { facts: 0 }, 800, 1)[0].overflow).toBe(true);
  });
});
