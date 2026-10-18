// Film B v2.1 · PRŮCHOD (1:30): logo jako v hooku → jeden souvislý záběr (navigace × čtení) → logo + QR (5,5 s).
import React from 'react';
import { AbsoluteFill, Img, staticFile, useCurrentFrame } from 'remotion';
import { Music, SfxTrack } from '../common/audio';
import { FilmLook, Hall } from '../common/Film';
import { LogoMark } from '../common/Logo';
import { LOGO, logoState } from '../common/LogoReveal';
import { EASE } from '../lib/Polish';
import { mulberry32 } from '../lib/rand';
import { C, INTER, MONO, iv, rgba } from '../theme';
import { ChapterLabel, Stage } from './Stage';
import { CHAPTERS, COMP, INTRO_LOGO, OUTRO, OUTRO_LOGO, SFX_B, T, WALK_MUSIC_ENV, WALK_TOTAL } from './timeline';

const LAP = { x: 64, y: 470, w: 560, h: 315 }; // obrazovka notebooku (16:9)
const SCR = { x: 712, y: 84, w: 1160, h: 712 }; // plátno v zasedačce
const PANEL = { x: 1036, y: 190, w: 420, h: 702 }; // náhled okna projektoru z editoru (stav po úpravě, ed3)

const Intro: React.FC<{ f: number }> = ({ f }) => {
  if (f > T.stageIn[1] + 2) return null;
  const out = iv(f, [T.stageIn[0], T.stageIn[1]], [0, 1], EASE.exit);
  const sub = iv(f, [INTRO_LOGO + 40, INTRO_LOGO + 54], [0, 1], EASE.snappy);
  return (
    <AbsoluteFill style={{ opacity: 1 - out, transform: `scale(${1 + 0.07 * out})`, filter: out > 0 ? `blur(${out * 10}px)` : undefined }}>
      <AbsoluteFill style={{ opacity: iv(f, [INTRO_LOGO + LOGO.bubble, INTRO_LOGO + LOGO.glow], [0, 0.9]), background: `radial-gradient(ellipse 34% 30% at 50% 44%, ${rgba(C.logoTeal, 0.16)} 0%, rgba(0,0,0,0) 75%)` }} />
      <div style={{ position: 'absolute', left: 960 - 560, top: 290 }}><LogoMark width={1120} s={logoState(f, INTRO_LOGO)} /></div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 720, textAlign: 'center', fontFamily: INTER, fontSize: 46, fontWeight: 500, color: C.ink2, opacity: sub, transform: `translateY(${(1 - sub) * 14}px)` }}>
        Jeden pacient · <span style={{ color: C.ink, fontWeight: 650 }}>jedno jednání komise</span>
      </div>
    </AbsoluteFill>
  );
};

