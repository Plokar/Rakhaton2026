// Klip „Okno pro projektor na míru“ (5 s, vertikální): úzké okno projektoru P04 jako vyskakovací okno.
// Preset pneumologa (seznam ze schůzky 17. 10., preset pneumolog-plice): viditelné skryté údaje vybuchnou
// na skleněné střepy a zbylé dosednou na svá místa → skutečný stav aplikace „upraveno u pacienta“.
// Textury: scripts/capture_pj_v.mjs [dark|light] → public/textures/pjv-<téma>/ (2×, okno 528 × 940 CSS px).
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { SfxTrack, type Sfx } from '../common/audio';
import { EASE } from '../lib/Polish';
import { mulberry32 } from '../lib/rand';
import { C, iv, rgba } from '../theme';
import DARK from '../../public/textures/pjv-dark/pjv.json';
import LIGHT from '../../public/textures/pjv-light/pjv.json';

export const PJ_TOTAL = 150;
export const PJ_W = 1056; // = okno 528 CSS px × 2
export const PJ_H = 1880;
type Theme = 'dark' | 'light';
const DATA = { dark: DARK, light: LIGHT };
const BG = { dark: { card: '#111a24' }, light: { card: '#ffffff' } }; // změřeno ze snímků

type Rect = { x: number; y: number; w: number; h: number };
type Cell = Rect & { key: string };
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

// ── časování (30 fps): 10 výbuchů zrychluje (R2), pak dosednutí a krátký klid ──
const ORDER = ['Zátěžový test (VO2max), ppo < 60 %', 'ppoFEV1', 'ppoDLCO', 'Alergie', 'Komorbidity', 'Sodík', 'CRP', 'CEA', 'Leukocyty', 'Neutrofily absolutně'];
const GAPS = [11, 9, 8, 7, 6, 5, 4, 4, 4];
const FIRST = 12;
const T = { reflow: 86, swap: [122, 130] } as const;
const BOOM_AT = ORDER.map((_, i) => FIRST + GAPS.slice(0, i).reduce((a, b) => a + b, 0));

/** Výřez vysoké textury (v ní je celý seznam bez posouvání) v prostoru okna. */
const crop = (src: string, x: number, y: number): React.CSSProperties => ({
  backgroundImage: `url(${src})`, backgroundSize: '528px 2600px', backgroundPosition: `${-x}px ${-y}px`, backgroundRepeat: 'no-repeat',
});

// ── výbuch: skleněné střepy (trojúhelníky z textury buňky) + rázová vlna + jiskry ──
type Shard = { pts: [number, number][]; cx: number; cy: number; vx: number; vy: number; spin: number; tx: number; ty: number; life: number };
const shardsOf = (c: Cell, seed: number): Shard[] => {
  const rnd = mulberry32(seed * 97 + 13);
  const cols = Math.max(4, Math.round(c.w / 34)), rows = 2;
  // mřížka bodů s posunutými vnitřními vrcholy → nepravidelné trojúhelníky (souřadnice v buňce)
  const P = Array.from({ length: cols + 1 }, (_, i) => Array.from({ length: rows + 1 }, (_, j) => {
    const edgeX = i === 0 || i === cols, edgeY = j === 0 || j === rows;
    return [(i + (edgeX ? 0 : (rnd() - 0.5) * 0.7)) * (c.w / cols), (j + (edgeY ? 0 : (rnd() - 0.5) * 0.5)) * (c.h / rows)] as [number, number];
  }));
  const out: Shard[] = [];
  for (let i = 0; i < cols; i++) for (let j = 0; j < rows; j++) {
    const q = [P[i][j], P[i + 1][j], P[i + 1][j + 1], P[i][j + 1]];
    const tris = rnd() < 0.5 ? [[q[0], q[1], q[2]], [q[0], q[2], q[3]]] : [[q[0], q[1], q[3]], [q[1], q[2], q[3]]];
    for (const pts of tris) {
      const cx = (pts[0][0] + pts[1][0] + pts[2][0]) / 3, cy = (pts[0][1] + pts[1][1] + pts[2][1]) / 3;
      const dx = (cx - c.w / 2) / (c.w / 2), dy = (cy - c.h / 2) / (c.h / 2);
      out.push({
        pts, cx, cy,
        vx: dx * (2.6 + rnd() * 3.6) + (rnd() - 0.5) * 2.4, vy: dy * 1.8 - (1.4 + rnd() * 3.4),
        spin: (rnd() - 0.5) * 50, tx: (rnd() - 0.5) * 160, ty: (rnd() - 0.5) * 160, life: 22 + rnd() * 14,
      });
    }
  }
  return out;
};

