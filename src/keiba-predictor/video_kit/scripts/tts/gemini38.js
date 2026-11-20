/**
 * gemini38.js — Gemini TTS の共通部品（2026-11-19）
 *
 * - モデル: 既定 gemini-3.8-flash-tts（.env の TTS_MODEL で変えられる）
 * - 声と読み方（style）を話し手ごとに分ける。話し手の設定は templates/voices.json（台本の "speakers" で上書きできる）
 * - 1日の上限（HTTP 429 の per day）に当たったら、GEMINI_API_KEY → GEMINI_API_KEY2 … の順に次の鍵へ移る
 * - 返り値は WAV（24kHz・16bit・モノラル）
 *
 * 使い方（ほかのスクリプトから）:
 *   const g = require("./gemini38");
 *   const sp = g.speakers(script);               // 話し手の一覧（voices.json＋台本の上書き）
 *   const wav = await g.tts(text, sp["kaisetsu"]); // { voice, style } を渡す
 */
require("dotenv").config({ path: require("path").resolve(__dirname, "../../.env") });
// リポジトリに取り込んだ版（src/keiba-predictor/video_kit）は、リポジトリ直下の .env も読む（先に読んだ値が優先）
require("dotenv").config({ path: require("path").resolve(__dirname, "../../../../../.env") });
const https = require("https");
const fs = require("fs");
const path = require("path");

const MODEL = process.env.TTS_MODEL || "gemini-3.8-flash-tts";
const KEYS = ["GEMINI_API_KEY", "GEMINI_API_KEY2", "GEMINI_API_KEY3", "GEMINI_API_KEY4", "GEMINI_API_KEY5"]
  .map((k) => process.env[k]).filter(Boolean);
let ki = 0;
let last = 0;
const MIN_INTERVAL_MS = 1500;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function wavHeader(n, sr = 24000) {
  const h = Buffer.alloc(44);
  h.write("RIFF", 0); h.writeUInt32LE(36 + n, 4); h.write("WAVE", 8); h.write("fmt ", 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(sr, 24);
  h.writeUInt32LE(sr * 2, 28); h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34); h.write("data", 36); h.writeUInt32LE(n, 40);
  return h;
}
const isWav = (b) => b.length > 12 && b.toString("ascii", 0, 4) === "RIFF";

function speakers(script = {}) {
  const base = JSON.parse(fs.readFileSync(path.resolve(__dirname, "../../templates/voices.json"), "utf8")).speakers;
  return { ...base, ...(script.speakers || {}) };
}

function post(body, key) {
  return new Promise((resolve, reject) => {
    const req = https.request({
      hostname: "generativelanguage.googleapis.com", path: "/v1beta/interactions", method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": key, "Content-Length": Buffer.byteLength(body) },
      timeout: 300000,
    }, (r) => { const ch = []; r.on("data", (c) => ch.push(c)); r.on("end", () => resolve({ status: r.statusCode, body: Buffer.concat(ch).toString("utf8") })); });
    req.on("error", reject);
    req.on("timeout", () => req.destroy(new Error("timeout")));
    req.end(body);
  });
}

/** 声に渡す文だけ、読み間違えやすい言葉をひらがなにする（tts_yomi.py の表を使う・字幕と台本は漢字のまま）。
 *  2026-11-19 手順書には書いてあったのに Gemini の道具から呼ばれていなかった（霜月S の試しで気づいた）。KVC_NO_YOMI=1 で止める */
function yomi(text) {
  if (process.env.KVC_NO_YOMI === "1") return text;
  const { spawnSync } = require("child_process");
  const py = process.platform === "win32" ? "python" : "python3";
  const code = "import sys; sys.path.insert(0, sys.argv[1]); from tts_yomi import yomi; sys.stdout.write(yomi(sys.stdin.read()))";
  const r = spawnSync(py, ["-c", code, __dirname], { input: text, encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf-8" } });
  if (r.status !== 0 || !r.stdout) { console.log("  （読み替えの表を使えませんでした。そのまま読ませます）"); return text; }
  return r.stdout;
}

/** text を、sp（{voice, style}）の声で読ませて WAV を返す。extraStyle は読み方に足す一言（まとめ読みの「間をあける」など） */
async function tts(text, sp, extraStyle = "") {
  if (!KEYS.length) throw new Error(".env に GEMINI_API_KEY がありません");
  text = yomi(text);
  const style = [sp.style, extraStyle].filter(Boolean).join("。");
  const content = { type: "text", text };
  if (style) content.annotations = [{ type: "speech_metadata", style }];
  const body = JSON.stringify({
    model: MODEL, input: [{ type: "user_input", content: [content] }],
    response_format: { type: "audio" }, generation_config: { speech_config: [{ voice: sp.voice }] },
  });
  for (let attempt = 1; ; attempt++) {
    const wait = last + MIN_INTERVAL_MS - Date.now();
    if (wait > 0) await sleep(wait);
    last = Date.now();
    const res = await post(body, KEYS[ki]);
    if (res.status === 200) {
      const j = JSON.parse(res.body);
      const auds = (j.steps || []).filter((s) => s.type === "model_output").flatMap((s) => s.content || []).filter((c) => c.type === "audio");
      if (!auds.length) throw new Error("音声が返りませんでした: " + res.body.slice(0, 200));
      const buf = Buffer.from(auds[auds.length - 1].data, "base64");
      return isWav(buf) ? buf : Buffer.concat([wavHeader(buf.length), buf]);
    }
    if (res.status === 402) throw new Error("Gemini API の前払い残高が0です（HTTP 402）");
    const perDay = res.status === 429 && /per ?day|PerDay|daily/i.test(res.body);
    if (perDay) {
      if (ki + 1 < KEYS.length) { ki++; console.log(`  （1日の上限 → ${ki + 1}本目の鍵に切り替え）`); attempt = 0; continue; }
      throw new Error("全部の鍵が1日の上限に当たりました（HTTP 429）");
    }
    if ([429, 500, 503].includes(res.status) && attempt < 5) {
      console.log(`  （HTTP ${res.status}。20秒待って打ち直します）`); await sleep(20000); continue;
    }
    throw new Error(`Gemini TTS が HTTP ${res.status}: ${res.body.slice(0, 300)}`);
  }
}

module.exports = { tts, speakers, wavHeader, MODEL, yomi };
