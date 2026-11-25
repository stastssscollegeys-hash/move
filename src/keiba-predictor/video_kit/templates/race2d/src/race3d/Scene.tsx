// 景色（2026-11-20・race3d-quality T-004）。外へ取りに行かない（絵はその場で描く・空は three 同梱の Sky）
// 空（Sky）・霧・地面の芝・芝コースとダートの質感・白い柵と柱（fence）・引き込み線・木（trees）・スタンド（stand）・ハロン棒（poles）・
// ゴールの線と柱（goal）・勝った馬の足元の金色の輪（winnerRing）
// 座標：3D の x＝frames の x、z＝−frames の y
import React, {useEffect, useMemo} from 'react';
import * as THREE from 'three';
import {Sky} from 'three/examples/jsm/objects/Sky.js';
import type {Mark} from './logic';

type Shapes = Record<string, number[][][] | number[][]>;
export type SceneProps = {shapes: Shapes | null | undefined; marks: Mark[]; stand: number[][]; poles: {u: number; p: number[]}[]; winnerRing: [number, number] | null; sun: [number, number, number]};

const rnd = (n: number) => { const x = Math.sin(n * 12.9898) * 43758.5453; return x - Math.floor(x); };   // 決まった乱数（毎回同じ絵）

const canvasTex = (w: number, h: number, draw: (x: CanvasRenderingContext2D) => void, rep: number) => {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d')!);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep, rep); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
};
const dirtTex = () => canvasTex(512, 512, (x) => {
  x.fillStyle = '#b5824f'; x.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 9000; i++) { const v = rnd(i); x.fillStyle = v > 0.55 ? 'rgba(92,56,26,0.20)' : v > 0.2 ? 'rgba(232,196,146,0.16)' : 'rgba(60,36,18,0.25)'; const s = 1 + v * 2.5; x.fillRect(rnd(i + 7) * 512, rnd(i + 13) * 512, s, s); }
  for (let i = 0; i < 60; i++) { x.strokeStyle = 'rgba(80,50,24,0.10)'; x.lineWidth = 2; x.beginPath(); const y = rnd(i + 900) * 512; x.moveTo(0, y); x.lineTo(512, y + (rnd(i + 950) - 0.5) * 30); x.stroke(); }   // 蹄の跡の筋
}, 1 / 8);
const turfTex = () => canvasTex(512, 512, (x) => {
  for (let i = 0; i < 4; i++) { x.fillStyle = i % 2 ? '#5aa851' : '#4f9a48'; x.fillRect(0, i * 128, 512, 128); }   // 刈り目の縞
  for (let i = 0; i < 12000; i++) { x.fillStyle = rnd(i) > 0.5 ? 'rgba(20,60,20,0.13)' : 'rgba(210,255,190,0.08)'; x.fillRect(rnd(i + 3) * 512, rnd(i + 5) * 512, 1, 2 + rnd(i + 8) * 2); }
}, 1 / 24);
const grassTex = () => canvasTex(256, 256, (x) => {
  x.fillStyle = '#3e7d3d'; x.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 5000; i++) { x.fillStyle = rnd(i + 99) > 0.5 ? 'rgba(10,40,10,0.15)' : 'rgba(180,240,160,0.08)'; x.fillRect(rnd(i + 31) * 256, rnd(i + 37) * 256, 1, 2); }
}, 1 / 14);
const standTex = () => canvasTex(1024, 256, (x) => {
  x.fillStyle = '#cfd5dd'; x.fillRect(0, 0, 1024, 256);
  for (let r = 0; r < 16; r++) for (let c = 0; c < 128; c++) {   // 客席（人がまばらに座っている）
    const v = rnd(r * 197 + c); x.fillStyle = v > 0.72 ? '#33415e' : v > 0.5 ? '#8a3d3d' : v > 0.32 ? '#ece6da' : v > 0.18 ? '#4d5560' : '#9aa3ad';
    x.fillRect(c * 8 + 1, 18 + r * 14, 6, 9);
  }
}, 1);

