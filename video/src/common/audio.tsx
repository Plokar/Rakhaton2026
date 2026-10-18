// Zvuk jako časová osa (sound-design §1): hudba s náběhem/doběhem a duckingem pod VO, SFX v jedné tabulce.
import React from 'react';
import { Sequence, getStaticFiles, staticFile } from 'remotion';
import { Audio } from '@remotion/media';
import { iv } from '../theme';

export type Sfx = { from: number; src: string; volume: number; dur?: number; note: string };
export type VoSlot = { file: string; from: number; maxDur: number; text: string };

/** VO soubory, které uživatel dodal do public/audio/vo/ (chybějící se tiše přeskočí). */
export const presentVo = (slots: VoSlot[]) => {
  const files = new Set(getStaticFiles().map((f) => f.name));
  return slots.filter((s) => files.has(`audio/vo/${s.file}`));
};

export const SfxTrack: React.FC<{ items: Sfx[] }> = ({ items }) => (
  <>
    {items.map((s, i) => (
      <Sequence key={i} from={Math.max(0, Math.round(s.from))} durationInFrames={s.dur ?? 150} layout="none" name={`sfx ${s.note}`}>
        <Audio src={staticFile(`audio/sfx/${s.src}`)} volume={s.volume} />
      </Sequence>
    ))}
  </>
);

export const VoTrack: React.FC<{ slots: VoSlot[] }> = ({ slots }) => (
  <>
    {presentVo(slots).map((s) => (
      <Sequence key={s.file} from={s.from} durationInFrames={s.maxDur + 15} layout="none" name={`VO ${s.file}`}>
        <Audio src={staticFile(`audio/vo/${s.file}`)} volume={1} />
      </Sequence>
    ))}
  </>
);

/** Hudba: offset ve snímcích, obálka [klíče → hlasitost] a ducking 0.55 během přítomných VO. */
export const Music: React.FC<{
  src: string; offset: number; total: number; env: [number, number][]; vo?: VoSlot[]; duck?: number;
}> = ({ src, offset, total, env, vo = [], duck = 0.55 }) => {
  const live = presentVo(vo);
  return (
    <Sequence from={0} durationInFrames={total} layout="none" name="music">
      <Audio
        src={staticFile(`audio/${src}`)}
        trimBefore={offset}
        volume={(f) => {
          const base = iv(f, env.map((e) => e[0]), env.map((e) => e[1]));
          const d = live.reduce((m, s) => Math.min(m, iv(f, [s.from - 6, s.from, s.from + s.maxDur, s.from + s.maxDur + 10], [1, duck, duck, 1])), 1);
          return base * d;
        }}
      />
    </Sequence>
  );
};
