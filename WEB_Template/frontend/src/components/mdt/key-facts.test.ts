import { describe, expect, it } from 'vitest';
import type { ObservationSeries } from '@/types/mdt';
import { buildKeyFacts, compactValue, warningLabel } from './key-facts';

const series = (points: ObservationSeries['points'], code = '718-7'): ObservationSeries => ({ code, label: 'Hemoglobin', unit: 'g/l', points });

describe('buildKeyFacts – laboratoř (normalita jen z referenčního rozmezí, T-383)', () => {
  const lab = (s: ObservationSeries) => buildKeyFacts(null, [s]).facts.find((f) => f.id === `lab:${s.code}`);

  it('poslední hodnota v rozmezí je v normě', () => {
    const f = lab(series([
      { date: '2026-09-01', value: 98, citation: 'P03-lab01-hb', ref_low: 120, ref_high: 160 },
      { date: '2026-10-01', value: 131, citation: 'P03-lab02-hb', ref_low: 120, ref_high: 160 },
    ]));
    expect(f?.status).toBe('normal');
    expect(f?.citations).toEqual(['P03-lab02-hb']);
  });

  it('mimo rozmezí nebo s interpretací H/L je mimo normu', () => {
    expect(lab(series([{ date: '2026-10-01', value: 99, citation: 'x', ref_low: 120, ref_high: 160 }]))?.status).toBe('abnormal');
    expect(lab(series([{ date: '2026-10-01', value: 130, citation: 'x', ref_low: 120, ref_high: 160, interpretation: 'L' }]))?.status).toBe('abnormal');
  });

  it('bez referenčního rozmezí se normalita neodhaduje', () => {
    expect(lab(series([{ date: '2026-10-01', value: 99, citation: 'x' }]))).toBeUndefined();
  });

  it('rozmezí z dřívějšího bodu platí pro poslední hodnotu', () => {
    const f = lab(series([
      { date: '2026-09-01', value: 140, citation: 'a', ref_low: 120, ref_high: 160 },
      { date: '2026-10-01', value: 170, citation: 'b' },
    ]));
    expect(f?.status).toBe('abnormal');
  });
});

describe('compactValue a warningLabel', () => {
  it('ISO datum česky, řádky na jeden řádek, bez nadpisu', () => {
    expect(compactValue('Histologie: adenokarcinom\n- G2\n- 2026-03-10')).toBe('adenokarcinom; G2; 10. 3. 2026');
  });
  it('popisek varování se nezdvojí', () => {
    expect(warningLabel({ kind: 'missing', title: 'Chybí: Deficit DPD' })).toEqual({ label: 'Chybí', text: 'Deficit DPD' });
  });
});
