// yt_studio_cdp.mjs — YouTube Studio の下書き作成を、画像生成用のデバッグChrome（ポート9222）にCDPで直接つないで行う（2026-11-11）
// Claude in Chrome の file_upload は10MBまで＝動画は入らない → CDP の DOM.setFileInputFiles を使う（大きさの制限なし）
// 使い方（<tab> はタブURLの先頭一致。例 https://studio.youtube.com/channel/<ID>/videos）:
//   node yt_studio_cdp.mjs open <url>                       新しいタブで開く（遷移はこれで。ページ内で location.href を変えるとアップロード中は固まる）
//   node yt_studio_cdp.mjs eval <tab> "<式>"                  ページ内で評価
//   node yt_studio_cdp.mjs shot <tab> <out.jpg>               スクリーンショット
//   node yt_studio_cdp.mjs files <tab> "<css>" <path>         input[type=file] にファイルを入れる
//   node yt_studio_cdp.mjs type <tab> "<css>" <textfile>      テキスト欄を全消しして入れ直す（改行はそのまま。Enterキーで入れると改行が2重になる）
//   node yt_studio_cdp.mjs tags <tab> <textfile>              タグ（カンマ区切り）を1つずつ Enter で確定
// CDP helper: node yt.mjs open|eval|files <args>
setTimeout(()=>{console.log("TIMEOUT");process.exit(3)},25000);
const [cmd, ...args] = process.argv.slice(2);
const list = await (await fetch("http://localhost:9222/json")).json();
let t;
if (cmd === "open") {
  const r = await (await fetch("http://localhost:9222/json/new?" + encodeURIComponent(args[0]), { method: "PUT" })).json();
  console.log(JSON.stringify({ id: r.id, url: r.url })); process.exit(0);
}
t = list.find(x => x.type === "page" && x.url.startsWith(args[0]));
if (!t) { console.log("no tab", list.map(x => x.url)); process.exit(1); }
const ws = new WebSocket(t.webSocketDebuggerUrl); await new Promise(r => ws.onopen = r);
let id = 0; const pend = {};
ws.onmessage = e => { const d = JSON.parse(e.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; } };
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
await send("Page.bringToFront"); await send("Emulation.setFocusEmulationEnabled", { enabled: true });
if (cmd === "eval") {
  const r = await send("Runtime.evaluate", { expression: args[1], returnByValue: true, awaitPromise: true });
  console.log(JSON.stringify(r.result.result?.value ?? r.result).slice(0, 4000));
} else if (cmd === "shot") {
  const r = await send("Page.captureScreenshot", { format: "jpeg", quality: 60 });
  (await import("fs")).writeFileSync(args[1], Buffer.from(r.result.data, "base64")); console.log("saved");
} else if (cmd === "type") {   // type <urlpart> <css selector> <textfile>
  const txt = (await import("fs")).readFileSync(args[2], "utf8");
  const sel = JSON.stringify(args[1]);
  await send("Runtime.evaluate", { expression: `(()=>{const e=document.querySelector(${sel}); e.focus(); document.execCommand('selectAll'); document.execCommand('delete'); return 1})()` });
  await send("Input.insertText", { text: txt });
  const r = await send("Runtime.evaluate", { expression: `document.querySelector(${sel}).innerText`, returnByValue: true });
  console.log(JSON.stringify(r.result.result.value).slice(0, 300), "len", r.result.result.value.length);
} else if (cmd === "tags") {   // tags <urlpart> <textfile comma separated>
  const tags = (await import("fs")).readFileSync(args[1], "utf8").split(",").map(x => x.trim()).filter(Boolean);
  await send("Runtime.evaluate", { expression: "document.querySelector('#tags-container #text-input').focus()" });
  for (const t of tags) {
    await send("Input.insertText", { text: t });
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
    await new Promise(r => setTimeout(r, 200));
  }
  const r = await send("Runtime.evaluate", { expression: "[...document.querySelectorAll('#tags-container ytcp-chip')].map(c=>c.innerText.trim()).join('|')", returnByValue: true });
  console.log(r.result.result.value);
} else if (cmd === "files") {     // files <urlpart> <css selector> <path>
  const doc = await send("DOM.getDocument", { depth: -1, pierce: true });
  const q = await send("DOM.querySelectorAll", { nodeId: doc.result.root.nodeId, selector: args[1] });
  const ids = q.result.nodeIds; console.log("inputs", ids.length);
  const r = await send("DOM.setFileInputFiles", { nodeId: ids[ids.length - 1], files: [args[2]] });
  console.log(JSON.stringify(r).slice(0, 300));
}
process.exit(0);
