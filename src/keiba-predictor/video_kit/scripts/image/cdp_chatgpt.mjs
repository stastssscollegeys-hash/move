// cdp_chatgpt.mjs — Chrome リモートデバッグ経由で ChatGPT 画像生成（MCP 不要・汎用版）
// =============================================================================
// chrome-devtools MCP / claude-in-chrome が使えない時でも、Chrome のリモート
// デバッグポート(9222)に Node から直接 CDP を話して ChatGPT を操作する方式。
// Node 18+ 標準の WebSocket / fetch のみ使用。追加インストール一切不要。
//
// 【前提】Chrome をリモートデバッグ起動しておくこと（Chrome 146/148 は Debug Data 必須）:
//   "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
//     --remote-debugging-port=9222 --remote-allow-origins=* ^
//     --user-data-dir="%LOCALAPPDATA%\Google\Chrome\Debug Data" ^
//     --no-first-run https://chatgpt.com/
//   → その Chrome で ChatGPT 契約アカウント(Plus/Team/Enterprise)にログイン
//
// 【使い方】
//   node cdp_chatgpt.mjs check                       接続確認・ChatGPT の状態表示
//   node cdp_chatgpt.mjs gen <promptFile> <outPath>  promptFile の内容で1枚生成→保存
//   node cdp_chatgpt.mjs grab <outPath>              生成済みの最新画像をDLして保存
//   node cdp_chatgpt.mjs batch <manifest.json>       一括生成
//        manifest.json = [{"prompt":"...","out":"abs\\path.png"}, ...]
//                     or [{"promptFile":"abs\\p.txt","out":"abs\\path.png"}, ...]
//   環境変数 CDP_PORT でポート変更可（既定 9222）
// =============================================================================
import { writeFileSync, readFileSync } from 'fs';

const PORT = process.env.CDP_PORT || '9222';
const DEBUG_HOST = `http://localhost:${PORT}`;

// ChatGPT 生成画像だけを拾うセレクタ（プロフィールアバター・GPTアイコンを除外）。
// 生成画像は src に backend-api/estuary/content? を含み gizmo_id を含まない大サイズ画像。
// ChatGPT生成画像のURL形式（backend-api/estuary / oaiusercontent.com / backend-api/files）に対応
// ★ユーザーメッセージ内の画像（クリップボード添付のエコー表示）は除外する。
//   添付画像の estuary URL が送信後の before 記録より遅れて DOM に現れると
//   「新規生成画像」と誤検出され、添付画像そのものが保存される事故が起きる
//   （2026-08-04 ai-douga-20man A+ page_03 で実発生・2回連続）。
// ★2026-09-26追記: ChatGPT が生成画像を blob: URL で描画するようになり、上記3形式の
//   どれにも当たらず「画像生成タイムアウト」で毎回失敗するようになった（スプリンターズS
//   の印画像で実発生・6枚全滅）。blob: も受け入れる。blob は画像ごとに一意なので、
//   送信後に記録する before/after の差分で添付画像のエコーとは区別できる。
//   なお data-message-author-role も現在のDOMには存在しないため、この除外条件は効かない。
const GEN_IMGS = `[...document.querySelectorAll('img')].filter(i =>
  (i.src.includes('backend-api/estuary/content?') ||
   i.src.includes('oaiusercontent.com') ||
   i.src.includes('backend-api/files/') ||
   i.src.startsWith('blob:')) &&
  !i.src.includes('gizmo_id') &&
  !i.closest('[data-message-author-role="user"]') &&
  i.naturalWidth > 200
)`;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function getChatGPTTarget() {
  const res = await fetch(`${DEBUG_HOST}/json`);
  const tabs = await res.json();
  const t = tabs.find((x) => x.type === 'page' && x.url.includes('chatgpt.com'));
  if (!t) throw new Error(`ChatGPT タブが見つかりません（Chrome ${PORT} に chatgpt.com を開いてください）`);
  return t.webSocketDebuggerUrl;
}

