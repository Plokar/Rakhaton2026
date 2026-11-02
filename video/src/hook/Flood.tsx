// A2 · Lavina (f105–300) + A3 · Nádech (f300–330).
// Úryvky skutečných (fiktivních) záznamů P03 letí hloubkovým tunelem ke kameře a zrychlují (flying-words:
// ruční perspektiva s = P/(P − z), stopy pohybu přes text-shadow). Uprostřed se zastaví rozpor lékař × pacient.
// A3: čas zamrzne, vše se stáhne do jednoho tyrkysového bodu.
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { EASE } from '../lib/Polish';
import { mulberry32 } from '../lib/rand';
import { C, INTER, MONO, iv, rgba } from '../theme';
import { S } from './timeline';

type Frag = { kind: 'doc'; id: string; title: string; line: string } | { kind: 'val'; text: string; warn?: boolean };

const FRAGS: Frag[] = [
  { kind: 'doc', id: 'P03-img01', title: 'CT hrudníku, břicha a pánve', line: 'staging · 28. 4. 2026' },
  { kind: 'val', text: 'CEA 13,9 µg/l' },
  { kind: 'doc', id: 'P03-pat01', title: 'Histologie', line: 'adenokarcinom sigmatu G2' },
  { kind: 'val', text: 'cT3 cN1 cM1a' },
  { kind: 'doc', id: 'P03-proc03', title: 'FOLFOX + bevacizumab', line: '8 cyklů · 6.–9. 2026' },
  { kind: 'val', text: 'MMR / MSI ?', warn: true },
  { kind: 'doc', id: 'P03-img04', title: 'MR jater', line: 'restaging · 28. 9. 2026' },
  { kind: 'val', text: 'FLR 38 %' },
  { kind: 'doc', id: 'P03-kom1', title: 'Komorbidity', line: 'I25.2 starý infarkt myokardu' },
  { kind: 'val', text: 'ECOG 0–1', warn: true },
  { kind: 'doc', id: 'P03-zad01', title: 'Žádost o MDT', line: 'resekabilita jaterních metastáz' },
  { kind: 'val', text: 'Hb 114 g/l' },
  { kind: 'doc', id: 'P03-doc07', title: 'Kontrola po restagingu', line: 'nominace na re-MDT' },
  { kind: 'val', text: 'C18.7' },
  { kind: 'doc', id: 'P03-prom01', title: 'Dotazník pacienta', line: 'brnění 6/10 (dříve 0/10)' },
  { kind: 'val', text: 'staging 176 dní', warn: true },
  { kind: 'doc', id: 'P03-mdt01', title: 'Záznam MDT', line: 'konverzní chemoterapie' },
  { kind: 'val', text: '78 kg · −7 %' },
  { kind: 'doc', id: 'P03-bm03', title: 'BRAF V600E', line: 'neprokázána' },
  { kind: 'val', text: 'DPYD ?', warn: true },
  { kind: 'doc', id: 'P03-img03', title: 'CT restaging', line: 'hrudník nebyl požadován' },
  { kind: 'val', text: 'stadium IVA' },
  { kind: 'doc', id: 'P03-doc05', title: 'Ambulantní zpráva', line: 'neuropatie G1' },
  { kind: 'val', text: 'KRC-2.4' },
  { kind: 'doc', id: 'P03-kom2', title: 'Medikace', line: 'hořčík, vitamin B?' },
  { kind: 'val', text: 'bevacizumab 7. 9.' },
  { kind: 'doc', id: 'P03-ecog03', title: 'ECOG lékaře', line: '0' },
  { kind: 'val', text: 'S3 · obou laloků' },
];

const P = 4400, Z0 = -7000, Z1 = 3200, CX = 960, CY = 540;
const LOCAL0 = S.flood.from;
const FREEZE = S.breath.from; // A3: čas zamrzne
const N = FRAGS.length;
const rnd = mulberry32(42);
const ITEMS = FRAGS.map((fr, i) => {
  const a = i * 2.39996 + rnd() * 0.7;
  const r = 360 + rnd() * 640;
  const start = (i / N) * 150 + rnd() * 8; // postupně hustší proud
  return { fr, x: Math.cos(a) * r, y: Math.sin(a) * r * 0.56, start, dur: 118 - start * 0.42, rz: (rnd() - 0.5) * 10, size: 1.05 + rnd() * 0.4 };
});
const OP = [0, 1, 0.8, 0.45, 0];
const OT = [0, 0.18, 0.6, 0.86, 1];
const life = (u: number) => {
  for (let k = 0; k < 4; k++) if (u <= OT[k + 1]) return OP[k] + ((OP[k + 1] - OP[k]) * (u - OT[k])) / (OT[k + 1] - OT[k]);
  return 0;
};
const proj = (x: number, y: number, u: number) => {
  const z = Z0 + (Z1 - Z0) * u;
  const d = 0.5 + u * 1.35;
  const s = P / (P - z);
  return { sx: CX + x * d * s, sy: CY + y * d * s, s };
};

