// レース展開3Dの計算（2026-11-20・race3d-quality T-002）。描く部分から切り離した純粋な関数だけ（three も React も使わない）。
// すべてコマ番号 f と frames.json だけで決まる（コマ同士で状態を持ち越さない＝Remotion の並列の書き出しで壊れない）。
// 座標：3D の x＝frames の x、z＝−frames の y、y＝上

export type Frame = {p: number[][]; cam: number[]; rank: number[]; gap: number[]; lead: number[]; phase: string; rem: number; rs?: number};
export type HorseMeta = {umaban: number; waku: number; name: string; finish?: number | null; style?: string | null; mark?: string | null};
export type Mark = {u: number; label: string; a: number[]; b: number[]};
export type CalcProps = {
  fps: number; w: number; h: number; view: number[]; mode?: 'result' | 'forecast' | 'prediction';   // prediction は result と同じカメラ（ゴールまで走る）
  horses: HorseMeta[]; frame: Frame[]; track: {marks: Mark[]; turn?: 'left' | 'right'};
  final_m?: number | null;   // 予想の着順：残り何mから速回しをゆるめて印の馬を追うか（build_frames.py --final-m）
};
export type V3 = [number, number, number];
export type Cam = {pos: V3; target: V3; fov?: number};   // fov（度）は無ければ既定（横32・縦40）。望遠にしたいショットだけ付ける
export type Shot = 'side_high' | 'follow' | 'head_on' | 'side_low' | 'goal_line' | 'finish' | 'forecast_end';
// 予想の着順（prediction）だけ：先頭が残りこの距離からは、ゴールの線の外に置いたカメラで線を越える瞬間を映す
// （2026-11-20 ユーザー「最後の展開がどうやって最終画面に変わったか分からない」「結果だけ急にポンっとなっちゃって」）
export const GOAL_LINE_M = 25;
export const GOAL_HOLD = 24;   // 線を越えた直後の止まった場面を、真横のまま見せるコマ数（決勝写真のように・2026-11-20）   // 40m だと最初の1秒は馬が遠くて小さかった（2026-11-20）

// 枠の色（地の色・文字の色）。Race2D・Race3DHQ ともここから読む（正本は1か所）
export const WAKU: Record<number, [string, string]> = {
  1: ['#ffffff', '#111111'], 2: ['#1b1b1b', '#ffffff'], 3: ['#e53935', '#ffffff'], 4: ['#1e5fd6', '#ffffff'],
  5: ['#ffd400', '#111111'], 6: ['#2e9e44', '#ffffff'], 7: ['#f28c00', '#ffffff'], 8: ['#f48fb1', '#111111'],
};

export const STRIDE = 7.2;   // ギャロップの1完歩（m）＝JRA の用語集「7〜8m」・研究で 7.08m（research_v1 C5・C6）
export const BLEND = 45;     // ショットの切り替えをなめらかにつなぐコマ数

// 毛色：鹿毛・黒鹿毛・栗毛・青鹿毛・芦毛・栃栗毛（main＝体／dark＝暗い所／light＝明るい所／hair＝たてがみ・尾）
const COATS = [
  {name: '鹿毛', main: '#7a4022', dark: '#4a2614', light: '#9a5a34', hair: '#1a100a'},
  {name: '黒鹿毛', main: '#3e2416', dark: '#24140c', light: '#5a3622', hair: '#0e0906'},
  {name: '栗毛', main: '#a3561f', dark: '#743a14', light: '#c27a3c', hair: '#b06a2c'},
  {name: '青鹿毛', main: '#261811', dark: '#140c08', light: '#3a281c', hair: '#0a0705'},
  {name: '芦毛', main: '#b4b1aa', dark: '#86837d', light: '#d6d3cc', hair: '#e4e2dc'},
  {name: '栃栗毛', main: '#6e3a1a', dark: '#4a2410', light: '#8e5428', hair: '#c9a06a'},
];
export const coatFor = (umaban: number) => COATS[(umaban * 5 + 1) % COATS.length];

