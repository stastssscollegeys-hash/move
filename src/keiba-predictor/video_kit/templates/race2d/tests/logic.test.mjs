// T-002：レース展開3Dの計算（src/race3d/logic.ts）のテスト（2026-11-20）
// データ＝tests/fixtures（フェブラリーS 2026・東京ダ1600 の frames.json。縦・横・展開予想）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import * as L from '../src/race3d/logic.ts';

const here = dirname(fileURLToPath(import.meta.url));
const load = (n) => JSON.parse(readFileSync(join(here, 'fixtures', n), 'utf8'));
const tall = load('result_tall.json');
const wide = load('result_wide.json');
const fc = load('forecast_tall.json');
const near = (a, b, e = 1e-6) => Math.abs(a - b) <= e;

test('TC-FR-HORSE-001: 毛色は馬番1〜16で4色以上・同じ馬番は同じ色', () => {
  const s = new Set();
  for (let n = 1; n <= 16; n++) s.add(L.coatFor(n).main);
  assert.ok(s.size >= 4, `毛色が ${s.size} 色しかない`);
  assert.deepEqual(L.coatFor(7), L.coatFor(7));
});

test('TC-FR-HORSE-002: ギャロップの時刻＝走った距離÷7.2m×動きの長さ（の余り）', () => {
  assert.ok(near(L.gallopTime(0, 0.58), 0));
  assert.ok(near(L.gallopTime(3.6, 0.58), 0.29));
  assert.ok(near(L.gallopTime(7.2, 0.58), 0));
  assert.ok(near(L.gallopTime(10.8, 0.58), 0.29));
});

test('TC-FR-HORSE-002: 走った距離の表＝0コマ目は全頭0・止めた最後の2コマで同じ（脚が止まる）', () => {
  const t = L.cumDistTable(tall.frame);
  const n = tall.frame.length;
  assert.equal(t.length, n);
  for (let i = 0; i < tall.horses.length; i++) {
    assert.equal(t[0][i], 0);
    assert.equal(L.hasStarted(t, 0, i), false);
    assert.ok(near(t[n - 1][i], t[n - 2][i], 1e-9), `${i} 番目の馬がゴールのあとも進んでいる`);
    assert.ok(t[n - 1][i] > 1500, '最後には1500m以上走っている');
    assert.equal(L.hasStarted(t, n - 1, i), true);
  }
  // 増えるだけ
  for (let f = 1; f < n; f++) for (let i = 0; i < tall.horses.length; i++) assert.ok(t[f][i] >= t[f - 1][i]);
});

test('TC-FR-HORSE-003: 向き＝前後3コマの進む向き・止まっていれば前後40コマ', () => {
  const F = tall.frame;
  const f = 200, i = 3;
  const a = F[f - 3].p[i], b = F[f + 3].p[i];
  assert.ok(near(L.yawAt(F, i, f), Math.atan2(b[1] - a[1], b[0] - a[0]), 0.01));
  assert.equal(L.isMoving(F, i, f), true);
  assert.equal(L.isMoving(F, i, F.length - 1), false);
  // ゴールで止まったコマでも向きは前（ゴールの直線の進む向き）を向いていて NaN でない
  const y = L.yawAt(F, i, F.length - 1);
  assert.ok(Number.isFinite(y));
});

test('TC-FR-DATA-001: 地面の位置＝frames.json の p（3D の z は −y）', () => {
  for (const f of [0, 100, 300, tall.frame.length - 1]) {
    for (let i = 0; i < tall.horses.length; i++) {
      const [x, z] = L.groundPos(tall.frame[f], i);
      assert.ok(near(x, tall.frame[f].p[i][0], 0.001));
      assert.ok(near(z, -tall.frame[f].p[i][1], 0.001));
    }
  }
});

