// T-006：見た目の仕上げ（T-004 のレビューの Should）を数字で確かめる（2026-11-20）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import * as L from '../src/race3d/logic.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const load = (n) => JSON.parse(readFileSync(join(root, 'tests', 'fixtures', n), 'utf8'));
const tall = load('result_tall.json'), fc = load('forecast_tall.json');
const scene = readFileSync(join(root, 'src', 'race3d', 'Scene.tsx'), 'utf8');

test('ゴールの柱の円盤は半径 0.7m 以下（カメラの前で大きく映らない）', () => {
  // 目印のコメント「決勝の柱の円盤」のすぐあとの円柱だけを見る（2026-11-20 最初の書き方はハロン棒の円柱に当たってしまい、赤にならなかった）
  const m = scene.match(/決勝の柱の円盤[^\n]*\n[^\n]*cylinderGeometry args=\{\[([\d.]+), ([\d.]+), [\d.]+, \d+\]\}/);
  assert.ok(m, 'ゴールの柱の円盤が見つからない');
  assert.ok(Number(m[1]) <= 0.7 && Number(m[2]) <= 0.7, `円盤の半径が ${m[1]}`);
});

test('縦のゴールのカメラは狙いを 2m 以上に上げる（下の地面を減らす）', () => {
  let n = 0;
  for (let f = 0; f < tall.frame.length; f++) {
    if (tall.frame[f].phase !== 'ゴール' || f - L.shotStartFrame(tall, f) < L.BLEND) continue;
    n++;
    assert.ok(L.cameraAt(tall, f).target[1] >= 2.0, `コマ ${f} の狙いの高さ ${L.cameraAt(tall, f).target[1]}`);
  }
  assert.ok(n > 0);
});

test('展開予想の最後のカメラは見下ろす角度 25度以下（遠景が入る）', () => {
  const c = L.cameraAt(fc, fc.frame.length - 1);
  const h = Math.hypot(c.pos[0] - c.target[0], c.pos[2] - c.target[2]);
  const deg = Math.atan2(c.pos[1] - c.target[1], h) * 180 / Math.PI;
  assert.ok(deg <= 25, `見下ろす角度 ${deg.toFixed(1)}度`);
});

test('効いていない色の設定（toneMapped={false}）を残さない', () => {
  assert.doesNotMatch(scene, /toneMapped=\{false\}/);
});
