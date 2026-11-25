// SSOT-001／TC-NFR-SEC-001：枠の色の正本は1か所・3Dの描画に外へ取りに行く読み込みが無い（2026-11-20 T-004）
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync, existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const src = (p) => readFileSync(join(root, 'src', p), 'utf8');

test('SSOT-001: 枠の色（WAKU）の定義は logic.ts だけ。Race2D と高品質版の3Dは logic.ts から読む', () => {
  assert.match(src('race3d/logic.ts'), /export const WAKU/);
  for (const f of ['Race2D.tsx', 'Race3DHQ.tsx', 'race3d/Scene.tsx', 'race3d/horses.ts']) {
    if (!existsSync(join(root, 'src', f))) assert.fail(`${f} が無い`);
    assert.doesNotMatch(src(f), /const WAKU\s*[:=]/, `${f} に WAKU の定義が残っている`);
  }
  assert.match(src('Race2D.tsx'), /import \{[^}]*WAKU[^}]*\} from '\.\/race3d\/logic'/);
});

test('TC-NFR-SEC-001: 高品質版の3Dの部品に http(s) で取りに行く読み込みが無い（コメントは除く）', () => {
  const files = ['Race3DHQ.tsx', ...readdirSync(join(root, 'src', 'race3d')).map((f) => `race3d/${f}`)];
  for (const f of files) {
    const code = src(f).split('\n').filter((l) => !l.trim().startsWith('//')).join('\n');
    assert.doesNotMatch(code, /['"`]https?:\/\//, `${f} に外への読み込みがある`);
  }
});

test('FR-ENV-001・FR-LOOK-001: 景色と後処理の部品がある（空・木・スタンド・柵・ハロン棒・ゴールの柱・輪・後処理）', () => {
  const s = src('race3d/Scene.tsx');
  for (const k of ['Sky', 'trees', 'stand', 'fence', 'poles', 'goal', 'winnerRing']) assert.match(s, new RegExp(k), `Scene に ${k} が無い`);
  const p = src('race3d/Post.tsx');
  for (const k of ['N8AO', 'SMAA', 'ToneMapping', 'Vignette']) assert.match(p, new RegExp(k), `Post に ${k} が無い`);
});