test('TC-FR-CAM-002: 勝った馬＝最後のコマの rank[0]（馬番12）の並び番号', () => {
  const w = L.winnerIndex(tall);
  assert.equal(tall.horses[w].umaban, 12);
  assert.equal(tall.horses[w].umaban, tall.frame[tall.frame.length - 1].rank[0]);
  // 並びが馬番順でないデータ（展開予想は脚質の順）でも、馬番と並び番号を取り違えない
  const wf = L.winnerIndex(fc);
  assert.equal(fc.horses[wf].umaban, fc.frame[fc.frame.length - 1].rank[0]);
  assert.notDeepEqual(fc.horses.map((h) => h.umaban), [...fc.horses.map((h) => h.umaban)].sort((a, b) => a - b), '展開予想のデータが馬番順になっている（このテストの意味が無くなる）');
});

test('TC-FR-CAM-002: 線と円柱の当たり判定（4例）', () => {
  // 円柱：中心 (0,0)・半径1・高さ0〜2
  assert.equal(L.rayHitsCylinder([-5, 1, 0], [5, 1, 0], [0, 0], 1, 2), true);    // 真ん中を横切る
  assert.equal(L.rayHitsCylinder([-5, 1, 3], [5, 1, 3], [0, 0], 1, 2), false);   // 横にずれる
  assert.equal(L.rayHitsCylinder([-5, 5, 0], [5, 5, 0], [0, 0], 1, 2), false);   // 上を通る
  assert.equal(L.rayHitsCylinder([-5, 1, 0], [-2, 1, 0], [0, 0], 1, 2), false);  // 手前で止まる
});

const ORDER = ['side_high', 'follow', 'head_on', 'side_low', 'finish'];
const checkOrder = (p) => {
  let k = -1;
  for (let f = 0; f < p.frame.length; f++) {
    const s = L.shotAt(p, f);
    const j = ORDER.indexOf(s);
    if (j < 0) continue;
    assert.ok(j >= k, `コマ ${f} でショットが ${ORDER[k]} → ${s} と戻った`);
    k = j;
  }
};

// SDD のショットの表（上から順に当てる）をテストの側で書き下ろして、1コマずつ照らし合わせる
const expectShot = (p, f) => {
  const F = p.frame[f], res = p.mode !== 'forecast';
  if (F.phase === 'ゴール' && res) return 'finish';
  if (F.phase === '直線へ' || (!res && f === p.frame.length - 1)) return 'forecast_end';
  if (F.rem <= 250 && res) return 'side_low';
  if (F.rem <= 500 && res) return 'head_on';
  if (['3コーナー', '4コーナー', '残り600m', '最後の直線'].includes(F.phase)) return 'follow';
  return 'side_high';
};
test('TC-FR-CAM-001: ショットは表どおりで、順が戻らない（縦・横・展開予想）', () => {
  for (const p of [tall, wide, fc]) {
    checkOrder(p);
    for (let f = 0; f < p.frame.length; f++) assert.equal(L.shotAt(p, f), expectShot(p, f), `コマ ${f}（${p.mode}）`);
  }
  const seen = new Set(tall.frame.map((_, f) => L.shotAt(tall, f)));
  for (const s of ORDER) assert.ok(seen.has(s), `${s} が一度も出ない`);
});