/** 05: notebook předsedy + plátno v zasedačce (snímky z PACS a vedle panel MedTeam). */
const Room: React.FC<{ f: number; p: number; push: number }> = ({ f, p, push }) => {
  if (p <= 0.001) return null;
  const labels = 1 - Math.min(1, push * 2.5); // popisky zmizí při přiblížení na panel
  const on0 = COMP.in[1] - 6;
  const screenOn = iv(f, [on0, on0 + 4, on0 + 6, on0 + 10, on0 + 18], [0, 0.7, 0.25, 0.9, 1]) * iv(f, [COMP.out[0], COMP.out[0] + 14], [1, 0]);
  const dot = (((f - on0) % 46) + 46) % 46 / 46;
  const k = (SCR.h - 44) / PANEL.h;
  const pw = PANEL.w * k;
  return (
    <AbsoluteFill style={{ opacity: Math.min(1, p * 1.4) }}>
      {/* světlo projektoru */}
      <AbsoluteFill style={{ mixBlendMode: 'screen', filter: 'blur(40px)', opacity: 0.55 * screenOn }}>
        <div style={{ position: 'absolute', inset: 0, clipPath: `polygon(${SCR.x + SCR.w / 2 - 40}px -80px, ${SCR.x + SCR.w / 2 + 40}px -80px, ${SCR.x + SCR.w}px ${SCR.y + SCR.h}px, ${SCR.x}px ${SCR.y + SCR.h}px)`, background: `linear-gradient(180deg, ${rgba(C.teal, 0.2)}, rgba(0,0,0,0))` }} />
      </AbsoluteFill>
      {/* plátno */}
      <div style={{ position: 'absolute', left: SCR.x, top: SCR.y, width: SCR.w, height: SCR.h, borderRadius: 14, background: '#05080c', border: `2px solid ${C.border}`, overflow: 'hidden', boxShadow: `0 40px 120px rgba(0,0,0,0.6), 0 0 ${80 * screenOn}px ${rgba(C.teal, 0.12 * screenOn)}` }}>
        <div style={{ position: 'absolute', left: 22, top: 22, width: SCR.w - pw - 66, bottom: 22, borderRadius: 10, border: `1.5px dashed ${C.border}`, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 18, opacity: screenOn }}>
          <svg width={92} height={92} viewBox="0 0 24 24" fill="none" stroke={C.ink3} strokeWidth={1.3} strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2.5" /><circle cx="12" cy="12" r="5" /><path d="M12 7v10M7 12h10" />
          </svg>
          <div style={{ fontFamily: INTER, fontSize: 36, fontWeight: 600, color: C.ink2 }}>Snímky z PACS</div>
          <div style={{ fontFamily: INTER, fontSize: 28, color: C.ink3 }}>promítá radiolog</div>
        </div>
        <div style={{ position: 'absolute', right: 22, top: 22, width: pw, height: PANEL.h * k, borderRadius: 12, overflow: 'hidden', opacity: screenOn, boxShadow: `0 0 0 1.5px ${rgba(C.teal, 0.4)}` }}>
          <Img src={staticFile('textures/v2/ed3.png')} style={{ position: 'absolute', left: -PANEL.x * k, top: -PANEL.y * k, width: 1920 * k }} />
        </div>
      </div>
      <div style={{ position: 'absolute', left: SCR.x, top: SCR.y + SCR.h + 22, width: SCR.w, textAlign: 'center', fontFamily: INTER, fontSize: 36, fontWeight: 650, color: C.ink, opacity: screenOn * labels }}>
        Plátno v zasedačce <span style={{ color: C.ink3, fontWeight: 500 }}>· panel MedTeam vedle snímků</span>
      </div>
      {/* notebook: rám kolem zmenšeného záběru + deska */}
      <div style={{ position: 'absolute', left: LAP.x - 14, top: LAP.y - 14, width: LAP.w + 28, height: LAP.h + 28, borderRadius: 18, border: `2px solid ${C.border}`, background: 'transparent', boxShadow: '0 30px 80px rgba(0,0,0,0.6)' }} />
      <div style={{ position: 'absolute', left: LAP.x - 60, top: LAP.y + LAP.h + 16, width: LAP.w + 120, height: 22, borderRadius: '0 0 18px 18px', background: '#141c26', border: `1px solid ${C.border}` }} />
      <div style={{ position: 'absolute', left: LAP.x - 60, top: LAP.y + LAP.h + 60, width: LAP.w + 120, textAlign: 'center', fontFamily: INTER, fontSize: 36, fontWeight: 650, color: C.ink, opacity: labels }}>
        Notebook předsedy <span style={{ color: C.ink3, fontWeight: 500 }}>· řídí jednání</span>
      </div>
      {/* spojení: plátno se přepíná samo */}
      <svg width={1920} height={1080} style={{ position: 'absolute', inset: 0, opacity: screenOn }}>
        <path id="sync" d={`M ${LAP.x + LAP.w + 18} ${LAP.y + 70} C ${LAP.x + LAP.w + 40} ${LAP.y - 40}, ${SCR.x - 60} ${SCR.y + SCR.h * 0.7}, ${SCR.x - 4} ${SCR.y + SCR.h * 0.55}`} fill="none" stroke={rgba(C.teal, 0.55)} strokeWidth={2.5} strokeDasharray="8 10" />
        <circle r={7} fill="#dffffa" style={{ offsetPath: `path("M ${LAP.x + LAP.w + 18} ${LAP.y + 70} C ${LAP.x + LAP.w + 40} ${LAP.y - 40}, ${SCR.x - 60} ${SCR.y + SCR.h * 0.7}, ${SCR.x - 4} ${SCR.y + SCR.h * 0.55}")`, offsetDistance: `${dot * 100}%`, filter: `drop-shadow(0 0 8px ${C.teal})` } as React.CSSProperties} />
      </svg>
      <div style={{ position: 'absolute', left: LAP.x + LAP.w - 36, top: LAP.y - 104, padding: '10px 22px', borderRadius: 999, fontFamily: INTER, fontSize: 30, fontWeight: 600, color: C.teal, border: `1.5px solid ${rgba(C.teal, 0.5)}`, background: 'rgba(4,7,11,0.9)', opacity: screenOn }}>
        přepíná se samo
      </div>
    </AbsoluteFill>
  );
};