// 入力の確かめ（2026-11-20 Codex の Should）。描き始める前に、分かる言葉で止める
export const checkProps = (p: CalcProps): void => {
  if (!p.frame || !p.frame.length) throw new Error('frames.json にコマがありません');
  if (!(p.w > 0 && p.h > 0) || !Number.isFinite(p.w) || !Number.isFinite(p.h)) throw new Error(`画面の大きさ（w・h）がおかしいです（${p.w}×${p.h}）`);
  if (!p.horses || !p.horses.length) throw new Error('frames.json に馬がいません');
  if (!p.view || p.view.length < 3) throw new Error('frames.json に view（映す範囲）がありません');
  p.frame.forEach((F, f) => {
    if (!F.p || F.p.length !== p.horses.length) throw new Error(`コマ ${f} の馬の数（${F.p ? F.p.length : 0}）が馬の一覧（${p.horses.length}）と合いません`);
    for (const q of F.p) if (!Number.isFinite(q[0]) || !Number.isFinite(q[1])) throw new Error(`コマ ${f} に数でない位置があります`);
    if (!F.cam || !F.cam.slice(0, 2).every(Number.isFinite)) throw new Error(`コマ ${f} のカメラの位置（cam）が数ではありません`);
    if (!F.lead || !F.lead.slice(0, 2).every(Number.isFinite)) throw new Error(`コマ ${f} の先頭の位置（lead）がありません`);
    if (!F.rank || !F.rank.length) throw new Error(`コマ ${f} の順位（rank）がありません`);
  });
};

export const groundPos = (fr: Frame, i: number): [number, number] => [fr.p[i][0], -fr.p[i][1]];

// 0コマ目から f コマ目までに各馬が走った距離の表 [f][i]（m）。最初に1回だけ作る
export const cumDistTable = (frames: Frame[]): number[][] => {
  const n = frames.length, m = n ? frames[0].p.length : 0;
  const t: number[][] = [new Array(m).fill(0)];
  for (let f = 1; f < n; f++) {
    const row = t[f - 1].slice();
    for (let i = 0; i < m; i++) row[i] += Math.hypot(frames[f].p[i][0] - frames[f - 1].p[i][0], frames[f].p[i][1] - frames[f - 1].p[i][1]);
    t.push(row);
  }
  return t;
};

export const gallopTime = (dist: number, clipDur: number, stride = STRIDE): number => {
  const x = (dist / stride) * clipDur;
  const r = x % clipDur;
  return Math.abs(r - clipDur) < 1e-9 ? 0 : r;
};

// ゲートを出たか（まだ一度も動いていない馬は Idle の姿勢）
export const hasStarted = (table: number[][], f: number, i: number): boolean => table[Math.max(0, Math.min(table.length - 1, f))][i] > 0.05;

const clampF = (frames: Frame[], f: number) => Math.max(0, Math.min(frames.length - 1, f));

export const isMoving = (frames: Frame[], i: number, f: number): boolean => {
  const a = frames[clampF(frames, f - 3)].p[i], b = frames[clampF(frames, f + 3)].p[i];
  return Math.hypot(b[0] - a[0], b[1] - a[1]) >= 0.05;
};

// 向き（2D の角度。3D の y 軸まわりの回転にそのまま使う）。止まっていれば前後40コマ、それでも止まっていれば全体の向き
export const yawAt = (frames: Frame[], i: number, f: number): number => {
  const d = (k: number) => {
    const a = frames[clampF(frames, f - k)].p[i], b = frames[clampF(frames, f + k)].p[i];
    return [b[0] - a[0], b[1] - a[1]];
  };
  let [dx, dy] = d(3);
  if (Math.hypot(dx, dy) < 0.05) [dx, dy] = d(40);
  if (Math.hypot(dx, dy) < 0.05) {
    // 最後に動いていた向きを探す（後ろへ）
    for (let k = f; k > 0; k--) {
      const a = frames[k - 1].p[i], b = frames[k].p[i];
      if (Math.hypot(b[0] - a[0], b[1] - a[1]) > 0.01) { dx = b[0] - a[0]; dy = b[1] - a[1]; break; }
    }
  }
  if (Math.hypot(dx, dy) < 1e-6) { const a = frames[0].p[i], b = frames[frames.length - 1].p[i]; dx = b[0] - a[0]; dy = b[1] - a[1]; }
  return Math.atan2(dy, dx);
};