// 集団の動き（frames.json の cam＝集団の真ん中）を差し引いたカメラの動きが1コマで5m以内＝急にとばない
// （速回しの区間は集団そのものが1コマに最大 約6.7m 進むので、カメラの動きそのものでは測らない・2026-11-20 TC を直した）
test('TC-FR-CAM-001: カメラは集団に対して1コマで5mを超えてとばない（縦・横・展開予想）', () => {
  for (const p of [tall, wide, fc]) {
    let prev = null, prevC = null;
    for (let f = 0; f < p.frame.length; f++) {
      const c = L.cameraAt(p, f);
      const C = [p.frame[f].cam[0], -p.frame[f].cam[1]];
      for (const v of [...c.pos, ...c.target]) assert.ok(Number.isFinite(v), `コマ ${f} の数が壊れている`);
      // ゴールへのつなぎで勝った馬が隠れるときだけ、つながずに切り替える（2026-11-20 Codex の Blocker の直し）。その1コマだけは数えない
      if (prev && !L.isCutFrame(p, f)) {
        const dx = (c.pos[0] - prev.pos[0]) - (C[0] - prevC[0]), dz = (c.pos[2] - prev.pos[2]) - (C[1] - prevC[1]), dy = c.pos[1] - prev.pos[1];
        const d = Math.hypot(dx, dy, dz);
        assert.ok(d <= 5, `コマ ${f} でカメラが集団に対して ${d.toFixed(2)}m とんだ（${L.shotAt(p, f - 1)} → ${L.shotAt(p, f)}）`);
      }
      prev = c; prevC = C;
    }
  }
});

test('TC-FR-CAM-002: ゴール後の全コマで、カメラは勝った馬を狙い、勝った馬は他の馬に隠れない', () => {
  for (const p of [tall, wide]) {
    const w = L.winnerIndex(p);
    let n = 0;
    for (let f = 0; f < p.frame.length; f++) {
      if (p.frame[f].phase !== 'ゴール') continue;
      const c = L.cameraAt(p, f);
      const [wx, wz] = L.groundPos(p.frame[f], w);
      n++;
      // 狙いはつなぎの途中（ゴールに切り替わって45コマ）は動いている最中なので、つなぎ終わってから判定する
      if (f - L.shotStartFrame(p, f) >= L.BLEND) assert.ok(Math.hypot(c.target[0] - wx, c.target[2] - wz) <= 3, `コマ ${f} でカメラの狙いが勝った馬から離れている`);
      // 隠れないかは、つなぎの途中も含めてゴール後の全コマで見る（2026-11-20 Codex の Blocker で、つなぎを飛ばしていたのを直した）
      // 胴・乗り手の頭・馬の頭・尻の4点を、前後に長いほかの馬の形で見る（2026-11-20 Codex の Must）
      assert.equal(L.hiddenSights(p, f, c.pos), 0, `コマ ${f} で勝った馬の一部が隠れる`);
      for (let i = 0; i < p.horses.length; i++) {
        if (i === w) continue;
        const [x, z] = L.groundPos(p.frame[f], i);
        assert.equal(L.rayHitsCylinder(c.pos, [wx, 1.5, wz], [x, z], 0.6, 2.5), false, `コマ ${f} で勝った馬が ${p.horses[i].umaban} 番に隠れる`);
      }
    }
    assert.ok(n > 0, 'ゴール後のコマが無い');
  }
});

test('TC-FR-OUT-002: 展開予想はゴールのカメラにならず、最後は forecast_end', () => {
  for (let f = 0; f < fc.frame.length; f++) assert.notEqual(L.shotAt(fc, f), 'finish');
  assert.equal(L.shotAt(fc, fc.frame.length - 1), 'forecast_end');
});

test('WAKU：枠の色は1〜8枠がそろう（Race2D・Race3DHQ の正本）', () => {
  for (let w = 1; w <= 8; w++) assert.equal(L.WAKU[w].length, 2);
});

test('全コース対応（2026-11-20）: 右回りのコースでは、カメラが進む向きの左（外ラチ側）に回る', () => {
  const p = JSON.parse(JSON.stringify(tall));
  let f = 30;   // つなぎの終わった side_high の所を探す
  while (!(L.shotAt(p, f) === 'side_high' && f - L.shotStartFrame(p, f) >= L.BLEND && L.shotAt(p, f + 10) === 'side_high')) f++;
  const side = (q) => {
    const c = L.cameraAt(q, f), F = q.frame[f], n = q.frame[f + 10];
    const hx = n.cam[0] - F.cam[0], hy = n.cam[1] - F.cam[1];       // 集団の進む向き（2D）
    const vx = c.pos[0] - F.cam[0], vy = -c.pos[2] - F.cam[1];        // 集団からカメラへ（3D の z は −y）
    return Math.sign(hx * vy - hy * vx);                              // ＋＝左・−＝右
  };
  assert.equal(side(p), -1, '左回りのカメラは進む向きの右（外）');
  p.track.turn = 'right';
  assert.equal(side(p), 1, '右回りのカメラは進む向きの左（外）');
});

