// テストの入口（2026-11-20）。node の組み込みのテスト（node:test）で tests/*.test.mjs を全部流す。
// logic.ts があれば、その行の通過率（80% 以上）も測る。使い方: node tests/run-tests.mjs
import {spawnSync} from 'node:child_process';
import {readdirSync, existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const files = readdirSync(join(root, 'tests')).filter((f) => f.endsWith('.test.mjs')).map((f) => join('tests', f));
const logic = join(root, 'src', 'race3d', 'logic.ts');
const args = ['--test'];
if (existsSync(logic)) {
  args.push('--experimental-test-coverage', '--test-coverage-include=src/race3d/logic.ts', '--test-coverage-lines=80');
}
const r = spawnSync(process.execPath, [...args, ...files], {cwd: root, stdio: 'inherit'});
process.exit(r.status ?? 1);