// 勝った馬（最後のコマの rank[0]＝馬番）の horses の並び番号
export const winnerIndex = (p: CalcProps): number => {
  const last = p.frame[p.frame.length - 1];
  const no = last.rank[0];
  const i = p.horses.findIndex((h) => h.umaban === no);
  return i < 0 ? 0 : i;
};

// 線分 a→b が、縦に立った円柱（中心 c＝[x, z]・半径 r・高さ 0〜h）に当たるか
export const rayHitsCylinder = (a: number[], b: number[], c: number[], r: number, h: number): boolean => {
  const dx = b[0] - a[0], dz = b[2] - a[2];
  const fx = a[0] - c[0], fz = a[2] - c[1];
  const A = dx * dx + dz * dz, B = 2 * (fx * dx + fz * dz), C = fx * fx + fz * fz - r * r;
  let t0 = 0, t1 = 1;
  if (A < 1e-12) { if (C > 0) return false; }
  else {
    const disc = B * B - 4 * A * C;
    if (disc < 0) return false;
    const s = Math.sqrt(disc);
    t0 = Math.max(0, (-B - s) / (2 * A)); t1 = Math.min(1, (-B + s) / (2 * A));
    if (t0 > t1) return false;
  }
  // 円の中を通る区間 [t0, t1] で、高さが 0〜h に入るか
  const y0 = a[1] + (b[1] - a[1]) * t0, y1 = a[1] + (b[1] - a[1]) * t1;
  return !(Math.min(y0, y1) > h || Math.max(y0, y1) < 0);
};

// ショット（SDD のショットの表。rem と phase だけで決まる・rem は減るだけなので順は戻らない）
const CORNER = new Set(['3コーナー', '4コーナー', '残り600m', '最後の直線']);
export const shotAt = (p: CalcProps, f: number): Shot => {
  const F = p.frame[clampF(p.frame, f)];
  if (F.phase === 'ゴール' && p.mode === 'prediction') {
    let g = clampF(p.frame, f);
    while (g > 0 && p.frame[g - 1].phase === 'ゴール') g--;
    return clampF(p.frame, f) - g < GOAL_HOLD ? 'goal_line' : 'finish';
  }
  if (F.phase === 'ゴール' && p.mode !== 'forecast') return 'finish';
  if (F.phase === '直線へ' || (p.mode === 'forecast' && f >= p.frame.length - 1)) return 'forecast_end';
  if (p.mode === 'prediction') {
    if (F.rem <= GOAL_LINE_M) return 'goal_line';
    if (p.final_m && F.rem <= p.final_m) return 'side_low';
  }
  if (F.rem <= 250 && p.mode !== 'forecast') return 'side_low';
  if (F.rem <= 500 && p.mode !== 'forecast') return 'head_on';
  if (CORNER.has(F.phase)) return 'follow';
  return 'side_high';
};

// そのショットが始まったコマ
export const shotStartFrame = (p: CalcProps, f: number): number => {
  const s = shotAt(p, f);
  let k = clampF(p.frame, f);
  while (k > 0 && shotAt(p, k - 1) === s) k--;
  return k;
};

const smooth = (x: number) => { const t = Math.max(0, Math.min(1, x)); return t * t * (3 - 2 * t); };
const lerp3 = (a: V3, b: V3, w: number): V3 => [a[0] + (b[0] - a[0]) * w, a[1] + (b[1] - a[1]) * w, a[2] + (b[2] - a[2]) * w];

