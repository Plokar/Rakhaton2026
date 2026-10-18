// Filmová vrstva: temný sál, zrno, vinětace, letterbox a titulky (blur-slide, Q11: titulek ≥ 56 px).
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { Grain, Vignette, EASE } from '../lib/Polish';
import { C, INTER, iv, rgba } from '../theme';

/** Pozadí sálu: téměř černá s jemným tyrkysovým světlem odněkud zezadu. */
export const Hall: React.FC<{ glow?: number; gx?: number; gy?: number }> = ({ glow = 1, gx = 50, gy = 46 }) => (
  <AbsoluteFill style={{ background: C.void }}>
    <AbsoluteFill style={{
      opacity: glow,
      background: `radial-gradient(ellipse 60% 55% at ${gx}% ${gy}%, ${rgba(C.teal, 0.1)} 0%, ${rgba(C.tealDeep, 0.05)} 40%, rgba(0,0,0,0) 75%)`,
    }} />
  </AbsoluteFill>
);

/** Zrno + vinětace přes celý obraz (poslední vrstva před letterboxem). */
export const FilmLook: React.FC<{ grain?: number; vignette?: number }> = ({ grain = 0.07, vignette = 0.55 }) => (
  <>
    <Vignette strength={vignette} inner={0.42} color="#000000" />
    <Grain opacity={grain} blend="soft-light" step={2} />
  </>
);

/** Letterbox 2,39 : 1 (pruhy 138 px); open 0 = zavřeno, 1 = plný obraz. */
export const Letterbox: React.FC<{ open: number }> = ({ open }) => {
  const h = 138 * (1 - open);
  if (h < 0.5) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: h, background: '#000' }} />
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: h, background: '#000' }} />
    </AbsoluteFill>
  );
};

/** Titulek: po slovech vjede zespodu z rozmazání (blur-slide), na konci se rozplyne. */
export const Caption: React.FC<{
  text: string;
  from: number;
  to: number;
  size?: number;
  weight?: number;
  color?: string;
  accent?: string; // slova v *hvězdičkách* dostanou tuto barvu
  x?: number | 'center';
  y: number;
  align?: 'left' | 'center';
  stagger?: number;
  maxWidth?: number;
}> = ({ text, from, to, size = 64, weight = 750, color = C.ink, accent = C.teal, x = 'center', y, align = 'center', stagger = 3, maxWidth = 1500 }) => {
  const f = useCurrentFrame();
  if (f < from - 1 || f > to + 14) return null;
  const words = text.split(' ');
  const out = iv(f, [to, to + 12], [1, 0], EASE.exit);
  const outBlur = iv(f, [to, to + 12], [0, 10]);
  const left = x === 'center' ? 0 : x;
  return (
    <div style={{
      position: 'absolute', top: y, left, right: x === 'center' ? 0 : undefined, maxWidth: x === 'center' ? undefined : maxWidth,
      textAlign: align, fontFamily: INTER, fontSize: size, fontWeight: weight, letterSpacing: size >= 90 ? '-0.04em' : '-0.025em',
      lineHeight: 1.08, color, opacity: out, filter: outBlur > 0.1 ? `blur(${outBlur}px)` : undefined,
      textShadow: '0 4px 40px rgba(0,0,0,0.65)', whiteSpace: 'pre-wrap',
    }}>
      {words.map((w, i) => {
        const p = iv(f, [from + i * stagger, from + i * stagger + 14], [0, 1], EASE.snappy);
        const hot = w.startsWith('*');
        const clean = w.replace(/\*/g, '');
        return (
          <span key={i} style={{
            display: 'inline-block', opacity: p, transform: `translateY(${(1 - p) * 0.38}em)`,
            filter: p < 0.99 ? `blur(${(1 - p) * 14}px)` : undefined, color: hot ? accent : undefined,
            marginRight: i < words.length - 1 ? '0.26em' : 0,
          }}>{clean}</span>
        );
      })}
    </div>
  );
};

/** Výřez snímku stránky (CSS px stránky) ve zvoleném měřítku; textury jsou 2× → ostré do zoomu 2. */
export const Tex: React.FC<{
  src: string; x: number; y: number; w: number; h: number; scale?: number; radius?: number; style?: React.CSSProperties;
}> = ({ src, x, y, w, h, scale = 1, radius = 0, style }) => (
  <div style={{ position: 'relative', width: w * scale, height: h * scale, overflow: 'hidden', borderRadius: radius, ...style }}>
    <Img src={staticFile(`textures/${src}`)} style={{ position: 'absolute', left: -x * scale, top: -y * scale, width: 1920 * scale }} />
  </div>
);
