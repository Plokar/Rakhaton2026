// Film A · HOOK „Pět minut“ (30 s, nebo 20 s přes `short`). Scény čtou absolutní snímek 30s verze, časování je v timeline.ts.
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
import { HOOK20_MUSIC_OFFSET, HOOK20_TOTAL, HOOK_MUSIC_OFFSET, HOOK_TOTAL, MUSIC_ENV, MUSIC_ENV_20, SFX_A, SFX_A20, VO_A, VO_A20, oldFrame20 } from './timeline';

export type HookProps = { bgm: boolean; short?: boolean };

export const Hook: React.FC<HookProps> = ({ bgm, short = false }) => {
  const frame = useCurrentFrame();
  const f = short ? oldFrame20(frame) : frame; // 20s verze: stejné scény, rychlejší čas po úsecích
  const glow = iv(f, [0, 100, 110, 300, 318, 330, 340], [0.35, 0.35, 0.55, 0.7, 0, 0, 1]);
  return (
    <AbsoluteFill style={{ background: '#000' }}>
      <Hall glow={glow} />
      <Pulse f={f} />
      <Flood f={f} />
      <PanelStage f={f} short={short} />
      <Rules f={f} short={short} />
      <Brand f={f} />
      <FilmLook grain={0.075} vignette={0.6} />
      <Letterbox open={iv(f, [775, 805], [0, 1], EASE.smooth)} />
      {bgm && (short
        ? <Music src="music-hook.mp3" offset={HOOK20_MUSIC_OFFSET} total={HOOK20_TOTAL} env={MUSIC_ENV_20} vo={VO_A20} />
        : <Music src="music-hook.mp3" offset={HOOK_MUSIC_OFFSET} total={HOOK_TOTAL} env={MUSIC_ENV} vo={VO_A} />)}
      <SfxTrack items={short ? SFX_A20 : SFX_A} />
      <VoTrack slots={short ? VO_A20 : VO_A} />
    </AbsoluteFill>
  );
};
