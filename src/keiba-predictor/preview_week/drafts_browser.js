// 来週の重賞プレビュー: X・Threads の「下書き保存」用ブラウザ処理（2026-11-02 作成・実績あり）
// 使い方: Claude in Chrome の javascript_tool で、前面のタブに貼って実行する（投稿はしない・下書きに保存するだけ）。
//   X       : x.com/home を開いたタブで __saveX(text) を投稿ごとに呼ぶ（1回の呼び出しは3〜4本まで）
//   Threads : threads.com を開いたタブで __saveThreads([text,...]) に配列で渡す（1回5〜7本まで）
// 文章は preview_week/posts.py が作る {日付}/research/preview_posts.json の x / threads から取る。
// 🔴 バックグラウンドのタブは省電力で固まる（9本で45秒超え→応答なし）。操作するタブを前面にして、数本ずつ。
// 🔴 応答しなかったあとに同じ内容をもう一度実行すると下書きが重複する。先に下書き一覧で状態を確認する。
// 🔴 古い下書きは Claude からは消さない（ユーザーが削除する）。
// 【2026-11-06 更新・実績あり】
//   ・X: 作成画面の「閉じる」ボタンが app-bar-close → app-bar-back に変わっていた（両方を試す）。貼り付け前に selectAll+delete で中身を空にする
//     （2本続けて貼ると1つの入力欄に連結される）。保存の結果 "0|保存|/home" は正常（文字数0と出ても保存される）。下書き一覧: x.com/compose/post/unsent/drafts
//   ・Threads: 「新しいスレッド」が svg ではなく role="button" の文字ラベルに変わっていた（両方を探す）。下書き一覧はダイアログ内の
//     [role=button][aria-label="下書き"]（innerText には出ない）。
//   ・🔴 ウィンドウが最小化/非表示のタブは innerWidth=0 になり Threads の画面が出ない（X は動く）。tabs_create_mcp で新しいタブを作ると 1280x585 で動く。
//   ・🔴 javascript_tool の出力に『=』や URL が混じると BLOCKED になる。結果は区切りを ' | ' にして返す。
// 【2026-11-08 更新・実績あり（当日朝の注目レース X5本・Threads20本を画像付きで保存）】
//   ・🔴 X: 合成の paste イベントでは文章が入らなくなった（__saveX は len 0 のまま空で保存される）。→ 下の __fillX（execCommand('insertText')）を使う。
//     入力欄は必ず '[role="dialog"] [data-testid="tweetTextarea_0"]'（ホームの入力欄にも同じ testid があり、そちらに入ってしまう）。
//     手順: __newX() → __fillX(本文) → find「hidden file input inside compose dialog」で file-input の ref → file_upload（画像）→ __saveCloseX()（"len N | imgs 1 | 保存 | /home"）
//   ・🔴 Threads: insertText だと改行が全部消えて1段落になる。→ 従来どおり paste イベント（__pasteTh）。改行は残る。
//     「新しいスレッド」はボタンが見つからないことがある → 左の「＋」の位置 elementFromPoint(30,132) をクリック（__openPaste / __oneTh）。
//     画像は1本目だけ: __openPaste(本文) → find「file input inside new thread dialog」の file-input → file_upload → __saveTh()。2〜4本目は __oneTh(本文)。
//     失敗して入れ直すときは computer で ctrl+a → BackSpace（execCommand では消えない）。画像は残る。
//   ・file_upload はセッションの scratchpad のファイルしか受け付けない → 画像を scratchpad\img{日付}\ にコピーしてから。
//   ・保存後の確認: X は下書き一覧の innerText で '【福島7R' などを数える。Threads は下書きダイアログで '【東京9R 百日草' のように日付固有の文字列で数える
//     （前日の同じレース番号の下書きが残っていると '【東京9R' だけでは重複に見える）。

// ---- X（compose を開いて貼り付け → 閉じる → 「保存」）----
window.__saveX = async (t) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  if (!location.pathname.includes("compose")) {
    const b = document.querySelector('[data-testid="SideNav_NewTweet_Button"]');
    if (!b) return "nobtn";
    b.click(); await sleep(1200);
  }
  let ed; for (let i = 0; i < 30 && !(ed = document.querySelector('[data-testid="tweetTextarea_0"]')); i++) await sleep(500);
  if (!ed) return "noeditor";
  await sleep(800); ed.focus();
  document.execCommand('selectAll'); document.execCommand('delete'); await sleep(300);
  const dt = new DataTransfer(); dt.setData("text/plain", t);
  ed.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
  await sleep(900);
  const out = ed.innerText.length;
  let c; for (let i = 0; i < 4 && !(c = document.querySelector('[data-testid="confirmationSheetConfirm"]')); i++) {
    (document.querySelector('[data-testid="app-bar-close"]') || document.querySelector('[data-testid="app-bar-back"]'))?.click(); await sleep(1000);
  }
  const label = c && c.innerText; if (label === "保存") c.click(); await sleep(1500);
  return out + "|" + label + "|" + location.pathname;   // 例: 646|保存|/home
};

