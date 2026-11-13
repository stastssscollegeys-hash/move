/**
 * tts_chunks.js（2026-11-13・枠順確定版の長尺用）
 * 無料枠（1キー×1モデルで1日10回）では長尺の50場面を1場面1回で作れないため、
 * 連続する場面を数場面ずつ「段落」として1回で読ませ、chunks に保存する。切り分けは split_chunks.py。
 * 使い方: node tts_chunks.js <script_long.json> [--max=6] [--chars=520] [--only=3,5]
 * 出力: <scriptのフォルダ>/_chunks/{tag}_cNN.wav と {tag}_chunks.json（各チャンクの場面id）
 * 呼び出し・キー切替は src/keiba-predictor/gen_short_tts.js と同じ（声 Zephyr・モデルは TTS_MODEL で1つに固定）。
 */
require("dotenv").config({ path: "C:/Users/User/dev/move/.env" });
const { GoogleGenAI } = require("@google/genai");
const fs = require("fs"), path = require("path");
const arg = (k, d) => { const a = process.argv.find((x) => x.startsWith(`--${k}=`)); return a ? a.split("=")[1] : d; };
const MODEL = process.env.TTS_MODEL || "gemini-2.5-pro-preview-tts";
const VOICE = arg("voice", "Zephyr"), MAX = +arg("max", 6), CHARS = +arg("chars", 520);
const BYIMG = arg("byimage", "1") !== "0";
const ONLY = arg("only", "") ? arg("only", "").split(",").map(Number) : null;
const PRE = "Read the following Japanese narration aloud in a calm, clear, friendly voice. Between paragraphs, pause for about two full seconds of silence:\n\n";
function wavHeader(n, sr = 24000) { const h = Buffer.alloc(44); h.write("RIFF", 0); h.writeUInt32LE(36 + n, 4); h.write("WAVE", 8); h.write("fmt ", 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(sr, 24); h.writeUInt32LE(sr * 2, 28); h.writeUInt16LE(2, 32);
  h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(n, 40); return h; }
(async () => {
  const sp = process.argv[2], S = JSON.parse(fs.readFileSync(sp, "utf8"));
  const tag = path.basename(sp).replace(/^script_|\.json$/g, ""), out = path.join(path.dirname(sp), "_chunks");
  fs.mkdirSync(out, { recursive: true });
  // チャンク分け: 同じ画像が続く間はまとめる（最大 MAX 場面・CHARS 字）
  const chunks = []; let cur = [];
  for (const s of S.scenes) {
    const len = cur.reduce((a, x) => a + x.narration.length, 0);
    if (cur.length && (cur.length >= MAX || len + s.narration.length > CHARS || (BYIMG && s.image !== cur[cur.length - 1].image && cur.length >= 3))) { chunks.push(cur); cur = []; }
    cur.push(s);
  }
  if (cur.length) chunks.push(cur);
  fs.writeFileSync(path.join(out, `${tag}_chunks.json`), JSON.stringify(chunks.map((c) => c.map((s) => s.id))));
  const KEYS = ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3", "GEMINI_API_KEY4", "GEMINI_API_KEY5"].filter((k) => process.env[k]);
  let ki = 0, ai = new GoogleGenAI({ apiKey: process.env[KEYS[ki]] });
  console.log(`モデル ${MODEL} ／ ${S.scenes.length}場面 → ${chunks.length}チャンク`);
  for (let i = 0; i < chunks.length; i++) {
    if (ONLY && !ONLY.includes(i + 1)) continue;
    const f = path.join(out, `${tag}_c${String(i + 1).padStart(2, "0")}.wav`);
    if (fs.existsSync(f) && fs.statSync(f).size > 10000) continue;
    const text = PRE + chunks[i].map((s) => s.narration).join("\n\n");
    for (let t = 0; t < 8; t++) {
      try {
        const r = await ai.models.generateContent({ model: MODEL, contents: [{ parts: [{ text }] }],
          config: { responseModalities: ["AUDIO"], speechConfig: { voiceConfig: { prebuiltVoiceConfig: { voiceName: VOICE } } } } });
        const pcm = Buffer.from(r.candidates[0].content.parts[0].inlineData.data, "base64");
        fs.writeFileSync(f, Buffer.concat([wavHeader(pcm.length), pcm]));
        console.log(`  c${i + 1} 場面${chunks[i].map((s) => s.id).join(",")}  ${(pcm.length / 48000).toFixed(1)}秒`); break;
      } catch (e) {
        const m = String(e.message || e);
        if (/per ?day|PerDay|quota/i.test(m) && ki < KEYS.length - 1) { ai = new GoogleGenAI({ apiKey: process.env[KEYS[++ki]] }); console.log(`  キー切替 → ${ki + 1}本目`); continue; }
        console.log(`  c${i + 1} 再試行 ${t + 1}: ${m.slice(0, 120)}`); await new Promise((r) => setTimeout(r, /429/.test(m) ? 25000 : 5000));
      }
    }
    await new Promise((r) => setTimeout(r, 7000));
  }
})();
