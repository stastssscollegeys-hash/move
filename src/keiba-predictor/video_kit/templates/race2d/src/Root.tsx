import React from 'react';
import {Composition} from 'remotion';
import {Race2D, Race2DProps} from './Race2D';
import {Race3DHQ} from './Race3DHQ';

// 大きさ・長さは frames.json（build_frames.py の出力）から決める。--props=frames.json で渡す
const meta = ({props}: {props: Record<string, unknown>}) => {
  const p = props as unknown as Race2DProps;
  return {durationInFrames: p.frames || 60, fps: p.fps || 30, width: p.w || 1080, height: p.h || 1652};
};

export const RemotionRoot: React.FC = () => (
  <>
  {/* 既定の3D（2026-11-20 ユーザー「切り替えて」で、手作りの馬の Race3D から切り替えた。Race3D は消した＝戻すなら git の履歴から） */}
  <Composition
    id="Race3DHQ"
    component={Race3DHQ as unknown as React.FC<Record<string, unknown>>}
    durationInFrames={60}
    fps={30}
    width={1080}
    height={1652}
    defaultProps={{} as Record<string, unknown>}
    calculateMetadata={meta}
  />
  <Composition
    id="Race2D"
    component={Race2D as unknown as React.FC<Record<string, unknown>>}
    durationInFrames={60}
    fps={30}
    width={1080}
    height={1652}
    defaultProps={{} as Record<string, unknown>}
    calculateMetadata={({props}) => {
      const p = props as unknown as Race2DProps;
      return {durationInFrames: p.frames || 60, fps: p.fps || 30, width: p.w || 1080, height: p.h || 1652};
    }}
  />
  </>
);