const DocCard: React.FC<{ fr: Extract<Frag, { kind: 'doc' }> }> = ({ fr }) => (
  <div style={{
    width: 430, padding: '18px 22px', borderRadius: 16, background: rgba(C.card, 0.94), border: `1.5px solid ${C.border}`,
    boxShadow: '0 30px 60px rgba(0,0,0,0.5)', fontFamily: INTER, textAlign: 'left',
  }}>
    <div style={{ fontFamily: MONO, fontSize: 21, color: C.teal, letterSpacing: '0.02em' }}>{fr.id}</div>
    <div style={{ fontSize: 30, fontWeight: 700, color: C.ink, marginTop: 6, letterSpacing: '-0.02em' }}>{fr.title}</div>
    <div style={{ fontSize: 24, color: C.ink2, marginTop: 4 }}>{fr.line}</div>
  </div>
);

const Conflict: React.FC<{ f: number; implode: number }> = ({ f, implode }) => {
  const c = iv(f, [205, 222], [0, 1], EASE.snappy);
  if (c <= 0) return null;
  const neq = iv(f, [226, 238], [0, 1], EASE.overshoot);
  const line = iv(f, [224, 234], [0, 1], EASE.swift);
  const glow = iv(f, [232, 240, 270], [0, 1, 0.45]);
  const card = (side: -1 | 1, eyebrow: string, title: string, sub: string, titleSize: number) => {
    const cx = CX + side * 330;
    const x = CX + (cx - CX) * (1 - implode);
    return (
      <div style={{
        position: 'absolute', left: x, top: CY, width: 520, transform: `translate(-50%,-50%) scale(${(0.6 + 0.52 * c) * (1 - implode)})`,
        opacity: c, filter: c < 0.99 ? `blur(${(1 - c) * 16}px)` : implode > 0 ? `grayscale(${implode})` : undefined,
        padding: '26px 30px', borderRadius: 20, background: rgba(C.card, 0.97), fontFamily: INTER,
        border: `2px solid ${rgba(C.red, 0.25 + 0.6 * glow)}`, boxShadow: `0 0 ${40 * glow}px ${rgba(C.red, 0.35 * glow)}, 0 40px 80px rgba(0,0,0,0.6)`,
      }}>
        <div style={{ fontFamily: MONO, fontSize: 22, color: C.ink2, letterSpacing: '0.08em' }}>{eyebrow}</div>
        <div style={{ fontSize: titleSize, fontWeight: 750, color: C.ink, marginTop: 10, letterSpacing: '-0.03em', lineHeight: 1.1 }}>{title}</div>
        <div style={{ fontSize: 26, color: C.ink2, marginTop: 10 }}>{sub}</div>
      </div>
    );
  };
  return (
    <>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0, opacity: 1 - implode }}>
        <line x1={CX - 70} y1={CY} x2={CX - 70 + 140 * line} y2={CY} stroke={C.red} strokeWidth={3} strokeOpacity={0.8} />
      </svg>
      {card(-1, 'LÉKAŘ · P03-neuro01', 'Neuropatie G1', 'hodnocení CTCAE', 60)}
      {card(1, 'PACIENT · P03-prom02', '„Padají mi věci z ruky.“', 'dotazník pacienta', 44)}
      <div style={{
        position: 'absolute', left: CX, top: CY, transform: `translate(-50%,-54%) scale(${neq * (1 - implode)})`, fontFamily: INTER,
        fontSize: 120, fontWeight: 800, color: C.red, textShadow: `0 0 40px ${rgba(C.red, 0.6)}`, background: C.void, padding: '0 14px', lineHeight: 1,
      }}>≠</div>
    </>
  );
};

