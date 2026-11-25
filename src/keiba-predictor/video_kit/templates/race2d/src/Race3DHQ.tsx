// レース展開の3D・高品質版（2026-11-20・race3d-quality）。既定の3D（2026-11-20 ユーザーの承認で、手作りの馬の Race3D から切り替え・Race3D は消した）。
// 馬＝Quaternius Horse（CC0・public/horse.glb）／計算＝src/race3d/logic.ts（コマ番号だけで決まる）／景色＝race3d/Scene.tsx／仕上げ＝race3d/Post.tsx
// 上の帯・順位・全体図＝Race2D overlayOnly
//
// 待ち方（2026-11-20 Codex の Must 3件で直した）：
//  ・読み込みごとに待ちを1つ持つ。馬を組み、仕上げの処理（SMAA の画像）がそろってから ThreeCanvas を出し、
//    中で1回描き終えてから待ちを外す（前は馬の読み込みの前に1コマ目を描いて、そのまま待ちを外すことがあり得た）
//  ・読み込みの途中で外れた・horseFile が変わったときは、その回の待ちを外し、組んだ馬と GLB を捨てる
//  ・失敗したときは、その回の読み込みだけを cancelRender に渡す
import React, {useCallback, useLayoutEffect, useMemo, useState} from 'react';
import {AbsoluteFill, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import {ThreeCanvas} from '@remotion/three';
import {useThree} from '@react-three/fiber';
import {Race2D, Race2DProps} from './Race2D';
import {cameraAt, checkProps, cumDistTable, gallopTime, groundPos, hasStarted, winnerIndex, yawAt, CalcProps, V3} from './race3d/logic';
import {buildField, disposeField, disposeKit, loadHorseKit, poseRig, HorseRig} from './race3d/horses';
import {Scene} from './race3d/Scene';
import {Post} from './race3d/Post';

export type Race3DHQProps = Race2DProps & {horseFile?: string; track: Race2DProps['track'] & {stand?: number[][]; poles?: {u: number; p: number[]}[]}};

const NO_STAND: number[][] = [];                      // 無いときも毎コマ同じ物を渡す（新しい [] だと景色を毎コマ作り直す・Codex の Must）
const NO_POLES: {u: number; p: number[]}[] = [];

const CameraRig: React.FC<{pos: V3; target: V3; fov: number}> = ({pos, target, fov}) => {
  const {camera} = useThree();
  if ('fov' in camera) (camera as {fov: number}).fov = fov;   // 毎コマ当て直す（望遠のショットのあとに戻すため）
  camera.position.set(pos[0], pos[1], pos[2]);
  camera.lookAt(target[0], target[1], target[2]);
  camera.updateProjectionMatrix();
  return null;
};

const SHADOW_SPAN = 70, SHADOW_MAP = 2048;
const TEXEL = (SHADOW_SPAN * 2) / SHADOW_MAP;   // 影の1画素の幅（m）。光の位置をこの幅にそろえて、影のちらつきを防ぐ（REV-R1-012）
const snap = (v: number) => Math.round(v / TEXEL) * TEXEL;

type Field = {key: string; rigs: HorseRig[]; release: () => void};

export const Race3DHQ: React.FC<Race3DHQProps> = (p) => {
  useMemo(() => checkProps(p as unknown as CalcProps), [p.frame, p.horses, p.w, p.h]);   // 入力がおかしければ分かる言葉で止める
  const f = useCurrentFrame();
  const n = p.frame.length;
  const ff = Math.min(f, n - 1);
  const F = p.frame[ff];
  const [field, setField] = useState<Field | null>(null);
  const url = staticFile(p.horseFile || 'horse.glb');
  const horseKey = `${url}|` + p.horses.map((h) => `${h.umaban}:${h.waku}`).join(',');   // 中身が同じなら読み直さない（T-003 のレビュー）
  // 待ちは描いた直後（layout effect）に取る＝最初の描画から待ちが0件の隙間を作らない（2026-11-20 検査役の Should）
  useLayoutEffect(() => {
    const hold = delayRender('馬のモデルを読み込んで、最初のコマを描き終えるまで待っています');
    let alive = true, released = false;
    const release = () => { if (!released) { released = true; continueRender(hold); } };
    let kit: Awaited<ReturnType<typeof loadHorseKit>> | null = null, rigs: HorseRig[] | null = null;
    loadHorseKit(url)
      .then((k) => {
        kit = k;
        if (!alive) { disposeKit(k); return; }
        rigs = buildField(k, p.horses);
        setField({key: horseKey, rigs, release});
      })
      .catch((e) => { if (alive) cancelRender(e instanceof Error ? e : new Error('馬のモデルが読めません')); });
    return () => {
      alive = false;
      release();
      if (rigs) disposeField(rigs);
      if (kit) disposeKit(kit);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [horseKey]);
  const ready = field && field.key === horseKey ? field : null;   // 古い馬は描かない（読み直しの間は ThreeCanvas を出さない）

  const calc = p as unknown as CalcProps;
  const dist = useMemo(() => cumDistTable(p.frame), [p.frame]);
  if (ready) {
    ready.rigs.forEach((r, i) => {
      const [x, z] = groundPos(F, i);
      poseRig(r, x, z, yawAt(p.frame, i, ff), gallopTime(dist[ff][i], r.gallop.getClip().duration), hasStarted(dist, ff, i));
    });
  }
  const cam = cameraAt(calc, f);
  const tall = p.h > p.w;
  const tx = snap(cam.target[0]), tz = snap(cam.target[2]);
  const sun: [number, number, number] = [60, 90, 40];
  const w = winnerIndex(calc);
  const ring: [number, number] | null = p.mode !== 'forecast' && F.phase === 'ゴール' ? groundPos(F, w) : null;
  const onPostReady = useCallback(() => { ready?.release(); }, [ready]);
  return (
    <AbsoluteFill style={{background: '#9cd0f2'}}>
      {ready && (
        <ThreeCanvas width={p.w} height={p.h} shadows flat gl={{antialias: false}} camera={{fov: tall ? 40 : 32, near: 0.3, far: 5000}}>
          <CameraRig pos={cam.pos} target={cam.target} fov={cam.fov ?? (tall ? 40 : 32)} />
          <hemisphereLight args={['#e3f2ff', '#4c6a3a', 0.85]} />
          <directionalLight position={[tx + sun[0], sun[1], tz + sun[2]]} intensity={2.3} castShadow
            shadow-mapSize-width={SHADOW_MAP} shadow-mapSize-height={SHADOW_MAP} shadow-camera-left={-SHADOW_SPAN} shadow-camera-right={SHADOW_SPAN}
            shadow-camera-top={SHADOW_SPAN} shadow-camera-bottom={-SHADOW_SPAN} shadow-camera-near={10} shadow-camera-far={320} shadow-bias={-0.0003} shadow-normalBias={0.02}>
            <object3D attach="target" position={[tx, 0, tz]} />
          </directionalLight>
          <Scene shapes={p.track.shapes} marks={p.track.marks} stand={p.track.stand || NO_STAND} poles={p.track.poles || NO_POLES} winnerRing={ring} sun={sun} />
          {ready.rigs.map((r, i) => <primitive key={p.horses[i].umaban} object={r.root} />)}
          {/* 最後に置く：ほかの物がそろってから、仕上げの準備を待って1回描き、待ちを外す */}
          <Post onReady={onPostReady} />
        </ThreeCanvas>
      )}
      <Race2D {...p} overlayOnly />
    </AbsoluteFill>
  );
};