// ---- 2026-11-20 Codex の Must・Should で足したテスト ----
const clone = (o) => JSON.parse(JSON.stringify(o));

test('Codex Must: ほかの馬が勝った馬と同じ位置にいても、ゴールのカメラは確かめた候補の中から選ぶ（数が壊れない）', () => {
  const p = clone(tall);
  const w = L.winnerIndex(p), o = w === 0 ? 1 : 0;
  for (const F of p.frame) if (F.phase === 'ゴール') F.p[o] = [...F.p[w]];
  let n = 0;
  for (let f = 0; f < p.frame.length; f++) {
    if (p.frame[f].phase !== 'ゴール') continue;
    n++;
    const c = L.finishCam(p, f);
    for (const v of [...c.pos, ...c.target]) assert.ok(Number.isFinite(v), `コマ ${f} の数が壊れている`);
    assert.ok(L.FINISH_HEIGHTS.includes(c.pos[1]), `コマ ${f} で確かめていない高さ ${c.pos[1]} を返した`);
    // 返した候補より隠れる数の少ない候補は無い（同じ数なら高い方）＝低い候補（4m）に落ちていない
    assert.ok(c.pos[1] > 4 || L.hiddenSights(p, f, c.pos) === 0, `コマ ${f} で一番低い候補に落ちた`);
  }
  assert.ok(n > 0);
});

test('Codex Must: 胴だけでなく乗り手の頭も見る（間に馬がいれば2点以上隠れる・真上からは見える）', () => {
  const p = clone(tall);
  const f = p.frame.length - 1, w = L.winnerIndex(p), o = w === 0 ? 1 : 0;
  const [x, y] = p.frame[f].p[w];
  p.frame[f].p[o] = [x + 4, y];
  assert.ok(L.hiddenSights(p, f, [x + 10, 2.0, -y], w) >= 2);
  assert.equal(L.hiddenSights(p, f, [x, 60, -y], w), 0);
});

test('Codex Should: 幅や倍率が 0 でもカメラの数が NaN にならない・1コマ1頭でも動く', () => {
  const p = clone(tall);
  p.view[2] = 0;
  for (const F of p.frame) F.cam[2] = 0;
  for (const f of [0, 100, 300]) {
    const c = L.cameraAt(p, f);
    for (const v of [...c.pos, ...c.target]) assert.ok(Number.isFinite(v), `コマ ${f}`);
  }
  const wi = L.winnerIndex(tall);
  const one = clone(tall);
  one.horses = [one.horses[wi]];
  one.frame = [one.frame[0]];
  one.frame[0].p = [one.frame[0].p[wi]];
  one.frame[0].rank = [one.horses[0].umaban];
  L.checkProps(one);
  const c = L.cameraAt(one, 0);
  for (const v of [...c.pos, ...c.target]) assert.ok(Number.isFinite(v));
});