class CDP {
  constructor(wsUrl) { this.wsUrl = wsUrl; this.seq = 0; this.pending = new Map(); }
  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.addEventListener('open', () => resolve());
      this.ws.addEventListener('error', (e) => reject(new Error('WS error: ' + (e.message || e))));
      this.ws.addEventListener('message', (ev) => {
        let msg; try { msg = JSON.parse(ev.data); } catch { return; }
        if (msg.id && this.pending.has(msg.id)) {
          const p = this.pending.get(msg.id);
          this.pending.delete(msg.id);
          if (msg.error) p.reject(new Error(JSON.stringify(msg.error)));
          else p.resolve(msg.result);
        }
      });
    });
  }
  send(method, params = {}) {
    const id = ++this.seq;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  async evaluate(expression, awaitPromise = false) {
    const r = await this.send('Runtime.evaluate', {
      expression, returnByValue: true, awaitPromise, userGesture: true,
    });
    if (r.exceptionDetails) {
      throw new Error('JS例外: ' + (r.exceptionDetails.exception?.description || JSON.stringify(r.exceptionDetails)));
    }
    return r.result.value;
  }
  close() { try { this.ws.close(); } catch {} }
}

async function checkState(cdp) {
  return cdp.evaluate(`(() => {
    const ed = document.querySelector('#prompt-textarea, div.ProseMirror, [contenteditable="true"]');
    const imgs = ${GEN_IMGS};
    return {
      url: location.href, title: document.title,
      hasEditor: !!ed, imageCount: imgs.length,
      bodyHead: document.body.innerText.slice(0, 160).replace(/\\s+/g, ' '),
    };
  })()`);
}

async function listImageSrcs(cdp) {
  return cdp.evaluate(`${GEN_IMGS}.map(i=>i.src).filter((v,i,a)=>a.indexOf(v)===i)`);
}

// 既知 src 集合に無い「新しい生成画像」が現れるまで待つ（Node.js側ポーリング方式）
// awaitPromise=true を使わずページナビゲーションによる切断を回避
async function waitForNewImage(cdp, knownSrcs, maxWaitMs = 360000) {
  const KNOWN = new Set(knownSrcs);
  const start = Date.now();
  while (Date.now() - start < maxWaitMs) {
    try {
      const srcs = await cdp.evaluate(`(() => {
        try {
          const imgs = ${GEN_IMGS};
          return [...new Set(imgs.map(i=>i.src))];
        } catch(e) { return []; }
      })()`);
      if (Array.isArray(srcs)) {
        const fresh = srcs.filter(s => !KNOWN.has(s));
        if (fresh.length) return { ready: true, latest: fresh[fresh.length - 1] };
      }
    } catch (e) {
      // ページ遷移等の一時的エラーは無視して継続
    }
    await sleep(4000);
  }
  return { ready: false, timedout: true };
}

async function pastePrompt(cdp, prompt) {
  return cdp.evaluate(`(() => {
    const ed = document.querySelector('#prompt-textarea, div.ProseMirror, [contenteditable="true"]');
    if (!ed) return 'NO_EDITOR';
    ed.focus();
    const dt = new DataTransfer();
    dt.setData('text/plain', ${JSON.stringify(prompt)});
    ed.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
    return 'PASTED';
  })()`);
}

async function clickSend(cdp) {
  return cdp.evaluate(`(() => {
    let btn = document.querySelector('button[data-testid="send-button"]')
      || document.querySelector('#composer-submit-button')
      || [...document.querySelectorAll('button')].find(b => /送信|Send prompt|Send message/i.test((b.getAttribute('aria-label')||'')));
    if (!btn) return 'NO_SEND_BUTTON';
    if (btn.disabled) return 'SEND_DISABLED';
    btn.click();
    return 'SENT';
  })()`);
}

