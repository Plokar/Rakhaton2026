// Kurzor jako „ruka“ (cursor-flyover): šipka, stisk 0.84 s přestřelem zpět a kruh dopadu po kliknutí.
import React from 'react';
import { EASE } from '../lib/Polish';
import { C, iv, rgba } from '../theme';

export type CursorKey = { f: number; x: number; y: number };

/** Pozice kurzoru mezi klíči (swift easing, mírný oblouk nahoru). */
export const cursorAt = (keys: CursorKey[], f: number) => {
  if (f <= keys[0].f) return keys[0];
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1];
    if (f <= b.f) {
      const t = iv(f, [a.f, b.f], [0, 1], EASE.swift);
      const arc = Math.sin(Math.PI * t) * Math.min(60, Math.hypot(b.x - a.x, b.y - a.y) * 0.12);
      return { f, x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t - arc };
    }
  }
  return keys[keys.length - 1];
};

export const Cursor: React.FC<{ x: number; y: number; f: number; clicks: number[]; size?: number; opacity?: number }> = ({ x, y, f, clicks, size = 44, opacity = 1 }) => {
  let press = 1;
  let ring = 0;
  let ringP = 0;
  for (const c of clicks) {
    if (f >= c - 3 && f <= c + 8) press = Math.min(press, iv(f, [c - 3, c, c + 8], [1, 0.84, 1], EASE.overshoot));
    if (f >= c && f <= c + 18) { ringP = iv(f, [c, c + 18], [0, 1], EASE.out); ring = 1 - ringP; }
  }
  return (
    <>
      {ring > 0 && (
        <div style={{
          position: 'absolute', left: x - 34 * (0.4 + ringP), top: y - 34 * (0.4 + ringP), width: 68 * (0.4 + ringP), height: 68 * (0.4 + ringP),
          borderRadius: '50%', border: `3px solid ${rgba(C.teal, 0.9 * ring)}`, boxShadow: `0 0 24px ${rgba(C.teal, 0.6 * ring)}`,
        }} />
      )}
      <svg width={size} height={size} viewBox="0 0 24 24" style={{
        position: 'absolute', left: x - size * 0.18, top: y - size * 0.1, opacity,
        transform: `scale(${press})`, transformOrigin: '18% 10%', filter: 'drop-shadow(0 6px 10px rgba(0,0,0,0.55))',
      }}>
        <path d="M4.3 2.6 L19.6 12.3 L12.6 13.6 L16.4 21.2 L13.7 22.5 L9.9 14.9 L4.6 19.6 Z" fill="#ffffff" stroke="#0b1118" strokeWidth={1.4} strokeLinejoin="round" />
      </svg>
    </>
  );
};
