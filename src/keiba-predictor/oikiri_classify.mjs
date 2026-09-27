/**
 * oikiri_classify.mjs — 追い切りコメント文からS〜Eを自動採点する（2026-09-25）
 *
 * ねらい: 手作業で貯めた評価（oikiri.json）を正解に、「文章だけで評価を当てられるか」を測る。
 *   当てられるなら、重賞以外や他サイトのコメントにも広げて sc[9] の蓄積を加速できる。
 *   Jev（型付き出力の新モデル）を使わなくても、既存のGeminiキー＋構造化出力で同じことができるか確かめる版。
 *
 * 使い方: node oikiri_classify.mjs <bench.json> <out.json> [件数]
 */
import fs from 'fs';
import { createRequire } from 'module';

const req = createRequire('C:/Users/User/dev/move/.claude/skills/manga-story-video-ss/scripts/');
req('dotenv').config({ path: 'C:/Users/User/dev/move/.env' });
const { GoogleGenAI } = req('@google/genai');

const MODEL = process.env.OIKIRI_MODEL || 'gemini-3.6-flash';   // 2.5-flashは2026-09時点で新規利用不可
const KEYS = [process.env.GEMINI_API_KEY, process.env.GEMINI_API_KEY2, process.env.GEMINI_API_KEY3,
              process.env.GEMINI_API_KEY4, process.env.GEMINI_API_KEY5].filter(Boolean);
let ki = 0;

const RULE = `あなたは競馬の調教（追い切り）評価を付ける担当です。
与えられるのは1頭分の「調教タイム」と「追い切りの内容を書いた文章」です。評価の文字は取り除いてあります。
この文章を書いた評論家が最終的に何段階の評価を付けたかを推定してください。

評価は6段階です。
S: 文句なしの最高の動き。時計も動きも際立ち、仕上がりが絶好と読める
A: 良い動き。好調とはっきり書かれている
B: 標準。悪くないが特筆するほどではない、順調程度
C: 物足りない。太め残り、動きが重い、集中を欠く、前走より劣るなどの指摘がある
D: 明確に不安が大きい
E: 測定不能（調教内容がほとんど不明）

注意: 文章の褒め方の強さと、不安要素の書かれ方の両方を見てください。日本語の婉曲表現に注意（「この馬なりに」「悪くはない」は高評価ではありません）。`;

function schema() {
  return {
    type: 'object',
    properties: {
      grade: { type: 'string', enum: ['S', 'A', 'B', 'C', 'D', 'E'] },
      confidence: { type: 'number', description: '0から1の確信度' },
      score: { type: 'number', description: '動きの良さの点数。0=最悪、100=絶好。同点を避けて細かく付ける' },
    },
    required: ['grade', 'confidence', 'score'],
  };
}

// MODE=times: 調教タイムの表だけを渡す（平場で手に入るのはタイムだけなので、その条件を再現する）
const MODE = process.env.OIKIRI_MODE || 'full';
function bodyOf(row) {
  if (MODE !== 'times') return row.text;
  const lines = row.text.split('\n');
  const end = lines.findIndex((l, i) => i > 2 && l.trim() === '');
  return lines.slice(0, end > 0 ? end : 8).join('\n');
}

async function classify(row) {
  for (let attempt = 0; attempt < KEYS.length * 2; attempt++) {
    const ai = new GoogleGenAI({ apiKey: KEYS[ki] });
    try {
      const res = await ai.models.generateContent({
        model: MODEL,
        contents: [{ parts: [{ text: `${RULE}\n\n---\n【馬名】${row.馬名}\n${bodyOf(row)}` }] }],
        config: { responseMimeType: 'application/json', responseSchema: schema(), temperature: 0 },
      });
      return JSON.parse(res.text);
    } catch (e) {
      const msg = e?.message || String(e);
      const quota = msg.includes('429') || msg.includes('quota') || msg.includes('RESOURCE_EXHAUSTED');
      ki = (ki + 1) % KEYS.length;
      await new Promise(r => setTimeout(r, quota ? 2000 : 8000));
      if (attempt === KEYS.length * 2 - 1) return { grade: null, confidence: 0, error: msg.slice(0, 120) };
    }
  }
}

const rows = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
const out = process.argv[3];
const limit = process.argv[4] ? Number(process.argv[4]) : rows.length;
const results = [];
for (const [i, row] of rows.slice(0, limit).entries()) {
  const t0 = Date.now();
  const r = await classify(row);
  results.push({ ...row, pred: r.grade, confidence: r.confidence, score: r.score, error: r.error, ms: Date.now() - t0, text: undefined });
  if (r.error) console.log('   err:', r.error);
  const ok = r.grade === row.grade_true ? 'OK ' : '   ';
  console.log(`[${i + 1}/${limit}] ${ok}${row.race} ${row.馬名} 正解=${row.grade_true} 予測=${r.grade} 確信=${(r.confidence ?? 0).toFixed(2)} ${Date.now() - t0}ms`);
  fs.writeFileSync(out, JSON.stringify(results, null, 1), 'utf-8');
}
console.log('saved', out);