// 先頭の進む向き：今の先頭の位置から、先のコマで15m以上離れた所への向き（止まっている間もとばない）。
// 先が無い（ゴールで止まったあと）ときは、後ろへ15m以上離れた所からの向き。前後のコマで平均してならす
// （2026-11-20 前後20コマ→80コマへ切り替える形だと、スタート直後にカメラが37m飛んだ＝TC-FR-CAM-001 で見つけた）
const rawHeading = (p: CalcProps, f: number): [number, number] => {
  const n = p.frame.length, a = p.frame[clampF(p.frame, f)].lead;
  for (let k = clampF(p.frame, f) + 1; k < n; k++) {
    const b = p.frame[k].lead;
    if (Math.hypot(b[0] - a[0], b[1] - a[1]) >= 15) return [b[0] - a[0], b[1] - a[1]];
  }
  for (let k = clampF(p.frame, f) - 1; k >= 0; k--) {
    const b = p.frame[k].lead;
    if (Math.hypot(b[0] - a[0], b[1] - a[1]) >= 15) return [a[0] - b[0], a[1] - b[1]];
  }
  return [0, 1];
};
const headCache = new WeakMap<object, [number, number][]>();
const headingAt = (p: CalcProps, f: number): [number, number] => {
  let t = headCache.get(p.frame);
  if (!t) {
    const raw = p.frame.map((_, k) => { const [x, y] = rawHeading(p, k); const l = Math.hypot(x, y) || 1; return [x / l, y / l] as [number, number]; });
    t = raw.map((_, k) => {
      let sx = 0, sy = 0;
      for (let j = -15; j <= 15; j++) { const q = raw[clampF(p.frame, k + j)]; sx += q[0]; sy += q[1]; }
      const l = Math.hypot(sx, sy) || 1;
      return [sx / l, sy / l] as [number, number];
    });
    headCache.set(p.frame, t);
  }
  return t[clampF(p.frame, f)];
};

// 1つのショットのカメラ。縦（ショート）は上に帯と順位の札が重なるので、狙いを少し上げて馬を画面の中ほどへ下ろす（ゴールは勝った馬を真ん中のまま）
export const shotCam = (p: CalcProps, f: number, shot: Shot): Cam => {
  const c = shotCamRaw(p, f, shot);
  if (p.h > p.w && shot !== 'finish') {
    const lift = Math.hypot(c.pos[0] - c.target[0], c.pos[2] - c.target[2]) * 0.07;
    return {pos: c.pos, target: [c.target[0], c.target[1] + lift, c.target[2]]};
  }
  return c;
};

// 1つのショットのカメラ（2D で決めてから 3D に直す）
const shotCamRaw = (p: CalcProps, f: number, shot: Shot): Cam => {
  const F = p.frame[clampF(p.frame, f)];
  const [hx, hy] = headingAt(p, f);
  const side = p.track.turn === 'right' ? -1 : 1;             // 2026-11-20 右回りに対応：外＝左回りは進む向きの右・右回りは左
  const nx = hy * side, ny = -hx * side;
  const tall = p.h > p.w;
  const k = tall ? 1.15 : 1.0;
  // 映す幅（m）。幅や倍率が 0・数でないときは NaN にせず真ん中の 60m（2026-11-20 Codex の Should）
  const ratio = p.view[2] / F.cam[2];
  const span = Number.isFinite(ratio) && ratio > 0 ? Math.min(110, Math.max(28, ratio)) : 60;
  const cx = F.cam[0], cy = F.cam[1];
  const to3 = (x: number, y: number, h: number): V3 => [x, h, -y];
  if (shot === 'finish') return finishCam(p, f);
  if (shot === 'goal_line') return goalLineCam(p, f);
  if (shot === 'forecast_end') {
    // 展開予想の最後（直線の入口で止まった隊列）：外の斜め後ろから。隊列が奥へ伸びて見えるので縦でも大きく収まる
    // （2026-11-20 横からだと縦の画面に隊列を収めるために遠くなり、馬が小さく・上半分が芝だけになった）
    const d = (span * 0.5 + 12) * k;
    return {pos: to3(cx + nx * d * 0.8 - hx * d * 0.9, cy + ny * d * 0.8 - hy * d * 0.9, d * 0.35), target: to3(cx + hx * 6, cy + hy * 6, 1.0)};
  }
  if (shot === 'side_high') {
    const d = (span * 0.65 + 14) * k;
    return {pos: to3(cx + nx * d - hx * span * 0.1, cy + ny * d - hy * span * 0.1, d * 0.55), target: to3(cx, cy, 1.0)};
  }
  if (shot === 'follow') {
    const d = (span * 0.45 + 10) * k;
    return {pos: to3(cx + nx * d - hx * (span * 0.55 + 12), cy + ny * d - hy * (span * 0.55 + 12), d * 0.32), target: to3(cx + hx * 4, cy + hy * 4, 1.0)};
  }
  // 2026-11-20 T-004：書き出して見ると前からと横からの低いカメラが遠く、馬が小さかった → 寄せた
  if (shot === 'head_on') {
    const ahead = (16 + span * 0.2) * k;
    return {pos: to3(cx + hx * ahead + nx * 6, cy + hy * ahead + ny * 6, 2.8), target: to3(cx, cy, 1.5)};
  }
  // side_low
  const d = (span * 0.28 + 6) * k;
  return {pos: to3(cx + nx * d + hx * span * 0.08, cy + ny * d + hy * span * 0.08, 2.2 + span * 0.03), target: to3(cx + hx * 3, cy + hy * 3, 1.3)};
};