// ページ内 fetch で画像を base64 化 → CDP 経由でチャンク受信（巨大メッセージ回避）
async function downloadImage(cdp, url) {
  const meta = await cdp.evaluate(`(async () => {
    try {
      const resp = await fetch(${JSON.stringify(url)}, { credentials: 'include' });
      if (!resp.ok) return { ok: false, status: resp.status };
      const buf = new Uint8Array(await (await resp.blob()).arrayBuffer());
      let bin = '';
      for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i+0x8000));
      window.__imgB64 = btoa(bin);
      return { ok: true, size: buf.length, b64len: window.__imgB64.length };
    } catch (e) { return { ok: false, error: String(e) }; }
  })()`, true);
  if (!meta.ok) throw new Error('画像 fetch 失敗: ' + JSON.stringify(meta));
  const CH = 400000;
  let b64 = '';
  for (let i = 0; i < meta.b64len; i += CH) {
    b64 += await cdp.evaluate(`window.__imgB64.slice(${i}, ${i + CH})`);
  }
  await cdp.evaluate(`delete window.__imgB64`);
  return Buffer.from(b64, 'base64');
}

// 毎回新規チャットへ遷移してクリーンな状態で生成する（長会話による検出ミス防止）
async function navigateNewChat(cdp) {
  // まず現在の状態を確認
  const pre = await checkState(cdp);
  if (pre.hasEditor && pre.imageCount === 0) {
    // 既にクリーンなエディタ状態ならスキップ
    try {
      await cdp.send('Page.bringToFront');
      await cdp.send('Emulation.setFocusEmulationEnabled', { enabled: true });
    } catch {}
    return;
  }
  // JS ナビゲーション（Page.navigate より安定）
  await cdp.evaluate(`window.location.href = 'https://chatgpt.com/'`);
  await sleep(8000);
  try {
    await cdp.send('Page.bringToFront');
    await cdp.send('Emulation.setFocusEmulationEnabled', { enabled: true });
  } catch {}
  const maxWait = 60000;
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    const state = await checkState(cdp);
    if (state.hasEditor) return;
    await sleep(2000);
  }
  throw new Error('新規チャット遷移タイムアウト');
}