const flat = (outer: number[][], hole?: number[][]) => {
  const sh = new THREE.Shape(outer.map((q) => new THREE.Vector2(q[0], q[1])));
  if (hole) sh.holes.push(new THREE.Path(hole.map((q) => new THREE.Vector2(q[0], q[1]))));
  const g = new THREE.ShapeGeometry(sh, 1);
  g.rotateX(-Math.PI / 2);
  return g;
};
// 白い柵の横木（線にそった細い帯）
const fence = (pts: number[][], y0: number, y1: number) => {
  const P = [...pts, pts[0]], pos: number[] = [];
  for (let i = 0; i < P.length - 1; i++) {
    const a = P[i], b = P[i + 1];
    pos.push(a[0], y0, -a[1], b[0], y0, -b[1], b[0], y1, -b[1], a[0], y0, -a[1], b[0], y1, -b[1], a[0], y1, -a[1]);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.computeVertexNormals();
  return g;
};
// 柵の柱（線にそって間隔 step m）
const postMatrices = (pts: number[][], step: number) => {
  const out: THREE.Matrix4[] = []; let acc = 0;
  for (let i = 0; i < pts.length; i++) {
    const a = pts[i], b = pts[(i + 1) % pts.length]; const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
    acc += l;
    if (acc >= step) { acc = 0; out.push(new THREE.Matrix4().makeTranslation(a[0], 0.48, -a[1])); }
  }
  return out;
};

const Instances: React.FC<{geo: THREE.BufferGeometry; mat: THREE.Material; mats: THREE.Matrix4[]; shadow?: boolean}> = ({geo, mat, mats, shadow}) => {
  const mesh = useMemo(() => {
    const m = new THREE.InstancedMesh(geo, mat, Math.max(1, mats.length));
    mats.forEach((x, i) => m.setMatrixAt(i, x)); m.count = mats.length; m.castShadow = !!shadow; m.receiveShadow = true;
    m.instanceMatrix.needsUpdate = true;
    return m;
  }, [geo, mat, mats, shadow]);
  useEffect(() => () => mesh.dispose(), [mesh]);   // 作り直し・外れるときに並べた位置の GPU の物を捨てる（形と材質は env の片づけで）
  return <primitive object={mesh} />;
};

export const Scene: React.FC<SceneProps> = ({shapes, marks, stand, poles, winnerRing, sun}) => {
  const env = useMemo(() => {
    const sky = new Sky(); sky.scale.setScalar(4500);   // far（5000）の中に収める
    const u = sky.material.uniforms;
    u.turbidity.value = 4; u.rayleigh.value = 1.4; u.mieCoefficient.value = 0.004; u.mieDirectionalG.value = 0.8;
    const dt = dirtTex(), tt = turfTex(), gt = grassTex(), st = standTex();
    const turfOut = shapes?.['芝外'] as number[][][] | undefined;   // 2026-11-20 外回り（新潟・中山・京都・阪神）
    const turf = shapes?.['芝'] as number[][][] | undefined, dirt = shapes?.['ダート'] as number[][][] | undefined, chute = shapes?.['chute'] as number[][] | undefined;
    const tchute = shapes?.['芝直線'] as number[][] | undefined;   // 新潟の直線1000m の延ばした所（芝）
    const all = shapes ? Object.values(shapes).flatMap((v) => (Array.isArray((v as number[][][])[0][0]) ? (v as number[][][]).flat() : (v as number[][]))) : [];
    const cx = all.length ? all.reduce((a, q) => a + q[0], 0) / all.length : 0, cy = all.length ? all.reduce((a, q) => a + q[1], 0) / all.length : 0;
    // 木：外の輪から外へ 45〜140m に決まった乱数で（スタンドの近くは避ける）
    const outer = turfOut ? turfOut[1] : turf ? turf[1] : dirt ? dirt[1] : [];
    const trees: THREE.Matrix4[] = [];
    outer.forEach((q, i) => {
      if (i % 3) return;
      const dx = q[0] - cx, dy = q[1] - cy, l = Math.hypot(dx, dy) || 1;
      for (let k = 0; k < 3; k++) {
        const d = 45 + rnd(i * 7 + k) * 95; const x = q[0] + (dx / l) * d + (rnd(i + k * 3) - 0.5) * 24, y = q[1] + (dy / l) * d;
        if (stand.some((s) => Math.hypot(s[0] - x, s[1] - y) < 80)) continue;
        const h = 9 + rnd(i * 13 + k) * 9;
        trees.push(new THREE.Matrix4().compose(new THREE.Vector3(x, 0, -y), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), rnd(i + k) * 6), new THREE.Vector3(h / 12, h / 12, h / 12)));
      }
    });
    const rails = [dirt?.[0], dirt?.[1], turf?.[0], turf?.[1], turfOut?.[0], turfOut?.[1]].filter(Boolean) as number[][][];
    return {
      sky, dt, tt, gt, st, cx, cy,
      turfOut: turfOut ? flat(turfOut[1], turfOut[0]) : null,
      turf: turf ? flat(turf[1], turf[0]) : null, dirt: dirt ? flat(dirt[1], dirt[0]) : null, chute: chute ? flat(chute) : null, tchute: tchute ? flat(tchute) : null,
      fences: rails.map((r) => fence(r, 0.78, 0.96)),
      posts: rails.flatMap((r) => postMatrices(r, 4)),
      trees,
      postGeo: new THREE.CylinderGeometry(0.05, 0.05, 0.96, 6), postMat: new THREE.MeshStandardMaterial({color: '#ffffff', roughness: 0.5}),
      trunkGeo: new THREE.CylinderGeometry(0.35, 0.5, 4.5, 6).translate(0, 2.25, 0), trunkMat: new THREE.MeshStandardMaterial({color: '#5a3f28', roughness: 1}),
      leafGeo: new THREE.ConeGeometry(3.6, 9, 8).translate(0, 8, 0), leafMat: new THREE.MeshStandardMaterial({color: '#2f6b34', roughness: 1}),
    };
  }, [shapes, stand]);
  // 景色を作り直す・外れるときに、ここで作った形・材質・絵を捨てる（2026-11-20 Codex の Must。R3F は props で渡した形や絵を捨てない）
  useEffect(() => () => {
    env.sky.geometry.dispose(); env.sky.material.dispose();
    for (const t of [env.dt, env.tt, env.gt, env.st]) t.dispose();
    for (const g of [env.turfOut, env.turf, env.dirt, env.chute, env.tchute, ...env.fences, env.postGeo, env.trunkGeo, env.leafGeo]) g?.dispose();
    for (const m of [env.postMat, env.trunkMat, env.leafMat]) m.dispose();
  }, [env]);
  env.sky.material.uniforms.sunPosition.value.set(sun[0], sun[1], sun[2]).normalize();
  const goal = marks.find((m) => m.u === 0);
  return (
    <>
      <primitive object={env.sky} />
      <fog attach="fog" args={['#cfe6f4', 220, 1500]} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.04, 0]} receiveShadow>
        <planeGeometry args={[9000, 9000]} />
        <meshStandardMaterial map={env.gt} roughness={1} />
      </mesh>
      {env.turfOut && <mesh geometry={env.turfOut} position={[0, 0.005, 0]} receiveShadow><meshStandardMaterial map={env.tt} roughness={0.95} /></mesh>}
      {env.turf && <mesh geometry={env.turf} position={[0, 0.01, 0]} receiveShadow><meshStandardMaterial map={env.tt} roughness={0.95} /></mesh>}
      {env.dirt && <mesh geometry={env.dirt} position={[0, 0.02, 0]} receiveShadow><meshStandardMaterial map={env.dt} roughness={1} /></mesh>}
      {env.tchute && <mesh geometry={env.tchute} position={[0, 0.015, 0]} receiveShadow><meshStandardMaterial map={env.tt} roughness={0.95} /></mesh>}
      {env.chute && <mesh geometry={env.chute} position={[0, 0.02, 0]} receiveShadow><meshStandardMaterial map={env.dt} roughness={1} /></mesh>}
      {/* fence：白い柵の横木と柱 */}
      {env.fences.map((g, i) => <mesh key={'f' + i} geometry={g} castShadow><meshStandardMaterial color="#ffffff" side={THREE.DoubleSide} roughness={0.4} /></mesh>)}
      <Instances geo={env.postGeo} mat={env.postMat} mats={env.posts} />
      {/* trees：コースの外の木 */}
      <Instances geo={env.trunkGeo} mat={env.trunkMat} mats={env.trees} />
      <Instances geo={env.leafGeo} mat={env.leafMat} mats={env.trees} shadow />
      {/* stand：ゴール前の直線の外のスタンド（コースから離れる向きに建てる） */}
      {stand.slice(0, -1).map((a, i) => {
        const b = stand[i + 1]; const mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2; const len = Math.hypot(b[0] - a[0], b[1] - a[1]) + 0.6;
        let ox = -(b[1] - a[1]), oy = b[0] - a[0]; const ol = Math.hypot(ox, oy) || 1; ox /= ol; oy /= ol;
        if ((mx - env.cx) * ox + (my - env.cy) * oy < 0) { ox = -ox; oy = -oy; }
        const ang = Math.atan2(ox, -oy);   // ローカルの +Z＝コースから離れる向き
        return (
          <group key={'s' + i} position={[mx, 0, -my]} rotation={[0, ang, 0]}>
            <mesh position={[0, 7, 13]} rotation={[-0.5, 0, 0]} receiveShadow><boxGeometry args={[len, 0.6, 28]} /><meshStandardMaterial map={env.st} roughness={0.9} /></mesh>
            <mesh position={[0, 3, 1]}><boxGeometry args={[len, 6, 2]} /><meshStandardMaterial color="#d8dde4" roughness={0.7} /></mesh>
            {/* 屋根は影を落とさない（2026-11-20 直線のダートに大きな黒い帯が出た） */}
            <mesh position={[0, 26, 18]}><boxGeometry args={[len, 0.8, 30]} /><meshStandardMaterial color="#eef1f5" roughness={0.5} /></mesh>
            <mesh position={[0, 13, 31]}><boxGeometry args={[len, 26, 2]} /><meshStandardMaterial color="#aab3bf" roughness={0.7} /></mesh>
            {i % 3 === 0 && <mesh position={[0, 13, 26]}><boxGeometry args={[0.8, 26, 0.8]} /><meshStandardMaterial color="#dfe3e8" /></mesh>}
          </group>
        );
      })}
      {/* poles：ハロン棒（赤と白） */}
      {poles.map((q) => (
        <group key={'p' + q.u} position={[q.p[0], 0, -q.p[1]]}>
          {[0, 1, 2, 3].map((k) => <mesh key={k} position={[0, 0.45 + k * 0.9, 0]} castShadow><cylinderGeometry args={[0.12, 0.12, 0.9, 12]} /><meshStandardMaterial color={k % 2 ? '#ffffff' : '#d32f2f'} roughness={0.4} /></mesh>)}
        </group>
      ))}
      {/* goal：ゴールの線と決勝の柱（内ラチ側） */}
      {goal && (() => {
        const a = new THREE.Vector3(goal.a[0], 0, -goal.a[1]), b = new THREE.Vector3(goal.b[0], 0, -goal.b[1]);
        const mid = a.clone().add(b).multiplyScalar(0.5); const len = a.distanceTo(b); const ang = Math.atan2(-(b.z - a.z), b.x - a.x);
        return (
          <group>
            <mesh position={[mid.x, 0.04, mid.z]} rotation={[0, ang, 0]}><boxGeometry args={[len, 0.02, 0.35]} /><meshBasicMaterial color="#ffffff" /></mesh>
            <mesh position={[a.x, 3, a.z]} castShadow><boxGeometry args={[0.32, 6, 0.32]} /><meshStandardMaterial color="#ffffff" /></mesh>
            {/* 決勝の柱の円盤（2026-11-20 半径1.1m だとゴールのカメラの前で大きく映った → 0.6m） */}
            <mesh position={[a.x, 6.1, a.z]} rotation={[Math.PI / 2, 0, ang + Math.PI / 2]} castShadow><cylinderGeometry args={[0.6, 0.6, 0.1, 28]} /><meshStandardMaterial color="#e53935" /></mesh>
          </group>
        );
      })()}
      {/* winnerRing：勝った馬の足元の金色の輪 */}
      {winnerRing && (
        <mesh position={[winnerRing[0], 0.06, winnerRing[1]]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[1.5, 1.9, 48]} />
          <meshBasicMaterial color="#f5c542" transparent opacity={0.9} />
        </mesh>
      )}
    </>
  );
};
