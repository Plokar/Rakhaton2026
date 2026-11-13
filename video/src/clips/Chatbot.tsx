// Klip „Chatbot“ (5 s, tmavý režim): v jednání P04 se lékař zeptá AI „Jaká je hodnota FEV1?“ a AI odpoví
// hodnotou, datem měření a odkazem na zdroj; klik na odkaz otevře skutečný panel zdroje se zvýrazněnou větou.
// Rozhovor je na produkci nefunkční, proto je vložený jen do DOM při snímání (scripts/capture_bot.mjs);
// hodnota, datum i zdroj jsou z datasetu (P04-spiro01 · 1,9 l / 58 % · 25. 8. 2026 · P04-doc03).
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { SfxTrack, type Sfx } from '../common/audio';
import { Cursor, cursorAt } from '../common/Cursor';
import { Hall } from '../common/Film';
import { EASE } from '../lib/Polish';
import { C, iv, rgba } from '../theme';
import B from '../../public/textures/bot/bot.json';

export const BOT_TOTAL = 150;
type Rect = { x: number; y: number; w: number; h: number };
const tex = (n: string) => staticFile(`textures/bot/${n}.png`);
const CARD = '#111a24';

// ── časování (30 fps) ──
const T = { type: [10, 40], send: 44, answer: 66, click: 108, drawer: [110, 124], mark: [126, 138] } as const;
const charsAt = (f: number) => Math.round(iv(f, [T.type[0], T.type[1]], [0, B.q.length]));

// ── kamera: (cx, cy) stránky do středu obrazu, zoom přes CSS zoom (ostré písmo) ──
const CAM: [number, number, number, number][] = [
  [0, 1560, 900, 2.25], [14, 1600, 940, 2.6], [T.send, 1600, 940, 2.6], [T.answer - 2, 1600, 300, 2.6],
  [T.drawer[0], 1600, 300, 2.6], [BOT_TOTAL, 1606, 300, 2.68],
];
const camAt = (f: number) => {
  let a = CAM[0], b = CAM[CAM.length - 1];
  for (let i = 0; i < CAM.length - 1; i++) if (f >= CAM[i][0] && f <= CAM[i + 1][0]) { a = CAM[i]; b = CAM[i + 1]; break; }
  const t = a[0] === b[0] ? 1 : iv(f, [a[0], b[0]], [0, 1], EASE.smooth);
  return { cx: a[1] + (b[1] - a[1]) * t, cy: a[2] + (b[2] - a[2]) * t, zoom: a[3] + (b[3] - a[3]) * t };
};

/** Výřez snímku v prostoru stránky. */
const Crop: React.FC<{ src: string; r: Rect; style?: React.CSSProperties }> = ({ src, r, style }) => (
  <div style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h, overflow: 'hidden', ...style }}>
    <Img src={src} style={{ position: 'absolute', left: -r.x, top: -r.y, width: 1920, height: 1080 }} />
  </div>
);
const Patch: React.FC<{ r: Rect; pad?: number }> = ({ r, pad = 2 }) => (
  <div style={{ position: 'absolute', left: r.x - pad, top: r.y - pad, width: r.w + pad * 2, height: r.h + pad * 2, background: CARD }} />
);
const Ring: React.FC<{ r: Rect; a: number; zoom: number; color?: string; pad?: number }> = ({ r, a, zoom, color = C.teal, pad = 4 }) =>
  a <= 0 ? null : (
    <div style={{
      position: 'absolute', left: r.x - pad, top: r.y - pad, width: r.w + pad * 2, height: r.h + pad * 2, borderRadius: 8,
      border: `${2 / zoom}px solid ${rgba(color, 0.9 * a)}`, boxShadow: `0 0 ${12 / zoom}px ${rgba(color, 0.55 * a)}`,
    }} />
  );