// PowerShell でクリップボードに画像をコピーし、Ctrl+V でChatGPTに貼り付ける方式
async function attachImagesCDP(cdp, imagePaths) {
  const { spawnSync } = await import('child_process');
  for (const imgPath of imagePaths) {
    const { existsSync } = await import('fs');
    if (!existsSync(imgPath)) { console.log(`  SKIP (not found): ${imgPath}`); continue; }
    const label = imgPath.split(/[/\\]/).pop();
    const safePath = imgPath.replace(/\\/g, '/').replace(/'/g, "''");
    const ps = spawnSync('powershell', ['-Sta', '-NoProfile', '-Command',
      `Add-Type -AssemblyName System.Drawing,System.Windows.Forms; ` +
      `try { $bmp = New-Object System.Drawing.Bitmap('${safePath}'); ` +
      `[System.Windows.Forms.Clipboard]::SetImage($bmp); $bmp.Dispose(); Write-Output 'OK' ` +
      `} catch { Write-Output ('ERR:' + $_.Exception.Message) }`
    ], { encoding: 'utf8', timeout: 15000 });
    const stdout = (ps.stdout || '').trim();
    if (ps.status !== 0 || !stdout.includes('OK')) {
      console.log(`  ❌ clipboard: ${label} (${stdout.slice(0,60)})`); continue;
    }
    await sleep(400);
    await cdp.evaluate(`(() => { const ed = document.querySelector('#prompt-textarea, div.ProseMirror, [contenteditable="true"]'); if (ed) { ed.click(); ed.focus(); } })()`);
    await sleep(200);
    await cdp.send('Input.dispatchKeyEvent', { type: 'rawKeyDown', modifiers: 2, windowsVirtualKeyCode: 86, nativeVirtualKeyCode: 86, key: 'v', code: 'KeyV', text: '' });
    await cdp.send('Input.dispatchKeyEvent', { type: 'char', modifiers: 2, key: 'v', code: 'KeyV', text: '\x16' });
    await cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', modifiers: 2, windowsVirtualKeyCode: 86, nativeVirtualKeyCode: 86, key: 'v', code: 'KeyV' });
    await sleep(2500);
    console.log(`  attach ✅: ${label}`);
  }
}

async function generateOne(cdp, prompt, outPath, attachImages = []) {
  // 新規チャットからスタートすることで検出が安定する
  await navigateNewChat(cdp);
  await sleep(1500);

  // キャラクターシート等の画像を先に添付
  if (attachImages.length > 0) {
    await attachImagesCDP(cdp, attachImages);
    await sleep(1000);
  }

  const pasted = await pastePrompt(cdp, prompt);
  if (pasted !== 'PASTED') throw new Error('プロンプト入力失敗: ' + pasted);
  await sleep(1500);

  let sent = await clickSend(cdp);
  for (let i = 0; i < 6 && sent !== 'SENT'; i++) { await sleep(1500); sent = await clickSend(cdp); }
  if (sent !== 'SENT') throw new Error('送信失敗: ' + sent);

  // ★ 送信後に待機してから before を記録: 添付画像の estuary URL を「既知」として
  //   登録し、生成画像と混同しないようにする（添付なしの場合は待機不要）
  await sleep(attachImages.length > 0 ? 8000 : 0);
  const before = await listImageSrcs(cdp);

  const res = await waitForNewImage(cdp, before, 360000);
  if (!res.ready) throw new Error('画像生成タイムアウト: ' + JSON.stringify(res));

  const buf = await downloadImage(cdp, res.latest);
  writeFileSync(outPath, buf);
  return buf.length;
}

// ── エントリポイント ─────────────────────────────────────
const cmd = process.argv[2] || 'check';
const wsUrl = await getChatGPTTarget();
const cdp = new CDP(wsUrl);
await cdp.connect();

// ★スロットリング対策（最重要）: CDP で繋いだだけのタブは Chrome に「バックグラウンド
// タブ」判定され throttle される → ChatGPT の画像生成・描画が30分超に激遅化する。
// タブを前面化＋フォーカスをエミュレートして「常に可視・フォーカスあり」と認識させ回避。
// （実測: 30分超 → 59秒）。詳細: docs/cdp-direct-fallback.md
try {
  await cdp.send('Page.enable');
  await cdp.send('Page.bringToFront');
  await cdp.send('Emulation.setFocusEmulationEnabled', { enabled: true });
} catch { /* 一部ドメインが無い環境でも続行 */ }

try {
  if (cmd === 'check') {
    console.log(JSON.stringify(await checkState(cdp), null, 2));

  } else if (cmd === 'gen') {
    const promptFile = process.argv[3], outPath = process.argv[4];
    if (!promptFile || !outPath) throw new Error('使い方: gen <promptFile> <outPath>');
    const prompt = readFileSync(promptFile, 'utf-8');
    console.log(`生成中… → ${outPath}`);
    const n = await generateOne(cdp, prompt, outPath);
    console.log(`✅ 保存: ${outPath}（${(n / 1024).toFixed(0)} KB）`);

  } else if (cmd === 'grab') {
    const outPath = process.argv[3];
    if (!outPath) throw new Error('使い方: grab <outPath>');
    const res = await waitForNewImage(cdp, [], 15000);
    if (!res.ready) throw new Error('生成済み画像が見つかりません');
    const buf = await downloadImage(cdp, res.latest);
    writeFileSync(outPath, buf);
    console.log(`✅ 保存: ${outPath}（${(buf.length / 1024).toFixed(0)} KB）`);

  } else if (cmd === 'batch') {
    const manifest = JSON.parse(readFileSync(process.argv[3], 'utf-8'));
    const failed = [];
    for (let i = 0; i < manifest.length; i++) {
      const m = manifest[i];
      const prompt = m.prompt || readFileSync(m.promptFile, 'utf-8');
      const attachImages = m.attachImages || [];
      try {
        console.log(`[${i}] 生成中… → ${m.out}${attachImages.length ? ` (添付${attachImages.length}枚)` : ''}`);
        const n = await generateOne(cdp, prompt, m.out, attachImages);
        console.log(`[${i}] ✅ ${(n / 1024).toFixed(0)} KB`);
      } catch (e) {
        console.log(`[${i}] ❌ ${e.message}`);
        failed.push(i);
      }
      await sleep(3000);
    }
    console.log(`=== 完了 成功 ${manifest.length - failed.length}/${manifest.length} ／ 失敗:[${failed.join(',')}] ===`);

  } else {
    console.log('使い方: node cdp_chatgpt.mjs [check | gen <promptFile> <out> | grab <out> | batch <manifest.json>]');
  }
} finally {
  cdp.close();
}