const Timer: React.FC<{ f: number; implode: number }> = ({ f, implode }) => {
  const sec = Math.max(0, Math.floor((Math.min(f, FREEZE) - LOCAL0) / 30));
  const left = 300 - sec;
  const label = `0${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}`;
  const tick = iv((Math.min(f, FREEZE) - LOCAL0) % 30, [0, 8], [1.07, 1]);
  const warm = iv(f, [180, 270], [0, 1]);
  const op = iv(f, [LOCAL0, LOCAL0 + 14], [0, 1]) * (1 - implode);
  return (
    <div style={{ position: 'absolute', right: 130, top: 168, textAlign: 'right', opacity: op }}>
      <div style={{ fontFamily: MONO, fontSize: 20, letterSpacing: '0.22em', color: C.ink3 }}>ČAS NA PACIENTA</div>
      <div style={{
        fontFamily: MONO, fontSize: 64, fontWeight: 700, marginTop: 4, transform: `scale(${tick})`, transformOrigin: '100% 50%',
        color: warm > 0.5 ? C.amber : C.ink, textShadow: warm > 0.5 ? `0 0 26px ${rgba(C.amber, 0.45)}` : undefined,
      }}>{label}</div>
    </div>
  );
};

export const Flood: React.FC<{ f: number }> = ({ f }) => {
  if (f < LOCAL0 || f > S.ignite.from + 2) return null;
  const fe = Math.min(f, FREEZE);
  const implode = iv(f, [FREEZE, FREEZE + 18], [0, 1], EASE.exit);
  const dot = iv(f, [FREEZE + 10, FREEZE + 18], [0, 1]);
  return (
    <AbsoluteFill>
      {ITEMS.map((it, i) => {
        const raw = (fe - LOCAL0 - it.start) / it.dur;
        if (raw <= 0 || raw >= 1) return null;
        const u = raw ** 1.25;
        const p = proj(it.x, it.y, u);
        const q = proj(it.x, it.y, Math.max(0, ((fe - 1 - LOCAL0 - it.start) / it.dur) ** 1.25));
        // rozpor uprostřed: úryvky v jeho oblasti ztlumit, ať se nebijí
        const k = ((p.sx - CX) / 880) ** 2 + ((p.sy - CY) / 300) ** 2;
        const occl = f > 198 && k < 1 ? 0.06 + 0.94 * k ** 3 : 1;
        const op = life(u) * occl * (1 - implode);
        if (op < 0.01) return null;
        const sx = CX + (p.sx - CX) * (1 - implode);
        const sy = CY + (p.sy - CY) * (1 - implode);
        const vx = (p.sx - q.sx) * (1 - implode), vy = (p.sy - q.sy) * (1 - implode);
        const fog = u < 0.2 ? (1 - u / 0.2) * 2.4 : 0;
        const near = u > 0.84 ? (u - 0.84) * 46 : 0;
        const sp = Math.hypot(vx, vy);
        const isVal = it.fr.kind === 'val';
        const color = it.fr.kind === 'val' ? (it.fr.warn ? C.amber : C.ink) : undefined;
        const trail = isVal && sp > 5
          ? [1, 2, 3, 4, 5].map((j) => `${(-vx * j * 0.18 / p.s).toFixed(1)}px ${(-vy * j * 0.18 / p.s).toFixed(1)}px ${(j * 0.9).toFixed(1)}px ${rgba(color ?? C.ink, 0.22 - j * 0.035)}`).join(', ')
          : undefined;
        return (
          <div key={i} style={{
            position: 'absolute', left: sx, top: sy, whiteSpace: 'nowrap', lineHeight: 1,
            transform: `translate(-50%,-50%) scale(${(p.s * it.size * (1 - implode * 0.9)).toFixed(4)}) rotate(${it.rz}deg)`,
            opacity: op, filter: `${fog + near > 0.05 ? `blur(${((fog + near) / Math.max(0.6, p.s)).toFixed(2)}px)` : ''} ${implode > 0 ? `grayscale(${implode})` : ''}`.trim() || undefined,
          }}>
            {isVal ? (
              <div style={{ fontFamily: INTER, fontWeight: 750, fontSize: 82, letterSpacing: '-0.035em', color, textShadow: trail }}>{it.fr.kind === 'val' ? it.fr.text : ''}</div>
            ) : (
              <DocCard fr={it.fr as Extract<Frag, { kind: 'doc' }>} />
            )}
          </div>
        );
      })}
      <Conflict f={f} implode={implode} />
      <Timer f={f} implode={implode} />
      {dot > 0 && (
        <div style={{
          position: 'absolute', left: CX - 7, top: CY - 7, width: 14, height: 14, borderRadius: '50%', background: '#eafffb', opacity: dot,
          boxShadow: `0 0 18px 6px ${rgba(C.teal, 0.8)}, 0 0 60px 20px ${rgba(C.teal, 0.35)}`,
          transform: `scale(${1 + 0.35 * iv(f, [324, 329], [0, 1])})`,
        }} />
      )}
    </AbsoluteFill>
  );
};
