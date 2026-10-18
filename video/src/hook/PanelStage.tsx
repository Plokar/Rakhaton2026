// A4 · Zážeh (f330–420) + A5 · Důkaz (f420–600).
// DROP: bod → světelná čára → skenovací linka nakreslí úzký panel projektoru P03 (skutečný snímek).
// Panel stoupá z hloubky a kamera ho obkrouží (spotlight-hero-card); pak detail hlavičky (PS 0 vs pac. 1),
// sken klíčových údajů a světelný oblouk (glow-flyline) z řádku PNP ke kartě zdroje P03-neuro01.
import React from 'react';
import { AbsoluteFill, Img, staticFile } from 'remotion';
import { Caption } from '../common/Film';
import { EASE } from '../lib/Polish';
import { mulberry32 } from '../lib/rand';
import { C, iv, rgba } from '../theme';
import { BEAT, S } from './timeline';

// Panel = okno projektoru, sloupec x 750–1170 snímku projector.png (CSS px). Lokální souřadnice od jeho levého horního rohu.
const PANEL = { x: 750, w: 420, h: 1080 };
const PERSP = 1800;
const SLIT = 420; // lokální y, kde se panel otevře (= ohnisko hero záběru, hlavička zůstane nad letterboxem)
type Cam = { f: number; ax: number; fx: number; fy: number; zoom: number; rotY: number; tz: number };
const CAM: Cam[] = [
  { f: 330, ax: 1250, fx: 210, fy: SLIT, zoom: 0.95, rotY: 34, tz: -520 },
  { f: 404, ax: 1250, fx: 210, fy: SLIT, zoom: 0.96, rotY: 12, tz: 0 },
  { f: 420, ax: 1250, fx: 210, fy: SLIT, zoom: 0.96, rotY: 10, tz: 0 },
  { f: 446, ax: 1010, fx: 200, fy: 86, zoom: 2.25, rotY: 6, tz: 0 },
  { f: 476, ax: 1000, fx: 200, fy: 86, zoom: 2.3, rotY: 5, tz: 0 },
  { f: 500, ax: 1260, fx: 210, fy: 330, zoom: 1.55, rotY: -11, tz: 0 },
  { f: 600, ax: 1280, fx: 210, fy: 330, zoom: 1.5, rotY: -13, tz: 0 },
];
const camAt = (f: number): Cam => {
  if (f <= CAM[0].f) return CAM[0];
  for (let i = 0; i < CAM.length - 1; i++) {
    const a = CAM[i], b = CAM[i + 1];
    if (f <= b.f) {
      const t = iv(f, [a.f, b.f], [0, 1], i === 0 ? EASE.out : EASE.swift);
      const m = (k: keyof Cam) => a[k] + (b[k] - a[k]) * t;
      return { f, ax: m('ax'), fx: m('fx'), fy: m('fy'), zoom: m('zoom'), rotY: m('rotY'), tz: m('tz') };
    }
  }
  return CAM[CAM.length - 1];
};
/** Lokální bod panelu → obrazovka (stejná matematika jako CSS: rotateY kolem ohniska, perspektiva v kotvě). */
const project = (c: Cam, lx: number, ly: number) => {
  const x = (lx - c.fx) * c.zoom, y = (ly - c.fy) * c.zoom;
  const th = (c.rotY * Math.PI) / 180;
  const z = -x * Math.sin(th) + c.tz;
  const s = PERSP / (PERSP - z);
  return { x: c.ax + x * Math.cos(th) * s, y: 540 + y * s };
};

// Karta zdroje = výřez panelu „Zdrojový dokument“ (drawer.png x 1536–1920, y 0–452)
const SRC = { x: 1536, y: 0, w: 384, h: 452, k: 1.3, left: 140, top: 214 };
const PNP = { x: 29, y: 243, w: 362, h: 32 }; // řádek PNP v panelu
const PS = { x: 257, y: 30, w: 64, h: 72 }; // PS 0 / pac. 1

const dust = (() => {
  const r = mulberry32(9);
  return Array.from({ length: 46 }, () => ({ x: 900 + r() * 700, y: r() * 1080, s: 1 + r() * 2.2, ph: r() * 6.28, sp: 0.2 + r() * 0.5 }));
})();

