// Film A · HOOK „Pět minut“ (30 s). Scény čtou absolutní snímek, časování je v timeline.ts.
import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { Music, SfxTrack, VoTrack } from '../common/audio';
import { FilmLook, Hall, Letterbox } from '../common/Film';
import { EASE } from '../lib/Polish';
import { iv } from '../theme';
import { Brand } from './Brand';
import { Flood } from './Flood';
import { PanelStage } from './PanelStage';
import { Pulse } from './Pulse';
import { Rules } from './Rules';
import { HOOK_MUSIC_OFFSET, HOOK_TOTAL, MUSIC_ENV, SFX_A, VO_A } from './timeline';

export type HookProps = { bgm: boolean };

export const Hook: React.FC<HookProps> = ({ bgm }) => {
  const f = useCurrentFrame();
  const glow = iv(f, [0, 100, 110, 300, 318, 330, 340], [0.35, 0.35, 0.55, 0.7, 0, 0, 1]);
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Hall glow={glow} />
      <Pulse f={f} />
      <Flood f={f} />
      <PanelStage f={f} />
      <Rules f={f} />
      <Brand f={f} />
      <FilmLook grain={0.075} vignette={0.6} />
      <Letterbox open={iv(f, [775, 805], [0, 1], EASE.smooth)} />
      {bgm && <Music src="music-hook.mp3" offset={HOOK_MUSIC_OFFSET} total={HOOK_TOTAL} env={MUSIC_ENV} vo={VO_A} />}
      <SfxTrack items={SFX_A} />
      <VoTrack slots={VO_A} />
    </AbsoluteFill>
  );
};