const Explosion: React.FC<{ f: number; c: Cell; at: number; seed: number; src: string; shards: Shard[] }> = ({ f, c, at, seed, src, shards }) => {
  const t = f - at;
  if (t < -5 || t > 40) return null;
  const cx = c.x + c.w / 2, cy = c.y + c.h / 2;
  if (t < 0) {
    // předzvěst: buňka se rozsvítí a nadechne
    const a = iv(t, [-5, -1], [0, 1], EASE.exit);
    return (
      <div style={{
        position: 'absolute', left: c.x, top: c.y, width: c.w, height: c.h, ...crop(src, c.x, c.y),
        transform: `scale(${1 + 0.05 * a})`, boxShadow: `0 0 ${18 * a}px ${rgba(C.teal, 0.7 * a)}, inset 0 0 0 1.5px ${rgba('#dffffa', 0.9 * a)}`,
        filter: `brightness(${1 + 0.6 * a})`, zIndex: 5,
      }} />
    );
  }
  const g = 0.3;
  const ring = iv(t, [0, 14], [0, 1], EASE.out);
  const rnd = mulberry32(seed * 31 + 7);
  return (
    <>
      <div style={{ position: 'absolute', left: c.x - 6, top: c.y - 6, width: c.w + 12, height: c.h + 12, borderRadius: 10, background: '#e9fffb', opacity: iv(t, [0, 1, 5], [0.7, 0.45, 0]), filter: 'blur(5px)', zIndex: 6 }} />
      <div style={{
        position: 'absolute', left: cx - (c.w / 2 + 40) * (0.6 + 0.6 * ring), top: cy - (c.h / 2 + 30) * (0.6 + 0.9 * ring),
        width: (c.w + 80) * (0.6 + 0.6 * ring), height: (c.h + 60) * (0.6 + 0.9 * ring), borderRadius: '50%',
        border: `2px solid ${rgba(C.teal, 0.75 * (1 - ring))}`, boxShadow: `0 0 18px ${rgba(C.teal, 0.45 * (1 - ring))}`, zIndex: 6,
      }} />
      {shards.map((s, i) => {
        if (t > s.life) return null;
        const p = t / s.life, hot = 1 - Math.min(1, t / 7);
        const dx = s.vx * t, dy = s.vy * t + 0.5 * g * t * t;
        const poly = s.pts.map(([x, y]) => `${x.toFixed(1)}px ${y.toFixed(1)}px`).join(', ');
        return (
          <div key={i} style={{
            position: 'absolute', left: c.x, top: c.y, width: c.w, height: c.h, zIndex: 7, opacity: 1 - p ** 1.8,
            transform: `translate(${dx}px, ${dy}px) perspective(500px) rotateX(${s.tx * p}deg) rotateY(${s.ty * p}deg) rotateZ(${s.spin * p}deg) scale(${1 - 0.45 * p})`,
            transformOrigin: `${s.cx}px ${s.cy}px`, filter: `brightness(${1 + 0.8 * hot}) drop-shadow(0 0 ${3 * hot}px ${rgba(C.teal, 0.9)})`,
          }}>
            <div style={{ position: 'absolute', inset: 0, ...crop(src, c.x, c.y), clipPath: `polygon(${poly})` }} />
          </div>
        );
      })}
      {Array.from({ length: 12 }, (_, i) => {
        const ang = rnd() * Math.PI * 2, sp = 6 + rnd() * 9, life = 9 + rnd() * 7;
        if (t > life) return null;
        const d = sp * t * (1 - t / (life * 2)), len = sp * 1.6 * (1 - t / life);
        return (
          <div key={`s${i}`} style={{
            position: 'absolute', left: cx + Math.cos(ang) * d, top: cy + Math.sin(ang) * d * 0.55, width: len, height: 1.6, borderRadius: 1,
            background: i % 3 ? '#dffffa' : C.teal, transform: `rotate(${ang}rad)`, transformOrigin: '0 50%', opacity: 1 - t / life, zIndex: 8,
          }} />
        );
      })}
    </>
  );
};

// ── dosednutí: zbylé buňky (a nadpisy skupin) přejedou z plného rozložení do rozložení pneumologa ──
const Sprite: React.FC<{ from: Rect; to: Rect; t: number; srcFrom: string; srcTo: string; bg: string; lift?: number; shadow?: number }> = ({ from, to, t, srcFrom, srcTo, bg, lift = 0, shadow = 0.35 }) => {
  const x = lerp(from.x, to.x, t), y = lerp(from.y, to.y, t) - lift * Math.sin(Math.PI * t);
  const w = lerp(from.w, to.w, t), h = lerp(from.h, to.h, t);
  const fade = iv(t, [0.25, 0.75], [0, 1]);
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, overflow: 'hidden', background: bg,
      boxShadow: t > 0.02 && t < 0.98 ? `0 ${8 * Math.sin(Math.PI * t)}px ${18 * Math.sin(Math.PI * t)}px rgba(0,0,0,${shadow})` : undefined }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width: from.w, height: from.h, ...crop(srcFrom, from.x, from.y), opacity: 1 - fade }} />
      <div style={{ position: 'absolute', left: 0, top: 0, width: to.w, height: to.h, ...crop(srcTo, to.x, to.y), opacity: fade }} />
    </div>
  );
};

