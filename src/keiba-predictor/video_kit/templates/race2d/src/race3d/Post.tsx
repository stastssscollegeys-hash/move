// 画の仕上げ（2026-11-20・race3d-quality T-004）。@react-three/postprocessing 2.19.1（React 18 で動く最後の版）
// 陰り（N8AO・半分の解像度）→ ギザギザ取り（SMAA）→ 色の調整（ACES）→ 周辺を少し暗く（Vignette）
// 色の調整はここだけ（ThreeCanvas は flat＝NoToneMapping にして二重にかけない・REV-R1-011）
//
// 2026-11-20 Codex の Must 3件で直した：
//  ・React.memo＝親が毎コマ描き直しても、ここは描き直さない（前は毎コマ EffectPass を作り直し、古いのを捨てていなかった）
//  ・SMAA の2枚の画像（埋め込み・読み込みは非同期）がそろうのを待ち、そろってから1回描いて onReady を呼ぶ
//  ・外れるときに、パスとコンポーザーを捨てる
import React, {useEffect, useRef} from 'react';
import {useThree} from '@react-three/fiber';
import {EffectComposer, N8AO, SMAA, ToneMapping, Vignette} from '@react-three/postprocessing';
import {ToneMappingMode, SMAAEffect, EffectComposer as Composer, Pass} from 'postprocessing';

// SMAA の画像がそろったか（そろうと weightsMaterial に searchTexture と areaTexture が入る）
export const smaaReady = (e: SMAAEffect) => {
  const m = e.weightsMaterial as unknown as {searchTexture: unknown; areaTexture: unknown};
  return !!m.searchTexture && !!m.areaTexture;
};

const PostImpl: React.FC<{onReady?: () => void}> = ({onReady}) => {
  const smaa = useRef<SMAAEffect>(null);
  const composer = useRef<Composer>(null);
  const advance = useThree((s) => s.advance);
  useEffect(() => {
    const e = smaa.current;
    const ev = e as unknown as {addEventListener(t: string, f: () => void): void; removeEventListener(t: string, f: () => void): void} | null;   // SMAAEffect は読み込み終わりに 'load' を出す（型の定義に無い）
    let done = false;
    const go = () => { if (done) return; done = true; advance(performance.now()); onReady?.(); };
    if (!e || smaaReady(e)) go();
    else ev!.addEventListener('load', go);
    return () => { done = true; ev?.removeEventListener('load', go); };
  }, [advance, onReady]);
  // 外れるときに捨てる。パスは EffectComposer の片づけ（先に走る）でリストから外れるので、ここで控えておく
  const passes = useRef<Pass[]>([]);
  useEffect(() => {
    passes.current = composer.current ? [...composer.current.passes] : [];
    const c = composer.current;
    return () => {
      for (const ps of passes.current) ps.dispose();
      c?.dispose();
    };
  }, []);
  return (
    <EffectComposer ref={composer} multisampling={0}>
      <N8AO aoRadius={1.6} intensity={2.2} distanceFalloff={1.0} halfRes />
      <SMAA ref={smaa as never} />
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
      <Vignette darkness={0.32} offset={0.32} />
    </EffectComposer>
  );
};
export const Post = React.memo(PostImpl);
