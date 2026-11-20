/**
 * tts_chunks.js — 本編（長尺）の声を、数場面ずつまとめて1回で読ませる（まとめ読み）
 *
 * 2026-11-19 改定: gemini-3.8-flash-tts（共通部品 gemini38.js）に変えた。
 *   - 場面の "speaker" で声と読み方を分ける（対話モード）。1回の呼び出しは1人の声なので、対話のときは
 *     【話し手ごとに台本じゅうのせりふを集めて】まとめ読みし、split_chunks.py で場面に切って元の順に並べる
 *   - 段落の間に約2秒の無音を入れさせる（切り分けは今までどおり split_chunks.py）
 * 元: 2026-11-13（無料枠で50場面を1場面1回で作れないため、まとめ読みにした）
 *
 * 使い方: node tts_chunks.js <script_long.json> [--max=6] [--chars=520] [--only=3,5] [--byimage=0]
 * 出力: <scriptのフォルダ>/_chunks/{tag}_cNN.wav と {tag}_chunks.json（各チャンクの場面id）
 */
const fs = require("fs"), path = require("path");
const g = require("./gemini38");
const arg = (k, d) => { const a = process.argv.find((x) => x.startsWith(`--${k}=`)); return a ? a.split("=")[1] : d; };
const MAX = +arg("max", 6), CHARS = +arg("chars", 520);
const BYIMG = arg("byimage", "1") !== "0";
const ONLY = arg("only", "") ? arg("only", "").split(",").map(Number) : null;
const GAP = "段落と段落のあいだは、かならず2秒ほど間をあけてから次を読む。文章は1文字も変えない";

(async () => {
  const sp = process.argv[2], S = JSON.parse(fs.readFileSync(sp, "utf8"));
  const tag = path.basename(sp).replace(/^script_|\.json$/g, ""), out = path.join(path.dirname(sp), "_chunks");
  fs.mkdirSync(out, { recursive: true });
  const SP = g.speakers(S);
  const who = (s) => s.speaker || "narrator";
  for (const s of S.scenes) if (!SP[who(s)]) { console.error(`場面${s.id}: 話し手「${who(s)}」が voices.json にありません`); process.exit(1); }
  // チャンク分け: 1人の語りのときは、同じ画像が続く間をまとめる（最大 MAX 場面・CHARS 字）
  // 2026-11-19 対話モード（話し手が2人以上）: 話し手ごとに台本じゅうのせりふを集めてまとめる（場面は飛び飛びでよい。切ったあとは場面の id で元の順に並ぶ）
  //   依頼「男性のセリフは男性のセリフ、女性のセリフは女性のセリフでまとめて作っちゃって、それをうまく切り繋ぐ」
  //   前は話し手が変わるたびに区切っていたので、掛け合いだと1場面ずつに近くなり回数が増えた
  const chunks = []; let cur = [];
  const dialogue = new Set(S.scenes.map(who)).size > 1;
  const add = (s, byimg) => {
    const len = cur.reduce((a, x) => a + x.narration.length, 0);
    const prev = cur[cur.length - 1];
    if (cur.length && (cur.length >= MAX || len + s.narration.length > CHARS ||
        (byimg && s.image !== prev.image && cur.length >= 3))) { chunks.push(cur); cur = []; }
    cur.push(s);
  };
  if (dialogue) {
    for (const w of [...new Set(S.scenes.map(who))]) {
      for (const s of S.scenes) if (who(s) === w) add(s, false);
      if (cur.length) { chunks.push(cur); cur = []; }
    }
  } else {
    for (const s of S.scenes) add(s, BYIMG);
    if (cur.length) chunks.push(cur);
  }
  const cj = path.join(out, `${tag}_chunks.json`), now = JSON.stringify(chunks.map((c) => c.map((s) => s.id)));
  if (fs.existsSync(cj) && fs.readFileSync(cj, "utf8") !== now) {   // まとめ方が前と違う → 前のまとめ読みの音声は中身が合わないので消して作り直す
    for (const f of fs.readdirSync(out)) if (f.startsWith(`${tag}_c`) && f.endsWith(".wav")) fs.rmSync(path.join(out, f));
    console.log("  まとめ方が前と違うので、前のまとめ読みの音声を消して作り直します");
  }
  fs.writeFileSync(cj, now);
  console.log(`モデル ${g.MODEL} ／ ${S.scenes.length}場面 → ${chunks.length}チャンク${dialogue ? "（対話：話し手ごとに集めた）" : ""}`);
  for (let i = 0; i < chunks.length; i++) {
    if (ONLY && !ONLY.includes(i + 1)) continue;
    const f = path.join(out, `${tag}_c${String(i + 1).padStart(2, "0")}.wav`);
    if (fs.existsSync(f) && fs.statSync(f).size > 10000) continue;
    const w = who(chunks[i][0]);
    const text = chunks[i].map((s) => s.narration).join("\n\n");
    try {
      const wav = await g.tts(text, SP[w], chunks[i].length > 1 ? GAP : "");
      fs.writeFileSync(f, wav);
      console.log(`  c${i + 1} ${w} 場面${chunks[i].map((s) => s.id).join(",")}  ${((wav.length - 44) / 48000).toFixed(1)}秒`);
    } catch (e) {
      console.error(`  c${i + 1} 失敗: ${String(e.message || e).slice(0, 200)}（--only=${i + 1} で続きから流し直せます）`);
      process.exit(2);
    }
  }
})();
