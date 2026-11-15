/**
 * tts_missing.js — 台本のうち「まだ音声が無い場面だけ」を Gemini TTS で作る（2026-11-15 新設）
 * gen_short_tts.js は毎回1場面目から作り直すので、無料枠（1分あたり・1日あたりの回数が少ない）では同じ場面ばかり作ってしまう。
 * これは 無い場面だけ・キーを順に試す・429 のときは待ってやり直す。月の上限に達したキー（spending cap）と無効なキーは飛ばす。
 * 使い方: node tts_missing.js <script.json> [--dir=audio] [--prefix=mcs] [--wait=35] [--model=gemini-2.5-flash-preview-tts]
 * 出力: <scriptのフォルダ>/<dir>/<prefix>_NN.wav（24kHz/16bit/mono・素の速さ）
 */
require("dotenv").config({ path: require("path").resolve(__dirname, "../../.env") });
const { GoogleGenAI } = require("@google/genai");
const fs = require("fs"), path = require("path");
const arg = (k, d) => { const a = process.argv.find((x) => x.startsWith(`--${k}=`)); return a ? a.split("=")[1] : d; };
const MODEL = arg("model", process.env.TTS_MODEL || "gemini-2.5-flash-preview-tts"), VOICE = arg("voice", "Zephyr"), WAIT = +arg("wait", 35);
const sp = process.argv[2], S = JSON.parse(fs.readFileSync(sp, "utf8"));
const out = path.join(path.dirname(sp), arg("dir", "audio")); fs.mkdirSync(out, { recursive: true });
const prefix = arg("prefix", path.basename(sp).replace(/^script_|\.json$/g, ""));
function wavHeader(n, sr = 24000) { const h = Buffer.alloc(44); h.write("RIFF", 0); h.writeUInt32LE(36 + n, 4); h.write("WAVE", 8); h.write("fmt ", 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(sr, 24); h.writeUInt32LE(sr * 2, 28); h.writeUInt16LE(2, 32);
  h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(n, 40); return h; }
const sleep = (s) => new Promise((r) => setTimeout(r, s * 1000));
(async () => {
  let keys = ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3", "GEMINI_API_KEY4", "GEMINI_API_KEY5"].filter((k) => process.env[k]);
  const todo = S.scenes.filter((s) => { const f = path.join(out, `${prefix}_${String(s.id).padStart(2, "0")}.wav`); return !(fs.existsSync(f) && fs.statSync(f).size > 10000); });
  console.log(`モデル ${MODEL} ／ 全${S.scenes.length}場面のうち未作成 ${todo.length}場面`);
  let ki = 0, day = {};
  for (const s of todo) {
    const f = path.join(out, `${prefix}_${String(s.id).padStart(2, "0")}.wav`);
    let done = false;
    for (let t = 0; t < 12 && !done && keys.length; t++) {
      const k = keys[ki % keys.length];
      try {
        const ai = new GoogleGenAI({ apiKey: process.env[k] });
        const r = await ai.models.generateContent({ model: MODEL, contents: [{ parts: [{ text: "Read the following Japanese narration aloud in a calm, clear, friendly voice:\n\n" + s.narration }] }],
          config: { responseModalities: ["AUDIO"], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: VOICE } } } } });
        const pcm = Buffer.from(r.candidates[0].content.parts[0].inlineData.data, "base64");
        fs.writeFileSync(f, Buffer.concat([wavHeader(pcm.length), pcm]));
        console.log(`  [${s.id}] ${(pcm.length / 48000).toFixed(1)}秒 (${k.replace("GEMINI_API_", "")})`); done = true;
        await sleep(WAIT / 2);
      } catch (e) {
        const m = String(e.message || e);
        if (/spending cap|not valid/i.test(m)) { console.log(`  ${k.replace("GEMINI_API_", "")} は使えない（${/spending/.test(m) ? "月の上限" : "無効"}）→外す`); keys = keys.filter((x) => x !== k); continue; }
        if (/PerDay|per day|daily/i.test(m)) { day[k] = (day[k] || 0) + 1; if (day[k] >= 2) { console.log(`  ${k.replace("GEMINI_API_", "")} は1日の上限→外す`); keys = keys.filter((x) => x !== k); continue; } }
        ki++; console.log(`  [${s.id}] 待ち ${WAIT}秒: ${m.slice(0, 90).replace(/\s+/g, " ")}`); await sleep(WAIT);
      }
    }
    if (!done) { console.log(`  [${s.id}] 作れなかった → 中止`); break; }
  }
  const left = S.scenes.filter((s) => !fs.existsSync(path.join(out, `${prefix}_${String(s.id).padStart(2, "0")}.wav`))).length;
  console.log(`残り ${left}場面`);
})();
