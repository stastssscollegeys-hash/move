/**
 * gen_short_tts.js — ショート動画のナレーション音声をGemini TTSで生成する（2026-09-28新規）
 *
 * 入力: shorts/script_*.json（scenes[].narration）
 * 出力: shorts/audio/{race}_{id}.wav  … シーンごとのWAV（24kHz/16bit/mono）
 *
 * 既存の character-video-creator-ss/scripts/generate-audio.js と同じ Gemini TTS 基盤を使うが、
 * 競馬ショートは1レース5シーンと小さいので依存を減らして単体スクリプトにした。
 *
 * 使い方: node gen_short_tts.js <script.json> [--voice Zephyr]
 */
require("dotenv").config({ path: require("path").resolve(__dirname, "../../.env") });
const { GoogleGenAI } = require("@google/genai");
const fs = require("fs");
const path = require("path");

const MODELS = [process.env.TTS_MODEL, "gemini-2.5-flash-preview-tts", "gemini-2.5-pro-preview-tts"].filter(Boolean);
const VOICE = (process.argv.find((a) => a.startsWith("--voice=")) || "--voice=Zephyr").split("=")[1];

function wavHeader(pcmLen, sampleRate = 24000, ch = 1, bits = 16) {
  const byteRate = (sampleRate * ch * bits) / 8;
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + pcmLen, 4); h.write("WAVE", 8);
  h.write("fmt ", 12); h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20);
  h.writeUInt16LE(ch, 22); h.writeUInt32LE(sampleRate, 24); h.writeUInt32LE(byteRate, 28);
  h.writeUInt16LE((ch * bits) / 8, 32); h.writeUInt16LE(bits, 34);
  h.write("data", 36); h.writeUInt32LE(pcmLen, 40);
  return h;
}

async function tts(ai, text, model) {
  const r = await ai.models.generateContent({
    model,
    contents: [{ parts: [{ text }] }],
    config: {
      responseModalities: ["AUDIO"],
      speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: VOICE } } },
    },
  });
  const b64 = r.candidates[0].content.parts[0].inlineData.data;
  const pcm = Buffer.from(b64, "base64");
  return Buffer.concat([wavHeader(pcm.length), pcm]);
}

(async () => {
  const scriptPath = process.argv[2];
  if (!scriptPath) { console.error("使い方: node gen_short_tts.js <script.json>"); process.exit(1); }
  const script = JSON.parse(fs.readFileSync(scriptPath, "utf-8"));
  const outDir = path.join(path.dirname(scriptPath), "audio");
  fs.mkdirSync(outDir, { recursive: true });
  const tag = path.basename(scriptPath).replace(/^script_|\.json$/g, "");

  // 2026-11-09: 無料枠は「1キー×1モデルで1日10回」。--resume で既存のwavを飛ばし、1日の上限（429・per day）に当たったら次のキーへ回す
  const RESUME = process.argv.includes("--resume");
  const KEYS = ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3", "GEMINI_API_KEY4", "GEMINI_API_KEY5"].filter((k) => process.env[k]);
  let ki = 0;
  let ai = new GoogleGenAI({ apiKey: process.env[KEYS[ki]] });
  const model = MODELS[0];               // 声をそろえるため、モデルは1つに固定（確認用の試し呼び出しはしない＝回数を使わない）
  console.log(`TTSモデル: ${model} ／ 声: ${VOICE} ／ キー${KEYS.length}本\n`);

  for (const s of script.scenes) {
    const out = path.join(outDir, `${tag}_${String(s.id).padStart(2, "0")}.wav`);
    if (RESUME && fs.existsSync(out) && fs.statSync(out).size > 10000) continue;
    for (let i = 0; i < 3; i++) {
      try {
        fs.writeFileSync(out, await tts(ai, s.narration, model));
        const kb = (fs.statSync(out).size / 1024).toFixed(0);
        console.log(`  [${s.id}] ${kb} KB  ${s.narration.slice(0, 28)}…`);
        break;
      } catch (e) {
        const msg = String(e.message || e);
        if (msg.includes("PerDay") && ki + 1 < KEYS.length) {           // 1日の上限 → 次のキー（回数に数えない）
          ki++; ai = new GoogleGenAI({ apiKey: process.env[KEYS[ki]] }); console.log(`  キーを切り替え（${ki + 1}本目）`); i--; continue;
        }
        if (msg.includes("PerDay")) { console.error(`  [${s.id}] 失敗: 全キーが1日の上限`); process.exit(2); }
        if (i === 2) console.error(`  [${s.id}] 失敗: ${msg.slice(0, 200)}`);
        else await new Promise((r) => setTimeout(r, msg.includes("429") ? 20000 : 4000));
      }
    }
    await new Promise((r) => setTimeout(r, 1200));   // レート制限対策
  }
  console.log(`\n保存: ${outDir}`);
})();
