// TC-FR-LIC-001 ほか：同梱の馬の素材と出どころの記録（2026-11-20）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const glb = join(root, 'public', 'horse.glb');
const lic = join(root, 'public', 'LICENSE_horse.txt');

const readGltfJson = (p) => {
  const b = readFileSync(p);
  assert.equal(b.toString('latin1', 0, 4), 'glTF', 'glb の頭が glTF でない');
  const len = b.readUInt32LE(12);
  return JSON.parse(b.toString('utf8', 20, 20 + len));
};

test('TC-FR-LIC-001: LICENSE_horse.txt に作者・配布元・CC0・取得日がある', () => {
  assert.ok(existsSync(lic), 'public/LICENSE_horse.txt が無い');
  const t = readFileSync(lic, 'utf8');
  assert.match(t, /Quaternius/);
  assert.match(t, /https:\/\/poly\.pizza\/m\/qvTrSG9pZF/);
  assert.match(t, /CC0/);
  assert.match(t, /取得日: \d{4}-\d{2}-\d{2}/);
});

test('DATA-002: horse.glb に Gallop と Idle の動き・背中の骨 Torso2・色の部品 Main がある', () => {
  assert.ok(existsSync(glb), 'public/horse.glb が無い');
  const j = readGltfJson(glb);
  const anims = (j.animations || []).map((a) => a.name);
  assert.ok(anims.includes('Gallop'), 'Gallop が無い');
  assert.ok(anims.includes('Idle'), 'Idle が無い');
  assert.ok((j.nodes || []).some((n) => n.name === 'Torso2'), '骨 Torso2 が無い');
  assert.ok((j.materials || []).some((m) => m.name === 'Main'), '色の部品 Main が無い');
});
