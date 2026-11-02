// Logo MedTeam jako SVG (originál v repu je JPG se zapečenou šachovnicí). Tmavá varianta pro film:
// „Med“ bílé místo navy a bublina s tyrkysovým obrysem, jinak by na černé zmizely (zapsáno ve FILM_SCENAR §2).
// Souřadnice podle MedTeam_logo.jpg zmenšeného na 2000 × 661.
import React from 'react';
import { C, MONT } from '../theme';

export type LogoState = {
  crossV: number; // svislé rameno: 0 = nad obrazem, 1 = na místě (může přestřelit)
  crossH: number; // vodorovné rameno: 0 = schované, 1 = celé
  bubble: number; // měřítko bubliny 0..1 (s přestřelem)
  bars: number[]; // výška pruhů vlny 0..1+ (6 pruhů)
  word: number; // odkrytí wordmarku zleva 0..1
  wordGlow?: number; // jednorázový lesk přes wordmark 0..1 (pozice sheen)
};

const BAR_H = [34, 74, 120, 86, 60, 28];
const CROSS = { cx: 338, cy: 376, arm: 228, th: 148, r: 26 };

export const LogoMark: React.FC<{ s: LogoState; showWord?: boolean; width?: number }> = ({ s, showWord = true, width = 1400 }) => {
  const vbW = showWord ? 2000 : 720;
  const k = width / vbW;
  const { cx, cy, arm, th, r } = CROSS;
  const vy = (1 - s.crossV) * -900;
  const hw = arm * s.crossH;
  return (
    <svg width={width} height={661 * k} viewBox={`0 0 ${vbW} 661`} style={{ overflow: 'visible' }}>
      <defs>
        <clipPath id="mt-word"><rect x={740} y={180} width={1220 * s.word} height={330} /></clipPath>
        <linearGradient id="mt-sheen" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity="0" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0.85" />
          <stop offset="1" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
        <filter id="mt-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="14" /></filter>
      </defs>
      {/* kříž */}
      {s.crossH > 0.001 && (
        <rect x={cx - hw} y={cy - th / 2} width={hw * 2} height={th} rx={r} fill={C.logoRed} />
      )}
      <g transform={`translate(0 ${vy})`}>
        <rect x={cx - th / 2} y={cy - arm} width={th} height={arm * 2} rx={r} fill={C.logoRed} />
      </g>
      {/* bublina s vlnou */}
      {s.bubble > 0.001 && (
        <g transform={`translate(556 175) scale(${s.bubble}) translate(-556 -175)`}>
          {/* kruh r = 118 se špičkou vlevo dole: body kruhu na 105° a 145°, dlouhý oblouk po směru hodin */}
          <path d="M 525.5 289 L 437 296 L 459.3 242.7 A 118 118 0 1 1 525.5 289 Z" fill={C.logoNavy} stroke={C.logoTeal} strokeOpacity={0.55} strokeWidth={5} strokeLinejoin="round" />
          {BAR_H.map((h, i) => {
            const bh = Math.max(6, h * (s.bars[i] ?? 0));
            return <rect key={i} x={479 + i * 28} y={175 - bh / 2} width={13} height={bh} rx={6.5} fill={C.logoTeal} />;
          })}
        </g>
      )}
      {/* wordmark */}
      {showWord && s.word > 0.001 && (
        <g clipPath="url(#mt-word)">
          <text x={752} y={446} fontFamily={MONT} fontWeight={800} fontSize={242} letterSpacing={-4}>
            <tspan fill={C.ink}>Med</tspan>
            <tspan fill={C.logoTeal}>Team</tspan>
          </text>
          {s.wordGlow !== undefined && s.wordGlow > 0 && s.wordGlow < 1 && (
            <rect x={700 + 1400 * s.wordGlow - 160} y={240} width={320} height={240} fill="url(#mt-sheen)" opacity={0.35} style={{ mixBlendMode: 'overlay' }} />
          )}
        </g>
      )}
    </svg>
  );
};
