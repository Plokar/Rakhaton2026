// Svět průchodu: snímky aplikace v prostoru stránky, kamera, která sleduje myš (kriticky tlumená pružina,
// deterministicky přepočtená od snímku 0), jemný 3D náklon podle rychlosti, reflektor a kurzor.
// Zvětšení přes CSS zoom (ne transform scale), aby písmo zůstalo ostré (aesthetic-rules Q2).
import React from 'react';
import { AbsoluteFill, Img, staticFile } from 'remotion';
import { Cursor, cursorAt } from '../common/Cursor';
import { EASE } from '../lib/Polish';
import { C, INTER, MONO, iv, rgba } from '../theme';
import { CLICKS, CURSOR, CURSOR_ON, DRAG, LAYERS, SHOTS, SPOTS, T, pageHAt, type Layer, type Spot } from './timeline';

// ── kamera: záběr platí od svého snímku do dalšího (žádné míchání myš × bod), pružina jen vyhladí přechod ──
const shotAt = (f: number) => { let sh = SHOTS[0]; for (const x of SHOTS) if (x.f <= f) sh = x; return sh; };
const camTarget = (f: number) => {
  const sh = shotAt(f);
  const zoom = sh.zoom;
  const c = cursorAt(CURSOR, f);
  let x = sh.mode === 'follow' ? c.x : sh.x;
  let y = sh.mode === 'follow' ? c.y : sh.y;
  const hw = 960 / zoom, hh = 540 / zoom, ph = pageHAt(f);
  const mx = hw * 0.6, my = hh * 0.35; // smí přejet okraj stránky (okno „pluje“ v sále), aby šlo vycentrovat boční panel
  x = zoom > 1 ? Math.min(Math.max(x, hw - mx), 1920 - hw + mx) : 960;
  y = zoom > 1 ? Math.min(Math.max(y, hh - my), Math.max(hh, ph - hh + my)) : Math.min(Math.max(y, 540), ph - 540);
  return { x, y, zoom };
};
type Cam = { cx: number; cy: number; zoom: number; vx: number; vy: number; vz: number };
const CACHE: Cam[] = [];
/** Pružina (ω = 0,12 rad/snímek, kriticky tlumená, klidný dojezd) iterovaná od 0 → stejný výsledek při každém renderu. */
export const camAt = (f: number): Cam => {
  if (CACHE[f]) return CACHE[f];
  const W = 0.12, WZ = 0.1;
  let s = CACHE.length ? CACHE[CACHE.length - 1] : (() => { const t = camTarget(0); return { cx: t.x, cy: t.y, zoom: t.zoom, vx: 0, vy: 0, vz: 0 }; })();
  for (let i = CACHE.length; i <= f; i++) {
    const t = camTarget(i);
    const ax = W * W * (t.x - s.cx) - 2 * W * s.vx;
    const ay = W * W * (t.y - s.cy) - 2 * W * s.vy;
    const az = WZ * WZ * (t.zoom - s.zoom) - 2 * WZ * s.vz;
    s = { cx: s.cx + s.vx + ax, cy: s.cy + s.vy + ay, zoom: s.zoom + s.vz + az, vx: s.vx + ax, vy: s.vy + ay, vz: s.vz + az };
    CACHE[i] = s;
  }
  return CACHE[f];
};

// ── vrstvy ──
const LayerView: React.FC<{ l: Layer; f: number }> = ({ l, f }) => {
  if (f < l.from || f > l.to) return null;
  const pin = iv(f, [l.from, l.from + (l.in ?? 6)], [0, 1], EASE.out);
  const pout = iv(f, [l.to - (l.out ?? 6), l.to], [1, 0], EASE.exit);
  const src = staticFile(`textures/v2/${l.src}.png`);
  const r = l.clip;
  let transform: string | undefined;
  let clipPath: string | undefined;
  let opacity = pin * pout;
  if (l.anim === 'pop') { transform = `scale(${0.96 + 0.04 * pin})`; }
  if (l.anim === 'slideR' && r) { transform = `translateX(${r.w * (1 - pin) + r.w * (1 - pout)}px)`; opacity = Math.min(1, pin * 3) * pout; }
  if (l.anim === 'rise') { transform = `translateY(${14 * (1 - pin)}px)`; }
  if (l.anim === 'reveal') { clipPath = `inset(0 0 ${(1 - pin) * 100}% 0)`; opacity = pout; }
  if (l.hole) {
    const h = l.hole;
    clipPath = `polygon(evenodd, 0 0, 1920px 0, 1920px 9999px, 0 9999px, 0 0, ${h.x}px ${h.y}px, ${h.x}px ${h.y + h.h}px, ${h.x + h.w}px ${h.y + h.h}px, ${h.x + h.w}px ${h.y}px, ${h.x}px ${h.y}px)`;
  }
  if (!r) {
    return <Img src={src} style={{ position: 'absolute', left: 0, top: 0, width: 1920, opacity, transform, clipPath }} />;
  }
  return (
    <div style={{
      position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, overflow: 'hidden', opacity, clipPath,
      transform, transformOrigin: l.origin ? `${l.origin[0]}px ${l.origin[1]}px` : undefined,
      boxShadow: l.anim === 'pop' || l.anim === 'slideR' ? '0 24px 60px rgba(0,0,0,0.5)' : undefined,
    }}>
      <Img src={src} style={{ position: 'absolute', left: -r.x, top: (l.top ?? 0) - r.y, width: 1920 }} />
    </div>
  );
};

