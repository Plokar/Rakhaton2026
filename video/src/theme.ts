// Vizuální tokeny filmů = tmavý režim aplikace (WEB_Template/frontend/src/app/globals.css) + barvy loga.
// Písma jsou lokálně v public/fonts (Google Fonts, OFL): render nezávisí na síti.
import { continueRender, delayRender, interpolate, staticFile } from 'remotion';

const FACES: [string, string, string][] = [
  ['Inter', 'inter-latin-ext.woff2', 'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF'],
  ['Inter', 'inter-latin.woff2', 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD'],
  ['Montserrat', 'montserrat-latin-ext.woff2', 'U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C4, U+2113, U+2C60-2C7F, U+A720-A7FF'],
  ['Montserrat', 'montserrat-latin.woff2', 'U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, U+2215, U+FEFF, U+FFFD'],
];
const fontsReady = delayRender('lokální písma Inter + Montserrat');
Promise.all(FACES.map(([family, file, unicodeRange]) =>
  new FontFace(family, `url('${staticFile(`fonts/${file}`)}') format('woff2')`, { weight: '100 900', unicodeRange }).load().then((ff) => document.fonts.add(ff)),
)).then(() => continueRender(fontsReady), (e) => { console.error(e); continueRender(fontsReady); });

export const INTER = 'Inter, system-ui, sans-serif';
export const MONT = 'Montserrat, Inter, sans-serif';
export const MONO = '"JetBrains Mono", "Cascadia Mono", Consolas, monospace';

export const C = {
  void: '#04070b', // hlubší než aplikace: sál kolem plátna
  bg: '#0b1118',
  card: '#111a24',
  border: '#263547',
  ink: '#f1f5f9',
  ink2: '#94a3b8',
  ink3: '#5b6b80',
  teal: '#2dd4bf',
  tealDeep: '#0f766e',
  ai: '#a78bfa',
  amber: '#fbbf24',
  red: '#f87171',
  green: '#34d399',
  gray: '#94a3b8',
  logoRed: '#c8102e',
  logoNavy: '#17375e',
  logoTeal: '#3fb4c0',
};

export const FPS = 30;
export const W = 1920;
export const H = 1080;

export const rgba = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

const clampOpt = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
/** interpolate s ořezem na obou koncích (nejčastější volání ve filmu). */
export const iv = (f: number, input: number[], output: number[], easing?: (t: number) => number) =>
  interpolate(f, input, output, { ...clampOpt, easing });
