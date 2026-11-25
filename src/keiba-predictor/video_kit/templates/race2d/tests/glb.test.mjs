// Codex の Must（2026-11-20）：外のファイルを読みに行く GLB は受け付けない
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';
import {externalUris} from '../src/race3d/glb.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const glb = (json) => {
  const t = new TextEncoder().encode(JSON.stringify(json));
  const pad = (4 - (t.length % 4)) % 4;
  const body = new Uint8Array(t.length + pad).fill(0x20); body.set(t);
  const b = new ArrayBuffer(20 + body.length); const v = new DataView(b);
  v.setUint32(0, 0x46546c67, true); v.setUint32(4, 2, true); v.setUint32(8, b.byteLength, true);
  v.setUint32(12, body.length, true); v.setUint32(16, 0x4e4f534a, true);
  new Uint8Array(b, 20).set(body);
  return b;
};

test('同梱の horse.glb は外のファイルを読みに行かない', () => {
  const b = readFileSync(join(root, 'public', 'horse.glb'));
  assert.deepEqual(externalUris(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)), []);
});

test('外の画像・外の buffer を指す GLB は見つかる（data: の埋め込みはよい）', () => {
  const found = externalUris(glb({asset: {version: '2.0'}, images: [{uri: 'https://example.com/a.png'}, {uri: 'data:image/png;base64,AAAA'}], buffers: [{uri: 'body.bin'}]}));
  assert.deepEqual(found.sort(), ['body.bin', 'https://example.com/a.png']);
  assert.deepEqual(externalUris(glb({asset: {version: '2.0'}, images: [{bufferView: 0}]})), []);
});

test('中身が途中で切れた GLB は分かる言葉で止める', () => {
  const b = glb({asset: {version: '2.0'}});
  assert.throws(() => externalUris(b.slice(0, b.byteLength - 8)), /途中で切れています/);
});

test('GLB でないファイル（.gltf の文字だけの形など）は止める', () => {
  assert.throws(() => externalUris(new TextEncoder().encode('{"asset":{}}').buffer), /1つのファイルで完結した形/);
});
