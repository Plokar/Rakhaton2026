// Animace loga z hooku (A8) jako sdílená věc: stejné časování i zvuk v hooku i v průchodu.
// start = snímek, kdy svislé rameno kříže začne padat; vše ostatní je relativně k němu.
import type { Sfx } from './audio';
import type { LogoState } from './Logo';
import { EASE } from '../lib/Polish';
import { iv } from '../theme';

export const LOGO = { bubble: 24, word: [33, 63], sheen: [65, 89], calm: 77, glow: 57 } as const;

export const logoState = (f: number, s: number): LogoState => {
  const b = s + LOGO.bubble;
  const calm = iv(f, [b + 10, s + LOGO.calm], [1, 0]);
  return {
    crossV: iv(f, [s, s + 8, s + 13], [0, 1.015, 1], EASE.out),
    crossH: iv(f, [s + 6, s + 16], [0, 1], EASE.snappy),
    bubble: iv(f, [b, b + 8, b + 14], [0, 1.1, 1], EASE.out),
    bars: Array.from({ length: 6 }, (_, i) => iv(f, [b + 3 + i * 2, b + 11 + i * 2], [0, 1], EASE.overshoot) * (1 + 0.38 * Math.sin((f - b) * 0.5 + i * 1.3) * calm)),
    word: iv(f, [s + LOGO.word[0], s + LOGO.word[1]], [0, 1], EASE.smooth),
    wordGlow: iv(f, [s + LOGO.sheen[0], s + LOGO.sheen[1]], [0, 1]),
  };
};

/** Zvuk loga: velký úder (vrchol ~ start), cvaknutí při dosednutí kříže, sub, jiskra bubliny, lesk wordmarku. */
export const logoSfx = (s: number, k = 1): Sfx[] => [
  { from: s - 38, src: 'impact-movie-epic.mp3', volume: 0.85 * k, dur: 165, note: 'značka (vrchol ~ dopad kříže)' },
  { from: s + 8, src: 'lock-digital.mp3', volume: 0.5 * k, dur: 30, note: 'switch: kříž dosedne' },
  { from: s + 12, src: 'sub-drop.wav', volume: 0.5 * k, dur: 66, note: 'kříž dosedne' },
  { from: s + LOGO.bubble, src: 'sparkle.mp3', volume: 0.32 * k, dur: 90, note: 'bublina vyskočí' },
  { from: s + LOGO.sheen[0], src: 'shimmer-sparkle-sweep.mp3', volume: 0.26 * k, dur: 62, note: 'lesk přes wordmark' },
];