export const PanelStage: React.FC<{ f: number }> = ({ f }) => {
  if (f < S.ignite.from || f > S.rules.from + 16) return null;
  const c = camAt(f);
  const reveal = iv(f, [338, 374], [0, 1], EASE.swift);
  const exit = iv(f, [594, 612], [0, 1], EASE.exit);
  const flash = iv(f, [BEAT.drop, BEAT.drop + 1, BEAT.drop + 9], [0, 0.55, 0]);
  const streakW = iv(f, [BEAT.drop, BEAT.drop + 8], [0, 1920], EASE.snappy);
  const streakOp = iv(f, [BEAT.drop, BEAT.drop + 3, 340, 346], [0, 1, 1, 0]);
  const cone = iv(f, [336, 362, 560, 600], [0, 0.55, 0.32, 0]);
  const psRing = iv(f, [428, 436, 488, 498], [0, 1, 1, 0]);
  const psPulse = 1 + 0.06 * Math.sin((f - 428) / 4) * iv(f, [428, 460], [1, 0]);
  const scan = iv(f, [468, 498], [0, 1], EASE.swift);
  const rowOn = iv(f, [494, 504], [0, 1]);
  const card = iv(f, [503, BEAT.b3], [0, 1], EASE.snappy);
  const sheen = iv(f, [BEAT.b3, BEAT.b3 + 22], [0, 1], EASE.swift);
  const marker = iv(f, [538, 554], [0, 1], EASE.swift);
  const fly = iv(f, [500, BEAT.b3], [0, 1], EASE.swift);
  const z = c.zoom;
  // oblouk: z levého okraje řádku PNP do pravého okraje karty u „grade 1“
  const a = project(c, PNP.x, PNP.y + PNP.h / 2);
  const b = { x: SRC.left + SRC.w * SRC.k - 6, y: SRC.top + 180 * SRC.k };
  const ctrl1 = { x: a.x - 120, y: a.y - 170 }, ctrl2 = { x: b.x + 140, y: b.y - 150 };
  const pathD = `M ${a.x} ${a.y} C ${ctrl1.x} ${ctrl1.y}, ${ctrl2.x} ${ctrl2.y}, ${b.x} ${b.y}`;

  return (
    <AbsoluteFill style={{ opacity: 1 - exit }}>
      {/* objemové světlo shora na panel */}
      <AbsoluteFill style={{ mixBlendMode: 'screen', opacity: cone, filter: 'blur(30px)' }}>
        <div style={{
          position: 'absolute', inset: 0, clipPath: `polygon(${c.ax - 30}px -100px, ${c.ax + 30}px -100px, ${c.ax + 360}px 1080px, ${c.ax - 360}px 1080px)`,
          background: `linear-gradient(180deg, ${rgba(C.teal, 0.28)} 0%, ${rgba(C.teal, 0.08)} 70%, rgba(0,0,0,0) 100%)`,
        }} />
      </AbsoluteFill>
      {dust.map((d, i) => {
        const y = (d.y - f * d.sp * 1.4 + 2160) % 1080;
        const x = d.x + Math.sin(f / 30 + d.ph) * 14 + (c.ax - 1240);
        return <div key={i} style={{ position: 'absolute', left: x, top: y, width: d.s, height: d.s, borderRadius: '50%', background: '#cffff8', opacity: cone * 0.5 }} />;
      })}

      {/* panel ve 3D: kotva = ohnisko kamery, perspektiva v kotvě */}
      <div style={{ position: 'absolute', left: c.ax + exit * 260, top: 540, width: 0, height: 0, perspective: PERSP, perspectiveOrigin: '0 0' }}>
        <div style={{
          position: 'absolute', left: -c.fx * z, top: -c.fy * z, width: PANEL.w * z, height: PANEL.h * z,
          transform: `translateZ(${c.tz}px) rotateY(${c.rotY}deg)`, transformOrigin: `${c.fx * z}px ${c.fy * z}px`,
        }}>
          <div style={{
            position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 18 * z, clipPath: `inset(${(1 - reveal) * SLIT / PANEL.h * 100}% 0 ${(1 - reveal) * (1 - SLIT / PANEL.h) * 100}% 0)`,
            boxShadow: `0 0 0 ${1.5 * z}px ${rgba(C.teal, 0.35)}, 0 0 ${80 * z}px ${rgba(C.teal, 0.18)}, 0 ${60 * z}px ${120 * z}px rgba(0,0,0,0.7)`,
          }}>
            <Img src={staticFile('textures/projector.png')} style={{ position: 'absolute', left: -PANEL.x * z, top: 0, width: 1920 * z }} />
          </div>
          {/* štěrbina: světelná čára dropu se rozevře do dvou skenovacích linek (nahoru a dolů od středu) */}
          {reveal > 0 && reveal < 1 && [-1, 1].map((d) => (
            <div key={d} style={{
              position: 'absolute', left: -40 * z, right: -40 * z, top: (SLIT + reveal * (d < 0 ? SLIT : PANEL.h - SLIT) * d) * z - 2, height: 4,
              background: '#eafffb', boxShadow: `0 0 18px 6px ${rgba(C.teal, 0.85)}, 0 0 80px 24px ${rgba(C.teal, 0.35)}`,
            }} />
          ))}
          {/* PS 0 vs pac. 1 */}
          {psRing > 0 && (
            <div style={{
              position: 'absolute', left: (PS.x - 6) * z, top: (PS.y - 6) * z, width: (PS.w + 12) * z, height: (PS.h + 12) * z,
              borderRadius: 14 * z, border: `${2.5}px solid ${C.amber}`, opacity: psRing, transform: `scale(${psPulse})`,
              boxShadow: `0 0 24px ${rgba(C.amber, 0.6)}, inset 0 0 18px ${rgba(C.amber, 0.25)}`,
            }} />
          )}
          {/* sken klíčových údajů */}
          {scan > 0 && scan < 1 && (
            <div style={{
              position: 'absolute', left: 0, right: 0, top: (238 + scan * 270) * z, height: 3,
              background: rgba(C.teal, 0.9), boxShadow: `0 0 16px 4px ${rgba(C.teal, 0.6)}`,
            }} />
          )}
          {rowOn > 0 && (
            <div style={{
              position: 'absolute', left: (PNP.x - 4) * z, top: (PNP.y - 3) * z, width: (PNP.w + 8) * z, height: (PNP.h + 6) * z,
              borderRadius: 8 * z, border: `2px solid ${rgba(C.teal, 0.95)}`, opacity: rowOn,
              boxShadow: `0 0 26px ${rgba(C.teal, 0.55)}, inset 0 0 20px ${rgba(C.teal, 0.18)}`,
            }} />
          )}
        </div>
      </div>

      {/* světelný oblouk řádek → zdroj */}
      {fly > 0 && (
        <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
          <defs><filter id="fl-glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="6" /></filter></defs>
          <path d={pathD} fill="none" stroke={C.teal} strokeWidth={8} opacity={0.35} pathLength={1} strokeDasharray={`${fly} 1`} filter="url(#fl-glow)" />
          <path d={pathD} fill="none" stroke="#dffffa" strokeWidth={2.5} pathLength={1} strokeDasharray={`${fly} 1`} />
        </svg>
      )}

      {/* karta zdroje: vlétne zleva, dosedne na úder f518, jeden lesk (Q4) a marker na větě pacienta */}
      {card > 0 && (
        <div style={{
          position: 'absolute', left: SRC.left - 340 * (1 - card) - exit * 260, top: SRC.top, perspective: 1600,
          opacity: Math.min(1, card * 1.4), filter: card < 0.98 ? `blur(${(1 - card) * 18}px)` : undefined,
        }}>
          <div style={{
            position: 'relative', width: SRC.w * SRC.k, height: SRC.h * SRC.k, borderRadius: 18, overflow: 'hidden',
            transform: `rotateY(${12 + 30 * (1 - card)}deg)`, transformOrigin: '0% 50%',
            border: `1.5px solid ${C.border}`, boxShadow: `0 40px 90px rgba(0,0,0,0.65), 0 0 50px ${rgba(C.teal, 0.12)}`,
          }}>
            <Img src={staticFile('textures/drawer.png')} style={{ position: 'absolute', left: -SRC.x * SRC.k, top: -SRC.y * SRC.k, width: 1920 * SRC.k }} />
            <div style={{
              position: 'absolute', left: 19 * SRC.k, top: 407 * SRC.k, height: 22 * SRC.k, width: 326 * SRC.k * marker,
              background: rgba(C.teal, 0.3), borderRadius: 4, mixBlendMode: 'screen',
            }} />
            {sheen > 0 && sheen < 1 && (
              <div style={{
                position: 'absolute', top: -100, bottom: -100, width: 160, left: -200 + sheen * (SRC.w * SRC.k + 400),
                background: 'linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.16), rgba(255,255,255,0))', transform: 'rotate(14deg)',
              }} />
            )}
          </div>
        </div>
      )}

      {/* bílý záblesk dropu + světelná čára (úder č. 1 na celý obraz, R4) */}
      <AbsoluteFill style={{ background: '#e6fffb', opacity: flash, mixBlendMode: 'screen' }} />
      {streakOp > 0 && (
        <div style={{
          position: 'absolute', left: 960 - streakW / 2, width: streakW, top: 538, height: 4, opacity: streakOp,
          background: 'linear-gradient(90deg, rgba(234,255,251,0), #eafffb 20%, #eafffb 80%, rgba(234,255,251,0))',
          boxShadow: `0 0 30px 8px ${rgba(C.teal, 0.7)}`,
        }} />
      )}

      {/* scrim pod titulky, když panel zaplní obraz (Q11) */}
      <div style={{
        position: 'absolute', left: 0, right: 0, bottom: 0, height: 480, opacity: iv(f, [440, 452, 590, 600], [0, 1, 1, 0]),
        background: 'linear-gradient(180deg, rgba(4,7,11,0) 0%, rgba(4,7,11,0.9) 42%, rgba(4,7,11,0.97) 100%)',
      }} />
      <Caption text="MedTeam připraví *celý případ.*" from={350} to={414} x={150} y={392} size={88} align="left" maxWidth={820} />
      <Caption text="Za pár sekund." from={374} to={414} x={150} y={604} size={54} weight={600} color={C.ink2} align="left" />
      <Caption text="Každé tvrzení má *zdroj.*" from={452} to={530} y={812} size={64} />
      <Caption text="Každý rozpor *na očích.*" from={538} to={592} y={812} size={64} accent={C.amber} />
    </AbsoluteFill>
  );
};
