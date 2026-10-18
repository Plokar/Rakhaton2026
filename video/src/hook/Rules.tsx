// A6 · Semafor (f600–700): tři skutečné řádky léčebných postupů z obrazovky jednání se snesou a zapadnou
// (row-embed: rotateX → 0, šev v barvě semaforu, záře štítku). A7 · Lékař (f700–775): stisk „Potvrdit“
// a razítko skutečného potvrzeného závěru (zapsáno do IRIS) dopadne (score-slam).
import React from 'react';
import { AbsoluteFill, Img, staticFile } from 'remotion';
import { Caption } from '../common/Film';
import { Cursor, cursorAt } from '../common/Cursor';
import { EASE } from '../lib/Polish';
import { C, INTER, iv, rgba } from '../theme';
import { CLICK, ROW_LAND, S } from './timeline';

const K = 1.9; // měřítko řádků (titulky řádků ≈ 27 px)
const ROWS = [
  { y: 343, h: 109, badge: { x: 543, y: 7, w: 63, h: 20 }, color: C.amber },
  { y: 636, h: 70, badge: { x: 527, y: 6, w: 79, h: 20 }, color: C.red },
  { y: 714, h: 27, badge: { x: 492, y: 3, w: 114, h: 21 }, color: C.gray },
];
const RX = 1195, RW = 610, PAD = 22, GAP = 20, TOP = 190;

const Row: React.FC<{ f: number; i: number; top: number; exit: number }> = ({ f, i, top, exit }) => {
  const r = ROWS[i];
  const land = ROW_LAND[i];
  const p = iv(f, [land - 14, land], [0, 1], EASE.out);
  const settle = iv(f, [land, land + 4, land + 10], [0, 1, 0]);
  const seam = iv(f, [land, land + 3, land + 30], [0, 1, 0.25]);
  const halo = iv(f, [land, land + 4, land + 40], [0, 1, 0.5]);
  if (p <= 0) return null;
  const w = RW * K + PAD * 2, h = r.h * K + PAD * 2;
  return (
    <div style={{ position: 'absolute', left: 960 - w / 2, top, width: w, height: h, perspective: 1400, opacity: Math.min(1, p * 1.6) * (1 - exit) }}>
      <div style={{
        position: 'absolute', inset: 0, borderRadius: 20, background: C.bg, border: `1.5px solid ${C.border}`, overflow: 'hidden',
        transform: `translateY(${-140 * (1 - p) + 4 * settle}px) rotateX(${55 * (1 - p)}deg) scale(${1 - 0.06 * exit})`, transformOrigin: '50% 0%',
        filter: p < 0.98 ? `blur(${(1 - p) * 10}px)` : exit > 0 ? `blur(${exit * 8}px)` : undefined,
        boxShadow: `0 30px 70px rgba(0,0,0,0.55), 0 0 ${40 * halo}px ${rgba(r.color, 0.12 * halo)}`,
      }}>
        <div style={{ position: 'absolute', left: PAD, top: PAD, width: RW * K, height: r.h * K, overflow: 'hidden' }}>
          <Img src={staticFile('textures/session.png')} style={{ position: 'absolute', left: -RX * K, top: -r.y * K, width: 1920 * K }} />
        </div>
        {/* záře štítku semaforu */}
        <div style={{
          position: 'absolute', left: PAD + (r.badge.x - 4) * K, top: PAD + (r.badge.y - 3) * K, width: (r.badge.w + 8) * K, height: (r.badge.h + 6) * K,
          borderRadius: 999, border: `2px solid ${rgba(r.color, 0.9 * halo)}`, boxShadow: `0 0 ${26 * halo}px ${rgba(r.color, 0.7 * halo)}`,
        }} />
        {/* šev při dosednutí */}
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 3, background: r.color, opacity: seam, boxShadow: `0 0 18px ${r.color}` }} />
      </div>
    </div>
  );
};