// ---- Threads（新しいスレッド → 貼り付け → キャンセル → 「保存」）----
window.__saveThreads = async (T) => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const leaf = (root, s) => [...root.querySelectorAll("*")].filter((e) => e.children.length === 0 && e.innerText && e.innerText.trim() === s);
  const log = [];
  for (const t of T) {
    await sleep(1500);
    const plus = [...document.querySelectorAll('[role="button"]')].find((e) => (e.innerText || "").trim() === "新しいスレッド") || [...document.querySelectorAll('svg[aria-label="新しいスレッド"]')][0]?.closest('[role="button"],a,div[tabindex]');
    if (!plus) { log.push("noplus"); break; }
    plus.click(); let d; for (let i = 0; i < 20 && !(d = document.querySelector('[role="dialog"] [contenteditable="true"]')); i++) await sleep(300);
    if (!d) { log.push("nodialog"); break; }
    await sleep(600); d.focus();
    const dt = new DataTransfer(); dt.setData("text/plain", t);
    d.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
    await sleep(900); const n = d.innerText.length;
    let cancel; for (let i = 0; i < 10 && !(cancel = leaf(document.querySelector('[role="dialog"]') || document.body, "キャンセル")[0]); i++) await sleep(300);
    if (!cancel) { log.push(n + ":nocancel"); break; }
    cancel.click(); await sleep(900);
    let save; for (let i = 0; i < 10 && !(save = leaf(document, "保存").pop()); i++) await sleep(300);
    if (!save) { log.push(n + ":nosave"); break; }
    save.click(); await sleep(1500); log.push(n + ":ok");
  }
  return log.join(" ");
};

// =====================================================================
// 2026-11-08 版（現行）: X は insertText・Threads は paste。画像は file_upload（Claude in Chrome のツール）で入れる
// =====================================================================
window.__sl = (ms) => new Promise((r) => setTimeout(r, ms));
window.__leaf = (root, s) => [...root.querySelectorAll("*")].filter((e) => e.children.length === 0 && e.innerText && e.innerText.trim() === s);

// ---- X ----
window.__newX = async () => { await __sl(1000); const b = document.querySelector('[data-testid="SideNav_NewTweet_Button"]'); if (!b) return "nobtn"; b.click(); await __sl(1500); return "opened"; };
window.__fillX = async (t) => {
  let ed; for (let i = 0; i < 30 && !(ed = document.querySelector('[role="dialog"] [data-testid="tweetTextarea_0"]')); i++) await __sl(500);
  if (!ed) return "noeditor";
  ed.focus(); await __sl(300); document.execCommand("selectAll"); document.execCommand("delete"); await __sl(300);
  document.execCommand("insertText", false, t); await __sl(1200);
  return "len " + ed.innerText.length + " | " + ed.innerText.slice(0, 10) + " | " + ed.innerText.slice(-8);
};
window.__saveCloseX = async () => {
  const d = document.querySelector('[role="dialog"]'); const ed = d && d.querySelector('[data-testid="tweetTextarea_0"]');
  const n = ed ? ed.innerText.length : -1; const imgs = d ? d.querySelectorAll('[data-testid="attachments"] img').length : -1;
  let c; for (let i = 0; i < 4 && !(c = document.querySelector('[data-testid="confirmationSheetConfirm"]')); i++) {
    (document.querySelector('[data-testid="app-bar-close"]') || document.querySelector('[data-testid="app-bar-back"]'))?.click(); await __sl(1000);
  }
  const label = c && c.innerText; if (label === "保存") c.click(); await __sl(1500);
  return "len " + n + " | imgs " + imgs + " | " + label + " | " + location.pathname;
};

// ---- Threads ----
window.__pasteTh = async (t) => {
  const d = document.querySelector('[role="dialog"] [contenteditable="true"]'); if (!d) return "nodialog";
  d.focus(); await __sl(300); const dt = new DataTransfer(); dt.setData("text/plain", t);
  d.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true })); await __sl(1000);
  return "len " + d.innerText.length + " | lines " + d.innerText.split("\n").length + " | imgs " + document.querySelectorAll('[role="dialog"] img[src^="blob:"]').length;
};
window.__openTh = async () => {
  await __sl(1200); if (document.querySelector('[role="dialog"]')) return "dialog-still-open";
  const el = document.elementFromPoint(30, 132); (el.closest('a,[role="button"],div[tabindex]') || el).click();
  let d; for (let i = 0; i < 20 && !(d = document.querySelector('[role="dialog"] [contenteditable="true"]')); i++) await __sl(300);
  if (!d) return "nodialog"; await __sl(500); return "ok";
};
window.__saveTh = async () => {
  const dlg = document.querySelector('[role="dialog"]'); const imgs = dlg ? dlg.querySelectorAll('img[src^="blob:"]').length : -1;
  const n = ((dlg && dlg.querySelector('[contenteditable="true"]')) || { innerText: "" }).innerText.length;
  let cancel; for (let i = 0; i < 10 && !(cancel = __leaf(dlg || document.body, "キャンセル")[0]); i++) await __sl(300);
  if (!cancel) return "nocancel"; cancel.click(); await __sl(900);
  let save; for (let i = 0; i < 10 && !(save = __leaf(document, "保存").pop()); i++) await __sl(300);
  if (!save) return "nosave"; save.click(); await __sl(1500); return "len " + n + " | imgs " + imgs + " | saved";
};
window.__openPaste = async (t) => { const o = await __openTh(); return o === "ok" ? await __pasteTh(t) : o; };   // 1本目（このあと file_upload → __saveTh）
window.__oneTh = async (t) => { const o = await __openTh(); if (o !== "ok") return o; const r = await __pasteTh(t); return r + " => " + (await __saveTh()); };   // 画像なし