test('Codex Should: 入力がおかしいときは分かる言葉で止まる', () => {
  const a = clone(tall); a.frame = [];
  assert.throws(() => L.checkProps(a), /コマがありません/);
  assert.throws(() => L.cameraAt(a, 0), /コマがありません/);
  const b = clone(tall); b.w = 0;
  assert.throws(() => L.checkProps(b), /画面の大きさ/);
  const c = clone(tall); c.frame[5].p.pop();
  assert.throws(() => L.checkProps(c), /コマ 5 の馬の数/);
  const d = clone(tall); d.frame[7].p[0] = [NaN, 0];
  assert.throws(() => L.checkProps(d), /コマ 7 に数でない位置/);
  const g = clone(tall); g.horses = [];
  assert.throws(() => L.checkProps(g), /馬がいません/);
  const h = clone(tall); delete h.view;
  assert.throws(() => L.checkProps(h), /view/);
  const i = clone(tall); delete i.frame[3].lead;
  assert.throws(() => L.checkProps(i), /コマ 3 の先頭の位置/);
  const j = clone(tall); j.frame[4].rank = [];
  assert.throws(() => L.checkProps(j), /コマ 4 の順位/);
  L.checkProps(tall); L.checkProps(wide); L.checkProps(fc);
});

// 2026-11-20 予想の着順（prediction）の最後の直線：ユーザー「最後の展開がどうやって最終画面に変わったか分からない」「最後まで丁寧に展開を入れられないのかな」
// データ＝tests/fixtures/prediction_wide.json（福島記念 2026・福島芝2000 を build_frames.py --fast 5.6 --slow 4.0 で。--final 1.5・--final-m 300 は既定）
const pr = load('prediction_wide.json');
test('TC-PRED-001: 予想の着順は、残り final_m から速回しをゆるめる（1コマに進む距離が小さい）', () => {
  assert.ok(pr.final_m > 0, 'final_m が frames.json に入っていない');
  for (let f = 1; f < pr.frame.length; f++) {
    const a = pr.frame[f - 1], b = pr.frame[f];
    if (a.rem <= pr.final_m && a.rem > 0 && b.rem > 0) assert.ok(a.rem - b.rem <= 1.2, `コマ ${f} で先頭が1コマに ${a.rem - b.rem}m 進んだ（ゆるめていない）`);
  }
});
test('TC-PRED-002: 予想の着順は、直線を印の馬に寄って追い → ゴールの線 → ゴールの順で、線は切り替え・カメラは止めたまま', () => {
  const seq = [];
  for (let f = 0; f < pr.frame.length; f++) { const s = L.shotAt(pr, f); if (seq[seq.length - 1] !== s) seq.push(s); }
  assert.deepEqual(seq.slice(-3), ['side_low', 'goal_line', 'finish'], `ショットの並び ${seq.join(' → ')}`);
  const g = []; for (let f = 0; f < pr.frame.length; f++) if (L.shotAt(pr, f) === 'goal_line') g.push(f);
  assert.ok(L.isCutFrame(pr, g[0]) && L.isCutFrame(pr, g[g.length - 1] + 1), 'ゴールの線の前後が切り替えになっていない');
  const c0 = L.cameraAt(pr, g[0]), c1 = L.cameraAt(pr, g[g.length - 1]);
  assert.deepEqual(c0.pos, c1.pos, 'ゴールの線のカメラの位置が動いた（真横に置いて振るだけ）');
  // 真横：カメラから線の真ん中への向きが、ゴールの線の向きと平行（進む向きとは直角）
  const goal = pr.track.marks.find((m) => m.u === 0);
  const gx = goal.b[0] - goal.a[0], gy = goal.b[1] - goal.a[1], gl = Math.hypot(gx, gy);
  const vx = c1.target[0] - c1.pos[0], vy = -(c1.target[2] - c1.pos[2]), vl = Math.hypot(vx, vy);
  assert.ok(Math.abs((vx * gx + vy * gy) / (vl * gl)) > 0.98, 'ゴールの線を真横から見ていない');
  assert.ok(pr.frame[g[0]].rem <= L.GOAL_LINE_M, 'ゴールの線のショットが早すぎる');
});
test('TC-PRED-003: 結果のレースと展開予想のショットは変わらない（予想の着順だけの直し）', () => {
  for (const p of [tall, wide, fc]) for (let f = 0; f < p.frame.length; f++) assert.notEqual(L.shotAt(p, f), 'goal_line');
});