export const ProjectorPreset: React.FC<{ theme: Theme }> = ({ theme }) => {
  const f = useCurrentFrame();
  const D = DATA[theme], bg = BG[theme].card;
  const tex = (n: string) => staticFile(`textures/pjv-${theme}/${n}.png`);
  const FULL_T = tex('full_tall'), MINE_T = tex('mine_tall');
  const full = D.full_tall.cells as Cell[], mine = D.mine_tall.cells as Cell[];
  const mineBy = new Map(mine.map((c) => [c.key, c]));
  const mineIdx = new Map(mine.map((c, i) => [c.key, i]));
  const clip = D.full_base.clip as Rect;
  const boom = ORDER.map((key, i) => ({ c: full.find((x) => x.key === key)!, at: BOOM_AT[i] }));
  const shards = React.useMemo(() => boom.map((b, i) => shardsOf(b.c, i + 1)), [theme]); // eslint-disable-line react-hooks/exhaustive-deps
  const before = f < T.reflow + 4;
  const mineOn = iv(f, [T.swap[0], T.swap[1]], [0, 1]);
  const k = iv(f, [T.reflow, T.reflow + 26], [0, 1], EASE.smooth);
  const sfx: Sfx[] = [
    { from: boom[0].at, src: 'glass-hit-cine.mp3', volume: 0.42, dur: 60, note: 'první výbuch' },
    ...boom.slice(1).map((b, i): Sfx => ({ from: b.at, src: i % 2 ? 'sparkle-poof-hit.mp3' : 'hit-weak.mp3', volume: Math.max(0.18, 0.42 - i * 0.025), dur: 26, note: `výbuch ${b.c.key}` })),
    { from: T.reflow, src: 'whoosh-swirl.mp3', volume: 0.3, dur: 50, note: 'údaje dosednou' },
    { from: T.swap[0], src: 'sparkle-touch.mp3', volume: 0.22, dur: 28, note: 'okno pneumologa' },
  ];
  return (
    <AbsoluteFill style={{ background: theme === 'dark' ? '#172230' : '#edf1f5' }}>
      <Img src={MINE_T} style={{ position: 'absolute', width: 1, height: 1, opacity: 0 }} />
      <Img src={tex('mine_base')} style={{ position: 'absolute', width: 1, height: 1, opacity: 0 }} />
      <div style={{ position: 'absolute', width: 528, height: 940, zoom: 2, overflow: 'hidden', opacity: iv(f, [0, 5], [0, 1]) }}>
        {/* hlavička a otázka jsou v obou stavech stejné: spodní snímek drží, dokud ho nenahradí cílový */}
        {f <= T.swap[1] && <Img src={tex('full_base')} style={{ position: 'absolute', left: 0, top: 0, width: 528, height: 940 }} />}
        {/* posuvná oblast klíčových údajů: díry po výbuších, pak dosednutí (ořez na okraj oblasti) */}
        <div style={{ position: 'absolute', left: clip.x, top: clip.y, width: clip.w, height: clip.h, overflow: 'hidden' }}>
          <div style={{ position: 'absolute', left: -clip.x, top: -clip.y, width: 528, height: 2600 }}>
            {before && boom.filter((b) => f >= b.at).map((b) => (
              <div key={`h${b.c.key}`} style={{ position: 'absolute', left: b.c.x, top: b.c.y, width: b.c.w, height: b.c.h, background: bg }} />
            ))}
            {f >= T.reflow - 6 && f <= T.swap[1] && (
              <>
                <div style={{ position: 'absolute', left: clip.x, top: clip.y, width: clip.w, height: 2600, background: theme === 'dark' ? '#172230' : '#edf1f5' }} />
                <div style={{ position: 'absolute', left: 8, top: clip.y, width: 512, height: 2600, borderRadius: 16, background: bg }} />
                <Sprite from={D.full_tall.title as Rect} to={D.mine_tall.title as Rect} t={k} srcFrom={FULL_T} srcTo={MINE_T} bg={bg} />
                {(D.full_tall.groups as (Rect & { label: string })[]).map((g) => {
                  const m = (D.mine_tall.groups as (Rect & { label: string })[]).find((x) => x.label === g.label);
                  return m ? <Sprite key={g.label} from={g} to={m} t={k} srcFrom={FULL_T} srcTo={MINE_T} bg={bg} /> : null;
                })}
                {full.filter((c) => mineBy.has(c.key)).map((c) => {
                  const i = mineIdx.get(c.key) ?? 0;
                  const t = iv(f, [T.reflow + i * 0.5, T.reflow + i * 0.5 + 26], [0, 1], EASE.swift);
                  return <Sprite key={c.key} from={c} to={mineBy.get(c.key)!} t={t} srcFrom={FULL_T} srcTo={MINE_T} bg={bg} lift={5} shadow={theme === 'dark' ? 0.35 : 0.12} />;
                })}
              </>
            )}
          </div>
        </div>
        {mineOn > 0 && <Img src={tex('mine_base')} style={{ position: 'absolute', left: 0, top: 0, width: 528, height: 940, opacity: mineOn }} />}
        {boom.map((b, i) => <Explosion key={b.c.key} f={f} c={b.c} at={b.at} seed={i + 1} src={FULL_T} shards={shards[i]} />)}
      </div>
      <SfxTrack items={sfx} />
    </AbsoluteFill>
  );
};
