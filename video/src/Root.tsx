import React from 'react';
import { Composition } from 'remotion';
import { Hook } from './hook/Hook';
import { HOOK20_TOTAL, HOOK_TOTAL } from './hook/timeline';
import { FPS, H, W } from './theme';
import { Walkthrough } from './walk/Walkthrough';
import { LogoPng } from './LogoPng';
import { PJ_H, PJ_TOTAL, PJ_W, ProjectorPreset } from './clips/ProjectorPreset';
import { DetailScroll, SCROLL_TOTAL } from './clips/DetailScroll';
import { BOT_TOTAL, Chatbot } from './clips/Chatbot';
import { WALK_TOTAL } from './walk/timeline';

export const Root: React.FC = () => (
  <>
    <Composition id="MedTeamHook" component={Hook} durationInFrames={HOOK_TOTAL} fps={FPS} width={W} height={H} defaultProps={{ bgm: true }} />
    <Composition id="MedTeamHook20" component={Hook} durationInFrames={HOOK20_TOTAL} fps={FPS} width={W} height={H} defaultProps={{ bgm: true, short: true }} />
    <Composition id="MedTeamWalkthrough" component={Walkthrough} durationInFrames={WALK_TOTAL} fps={FPS} width={W} height={H} defaultProps={{ bgm: true }} />
    <Composition id="KlipProjektor" component={ProjectorPreset} durationInFrames={PJ_TOTAL} fps={FPS} width={PJ_W} height={PJ_H} defaultProps={{ theme: 'dark' as const }} />
    <Composition id="KlipProjektorSvetly" component={ProjectorPreset} durationInFrames={PJ_TOTAL} fps={FPS} width={PJ_W} height={PJ_H} defaultProps={{ theme: 'light' as const }} />
    <Composition id="KlipPodklad" component={DetailScroll} durationInFrames={SCROLL_TOTAL} fps={FPS} width={W} height={H} />
    <Composition id="KlipChatbot" component={Chatbot} durationInFrames={BOT_TOTAL} fps={FPS} width={W} height={H} />
    <Composition id="LogoPng" component={LogoPng} durationInFrames={1} fps={FPS} width={2000} height={661} defaultProps={{ mark: false }} />
    <Composition id="MarkPng" component={LogoPng} durationInFrames={1} fps={FPS} width={720} height={661} defaultProps={{ mark: true }} />
  </>
);