// 勝った馬が隠れていないかの判定（2026-11-20 Codex の Must で、胴の1点・円柱1本から広げた）
// 見たい所＝勝った馬の胴・乗り手の頭・馬の頭・尻の4点（描く馬は体長 2.45m・乗り手の頭は高さ約2.5m）。
// ほかの馬＝進む向きにそった3本の円柱（真ん中は半径0.6m、前後 0.85m は半径0.5m・高さ2.6m）
export const SIGHT_R = 0.6, SIGHT_H = 2.6;
export const sightPoints = (p: CalcProps, f: number, i: number): V3[] => {
  const F = p.frame[clampF(p.frame, f)];
  const [x, z] = groundPos(F, i);
  const yaw = yawAt(p.frame, i, clampF(p.frame, f)), ex = Math.cos(yaw), ez = -Math.sin(yaw);
  return [[x, 1.5, z], [x, 2.4, z], [x + ex * 1.0, 1.8, z + ez * 1.0], [x - ex * 0.9, 1.3, z - ez * 0.9]];
};
const bodyCylinders = (p: CalcProps, f: number, i: number): {c: [number, number]; r: number}[] => {
  const F = p.frame[clampF(p.frame, f)];
  const [x, z] = groundPos(F, i);
  const yaw = yawAt(p.frame, i, clampF(p.frame, f)), ex = Math.cos(yaw), ez = -Math.sin(yaw);
  return [{c: [x, z], r: SIGHT_R}, {c: [x + ex * 0.85, z + ez * 0.85], r: 0.5}, {c: [x - ex * 0.85, z - ez * 0.85], r: 0.5}];
};
// カメラの位置 pos から見て、勝った馬（w）の見たい所が他の馬に隠れている数（0＝全部見える）
export const hiddenSights = (p: CalcProps, f: number, pos: number[], w = winnerIndex(p)): number => {
  const pts = sightPoints(p, f, w);
  const occ = p.horses.map((_, i) => i).filter((i) => i !== w).flatMap((i) => bodyCylinders(p, f, i));
  return pts.filter((t) => occ.some((o) => rayHitsCylinder(pos, t, o.c, o.r, SIGHT_H))).length;
};

