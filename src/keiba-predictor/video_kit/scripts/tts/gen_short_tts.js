/**
 * gen_short_tts.js — ショート動画のナレーション音声を Gemini TTS で場面ごとに作る
 *
 * 2026-11-19 改定: gemini-3.8-flash-tts（共通部品 gemini38.js）に変えた。場面の "speaker" で声と読み方を分ける（対話モード）
 *   話し手の設定 = templates/voices.json（narrator＝1人の語り・kaisetsu＝対話の解説役・asumeshi＝アスメシ）
 *
 * 入力: shorts/script_*.json（scenes[].narration ／ 任意で scenes[].speaker）
 * 出力: shorts/audio/{tag}_NN.wav（24kHz・16bit・モノラル）
 * 対話（話し手が2人以上）のときは、話し手ごとにまとめ読みして場面に切る（tts_chunks.js → split_chunks.py・回数が減る）
 * 使い方: node gen_short_tts.js <script.json> [--voice=Zephyr] [--resume] [--per-scene]
 *   --voice は1人の語り（narrator）の声だけを変える
 */
const fs = require("fs");
const path = require("path");
const g = require("./gemini38");

(async () => {
  const scriptPath = process.argv[2];
  if (!scriptPath) { console.error("使い方: node gen_short_tts.js <script.json>"); process.exit(1); }
  const script = JSON.parse(fs.readFileSync(scriptPath, "utf-8"));
  const outDir = path.join(path.dirname(scriptPath), "audio");
  fs.mkdirSync(outDir, { recursive: true });
  const tag = path.basename(scriptPath).replace(/^script_|\.json$/g, "");
  const RESUME = process.argv.includes("--resume");
  const sp = g.speakers(script);
  const v = process.argv.find((a) => a.startsWith("--voice="));
  if (v) sp.narrator = { ...sp.narrator, voice: v.split("=")[1] };
  console.log(`TTSモデル: ${g.MODEL} ／ 話し手: ${Object.entries(sp).map(([k, x]) => `${k}=${x.voice}`).join("・")}\n`);

  // 2026-11-19 対話モード（話し手が2人以上）: 場面ごとに1回ずつ読ませず、話し手ごとにせりふを集めてまとめ読み → 場面に切る
  //   （本編と同じ tts_chunks.js → split_chunks.py を通し、切った声を audio/ に置く）。--per-scene で今までどおり場面ごと
  const dialogue = new Set(script.scenes.map((s) => s.speaker || "narrator")).size > 1;
  if (dialogue && !process.argv.includes("--per-scene") && !v) {
    const { spawnSync } = require("child_process");
    const py = process.platform === "win32" ? "python" : "python3";
    const run = (cmd, args) => { const r = spawnSync(cmd, args, { stdio: "inherit" }); if (r.status) process.exit(r.status); };
    run(process.execPath, [path.join(__dirname, "tts_chunks.js"), scriptPath, "--max=8", "--chars=700"]);
    run(py, [path.join(__dirname, "..", "audio", "split_chunks.py"), scriptPath]);
    const raw = path.join(path.dirname(scriptPath), "_raw");
    for (const s of script.scenes) {
      const f = `${tag}_${String(s.id).padStart(2, "0")}.wav`;
      if (!fs.existsSync(path.join(raw, f))) { console.error(`  [${s.id}] 切り分けた声がありません（--per-scene で場面ごとに作り直せます）`); process.exit(2); }
      fs.copyFileSync(path.join(raw, f), path.join(outDir, f));
    }
    console.log(`\n保存: ${outDir}（対話：話し手ごとにまとめ読みして場面に切った。切り分けは文字起こしで確かめる）`);
    return;
  }

  for (const s of script.scenes) {
    const who = s.speaker || "narrator";
    if (!sp[who]) { console.error(`  [${s.id}] 話し手「${who}」が voices.json にありません`); process.exit(1); }
    const out = path.join(outDir, `${tag}_${String(s.id).padStart(2, "0")}.wav`);
    if (RESUME && fs.existsSync(out) && fs.statSync(out).size > 10000) continue;
    try {
      fs.writeFileSync(out, await g.tts(s.narration, sp[who]));
      console.log(`  [${s.id}] ${who}  ${(fs.statSync(out).size / 1024).toFixed(0)} KB  ${s.narration.slice(0, 28)}…`);
    } catch (e) {
      console.error(`  [${s.id}] 失敗: ${String(e.message || e).slice(0, 200)}`);
      process.exit(2);
    }
  }
  console.log(`\n保存: ${outDir}`);
})();
