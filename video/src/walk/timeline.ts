// Film B v2.1 · PRŮCHOD „Jeden pacient, jedno jednání“ (FILM_SCENAR §5): jeden souvislý záběr.
// Gramatika kamery (zpětná vazba 17. 10.): každý okamžik je BUĎ navigace (kamera sleduje myš až do kliknutí),
// NEBO čtení (kamera stojí na zvýrazněné části, myš zmizí, reflektor se rozsvítí až po zastavení kamery). Nikdy obojí.
// Souřadnice = CSS px snímků v public/textures/v2 (stránky 1920 široké), snímky = absolutní čas filmu.
import type { Sfx } from '../common/audio';
import { logoSfx } from '../common/LogoReveal';

export const WALK_TOTAL = 2700;
export const INTRO_LOGO = 30;
export const OUTRO = 2530; // začátek závěru (logo + QR, 5,5 s)
export const OUTRO_LOGO = 2556;
export const COMP = { in: [1270, 1302], out: [1445, 1477], push: [1345, 1395, 1420, 1440] } as const; // 05: notebook + plátno

export const T = {
  stageIn: [100, 124], stageOut: [2512, 2536],
  ask: { wait: [752, 772], answer: 772 },
  drag: { from: 1122, to: 1152 },
  marker: [1556, 1572], drawer: [1523, 1736],
  esc: 1724, chatMsg: 1850,
  rec: [2018, 2128], wave: [2026, 2110], keyZ: 2116,
  confirmed: 2268, iris: [2276, 2530],
} as const;

export const CHAPTERS = [
  { n: '01', title: 'Rychlý přehled za 30 sekund', from: 120, to: 420 },
  { n: '02', title: 'Podklad podle odbornosti', from: 420, to: 710 },
  { n: '03', title: 'Otázka nad případem', from: 710, to: 980 },
  { n: '04', title: 'Okno pro projektor na míru', from: 980, to: 1255 },
  { n: '05', title: 'Jednání a plátno v sále', from: 1255, to: 1485 },
  { n: '06', title: 'Každé tvrzení se zdrojem', from: 1485, to: 1725 },
  { n: '07', title: 'Chat komise u pacienta', from: 1725, to: 1985 },
  { n: '08', title: 'AI zapisovatel', from: 1985, to: 2255 },
  { n: '09', title: 'Zápis do nemocnice (IRIS)', from: 2255, to: 2530 },
];

type Rect = { x: number; y: number; w: number; h: number };
export type Layer = {
  src: string; from: number; to: number; in?: number; out?: number;
  anim?: 'fade' | 'pop' | 'slideR' | 'rise' | 'reveal';
  clip?: Rect; hole?: Rect; origin?: [number, number]; top?: number; // top = y stránky, kde textura začíná (ořezané snímky)
};
const R = (x: number, y: number, w: number, h: number): Rect => ({ x, y, w, h });
const DIALOG = R(448, 108, 1024, 865);

// Vrstvy obrazovek (dřív = níž). Přechody napodobují aplikaci: menu „pop“, boční panel a chat zprava, stránka fade + rise.
export const LAYERS: Layer[] = [
  { src: 'cal_base', from: 100, to: 199, in: 24, out: 4 },
  { src: 'cal_hover', from: 197, to: 256, in: 4, out: 8 },
  { src: 'cal_sheet', from: 248, to: 412, in: 10, out: 8, clip: R(0, 0, 1480, 1080) },
  { src: 'cal_sheet', from: 248, to: 412, in: 14, out: 8, clip: R(1480, 0, 440, 1080), anim: 'slideR' },
  { src: 'cal_menu', from: 221, to: 251, in: 7, out: 4, clip: R(986, 539, 224, 157), anim: 'pop', origin: [224, 0] },
  { src: 'cal_menu_hover', from: 236, to: 251, in: 3, out: 4, clip: R(986, 539, 224, 157) },
  { src: 'det_me_full', from: 404, to: 1012, in: 10, out: 6, anim: 'rise' },
  { src: 'det_ask_loading', from: 751, to: 1012, in: 3, out: 6, clip: R(600, 2830, 1220, 139), top: 2700 },
  { src: 'det_ask_answer', from: 772, to: 1012, in: 22, out: 6, clip: R(600, 2830, 1220, 278), anim: 'reveal', top: 2700 },
  { src: 'meet', from: 1008, to: 2130, in: 8, out: 8, anim: 'rise' },
  { src: 'ed0', from: 1042, to: 1252, in: 8, out: 7, hole: DIALOG },
  { src: 'ed0', from: 1042, to: 1076, in: 9, out: 2, clip: DIALOG, anim: 'pop', origin: [512, 432] },
  { src: 'ed1', from: 1074, to: 1102, in: 3, out: 2, clip: DIALOG },
  { src: 'ed2', from: 1100, to: 1156, in: 3, out: 2, clip: DIALOG },
  { src: 'ed3', from: 1153, to: 1252, in: 5, out: 7, clip: DIALOG, anim: 'pop', origin: [512, 432] },
  { src: 'drawer', from: 1523, to: 1736, in: 12, out: 10, clip: R(1536, 0, 384, 1080), anim: 'slideR' },
  { src: 'chat3', from: 1762, to: 1862, in: 8, out: 2, hole: R(1580, 129, 340, 952) },
  { src: 'chat3', from: 1762, to: 1862, in: 12, out: 2, clip: R(1580, 129, 340, 952), anim: 'slideR' },
  { src: 'chat4', from: 1859, to: 2130, in: 1, out: 8 },
  { src: 'chat4', from: 1850, to: 2130, in: 10, out: 8, clip: R(1596, 464, 308, 78), anim: 'rise' },
  { src: 'record', from: 2122, to: 2536, in: 10, out: 14, anim: 'rise' },
];

