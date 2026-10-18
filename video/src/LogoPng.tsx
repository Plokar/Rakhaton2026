// Logo pro prezentaci (průhledné PNG): celé a samotná značka. Stejná SVG kresba jako ve videích.
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { LogoMark } from './common/Logo';

const FULL = { crossV: 1, crossH: 1, bubble: 1, bars: [1, 1, 1, 1, 1, 1], word: 1 };
export const LogoPng: React.FC<{ mark: boolean }> = ({ mark }) => (
  <AbsoluteFill style={{ alignItems: 'center', justifyContent: 'center' }}>
    <LogoMark width={mark ? 720 : 2000} s={FULL} showWord={!mark} />
  </AbsoluteFill>
);
