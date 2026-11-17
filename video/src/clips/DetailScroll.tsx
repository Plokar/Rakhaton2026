// Klip „Průjezd podkladem“ (5 s, tmavý režim) podle whatsapp_inspirace.mp4: detail pacienta P02 se celý
// projede shora dolů. Panel, lišta, hlavička pacienta a navigace sekcí stojí (navigace přepíná aktivní sekci
// jako v aplikaci), obsah pod nimi jede. Rychlost řídí rozmazání pohybem a lehké oddálení s náklonem kamery.
// Textury: scripts/capture_scroll.mjs → public/textures/scroll/ (obsah po pruzích, pevné prvky, stavy navigace).
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { SfxTrack, type Sfx } from '../common/audio';
import { Hall } from '../common/Film';
import { EASE } from '../lib/Polish';
import { C, iv } from '../theme';
import S from '../../public/textures/scroll/scroll.json';

export const SCROLL_TOTAL = 150;
const MAX = S.height - 1080; // konec stránky: Hlas pacienta + Zeptat se na případ
const WARN = 6300; // Varovné signály těsně pod hlavičkou
const tex = (f: string) => staticFile(`textures/scroll/${f}`);

// posun stránky: klid → průjezd → nádech u varovných signálů → průjezd → dojezd (setrvačnost) → klid
const KEYS: [number, number, (t: number) => number][] = [
  [14, 0, EASE.linear], [58, WARN, EASE.smooth], [72, WARN + 140, EASE.linear], [116, MAX, EASE.swift],
];
const scrollAt = (f: number) => {
  let prevF = 0, prevS = 0;
  for (const [kf, ks, ease] of KEYS) {
    if (f <= kf) return f <= prevF ? prevS : prevS + (ks - prevS) * ease((f - prevF) / (kf - prevF));
    prevF = kf; prevS = ks;
  }
  return MAX;
};
const speedAt = (f: number) => Math.abs(scrollAt(f + 0.5) - scrollAt(f - 0.5));
const PEAK = Math.max(...Array.from({ length: SCROLL_TOTAL }, (_, f) => speedAt(f)));

/** Výřez snímku pevných prvků (1920 × 1080 CSS px, textura 2×). */
const Pin: React.FC<{ src: string; x: number; y: number; w: number; h: number }> = ({ src, x, y, w, h }) => (
  <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, backgroundImage: `url(${src})`, backgroundSize: '1920px 1080px', backgroundPosition: `${-x}px ${-y}px` }} />
);

export const DetailScroll: React.FC = () => {
  const f = useCurrentFrame();
  const s = scrollAt(f);
  const v = speedAt(f) / PEAK; // 0..1
  const blur = Math.min(24, speedAt(f) * 0.085);
  const scale = 1 - 0.075 * v;
  const tilt = 5 * v * (f < 72 ? 1 : 0.8);
  const nav = [...S.navStates].reverse().find((n) => s >= n.from - 250) ?? S.navStates[0]; // aktivní, jakmile je sekce vidět pod hlavičkou
  const tiles = S.tiles.filter((t) => t.y < s + 1080 + 200 && t.y + t.h > s - 200);
  const sfx: Sfx[] = [
    { from: 12, src: 'swoosh-quick.mp3', volume: 0.3, dur: 24, note: 'rozjezd' },
    { from: 14, src: 'whoosh-big.mp3', volume: 0.42, dur: 60, note: 'první průjezd (vrchol ~f36)' },
    { from: 56, src: 'air-zoom-vacuum.mp3', volume: 0.3, dur: 38, note: 'zpomalení u varovných signálů' },
    { from: 74, src: 'whoosh-fast.mp3', volume: 0.42, dur: 50, note: 'druhý průjezd' },
    { from: 114, src: 'transition-snap.mp3', volume: 0.45, dur: 20, note: 'dojezd na konec podkladu' },
    { from: 118, src: 'sparkle-touch.mp3', volume: 0.16, dur: 32, note: 'klid' },
  ];
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Hall glow={0.6} />
      <svg width={0} height={0} style={{ position: 'absolute' }}>
        <filter id="vblur" x="0" y="-5%" width="100%" height="110%"><feGaussianBlur stdDeviation={`0 ${blur.toFixed(2)}`} /></filter>
      </svg>
      <AbsoluteFill style={{ perspective: 2200, perspectiveOrigin: '50% 40%', opacity: iv(f, [0, 6], [0, 1]) }}>
        <div style={{
          position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 18 * v,
          transform: `scale(${scale}) rotateX(${tilt}deg)`, transformOrigin: '50% 45%',
          boxShadow: `0 0 0 ${1.5 * v}px ${C.border}, 0 40px 140px rgba(0,0,0,${0.7 * v})`,
        }}>
          {/* obsah stránky: jede pod pevnými prvky, rozmazaný podle rychlosti */}
          <div style={{ position: 'absolute', inset: 0, background: '#0b1118', filter: blur > 0.4 ? 'url(#vblur)' : undefined }}>
            {tiles.map((t) => <Img key={t.file} src={tex(t.file)} style={{ position: 'absolute', left: 0, top: t.y - s, width: 1920, height: t.h }} />)}
          </div>
          {/* pevné prvky aplikace */}
          {S.pinned.map((r, i) => i === 3
            ? <Img key={i} src={tex(nav.file)} style={{ position: 'absolute', left: r.x, top: r.y, width: r.w, height: r.h }} />
            : <Pin key={i} src={tex('chrome.png')} x={r.x} y={r.y} w={r.w} h={r.h} />)}
          {S.navStates.map((n) => <Img key={n.file} src={tex(n.file)} style={{ position: 'absolute', width: 1, height: 1, opacity: 0 }} />)}
        </div>
      </AbsoluteFill>
      <SfxTrack items={sfx} />
    </AbsoluteFill>
  );
};
