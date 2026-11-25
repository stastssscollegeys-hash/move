// 馬の組み立て（2026-11-20・race3d-quality T-003）
// 同梱の Quaternius Horse（CC0・public/horse.glb・出どころ public/LICENSE_horse.txt）を16頭に複製し、
// 毛色（logic.ts の coatFor）・ゼッケン（枠の色＋馬番）・乗り手（顔なし・前傾・帽子だけ枠の色）を足す。
// モデルの前は +Z。大きさはモデルの体長を 2.45m にそろえる。乗り手とゼッケンは、毎コマ 背中の骨（Torso2）の位置に合わせて置く
import * as THREE from 'three';
import {GLTFLoader} from 'three/examples/jsm/loaders/GLTFLoader.js';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import {coatFor, WAKU, HorseMeta} from './logic';
import {externalUris} from './glb';

export type HorseKit = {scene: THREE.Object3D; gallop: THREE.AnimationClip; idle: THREE.AnimationClip};
export type HorseRig = {
  root: THREE.Group;          // 位置と向き（frames.json のまま）
  model: THREE.Object3D;      // 骨つきの馬（大きさをそろえて root の子）
  mixer: THREE.AnimationMixer;
  gallop: THREE.AnimationAction; idle: THREE.AnimationAction;
  back: THREE.Object3D | null;   // 背中の骨
  rider: THREE.Group; cloth: THREE.Group;
  seat: THREE.Vector3;           // 背中の骨から鞍までのずれ（root の中・m）
};

export const BODY_LENGTH = 2.45;   // サラブレッドの体長の目安（研究で約1.63m＋首と頭）を見た目で合わせた値

export const loadHorseKit = async (url: string): Promise<HorseKit> => {
  let buf: ArrayBuffer;
  try {
    const r = await fetch(url);
    if (!r.ok) throw new Error(String(r.status));
    buf = await r.arrayBuffer();
  } catch { throw new Error(`馬のモデルが読めません（${url}）`); }
  const ext = externalUris(buf);
  if (ext.length) throw new Error(`馬のモデルが外のファイルを読みに行きます（${ext.slice(0, 3).join('、')}）。1つのファイルで完結した .glb だけ使えます`);
  // 念のため、読み込みの途中で外へ取りに行こうとしたら止める（data: と blob: だけ通す）
  const manager = new THREE.LoadingManager();
  manager.setURLModifier((u) => { if (/^(data|blob):/.test(u)) return u; throw new Error(`馬のモデルが外のファイルを読みに行きます（${u}）`); });
  const g = await new GLTFLoader(manager).parseAsync(buf, '');
  const gallop = g.animations.find((a) => a.name === 'Gallop');
  const idle = g.animations.find((a) => a.name === 'Idle');
  if (!gallop || !idle) throw new Error('馬のモデルが読めません（Gallop か Idle の動きがありません）');
  return {scene: g.scene, gallop, idle};
};

// 片づけ（2026-11-20 Codex の Must：差し替え・終わりに GPU の物が残っていた）
// 馬ごとの物（複製した材質・乗り手とゼッケンの形・ゼッケンの絵・骨・動き）と、GLB の共有の物（形・元の材質）を分けて捨てる
const disposeMaterial = (m: THREE.Material) => {
  for (const v of Object.values(m)) if (v instanceof THREE.Texture) v.dispose();
  m.dispose();
};
export const disposeField = (rigs: HorseRig[]) => {
  for (const r of rigs) {
    r.mixer.stopAllAction(); r.mixer.uncacheRoot(r.model);
    r.model.traverse((o) => {
      const m = o as THREE.SkinnedMesh;
      if (m.isMesh) (Array.isArray(m.material) ? m.material : [m.material]).forEach(disposeMaterial);   // 複製した材質（形は共有なので disposeKit で）
      if (m.isSkinnedMesh && m.skeleton) m.skeleton.dispose();
    });
    for (const g of [r.rider, r.cloth]) g.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.geometry.dispose();
      (Array.isArray(m.material) ? m.material : [m.material]).forEach(disposeMaterial);
    });
    r.root.removeFromParent();
  }
};
export const disposeKit = (kit: HorseKit) => {
  kit.scene.traverse((o) => {
    const m = o as THREE.Mesh;
    if (!m.isMesh) return;
    m.geometry.dispose();
    (Array.isArray(m.material) ? m.material : [m.material]).forEach(disposeMaterial);
  });
};

// ゼッケンの絵（枠の色の地に馬番）
const clothTexture = (no: number, waku: number) => {
  const c = document.createElement('canvas'); c.width = 192; c.height = 144;
  const x = c.getContext('2d')!;
  const [bg, fg] = WAKU[waku] || ['#888888', '#ffffff'];
  x.fillStyle = bg; x.fillRect(0, 0, 192, 144);
  x.strokeStyle = fg === '#111111' ? '#444444' : '#ffffff'; x.lineWidth = 8; x.strokeRect(8, 8, 176, 128);
  x.fillStyle = fg; x.font = 'bold 96px sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(String(no), 96, 78);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
};

const mat = (color: string, roughness = 0.6) => new THREE.MeshStandardMaterial({color, roughness});
const add = (g: THREE.Object3D, geo: THREE.BufferGeometry, m: THREE.Material, pos: number[], rot: number[] = [0, 0, 0]) => {
  const o = new THREE.Mesh(geo, m); o.position.set(pos[0], pos[1], pos[2]); o.rotation.set(rot[0], rot[1], rot[2]);
  o.castShadow = true; g.add(o); return o;
};