// ── reflektor ──
const COLORS = { teal: C.teal, amber: C.amber, red: C.red, ai: C.ai };
const Spotlight: React.FC<{ f: number; zoom: number }> = ({ f, zoom }) => {
  const live = SPOTS.map((s) => ({ s, a: iv(f, [s.from, s.from + 12, s.to - 10, s.to], [0, 1, 1, 0], EASE.smooth) })).filter((x) => x.a > 0.001);
  if (!live.length) return null;
  const dim = Math.max(...live.map((x) => x.a));
  const id = `sp${live.map((x) => x.s.from).join('-')}`;
  const pad = 8;
  const rect = (s: Spot) => ({ x: s.x - pad, y: s.y - pad, width: s.w + pad * 2, height: s.h + pad * 2, rx: 12 });
  return (
    <svg width={1920} height={4000} style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible', pointerEvents: 'none' }}>
      <defs>
        <filter id={`${id}f`} x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation={10} /></filter>
        <mask id={id} maskUnits="userSpaceOnUse" x={-400} y={-400} width={2720} height={4800}>
          <rect x={-400} y={-400} width={2720} height={4800} fill="white" />
          {live.map(({ s, a }, i) => <rect key={i} {...rect(s)} fill="black" fillOpacity={a} filter={`url(#${id}f)`} />)}
        </mask>
      </defs>
      <rect x={-400} y={-400} width={2720} height={4800} fill="rgb(4,7,11)" fillOpacity={0.62 * dim} mask={`url(#${id})`} />
      {live.map(({ s, a }, i) => {
        const col = COLORS[s.color ?? 'teal'];
        return <rect key={`o${i}`} {...rect(s)} fill="none" stroke={col} strokeOpacity={0.9 * a} strokeWidth={2.2 / zoom} style={{ filter: `drop-shadow(0 0 ${8 / zoom}px ${rgba(col, 0.7 * a)})` }} />;
      })}
    </svg>
  );
};

// ── přetažení řádku MMR/MSI v editoru okna projektoru ──
const DragRow: React.FC<{ f: number }> = ({ f }) => {
  if (f < DRAG.from - 2 || f > DRAG.to + 2) return null;
  const p = iv(f, [DRAG.from, DRAG.to], [0, 1], EASE.swift);
  const lift = iv(f, [DRAG.from - 2, DRAG.from + 3, DRAG.to - 3, DRAG.to + 2], [0, 1, 1, 0]);
  const r = DRAG.row;
  return (
    <>
      <div style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: 8, background: C.card, border: `1px dashed ${rgba(C.teal, 0.5)}`, opacity: lift }} />
      <div style={{
        position: 'absolute', left: r.x, top: r.y + (DRAG.toY - r.y) * p, width: r.w, height: r.h, borderRadius: 8, overflow: 'hidden',
        transform: `scale(${1 + 0.03 * lift}) rotate(${-0.6 * lift}deg)`, boxShadow: `0 ${18 * lift}px ${40 * lift}px rgba(0,0,0,0.6), 0 0 0 1.5px ${rgba(C.teal, 0.7 * lift)}`,
      }}>
        <Img src={staticFile('textures/v2/ed2.png')} style={{ position: 'absolute', left: -r.x, top: -r.y, width: 1920 }} />
      </div>
    </>
  );
};

// ── AI hledá (dokreslený stav čekání na odpověď; skutečná odpověď trvá ~10 s, ve filmu zkráceno) ──
const AskWait: React.FC<{ f: number }> = ({ f }) => {
  const a = iv(f, [T.ask.wait[0], T.ask.wait[0] + 4, T.ask.wait[1] - 4, T.ask.wait[1] + 2], [0, 1, 1, 0]);
  if (a <= 0) return null;
  return (
    <div style={{ position: 'absolute', left: 640, top: 2950, display: 'flex', alignItems: 'center', gap: 10, fontFamily: INTER, fontSize: 14, fontWeight: 500, color: C.ai, opacity: a }}>
      {[0, 1, 2].map((i) => <span key={i} style={{ width: 7, height: 7, borderRadius: 4, background: C.ai, opacity: 0.35 + 0.65 * Math.abs(Math.sin((f - i * 4) / 5)) }} />)}
      AI hledá jen v datech pacienta v IRIS…
    </div>
  );
};

// ── zvýraznění věty pacienta v panelu zdroje (jede s panelem) ──
const DrawerMarker: React.FC<{ f: number }> = ({ f }) => {
  if (f < T.marker[0] - 2 || f > T.drawer[1]) return null;
  const grow = iv(f, [T.marker[0], T.marker[1]], [0, 1], EASE.swift);
  const slide = 384 * (1 - iv(f, [T.drawer[1] - 10, T.drawer[1]], [1, 0], EASE.exit));
  return <div style={{ position: 'absolute', left: 1557 + slide, top: 408, height: 22, width: 322 * grow, borderRadius: 4, background: rgba(C.teal, 0.32), mixBlendMode: 'screen' }} />;
};