// živá vlna nahrávání (voice-waveform-live)
const WAVE = (() => { const r = mulberry32(5); return Array.from({ length: 64 }, () => ({ a: r(), b: r() * 6.28, c: 0.6 + r() * 1.4 })); })();
const Waveform: React.FC<{ f: number }> = ({ f }) => {
  const op = iv(f, [T.wave[0], T.wave[0] + 12, T.wave[1] - 12, T.wave[1]], [0, 1, 1, 0]);
  if (op <= 0) return null;
  const speech = 0.35 + 0.65 * Math.abs(Math.sin(f / 23) * Math.sin(f / 9.7 + 1.2));
  return (
    <>
      <div style={{ position: 'absolute', left: 960 - 520, top: 170, width: 1040, height: 150, borderRadius: 75, opacity: op, background: 'rgba(17,26,36,0.86)', border: `1px solid ${C.border}`, boxShadow: '0 30px 80px rgba(0,0,0,0.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
        <div style={{ width: 20, height: 20, borderRadius: 10, background: C.red, boxShadow: `0 0 16px ${C.red}`, opacity: 0.6 + 0.4 * Math.sin(f / 5), marginRight: 22 }} />
        {WAVE.map((w, i) => {
          const mid = 1 - Math.abs(i - 31.5) / 34;
          const h = 6 + 92 * speech * mid * (0.45 + 0.55 * Math.abs(Math.sin(f / (4 * w.c) + w.b))) * (0.6 + 0.4 * w.a);
          return <div key={i} style={{ width: 7, height: h, borderRadius: 4, background: i % 2 ? C.ink2 : C.ink }} />;
        })}
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 340, textAlign: 'center', fontFamily: INTER, fontSize: 36, fontWeight: 600, color: C.ink, opacity: op, textShadow: '0 4px 30px rgba(0,0,0,0.85)' }}>
        Diskuse komise → přepis (Whisper) → návrh zápisu
      </div>
    </>
  );
};

/** Klávesová zkratka (Z = Závěr komise, Esc = zavřít panel zdroje). */
const Key: React.FC<{ f: number; at: number; k: string; label: string }> = ({ f, at, k, label }) => {
  const p = iv(f, [at - 6, at, at + 14, at + 20], [0, 1, 1, 0]);
  if (p <= 0) return null;
  const press = iv(f, [at - 1, at + 1, at + 5], [0, 1, 0]);
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, top: 470, display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 22, opacity: p }}>
      <div style={{ height: 96, borderRadius: 18, background: '#1a2431', border: `2px solid ${C.border}`, borderBottomWidth: 8 - 5 * press, transform: `translateY(${4 * press}px)`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: INTER, fontSize: k.length > 1 ? 34 : 52, fontWeight: 700, color: C.ink, boxShadow: '0 20px 50px rgba(0,0,0,0.6)', minWidth: 96, padding: '0 14px' }}>{k}</div>
      <div style={{ fontFamily: INTER, fontSize: 44, fontWeight: 650, color: C.ink, textShadow: '0 4px 30px rgba(0,0,0,0.85)' }}>{label}</div>
    </div>
  );
};

const IrisChip: React.FC<{ f: number }> = ({ f }) => {
  const p = iv(f, [T.iris[0], T.iris[0] + 16], [0, 1], EASE.snappy) * iv(f, [T.iris[1] - 16, T.iris[1]], [1, 0]);
  if (p <= 0) return null;
  return (
    <div style={{ position: 'absolute', right: 64, bottom: 58, opacity: p, transform: `translateX(${(1 - p) * 40}px)` }}>
      <div style={{ padding: '16px 30px', borderRadius: 16, fontFamily: INTER, fontSize: 34, fontWeight: 650, color: C.teal, border: `1.5px solid ${rgba(C.teal, 0.5)}`, background: 'rgba(4,7,11,0.88)', boxShadow: '0 20px 50px rgba(0,0,0,0.5)' }}>
        InterSystems IRIS for Health · HL7 FHIR R4 · jedna transakce
      </div>
    </div>
  );
};