// 乗り手（m・前が +Z・上が +Y）。モンキー乗りの前傾。顔は描かない。服は白系、帽子だけ枠の色
const makeRider = (waku: number) => {
  const g = new THREE.Group();
  const silk = mat('#eef0f3', 0.75), pants = mat('#f6f6f4', 0.8), boot = mat('#1a1a1a', 0.4);
  const [capColor] = WAKU[waku] || ['#888888'];
  add(g, new THREE.CapsuleGeometry(0.16, 0.42, 6, 12), silk, [0, 0.36, 0.12], [1.25, 0, 0]);       // 胴（前へ倒す）
  add(g, new THREE.SphereGeometry(0.12, 16, 12), mat(capColor, 0.35), [0, 0.52, 0.43]);              // 頭＝帽子（顔なし）
  add(g, new THREE.CylinderGeometry(0.125, 0.125, 0.02, 16), mat(capColor, 0.35), [0, 0.48, 0.49], [0.25, 0, 0]);  // つば
  for (const s of [1, -1]) {
    add(g, new THREE.CapsuleGeometry(0.06, 0.34, 4, 8), pants, [0.17 * s, 0.2, -0.02], [-0.6, 0, 0]);   // もも（前へ）
    add(g, new THREE.CapsuleGeometry(0.05, 0.3, 4, 8), boot, [0.2 * s, 0.02, 0.06], [0.7, 0, 0]);       // すね（鐙へ）
    add(g, new THREE.CapsuleGeometry(0.045, 0.34, 4, 8), silk, [0.14 * s, 0.38, 0.48], [1.6, 0, 0]);    // 腕（手綱へ）
  }
  return g;
};

// ゼッケン（鞍の下の布・左右）
const makeCloth = (no: number, waku: number) => {
  const g = new THREE.Group();
  const m = new THREE.MeshStandardMaterial({map: clothTexture(no, waku), roughness: 0.85, side: THREE.DoubleSide});
  for (const s of [1, -1]) {
    const o = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.46), m);
    o.position.set(0.335 * s, -0.12, 0.02); o.rotation.set(0, s > 0 ? Math.PI / 2 : -Math.PI / 2, 0);
    g.add(o);
  }
  add(g, new THREE.BoxGeometry(0.5, 0.06, 0.55), mat('#2a1d14', 0.5), [0, 0.06, 0.02]);   // 鞍
  return g;
};

export const buildField = (kit: HorseKit, horses: HorseMeta[]): HorseRig[] => {
  // 大きさ：Idle の姿勢で体長（Z の長さ）を BODY_LENGTH にそろえる
  const probe = SkeletonUtils.clone(kit.scene);
  const pm = new THREE.AnimationMixer(probe); pm.clipAction(kit.idle).play(); pm.setTime(0); probe.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(probe); const size = new THREE.Vector3(); box.getSize(size);
  const scale = BODY_LENGTH / Math.max(size.z, 1e-6);
  const footY = box.min.y * scale;
  return horses.map((h) => {
    const model = SkeletonUtils.clone(kit.scene);
    const coat = coatFor(h.umaban);
    model.traverse((o: THREE.Object3D) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh) return;
      m.castShadow = true; m.receiveShadow = true; m.frustumCulled = false;
      const recolor = (mt: THREE.Material) => {
        const n = (mt as THREE.MeshStandardMaterial).clone();
        const name = mt.name;
        if (name === 'Main') n.color = new THREE.Color(coat.main);
        else if (name === 'Main_Dark') n.color = new THREE.Color(coat.dark);
        else if (name === 'Main_Light') n.color = new THREE.Color(coat.light);
        else if (name === 'Hair') n.color = new THREE.Color(coat.hair);
        n.roughness = name === 'Hooves' ? 0.4 : 0.55;
        return n;
      };
      m.material = Array.isArray(m.material) ? m.material.map(recolor) : recolor(m.material);
    });
    model.scale.setScalar(scale);
    model.position.y = -footY;
    const root = new THREE.Group();
    root.add(model);
    const mixer = new THREE.AnimationMixer(model);
    const gallop = mixer.clipAction(kit.gallop); const idle = mixer.clipAction(kit.idle);
    gallop.play(); idle.play();
    const rider = makeRider(h.waku); const cloth = makeCloth(h.umaban, h.waku);
    root.add(rider); root.add(cloth);
    return {root, model, mixer, gallop, idle, back: model.getObjectByName('Torso2') || null, rider, cloth, seat: new THREE.Vector3(0, 0.06, 0.05)};
  });
};

// 1コマ分の姿勢：位置・向き・動きの時刻。止まっている（ゲートの中）なら Idle、それ以外は Gallop
const tmp = new THREE.Vector3();
export const poseRig = (r: HorseRig, x: number, z: number, yaw2d: number, gallopTime: number, started: boolean) => {
  r.root.position.set(x, 0, z);
  r.root.rotation.set(0, yaw2d + Math.PI / 2, 0);     // 2D の角度 → モデルの前（+Z）を進む向きへ
  r.gallop.setEffectiveWeight(started ? 1 : 0);
  r.idle.setEffectiveWeight(started ? 0 : 1);
  r.mixer.setTime(started ? gallopTime : 0);
  r.root.updateMatrixWorld(true);
  if (r.back) {
    r.back.getWorldPosition(tmp);
    r.root.worldToLocal(tmp);
    r.cloth.position.set(0, tmp.y + 0.02, tmp.z);
    r.rider.position.set(0, tmp.y + r.seat.y + 0.08, tmp.z + r.seat.z);
  }
};