export const Chatbot: React.FC = () => {
  const f = useCurrentFrame();
  const cam = camAt(f);
  const z = cam.zoom;
  const n = charsAt(f);
  const answer = B.answer as Rect, question = B.question as Rect, loader = B.loader as Rect;
  // fáze
  const stage = f < T.send ? 'empty' : f < T.answer ? 'loading' : 'answer';
  const qIn = iv(f, [T.send, T.send + 8], [0, 1], EASE.out);
  const aIn = iv(f, [T.answer, T.answer + 16], [0, 1], EASE.out);
  const drawerP = iv(f, [T.drawer[0], T.drawer[1]], [0, 1], EASE.out);
  const markP = iv(f, [T.mark[0], T.mark[1]], [0, 1], EASE.swift);
  const link = B.link as Rect;
  const cur = cursorAt([{ f: 90, x: 1840, y: 520 }, { f: 106, x: link.x + link.w * 0.55, y: link.y + link.h * 0.6 }], f);
  const curOp = iv(f, [90, 96, T.click + 6, T.click + 12], [0, 1, 1, 0]);
  const spin = ((f - T.send) * 24) % 360;
  const sfx: Sfx[] = [
    { from: T.type[0], src: 'keyboard.mp3', volume: 0.75, dur: T.type[1] - T.type[0] + 4, note: 'psaní dotazu' },
    { from: T.send, src: 'click-a.wav', volume: 0.5, dur: 12, note: 'Enter' },
    { from: T.send + 1, src: 'swoosh-quick.mp3', volume: 0.14, dur: 24, note: 'dotaz odeslán' },
    { from: T.answer, src: 'ui-message-pop.mp3', volume: 0.28, dur: 20, note: 'odpověď AI' },
    { from: T.answer + 8, src: 'sparkle-touch.mp3', volume: 0.14, dur: 34, note: 'hodnota a datum' },
    { from: T.click, src: 'click-b.wav', volume: 0.5, dur: 12, note: 'klik na zdroj' },
    { from: T.drawer[0], src: 'swoosh-quick.mp3', volume: 0.16, dur: 24, note: 'panel zdroje' },
    { from: T.mark[0], src: 'sparkle-touch.mp3', volume: 0.16, dur: 30, note: 'věta ve zdroji' },
  ];
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Hall glow={0.6} />
      {['empty', 'loading', 'answer', 'drawer'].map((s) => <Img key={s} src={tex(s)} style={{ position: 'absolute', width: 1, height: 1, opacity: 0 }} />)}
      <AbsoluteFill style={{ opacity: iv(f, [0, 6], [0, 1]) }}>
        <div style={{ position: 'absolute', width: 1920, height: 1080, zoom: z, transform: `translate(${960 / z - cam.cx}px, ${540 / z - cam.cy}px)` }}>
          <div style={{ position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, boxShadow: `0 0 0 ${1 / z}px ${C.border}, 0 0 ${80 / z}px rgba(0,0,0,0.8)` }} />
          <Img src={tex(stage)} style={{ position: 'absolute', left: 0, top: 0, width: 1920, height: 1080 }} />
          {/* psaní: skutečné pole při psaní (vyplněno, neodesláno) */}
          {stage === 'empty' && n > 0 && <Img src={tex(`type_${n}`)} style={{ position: 'absolute', left: B.form.x, top: B.form.y, width: B.form.w, height: B.form.h }} />}
          {/* dotaz vyskočí */}
          {stage === 'loading' && qIn < 1 && (
            <>
              <Patch r={question} />
              <Crop src={tex('loading')} r={question} style={{ opacity: qIn, transform: `translateY(${(1 - qIn) * 14}px)` }} />
            </>
          )}
          {/* AI odpovídá: točící se ikona */}
          {stage === 'loading' && (
            <>
              <div style={{ position: 'absolute', left: loader.x - 1, top: loader.y + 1, width: 18, height: 18, background: CARD }} />
              <svg width={16} height={16} viewBox="0 0 24 24" style={{ position: 'absolute', left: loader.x, top: loader.y + 2, transform: `rotate(${spin}deg)` }}>
                <path d="M21 12a9 9 0 1 1-6.219-8.56" fill="none" stroke={C.ink2} strokeWidth={2} strokeLinecap="round" />
              </svg>
            </>
          )}
          {/* odpověď AI: rozbalí se shora */}
          {stage === 'answer' && aIn < 1 && (
            <>
              <Patch r={answer} pad={4} />
              <Crop src={tex('answer')} r={answer} style={{ opacity: Math.min(1, aIn * 1.6), transform: `translateY(${(1 - aIn) * 12}px)`, clipPath: `inset(0 0 ${(1 - aIn) * 100}% 0)` }} />
            </>
          )}
          <Ring r={B.value as Rect} a={iv(f, [76, 82, 104, 110], [0, 1, 1, 0])} zoom={z} />
          <Ring r={B.date as Rect} a={iv(f, [86, 92, 104, 110], [0, 1, 1, 0])} zoom={z} pad={3} />
          {/* dim mimo chatbot: pozornost na panel */}
          <div style={{ position: 'absolute', left: 0, top: 0, width: 1560, height: 1080, background: 'rgba(4,7,11,0.6)' }} />
          {/* skutečný panel zdroje vyjede zprava */}
          {drawerP > 0 && (
            <>
              <div style={{ position: 'absolute', left: 0, top: 0, width: 1920, height: 1080, background: `rgba(4,7,11,${0.35 * drawerP})` }} />
              <Crop src={tex('drawer')} r={B.drawer as Rect} style={{ transform: `translateX(${(1 - drawerP) * 384}px)`, boxShadow: `-24px 0 60px rgba(0,0,0,${0.5 * drawerP})` }} />
            </>
          )}
          {markP > 0 && (B.sentence as Rect[]).map((r, i) => (
            <div key={i} style={{ position: 'absolute', left: r.x - 2, top: r.y - 1, width: (r.w + 4) * markP, height: r.h + 2, borderRadius: 3, background: rgba(C.teal, 0.32), mixBlendMode: 'screen' }} />
          ))}
          {curOp > 0 && <Cursor x={cur.x} y={cur.y} f={f} clicks={[T.click]} size={44 / z} opacity={curOp} />}
        </div>
      </AbsoluteFill>
      <SfxTrack items={sfx} />
    </AbsoluteFill>
  );
};
