// Film A · HOOK „Pět minut“: jediný zdroj pravdy pro časování (FILM_SCENAR §4).
// Hudba Mixkit #598 „We Will Get It“ od 41,92 s → drop skladby (52,92 s) = f330.
// Naměřené údery po dropu (onsets.py): 330 · 399 · 423 · 518 · 610 · 704 · 773 · 797 · 892.
import type { Sfx, VoSlot } from '../common/audio';
import { logoSfx } from '../common/LogoReveal';

export const HOOK_TOTAL = 900;
export const HOOK_MUSIC_OFFSET = Math.round(41.92 * 30); // snímky přeskočené na začátku skladby

export const S = {
  pulse: { from: 0, to: 110 }, // A1 tep
  flood: { from: 105, to: 300 }, // A2 lavina
  breath: { from: 300, to: 330 }, // A3 nádech (imploze)
  ignite: { from: 330, to: 420 }, // A4 zážeh (DROP)
  proof: { from: 420, to: 600 }, // A5 důkaz
  rules: { from: 600, to: 700 }, // A6 semafor
  doctor: { from: 700, to: 775 }, // A7 lékař
  brand: { from: 773, to: 900 }, // A8 značka
} as const;

export const BEAT = { drop: 330, b1: 399, b2: 423, b3: 518, b4: 610, b5: 704, b6: 773, b7: 797 } as const;
export const HEARTBEATS = [8, 40, 72];
export const ROW_LAND = [BEAT.b4, BEAT.b4 + 23, BEAT.b4 + 46]; // tři řádky semaforu
export const CLICK = BEAT.b5; // stisk „Potvrdit“

// Hudba: náběh, tlak, nasátí před dropem, drop, doběh pod logem.
export const MUSIC_ENV: [number, number][] = [
  [0, 0], [45, 0.3], [290, 0.36], [316, 0.06], [329, 0.06], [330, 0.5], [345, 0.6], [760, 0.6], [850, 0.42], [899, 0],
];

// SFX přibité na děj (S2). Údery s náběhem: from = cílový snímek − zpoždění vrcholu souboru.
const ticks: Sfx[] = Array.from({ length: 7 }, (_, i) => ({
  from: S.flood.from + i * 30, src: 'clock-tick-single.mp3', volume: 0.55 + i * 0.07, dur: 25, note: `odpočet ${5 * 60 - i}`,
}));
export const SFX_A: Sfx[] = [
  ...HEARTBEATS.map((f, i) => ({ from: f, src: 'heartbeat-single.mp3', volume: 0.95 - i * 0.05, dur: 33, note: `tep ${i + 1}` })),
  ...ticks,
  { from: 196, src: 'riser-synth.wav', volume: 0.7, dur: 126, note: 'gradace do dropu (končí f322)' },
  { from: 256, src: 'whoosh-reverse.wav', volume: 0.55, dur: 74, note: 'nasátí do bodu (vrchol f330)' },
  { from: 304, src: 'impact-epic-trailer.mp3', volume: 0.7, dur: 140, note: 'DROP (vrchol ~f330)' },
  { from: BEAT.drop, src: 'sub-drop.wav', volume: 0.45, dur: 66, note: 'sub pod drop' },
  { from: 334, src: 'whoosh-big.mp3', volume: 0.38, dur: 70, note: 'panel stoupá z hloubky' },
  { from: BEAT.b1, src: 'sparkle.mp3', volume: 0.3, dur: 60, note: 'panel odhalen' },
  { from: 430, src: 'click-camera.mp3', volume: 0.32, dur: 12, note: 'zaostření na PS 0 / pac. 1' },
  { from: 470, src: 'data-scan.mp3', volume: 0.3, dur: 40, note: 'skenovací linka přes údaje' },
  { from: 503, src: 'swoosh-quick.mp3', volume: 0.35, dur: 24, note: 'karta zdroje vlétá' },
  { from: BEAT.b3, src: 'light-sweep-magic.mp3', volume: 0.36, dur: 60, note: 'karta zdroje dosedne + lesk' },
  { from: 596, src: 'whoosh-fast.mp3', volume: 0.3, dur: 40, note: 'přechod na semafor' },
  ...ROW_LAND.map((f, i) => ({ from: f, src: 'bass-hit-short.mp3', volume: 0.7 - i * 0.07, dur: 30, note: `řádek semaforu ${i + 1}` })),
  { from: 694, src: 'swoosh-quick.mp3', volume: 0.22, dur: 24, note: 'řádky odcházejí' },
  { from: CLICK, src: 'click-camera.mp3', volume: 0.65, dur: 12, note: 'stisk Potvrdit' },
  { from: CLICK - 13, src: 'impact-zoom-quick.mp3', volume: 0.55, dur: 36, note: 'razítko dopadne (vrchol f704)' },
  ...logoSfx(BEAT.b6), // značka: stejné SFX jako logo v průchodu (common/LogoReveal)
];

export const VO_A: VoSlot[] = [
  { file: 'A_01.mp3', from: 18, maxDur: 90, text: 'Pět specialistů. Pět minut. Jeden pacient.' },
  { file: 'A_02.mp3', from: 126, maxDur: 135, text: 'A za ním roky zpráv, nálezů… a rozporů.' },
  { file: 'A_03.mp3', from: 348, maxDur: 90, text: 'MedTeam připraví celý případ za pár sekund.' },
  { file: 'A_04.mp3', from: 450, maxDur: 120, text: 'Každé tvrzení má zdroj. Každý rozpor je na očích.' },
  { file: 'A_05.mp3', from: 612, maxDur: 84, text: 'Semafor léčby počítají pravidla. Ne AI.' },
  { file: 'A_06.mp3', from: 705, maxDur: 54, text: 'Rozhoduje vždy lékař.' },
  { file: 'A_07.mp3', from: 798, maxDur: 78, text: 'MedTeam. Copilot onkologické komise.' },
];
