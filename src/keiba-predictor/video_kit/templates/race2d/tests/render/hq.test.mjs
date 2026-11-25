// T-003：Race3DHQ の書き出しのテスト（実際に Remotion で静止画を書き出す・1本 数秒〜十数秒）
// 使い方: node --test tests/render/hq.test.mjs   （普段の node tests/run-tests.mjs には入れない）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync, writeFileSync, existsSync, mkdtempSync, statSync, readdirSync, rmSync} from 'node:fs';
import {readPng} from './png.mjs';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const fx = join(root, 'tests', 'fixtures');
const work = mkdtempSync(join(tmpdir(), 'race3dhq-'));
const still = (props, frame, out) => spawnSync('npx', ['remotion', 'still', 'src/index.ts', 'Race3DHQ', out, `--props=${props}`, `--frame=${frame}`, '--gl=angle', '--log=error'],
  {cwd: root, encoding: 'utf8', timeout: 180000});

test('Integration: Race3DHQ の0コマ目が書き出せる（縦・終わったレース）', () => {
  const out = join(work, 'f0.png');
  const r = still(join(fx, 'result_tall.json'), 0, out);
  assert.equal(r.status, 0, r.stderr.slice(-800));
  assert.ok(existsSync(out) && statSync(out).size > 50000, '静止画ができていない（または真っ白に近い）');
});

test('E2E-04: 馬のモデルが読めないと「馬のモデルが読めません」で止まる', () => {
  const p = JSON.parse(readFileSync(join(fx, 'result_tall.json'), 'utf8'));
  p.horseFile = 'no_such_horse.glb';
  const pj = join(work, 'nohorse.json'); writeFileSync(pj, JSON.stringify(p));
  const r = still(pj, 0, join(work, 'x.png'));
  assert.notEqual(r.status, 0, '止まらずに書き出せてしまった');
  assert.match(r.stdout + r.stderr, /馬のモデルが読めません/);
});

// ---- 2026-11-20 Codex の Must で足した（馬が本当に映っているか・書き出し方で画が変わらないか・外を読む GLB を止めるか）----
const fps = JSON.parse(readFileSync(join(fx, 'result_tall.json'), 'utf8'));
rmSync(join(root, 'public', '_test_external.glb'), {force: true});   // 前の実行が途中で止まって残っていたら消す

test('Codex Must: 馬のいる所に、馬が本当に描かれている（馬だけ遠くへ動かした画と比べる）', async () => {
  const THREE = await import('three');
  const L = await import('../../src/race3d/logic.ts');
  const F = 200;
  const a = join(work, 'with.png'), b = join(work, 'without.png');
  assert.equal(still(join(fx, 'result_tall.json'), F, a).status, 0);
  const away = JSON.parse(JSON.stringify(fps));
  away.frame[F].p = away.frame[F].p.map((q) => [q[0] + 5000, q[1] + 5000]);   // カメラは集団の真ん中（cam）で決まるので同じ・馬だけ画面から消える
  const pj = join(work, 'away.json'); writeFileSync(pj, JSON.stringify(away));
  assert.equal(still(pj, F, b).status, 0);
  const A = readPng(a), B = readPng(b);
  const c = L.cameraAt(fps, F);
  const cam = new THREE.PerspectiveCamera(fps.h > fps.w ? 40 : 32, fps.w / fps.h, 0.3, 5000);
  cam.position.set(...c.pos); cam.lookAt(...c.target); cam.updateMatrixWorld(); cam.updateProjectionMatrix();
  let seen = 0, drawn = 0;
  for (let i = 0; i < fps.horses.length; i++) {
    const [x, z] = L.groundPos(fps.frame[F], i);
    const v = new THREE.Vector3(x, 1.3, z).project(cam);
    const px = Math.round((v.x + 1) / 2 * A.w), py = Math.round((1 - v.y) / 2 * A.h);
    if (v.z > 1 || px < 20 || px >= A.w - 20 || py < A.h * 0.3 || py >= A.h - 20) continue;   // 画面の外・上の帯と順位の所は数えない
    seen++;
    let diff = 0, all = 0;
    for (let y = py - 14; y <= py + 14; y++) for (let x2 = px - 14; x2 <= px + 14; x2++) {
      const p = A.at(x2, y), q = B.at(x2, y); all++;
      if (Math.max(Math.abs(p[0] - q[0]), Math.abs(p[1] - q[1]), Math.abs(p[2] - q[2])) > 40) diff++;
    }
    if (diff / all > 0.1) drawn++;
  }
  assert.ok(seen >= 8, `画面に入る馬が ${seen} 頭しかない（テストの前提が崩れている）`);
  assert.ok(drawn >= seen * 0.8, `馬のいる所 ${seen} か所のうち、馬が描かれていたのは ${drawn} か所だけ`);
});

test('Codex Must: 同じコマは、続けて書き出しても1コマだけ書き出しても同じ画になる', () => {
  const dir = join(work, 'seq');
  const r = spawnSync('npx', ['remotion', 'render', 'src/index.ts', 'Race3DHQ', dir, '--sequence', '--frames=198-200', '--image-format=png', `--props=${join(fx, 'result_tall.json')}`, '--gl=angle', '--log=error'],
    {cwd: root, encoding: 'utf8', timeout: 300000});
  assert.equal(r.status, 0, r.stderr.slice(-800));
  const seqFile = readdirSync(dir).find((f) => /200\.png$/.test(f));
  assert.ok(seqFile, '続けて書き出した 200 コマ目が無い');
  const one = join(work, 'one200.png');
  assert.equal(still(join(fx, 'result_tall.json'), 200, one).status, 0);
  assert.ok(readPng(join(dir, seqFile)).px.equals(readPng(one).px), '続けて書き出した画と、1コマだけ書き出した画が違う');
});

test('Codex Must: 外のファイルを読みに行く馬のモデル（GLB）は「外のファイルを読みに行きます」で止まる', () => {
  const t = new TextEncoder().encode(JSON.stringify({asset: {version: '2.0'}, images: [{uri: 'https://example.com/a.png'}]}));
  const body = new Uint8Array(Math.ceil(t.length / 4) * 4).fill(0x20); body.set(t);
  const g = Buffer.alloc(20 + body.length);
  g.writeUInt32LE(0x46546c67, 0); g.writeUInt32LE(2, 4); g.writeUInt32LE(g.length, 8); g.writeUInt32LE(body.length, 12); g.writeUInt32LE(0x4e4f534a, 16); g.set(body, 20);
  const name = '_test_external.glb', gp = join(root, 'public', name);
  writeFileSync(gp, g);
  try {
    const p = JSON.parse(JSON.stringify(fps)); p.horseFile = name;
    const pj = join(work, 'ext.json'); writeFileSync(pj, JSON.stringify(p));
    const r = still(pj, 0, join(work, 'ext.png'));
    assert.notEqual(r.status, 0, '止まらずに書き出せてしまった');
    assert.match(r.stdout + r.stderr, /外のファイルを読みに行きます/);
  } finally { rmSync(gp, {force: true}); }
});

test('E2E-05: コマの無いデータは「frames.json にコマがありません」で止まる', () => {
  const p = JSON.parse(readFileSync(join(fx, 'result_tall.json'), 'utf8'));
  p.frame = [];
  const pj = join(work, 'empty.json'); writeFileSync(pj, JSON.stringify(p));
  const r = still(pj, 0, join(work, 'y.png'));
  assert.notEqual(r.status, 0, '止まらずに書き出せてしまった');
  assert.match(r.stdout + r.stderr, /frames\.json にコマがありません/);
});
