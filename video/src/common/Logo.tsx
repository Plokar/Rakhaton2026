// Logo MDTcore: světlý symbol (public/brand/mdtcore-symbol.png) + wordmark MDTcore.
// Animace se drží stejného rozhraní LogoState jako dřív: bubble = zvětšení symbolu, word = odkrytí wordmarku zleva.
import React from 'react';
import { Img, staticFile } from 'remotion';
import { MONT } from '../theme';

export type LogoState = {
  crossV: number; // zachováno kvůli kompatibilitě scén, v novém logu se nepoužívá
  crossH: number; // zachováno kvůli kompatibilitě scén, v novém logu se nepoužívá
  bubble: number; // měřítko symbolu 0..1 (s přestřelem)
  bars: number[]; // zachováno kvůli kompatibilitě scén, v novém logu se nepoužívá
  word: number; // odkrytí wordmarku zleva 0..1
  wordGlow?: number; // zachováno kvůli kompatibilitě scén
};

const WORD_INK = '#f1f5f9'; // světlý text na tmavém „sále“
const WORD_ACCENT = '#38bdf8'; // „core“ světle modře, jako symbol

export const LogoMark: React.FC<{ s: LogoState; showWord?: boolean; width?: number }> = ({ s, showWord = true, width = 1400 }) => {
  const symbolSize = showWord ? width * 0.3 : width;
  const scale = 0.6 + 0.4 * Math.min(Math.max(s.bubble, 0), 1.08);
  const opacity = Math.min(1, Math.max(0, s.bubble));
  const reveal = Math.min(1, Math.max(0, s.word));
  return (
    <div style={{ position: 'relative', width, height: symbolSize, display: 'flex', alignItems: 'center', gap: width * 0.03 }}>
      <Img
        src={staticFile('brand/mdtcore-symbol.png')}
        style={{ width: symbolSize, height: symbolSize, flexShrink: 0, opacity, transform: `scale(${scale})`, transformOrigin: 'center' }}
      />
      {showWord && (
        <div
          style={{
            fontFamily: MONT,
            fontWeight: 700,
            fontSize: width * 0.13,
            lineHeight: 1,
            letterSpacing: -width * 0.004,
            whiteSpace: 'nowrap',
            clipPath: `inset(0 ${(1 - reveal) * 100}% 0 0)`,
          }}
        >
          <span style={{ color: WORD_INK }}>MDT</span>
          <span style={{ color: WORD_ACCENT }}>core</span>
        </div>
      )}
    </div>
  );
};