// ゴール：勝った馬を狙い、勝った馬の見たい所が1つも隠れない最初の候補。
// どの候補でも隠れる（ほかの馬が勝った馬と同じ位置にいる・2026-11-20 Codex の Must）ときは、確かめた候補の中で隠れる所が一番少ないもの
// （同じ数なら先の候補）。真上に近い高さ40m も候補に入れてある＝確かめていない位置は返さない
export const FINISH_HEIGHTS = [4, 8, 14, 22, 30, 40];
// ゴールの線のカメラ：線を外へまっすぐ延ばした所（真横）に望遠で置き、先頭を追って横に振って、線に来たら線の上で止める
// （2026-11-20 ユーザー「最後斜めからじゃない方が良くない?」＝決勝写真・中継のゴール板のカメラと同じ真横。
//   その前は線の先の斜めから＝誰が先に線を越えたかが分かりにくかった。さらに前は外の端に置いて馬が小さかった）
export const goalLineCam = (p: CalcProps, f: number): Cam => {
  const goal = p.track.marks.find((m) => m.u === 0);
  const F = p.frame[clampF(p.frame, f)];
  const f0 = shotStartFrame(p, f), F0 = p.frame[clampF(p.frame, f0)];
  const [hx, hy] = headingAt(p, f0);
  const tall = p.h > p.w;
  if (!goal) return {pos: [F0.lead[0] + hx * 20, 3, -(F0.lead[1] + hy * 20)], target: [F0.lead[0], 1.3, -F0.lead[1]]};
  let gx = goal.b[0] - goal.a[0], gy = goal.b[1] - goal.a[1];
  const gl = Math.hypot(gx, gy) || 1; gx /= gl; gy /= gl;                   // a＝内・b＝外（build_frames.py の marks）
  const idx = F0.rank.slice(0, 5).map((u) => p.horses.findIndex((h) => h.umaban === u)).filter((i) => i >= 0);
  const ts = idx.map((i) => (F0.p[i][0] - goal.a[0]) * gx + (F0.p[i][1] - goal.a[1]) * gy);   // 線の上の横の位置（内から何m）
  const tOut = ts.length ? Math.max(...ts) : gl, tMid = ts.length ? ts.reduce((x, y) => x + y, 0) / ts.length : gl / 2;
  const away = tall ? 52 : 44;                                            // 前の5頭の外から何m 離れるか（望遠なので遠め）
  const px = goal.a[0] + gx * (tOut + away), py = goal.a[1] + gy * (tOut + away);
  const lx = goal.a[0] + gx * tMid, ly = goal.a[1] + gy * tMid;           // 線の上・前の5頭の真ん中
  const s = (F.lead[0] - lx) * hx + (F.lead[1] - ly) * hy;               // 先頭が線の何m 手前か（負＝まだ手前）
  const along = Math.min(0, s + 2);                                       // 先頭の少し前を見る・線を越えたら線で止める
  return {pos: [px, tall ? 4.2 : 3.2, -py], target: [lx + hx * along, tall ? 1.9 : 1.3, -(ly + hy * along)], fov: tall ? 17 : 12};
};

export const finishCam = (p: CalcProps, f: number): Cam => {
  const F = p.frame[clampF(p.frame, f)];
  const w = winnerIndex(p);
  const [wx, wz] = groundPos(F, w);
  const goal = p.track.marks.find((m) => m.u === 0);
  let gx = 0, gy = 1;
  if (goal) { gx = goal.b[0] - goal.a[0]; gy = goal.b[1] - goal.a[1]; const l = Math.hypot(gx, gy) || 1; gx /= l; gy /= l; }
  const [hx, hy] = headingAt(p, f);
  const tall = p.h > p.w;
  const d = tall ? 18 : 14;
  const look: V3 = [wx, tall ? 2.4 : 1.5, wz];   // 縦は狙いを上げて馬を下寄りに（下の地面を減らす・2026-11-20）
  let best: Cam | null = null, bestHidden = Infinity;
  // 2026-11-20 進路を保つ作りにしたら、勝った馬のすぐ外を2着の馬が並ぶことが増え、外からはどの低い所でも隠れて真上から見下ろす絵になった
  //   → 外（side=1）で隠れるときは内（side=-1）からも探す。低い所で隠れない所を先に選ぶ（高さが先・内外は同じ高さの中で）
  for (const height of FINISH_HEIGHTS) {
    for (const side of [1, -1]) for (const ahead of [6, 12, 0]) {
      const x = F.p[w][0] + gx * d * side + hx * ahead, y = F.p[w][1] + gy * d * side + hy * ahead;
      const pos: V3 = [x, height, -y];
      const hidden = hiddenSights(p, f, pos, w);
      if (hidden === 0) return {pos, target: look};
      if (hidden <= bestHidden) { best = {pos, target: look}; bestHidden = hidden; }   // 同じ数なら後の（高い）候補＝上から見るほど隠れにくい（2026-11-20 検査役の Should）
    }
  }
  return best!;
};

// ショットの並び（切り替わったコマ）。frames ごとに1回だけ作って覚える
const segCache = new WeakMap<object, Map<string, {shot: Shot; start: number}[]>>();   // 鍵＝frames と mode（shotAt は mode にも左右される）
const segments = (p: CalcProps) => {
  let byMode = segCache.get(p.frame);
  if (!byMode) { byMode = new Map(); segCache.set(p.frame, byMode); }
  let s = byMode.get(p.mode || 'result');
  if (!s) {
    s = [];
    for (let f = 0; f < p.frame.length; f++) {
      const sh = shotAt(p, f);
      if (!s.length || s[s.length - 1].shot !== sh) s.push({shot: sh, start: f});
    }
    byMode.set(p.mode || 'result', s);
  }
  return s;
};