// ── nahrávání diskuse (dokreslený stav tlačítka) ──
const Recording: React.FC<{ f: number }> = ({ f }) => {
  if (f < T.rec[0] || f > T.rec[1]) return null;
  const sec = Math.floor((f - T.rec[0]) / 30);
  return (
    <div style={{
      position: 'absolute', left: 268, top: 923, width: 264, height: 32, borderRadius: 8, background: '#1c1015', border: `1px solid ${rgba(C.red, 0.7)}`,
      display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, fontFamily: INTER, fontSize: 14, fontWeight: 600, color: C.ink,
      opacity: iv(f, [T.rec[0], T.rec[0] + 4], [0, 1]),
    }}>
      <span style={{ width: 9, height: 9, borderRadius: 5, background: C.red, opacity: 0.55 + 0.45 * Math.sin(f / 5) }} />
      Nahrává se · 00:{String(sec + 7).padStart(2, '0')}
    </div>
  );
};

// ── potvrzený závěr se rozsvítí ──
const Confirmed: React.FC<{ f: number }> = ({ f }) => {
  const a = iv(f, [T.confirmed - 2, T.confirmed + 6, T.confirmed + 60, T.confirmed + 110], [0, 1, 1, 0.35]) * iv(f, [T.stageOut[0], T.stageOut[1]], [1, 0]);
  if (a <= 0) return null;
  return <div style={{ position: 'absolute', left: 671, top: 159, width: 834, height: 129, borderRadius: 14, border: `2px solid ${C.teal}`, opacity: a, boxShadow: `0 0 30px ${rgba(C.teal, 0.55)}` }} />;
};

export const Stage: React.FC<{ f: number; tilt?: number }> = ({ f, tilt = 0 }) => {
  const c = camAt(f);
  const zoom = c.zoom;
  const rotY = Math.max(-1.5, Math.min(1.5, -c.vx * zoom * 0.025));
  const rotX = Math.max(-1, Math.min(1, c.vy * zoom * 0.012)) + tilt;
  const cur = cursorAt(CURSOR, f);
  const on = CURSOR_ON.find(([a, b]) => f >= a && f <= b);
  const curOp = on ? iv(f, [on[0], on[0] + 10, on[1] - 8, on[1]], [0, 1, 1, 0]) : 0;
  return (
    <AbsoluteFill style={{ overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, perspective: `${1500 * zoom}px`, perspectiveOrigin: '960px 540px' }}>
        <div style={{
          position: 'absolute', width: 1920, height: 4000, zoom,
          transform: `translate(${960 / zoom - c.cx}px, ${540 / zoom - c.cy}px) rotateY(${rotY}deg) rotateX(${rotX}deg)`,
          transformOrigin: `${c.cx}px ${c.cy}px`, transformStyle: 'preserve-3d',
        }}>
          <div style={{ position: 'absolute', left: 0, top: 0, width: 1920, height: pageHAt(f), boxShadow: `0 0 0 1px ${C.border}, 0 40px 140px rgba(0,0,0,0.7)` }} />
          {LAYERS.map((l, i) => <LayerView key={i} l={l} f={f} />)}
          <AskWait f={f} />
          <DrawerMarker f={f} />
          <DragRow f={f} />
          <Recording f={f} />
          <Confirmed f={f} />
          <Spotlight f={f} zoom={zoom} />
          {curOp > 0 && <Cursor x={cur.x} y={cur.y} f={f} clicks={CLICKS} size={44 / zoom} opacity={curOp} />}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/** Štítek kapitoly vlevo dole: tahák pro řečníka i orientace pro sál. */
export const ChapterLabel: React.FC<{ f: number; from: number; to: number; n: string; title: string }> = ({ f, from, to, n, title }) => {
  const p = iv(f, [from + 6, from + 24], [0, 1], EASE.snappy) * iv(f, [to - 8, to + 4], [1, 0]);
  if (p <= 0) return null;
  return (
    <div style={{
      position: 'absolute', left: 64, bottom: 58, display: 'flex', alignItems: 'center', gap: 20, padding: '16px 30px 16px 22px',
      borderRadius: 16, background: 'rgba(4,7,11,0.84)', border: `1px solid ${C.border}`, boxShadow: '0 20px 50px rgba(0,0,0,0.5)',
      opacity: p, transform: `translateX(${(1 - p) * -40}px)`,
    }}>
      <span style={{ fontFamily: MONO, fontSize: 32, fontWeight: 700, color: C.teal }}>{n}</span>
      <span style={{ width: 2, height: 34, background: C.border }} />
      <span style={{ fontFamily: INTER, fontSize: 40, fontWeight: 650, color: C.ink, letterSpacing: '-0.02em' }}>{title}</span>
    </div>
  );
};
