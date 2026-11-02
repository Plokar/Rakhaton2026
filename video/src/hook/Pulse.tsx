// A1 · Tep (f0–110): EKG linka jako osciloskop (chart-live-moves) a tři věty na tři údery srdce (blur-slide).
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { EASE } from '../lib/Polish';
import { C, INTER, iv, rgba } from '../theme';
import { HEARTBEATS } from './timeline';

const ECG_Y = 760;
const dotX = (f: number) => iv(f, [0, 108], [-40, 2010]);
const BEAT_X = HEARTBEATS.map(dotX);
const g = (d: number, s: number) => Math.exp(-(d * d) / (2 * s * s));
const ecgY = (x: number) => {
  let y = 0;
  for (const bx of BEAT_X) {
    const d = x - bx;
    y += -16 * g(d + 70, 14) + 14 * g(d + 14, 4) - 175 * g(d, 5) + 48 * g(d - 13, 5) - 30 * g(d - 64, 18);
  }
  return ECG_Y + y;
};

const LINES = [
  { t: 'Pět specialistů.', f: HEARTBEATS[0] + 2 },
  { t: 'Pět minut.', f: HEARTBEATS[1] + 2 },
  { t: 'Jeden pacient.', f: HEARTBEATS[2] + 2, accent: true },
];

export const Pulse: React.FC<{ f: number }> = ({ f }) => {
  if (f > 120) return null;
  const dx = dotX(f);
  const pts: string[] = [];
  for (let x = Math.max(-40, dx - 1500); x <= dx; x += 3) pts.push(`${x.toFixed(1)},${ecgY(x).toFixed(1)}`);
  pts.push(`${dx.toFixed(1)},${ecgY(dx).toFixed(1)}`);
  const beatFlash = Math.max(...HEARTBEATS.map((b) => iv(f, [b - 1, b + 2, b + 12], [0, 1, 0])));
  const fade = iv(f, [96, 114], [1, 0], EASE.exit);
  // výstup vět: zmenší se do hloubky a rozmažou, jako by je pohltil tunel A2
  const recede = iv(f, [98, 118], [0, 1], EASE.exit);
  return (
    <AbsoluteFill style={{ opacity: fade }}>
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <linearGradient id="ecg-trail" gradientUnits="userSpaceOnUse" x1={dx - 1300} x2={dx} y1={0} y2={0}>
            <stop offset="0" stopColor={C.teal} stopOpacity={0} />
            <stop offset="0.7" stopColor={C.teal} stopOpacity={0.55} />
            <stop offset="1" stopColor="#d9fffa" stopOpacity={1} />
          </linearGradient>
          <filter id="ecg-blur" x="-10%" y="-50%" width="120%" height="200%"><feGaussianBlur stdDeviation="7" /></filter>
        </defs>
        <polyline points={pts.join(' ')} fill="none" stroke="url(#ecg-trail)" strokeWidth={10} opacity={0.45} filter="url(#ecg-blur)" />
        <polyline points={pts.join(' ')} fill="none" stroke="url(#ecg-trail)" strokeWidth={3.2} strokeLinejoin="round" />
        <circle cx={dx} cy={ecgY(dx)} r={26 + 30 * beatFlash} fill={rgba(C.teal, 0.12 + 0.25 * beatFlash)} filter="url(#ecg-blur)" />
        <circle cx={dx} cy={ecgY(dx)} r={5.5} fill="#eafffb" />
      </svg>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 268, textAlign: 'center', fontFamily: INTER,
        transform: `scale(${1 - 0.28 * recede})`, filter: recede > 0.01 ? `blur(${recede * 12}px)` : undefined, transformOrigin: '50% 60%',
      }}>
        {LINES.map((l, i) => {
          const p = iv(f, [l.f, l.f + 14], [0, 1], EASE.snappy);
          const next = LINES[i + 1];
          const dim = next ? iv(f, [next.f, next.f + 10], [1, 0.36]) : 1;
          return (
            <div key={i} style={{
              fontSize: 104, fontWeight: 800, letterSpacing: '-0.045em', lineHeight: 1.12,
              color: l.accent ? C.teal : C.ink, opacity: p * dim, transform: `translateY(${(1 - p) * 40}px)`,
              filter: p < 0.99 ? `blur(${(1 - p) * 16}px)` : undefined,
              textShadow: l.accent ? `0 0 40px ${rgba(C.teal, 0.35)}` : '0 4px 40px rgba(0,0,0,0.6)',
            }}>{l.t}</div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