export const pageHAt = (f: number) => (f < 406 ? 1080 : f < 1010 ? 3108 : f < 2124 ? 1080 : 1543);

// Záběry kamery: od daného snímku platí, dokud nepřijde další (žádné míchání). Přechod mezi nimi vyhladí pružina.
// follow = sleduje myš (navigace), frame = stojí na bodě (čtení / akce v dialogu).
export type Shot = { f: number; zoom: number } & ({ mode: 'follow' } | { mode: 'frame'; x: number; y: number });
export const SHOTS: Shot[] = [
  { f: 0, mode: 'frame', x: 960, y: 540, zoom: 1 },
  { f: 165, mode: 'follow', zoom: 1.5 },
  { f: 246, mode: 'frame', x: 1700, y: 300, zoom: 1.75 }, // čtení: hlavička rychlého přehledu
  { f: 356, mode: 'follow', zoom: 1.45 },
  { f: 404, mode: 'frame', x: 1000, y: 430, zoom: 1.25 },
  { f: 448, mode: 'frame', x: 1205, y: 2215, zoom: 1.5 }, // čtení: Pro vás
  { f: 696, mode: 'frame', x: 1204, y: 2905, zoom: 1.5 },
  { f: 772, mode: 'frame', x: 1204, y: 2990, zoom: 1.62 }, // čtení: odpověď AI
  { f: 978, mode: 'frame', x: 900, y: 420, zoom: 1.3 },
  { f: 1012, mode: 'frame', x: 1150, y: 450, zoom: 1.25 },
  { f: 1044, mode: 'frame', x: 960, y: 540, zoom: 1.12 }, // akce v dialogu: kamera stojí
  { f: 1160, mode: 'frame', x: 1246, y: 540, zoom: 1.55 }, // čtení: náhled okna projektoru
  { f: 1218, mode: 'frame', x: 1250, y: 700, zoom: 1.35 },
  { f: 1250, mode: 'frame', x: 960, y: 540, zoom: 1 },
  { f: 1478, mode: 'frame', x: 930, y: 430, zoom: 1.6 },
  { f: 1530, mode: 'frame', x: 1700, y: 380, zoom: 1.8 }, // čtení: zdroj
  { f: 1730, mode: 'frame', x: 1350, y: 300, zoom: 1.35 },
  { f: 1770, mode: 'frame', x: 1720, y: 440, zoom: 1.75 }, // čtení: chat
  { f: 1980, mode: 'frame', x: 600, y: 780, zoom: 1.45 },
  { f: 2124, mode: 'frame', x: 1088, y: 720, zoom: 1.45 }, // čtení: AI návrh
  { f: 2252, mode: 'frame', x: 1088, y: 250, zoom: 1.75 }, // čtení: potvrzeno, IRIS, export
];

// Myš (souřadnice stránky). Je vidět jen při navigaci a akci; při čtení zmizí.
export const CURSOR = [
  { f: 150, x: 1700, y: 960 }, { f: 200, x: 1060, y: 524 }, { f: 214, x: 1196, y: 521 }, { f: 238, x: 1098, y: 557 },
  { f: 252, x: 1150, y: 600 }, { f: 356, x: 1500, y: 700 }, { f: 396, x: 1551, y: 1050 }, { f: 440, x: 434, y: 203 },
  { f: 450, x: 434, y: 260 }, { f: 712, x: 1500, y: 3010 }, { f: 742, x: 800, y: 2924 }, { f: 758, x: 900, y: 2960 },
  { f: 982, x: 700, y: 400 }, { f: 1004, x: 434, y: 92 }, { f: 1036, x: 1572, y: 270 }, { f: 1068, x: 931, y: 565 },
  { f: 1094, x: 931, y: 733 }, { f: 1118, x: 481, y: 817 }, { f: 1122, x: 481, y: 817 }, { f: 1152, x: 481, y: 439 },
  { f: 1162, x: 520, y: 439 }, { f: 1218, x: 1150, y: 800 }, { f: 1238, x: 1362, y: 941 }, { f: 1262, x: 1554, y: 92 },
  { f: 1272, x: 1554, y: 92 }, { f: 1490, x: 1300, y: 600 }, { f: 1515, x: 861, y: 358 }, { f: 1528, x: 900, y: 380 },
  { f: 1736, x: 1500, y: 600 }, { f: 1756, x: 1443, y: 92 }, { f: 1768, x: 1450, y: 120 }, { f: 1984, x: 900, y: 700 },
  { f: 2010, x: 400, y: 939 }, { f: 2020, x: 420, y: 939 }, { f: 2380, x: 1300, y: 500 }, { f: 2405, x: 948, y: 247 },
  { f: 2440, x: 1114, y: 247 }, { f: 2475, x: 845, y: 328 }, { f: 2515, x: 845, y: 328 },
];
export const CURSOR_ON: [number, number][] = [
  [150, 252], [356, 452], [712, 760], [982, 1164], [1218, 1274], [1490, 1530], [1736, 1770], [1984, 2022], [2380, 2515],
];
export const CLICKS = [220, 246, 402, 446, 750, 1010, 1042, 1074, 1100, 1122, 1244, 1268, 1521, 1762, 2016];
export const DRAG = { from: T.drag.from, to: T.drag.to, row: R(464, 806, 548, 38), toY: 420 };