const Outro: React.FC<{ f: number }> = ({ f }) => {
  if (f < OUTRO) return null;
  const s = OUTRO_LOGO;
  const tag = iv(f, [s + 60, s + 74], [0, 1], EASE.snappy);
  const url = iv(f, [s + 66, s + 80], [0, 1], EASE.snappy);
  const qr = iv(f, [s + 18, s + 32], [0, 1], EASE.overshoot);
  const sweep = iv(f, [s + 34, s + 58], [0, 1], EASE.swift);
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ opacity: iv(f, [s + LOGO.bubble, s + LOGO.glow], [0, 0.85]), background: `radial-gradient(ellipse 40% 36% at 30% 42%, ${rgba(C.logoTeal, 0.14)} 0%, rgba(0,0,0,0) 75%)` }} />
      <div style={{ position: 'absolute', left: 110, top: 250 }}><LogoMark width={1040} s={logoState(f, s)} /></div>
      <div style={{ position: 'absolute', left: 150, top: 640, fontFamily: INTER, fontSize: 62, fontWeight: 750, letterSpacing: '-0.03em', color: C.ink, opacity: tag, transform: `translateY(${(1 - tag) * 14}px)` }}>
        AI předkládá. <span style={{ color: C.teal }}>Lékař rozhoduje.</span>
      </div>
      <div style={{ position: 'absolute', left: 152, top: 742, fontFamily: MONO, fontSize: 38, color: C.ink2, opacity: url }}>medteam.nervelabs.co.uk</div>
      <div style={{ position: 'absolute', left: 150, top: 960, fontFamily: INTER, fontSize: 32, fontWeight: 500, color: C.ink3, opacity: url }}>
        Rakathon 2026 · výzva Asseco CE · InterSystems IRIS for Health
      </div>
      {qr > 0 && (
        <div style={{ position: 'absolute', left: 1360, top: 250, width: 420, transform: `scale(${0.85 + 0.15 * qr})`, opacity: Math.min(1, qr * 1.5), transformOrigin: '50% 40%' }}>
          <div style={{ position: 'relative', width: 420, height: 420, borderRadius: 32, background: '#ffffff', padding: 28, boxShadow: `0 40px 100px rgba(0,0,0,0.6), 0 0 80px ${rgba(C.teal, 0.25)}`, overflow: 'hidden' }}>
            <Img src={staticFile('qr.svg')} style={{ width: 364, height: 364, display: 'block' }} />
            {/* logo uprostřed (oprava chyb H unese ~25 % plochy) */}
            <div style={{ position: 'absolute', left: 210 - 38, top: 210 - 38, width: 76, height: 76, borderRadius: 14, background: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width={52} height={52} viewBox="0 0 24 24"><path d="M9 2.5h6v6.5h6.5v6H15v6.5H9V15H2.5V9H9z" fill={C.logoRed} /></svg>
            </div>
            {sweep > 0 && sweep < 1 && <div style={{ position: 'absolute', top: -60, bottom: -60, width: 120, left: -160 + sweep * 640, background: 'linear-gradient(90deg, rgba(45,212,191,0), rgba(45,212,191,0.35), rgba(45,212,191,0))', transform: 'rotate(12deg)' }} />}
          </div>
          <div style={{ marginTop: 26, textAlign: 'center', fontFamily: INTER, fontSize: 38, fontWeight: 650, color: C.ink }}>Vyzkoušejte si demo</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

export const Walkthrough: React.FC<{ bgm: boolean }> = ({ bgm }) => {
  const f = useCurrentFrame();
  const pIn = iv(f, [COMP.in[0], COMP.in[1]], [0, 1], EASE.smooth);
  const pOut = iv(f, [COMP.out[0], COMP.out[1]], [1, 0], EASE.smooth);
  const p = Math.min(pIn, pOut);
  const push = iv(f, [COMP.push[0], COMP.push[1]], [0, 1], EASE.smooth) * iv(f, [COMP.push[2], COMP.push[3]], [1, 0], EASE.smooth);
  const k = LAP.w / 1920;
  const stageOn = f >= T.stageIn[0] && f <= T.stageOut[1] + 2;
  const stageOp = iv(f, [T.stageIn[0], T.stageIn[1]], [0, 1]) * iv(f, [T.stageOut[0], T.stageOut[1]], [1, 0]);
  const origin = `${SCR.x + SCR.w - 22 - (PANEL.w * (SCR.h - 44)) / PANEL.h / 2}px ${SCR.y + SCR.h / 2}px`; // střed panelu na plátně
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Hall glow={0.8} />
      <Intro f={f} />
      {stageOn && (
        <AbsoluteFill style={{ opacity: stageOp, transform: `scale(${1 + 0.3 * push})`, transformOrigin: origin }}>
          <Room f={f} p={p} push={push} />
          <AbsoluteFill style={{
            transform: `translate(${LAP.x * p}px, ${LAP.y * p}px) scale(${1 - (1 - k) * p})`, transformOrigin: '0 0',
            borderRadius: 18 * p / Math.max(k, 1 - (1 - k) * p), overflow: 'hidden',
          }}>
            <Stage f={f} tilt={iv(f, [T.stageIn[0], T.stageIn[0] + 70], [12, 0], EASE.out)} />
          </AbsoluteFill>
        </AbsoluteFill>
      )}
      <Waveform f={f} />
      <Key f={f} at={T.esc} k="Esc" label="Zavřít zdroj" />
      <Key f={f} at={T.keyZ} k="Z" label="Závěr komise" />
      <IrisChip f={f} />
      {CHAPTERS.map((c) => <ChapterLabel key={c.n} f={f} {...c} />)}
      <Outro f={f} />
      <FilmLook grain={0.05} vignette={0.4} />
      {bgm && <Music src="music-walk.mp3" offset={0} total={WALK_TOTAL} env={WALK_MUSIC_ENV} />}
      <SfxTrack items={SFX_B} />
    </AbsoluteFill>
  );
};
