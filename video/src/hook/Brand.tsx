// A8 · Značka (f773–900): kříž dosedne na úder f773, bublina vyskočí na f797, vlna pulzuje a doběhne do klidu,
// wordmark se odkryje maskou a jedním leskem. Od f850 vše stojí (R1: hold ≥ 1 s).
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { LogoMark } from '../common/Logo';
import { LOGO, logoState } from '../common/LogoReveal';
import { EASE } from '../lib/Polish';
import { C, INTER, iv, rgba } from '../theme';
import { BEAT, S } from './timeline';

export const Brand: React.FC<{ f: number }> = ({ f }) => {
  if (f < S.brand.from) return null;
  const b6 = BEAT.b6;
  const glow = iv(f, [b6 + LOGO.bubble, b6 + LOGO.glow], [0, 1]);
  const bump = iv(f, [b6 + 10, b6 + 13, b6 + 24], [1, 1.014, 1]); // úder č. 3 na celý obraz
  const push = 1 + iv(f, [b6, 900], [0, 0.03]);
  const sub = iv(f, [834, 848], [0, 1], EASE.snappy);
  const credit = iv(f, [850, 864], [0, 1], EASE.snappy);
  return (
    <AbsoluteFill style={{ transform: `scale(${bump * push})` }}>
      <AbsoluteFill style={{
        opacity: glow * 0.9,
        background: `radial-gradient(ellipse 34% 30% at 50% 44%, ${rgba(C.logoTeal, 0.16)} 0%, ${rgba(C.logoTeal, 0.05)} 45%, rgba(0,0,0,0) 75%)`,
      }} />
      <div style={{ position: 'absolute', left: 960 - 650, top: 470 - 215 }}>
        <LogoMark width={1300} s={logoState(f, b6)} />
      </div>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 712, textAlign: 'center', fontFamily: INTER, fontSize: 46, fontWeight: 500,
        letterSpacing: '-0.01em', color: C.ink2, opacity: sub, transform: `translateY(${(1 - sub) * 16}px)`,
      }}>
        <span style={{ color: C.ink, fontWeight: 650 }}>MDT Copilot</span> · podklady pro onkologickou komisi
      </div>
      <div style={{
        position: 'absolute', left: 0, right: 0, top: 968, textAlign: 'center', fontFamily: INTER, fontSize: 32, fontWeight: 500,
        color: C.ink3, opacity: credit, letterSpacing: '0.01em',
      }}>
        Rakathon 2026 · výzva Asseco CE · InterSystems IRIS for Health
      </div>
    </AbsoluteFill>
  );
};