// ゴールへのつなぎ（BLEND コマ）の間に、勝った馬が他の馬に隠れるコマが1つでもあるか。
// 2026-11-20 Codex のレビューの Blocker：つなぎの途中の位置は finishCam の判定を通っていなかった（縦11コマ・横21コマ隠れていた）。
// あれば、そのショットはつながずに切り替える（中継の切り替えと同じ）。frames と mode ごとに1回だけ数えて覚える
const cutCache = new WeakMap<object, Map<string, boolean>>();
const finishCut = (p: CalcProps, segs: {shot: Shot; start: number}[], j: number): boolean => {
  let m = cutCache.get(p.frame);
  if (!m) { m = new Map(); cutCache.set(p.frame, m); }
  const key = `${p.mode || 'result'}:${j}`;
  const hit = m.get(key);
  if (hit !== undefined) return hit;
  const w = winnerIndex(p);
  const end = Math.min(segs[j].start + BLEND, segs[j + 1]?.start ?? p.frame.length, p.frame.length);
  let occluded = false;
  for (let f = segs[j].start; f < end && !occluded; f++) {
    const prev = j > 0 ? blendedBefore(p, segs, j - 1, f) : shotCam(p, f, segs[j].shot);
    const cur = shotCam(p, f, segs[j].shot);
    const t = smooth((f - segs[j].start) / BLEND);
    const pos = lerp3(prev.pos, cur.pos, t);
    occluded = hiddenSights(p, f, pos, w) > 0;
  }
  m.set(key, occluded);
  return occluded;
};
// コマ f が「つながずに切り替えた最初のコマ」か（カメラが1コマで大きく動いてよいのはここだけ）
export const isCutFrame = (p: CalcProps, f: number): boolean => {
  const segs = segments(p);
  const j = segs.findIndex((s) => s.start === f);
  if (j > 0 && (segs[j].shot === 'goal_line' || (segs[j].shot === 'finish' && segs[j - 1].shot === 'goal_line'))) return true;   // ゴールの線へは切り替える（つなぐと線の前でカメラが流れる）
  return j > 0 && segs[j].shot === 'finish' && finishCut(p, segs, j);
};
// セグメント j のカメラ（j 自身のつなぎも含む）をコマ f で。finishCut から前のショットを求めるのに使う
const blendedBefore = (p: CalcProps, segs: {shot: Shot; start: number}[], j: number, f: number): Cam => {
  const cur = shotCam(p, f, segs[j].shot);
  if (j === 0 || f - segs[j].start >= BLEND) return cur;
  const prev = blendedBefore(p, segs, j - 1, f);
  return {pos: lerp3(prev.pos, cur.pos, smooth((f - segs[j].start) / BLEND)), target: lerp3(prev.target, cur.target, smooth((f - segs[j].start) / BLEND))};
};

// カメラ：今のショットと、前のショットからのつなぎ（BLEND コマ）。前のつなぎの途中でまた切り替わったら新しい方が勝つ
export const cameraAt = (p: CalcProps, f: number): Cam => {
  if (!p.frame.length) throw new Error('frames.json にコマがありません');
  const segs = segments(p);
  const ff = clampF(p.frame, f);
  let k = 0;
  while (k + 1 < segs.length && segs[k + 1].start <= ff) k++;
  const camSeg = (j: number): Cam => {
    const cur = shotCam(p, ff, segs[j].shot);
    if (j === 0 || ff - segs[j].start >= BLEND) return cur;
    if (segs[j].shot === 'goal_line' || (segs[j].shot === 'finish' && segs[j - 1].shot === 'goal_line')) return cur;   // ゴールの線の前後は切り替え
    if (segs[j].shot === 'finish' && finishCut(p, segs, j)) return cur;   // つなぎで勝った馬が隠れるなら、つながずに切り替える
    const prev = camSeg(j - 1);
    const w = smooth((ff - segs[j].start) / BLEND);
    return {pos: lerp3(prev.pos, cur.pos, w), target: lerp3(prev.target, cur.target, w)};
  };
  return camSeg(k);
};