export const Rules: React.FC<{ f: number }> = ({ f }) => {
  if (f < S.rules.from - 14 || f > S.brand.from + 6) return null;
  const rowsExit = iv(f, [692, 706], [0, 1], EASE.exit);
  let top = TOP;
  const tops = ROWS.map((r) => { const t = top; top += r.h * K + PAD * 2 + GAP; return t; });

  // A7
  const btnIn = iv(f, [690, 702], [0, 1], EASE.snappy);
  const press = iv(f, [CLICK - 2, CLICK, CLICK + 7], [1, 0.95, 1]);
  const stamp = iv(f, [CLICK + 2, CLICK + 12], [0, 1], EASE.snappy);
  const btnOut = iv(f, [CLICK + 2, CLICK + 8], [0, 1]);
  const flash = iv(f, [CLICK, CLICK + 1, CLICK + 9], [0, 0.16, 0]);
  const allOut = iv(f, [766, 776], [0, 1], EASE.exit);
  const cur = cursorAt([{ f: 684, x: 1560, y: 930 }, { f: 700, x: 1012, y: 492 }], f);
  const chips = ['InterSystems IRIS for Health', 'HL7 FHIR R4', 'Provenance'];
  const BOX = { x: 673, y: 161, w: 830, h: 125, k: 1.3 };

  return (
    <AbsoluteFill style={{ opacity: 1 - allOut }}>
      {ROWS.map((_, i) => <Row key={i} f={f} i={i} top={tops[i]} exit={rowsExit} />)}
      <Caption text="Semafor počítají *pravidla.* Ne AI." from={628} to={690} y={812} size={64} />

      {f >= 688 && (
        <>
          {/* tlačítko ve stylu primární akce aplikace */}
          <div style={{
            position: 'absolute', left: 960, top: 470, transform: `translate(-50%,-50%) scale(${(0.9 + 0.1 * btnIn) * press})`,
            opacity: btnIn * (1 - btnOut), display: 'flex', alignItems: 'center', gap: 18, padding: '26px 54px', borderRadius: 18,
            background: C.teal, color: '#042f2e', fontFamily: INTER, fontSize: 46, fontWeight: 700, letterSpacing: '-0.02em',
            boxShadow: `0 0 60px ${rgba(C.teal, 0.45)}, 0 24px 60px rgba(0,0,0,0.5)`,
          }}>
            <svg width={44} height={44} viewBox="0 0 24 24"><path d="M5 12.5l4.2 4.2L19 7" fill="none" stroke="#042f2e" strokeWidth={2.8} strokeLinecap="round" strokeLinejoin="round" /></svg>
            Potvrdit závěr komise
          </div>
          {/* razítko: skutečný potvrzený závěr z obrazovky Závěr komise */}
          {stamp > 0 && (
            <div style={{
              position: 'absolute', left: 960, top: 430, transform: `translate(-50%,-50%) scale(${1.55 - 0.55 * stamp})`, opacity: Math.min(1, stamp * 2),
              filter: stamp < 0.98 ? `blur(${(1 - stamp) * 12}px)` : undefined,
              width: BOX.w * BOX.k, height: BOX.h * BOX.k, borderRadius: 20, overflow: 'hidden',
              border: `2px solid ${rgba(C.teal, 0.55)}`, boxShadow: `0 0 70px ${rgba(C.teal, 0.25)}, 0 40px 90px rgba(0,0,0,0.6)`,
            }}>
              <Img src={staticFile('textures/record.png')} style={{ position: 'absolute', left: -BOX.x * BOX.k, top: -BOX.y * BOX.k, width: 1920 * BOX.k }} />
            </div>
          )}
          <div style={{ position: 'absolute', left: 0, right: 0, top: 572, display: 'flex', justifyContent: 'center', gap: 18 }}>
            {chips.map((t, i) => {
              const p = iv(f, [716 + i * 5, 730 + i * 5], [0, 1], EASE.snappy);
              return (
                <div key={t} style={{
                  opacity: p, transform: `translateY(${(1 - p) * 18}px)`, padding: '10px 24px', borderRadius: 999, fontFamily: INTER, fontSize: 32, fontWeight: 600,
                  color: C.teal, border: `1.5px solid ${rgba(C.teal, 0.45)}`, background: rgba(C.teal, 0.08),
                }}>{t}</div>
              );
            })}
          </div>
          {f < CLICK + 14 && <Cursor x={cur.x} y={cur.y} f={f} clicks={[CLICK]} size={52} opacity={iv(f, [684, 690, CLICK + 6, CLICK + 14], [0, 1, 1, 0])} />}
          <AbsoluteFill style={{ background: '#ffffff', opacity: flash, mixBlendMode: 'screen' }} />
        </>
      )}
      <Caption text="Rozhoduje vždy *lékař.*" from={712} to={764} y={744} size={88} />
    </AbsoluteFill>
  );
};