// Reflektory jen v záběrech „čtení“, rozsvítí se až po zastavení kamery (~20 snímků po začátku záběru).
export type Spot = Rect & { from: number; to: number; color?: 'teal' | 'amber' | 'red' | 'ai' };
export const SPOTS: Spot[] = [
  { from: 270, to: 322, ...R(1486, 2, 428, 118) },
  { from: 314, to: 354, ...R(1486, 136, 428, 250), color: 'amber' },
  { from: 476, to: 592, ...R(650, 2096, 560, 48), color: 'amber' },
  { from: 488, to: 592, ...R(650, 2178, 560, 48), color: 'red' },
  { from: 592, to: 690, ...R(1218, 1996, 566, 330) },
  { from: 798, to: 972, ...R(626, 2944, 1156, 135), color: 'ai' },
  { from: 1180, to: 1218, ...R(1036, 190, 420, 702) },
  { from: 1550, to: 1718, ...R(1548, 236, 364, 214) },
  { from: 1866, to: 1978, ...R(1592, 460, 316, 86) },
  { from: 2024, to: 2106, ...R(264, 916, 272, 46), color: 'red' },
  { from: 2144, to: 2250, ...R(690, 592, 796, 176), color: 'ai' },
  { from: 2164, to: 2250, ...R(690, 810, 796, 144), color: 'ai' },
  { from: 2272, to: 2384, ...R(680, 170, 640, 52) },
  { from: 2394, to: 2470, ...R(884, 224, 334, 46) },
  { from: 2468, to: 2516, ...R(668, 306, 354, 44) },
];

const click = (f: number, i: number): Sfx => ({ from: f, src: i % 2 ? 'click-b.wav' : 'click-a.wav', volume: i % 2 ? 0.5 : 0.55, dur: 12, note: `klik ${f}` });
export const SFX_B: Sfx[] = [
  ...logoSfx(INTRO_LOGO, 0.8),
  ...CLICKS.map(click),
  { from: T.drag.to + 2, src: 'click-b.wav', volume: 0.35, dur: 12, note: 'puštění řádku' },
  { from: T.esc, src: 'click-a.wav', volume: 0.4, dur: 12, note: 'klávesa Esc' },
  { from: T.keyZ, src: 'click-a.wav', volume: 0.45, dur: 12, note: 'klávesa Z' },
  { from: 248, src: 'swoosh-quick.mp3', volume: 0.12, dur: 24, note: 'boční panel vyjede' },
  { from: 1042, src: 'swoosh-quick.mp3', volume: 0.1, dur: 24, note: 'dialog' },
  { from: COMP.in[0] + 2, src: 'transition-soft.mp3', volume: 0.2, dur: 40, note: 'obraz do notebooku' },
  { from: COMP.in[1] - 4, src: 'power-up-electronic.mp3', volume: 0.12, dur: 40, note: 'plátno se rozsvítí' },
  { from: COMP.out[0] + 2, src: 'transition-soft.mp3', volume: 0.18, dur: 40, note: 'zpět do notebooku' },
  { from: 1523, src: 'swoosh-quick.mp3', volume: 0.12, dur: 24, note: 'panel zdroje' },
  { from: 1762, src: 'swoosh-quick.mp3', volume: 0.1, dur: 24, note: 'chat vyjede' },
  { from: T.chatMsg + 1, src: 'ui-message-pop.mp3', volume: 0.22, dur: 20, note: 'nová zpráva v chatu' },
  { from: T.confirmed, src: 'sparkle.mp3', volume: 0.2, dur: 70, note: 'potvrzeno a zapsáno do IRIS' },
  ...logoSfx(OUTRO_LOGO, 0.8),
  { from: OUTRO_LOGO + 30, src: 'shimmer-sparkle-sweep.mp3', volume: 0.18, dur: 62, note: 'QR kód' },
];
export const WALK_MUSIC_ENV: [number, number][] = [[0, 0], [70, 0.15], [2620, 0.15], [2699, 0]];
