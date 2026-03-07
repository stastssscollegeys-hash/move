// ===== ワンクリックLP画像クリエイター - Frontend Logic =====

(function () {
  'use strict';

  // --- State ---
  const state = {
    generating: false,
    sections: {},      // { 1: { status, base64, prompt, error }, ... }
    copyText: '',
    startTime: null,
    sectionTimes: [],
    bulkParsed: false,
    elapsedTimer: null,
    currentPhase: null, // 'copy' | 'design' | 'image' | 'done' | null
    phaseStartTime: null, // timestamp when current phase started
    copyChunkCount: 0,    // number of copy chunks received
    imageStartTimes: {},  // { sectionId: timestamp } — when each image started
    imageDurations: [],   // completed image durations in seconds
  };

  // --- Constants ---
  const SECTION_NAMES = [
    'ファーストビュー',
    '問題提起',
    '解決策',
    'ベネフィット',
    'お客様の声',
    '特典・料金',
    'CTA',
  ];

  // --- DOM refs ---
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // --- LocalStorage keys ---
  const LS_CLAUDE_KEY = 'lp-nb-claude-key';
  const LS_GEMINI_KEY = 'lp-nb-gemini-key';

  // --- Init ---
  document.addEventListener('DOMContentLoaded', () => {
    loadApiKeys();
    setupRadioCards();
    setupCharCounters();
    setupModal();

    $('#btn-generate').addEventListener('click', startGeneration);
    $('#btn-download').addEventListener('click', downloadZip);
    $('#btn-parse').addEventListener('click', parseBulkInput);
    $('#btn-test-keys').addEventListener('click', testApiKeys);

    // Save API keys on blur
    $('#claude-api-key').addEventListener('blur', saveApiKeys);
    $('#gemini-api-key').addEventListener('blur', saveApiKeys);
  });

  function loadApiKeys() {
    const ck = localStorage.getItem(LS_CLAUDE_KEY) || '';
    const gk = localStorage.getItem(LS_GEMINI_KEY) || '';
    $('#claude-api-key').value = ck;
    $('#gemini-api-key').value = gk;
    updateKeyStatus('claude', ck);
    updateKeyStatus('gemini', gk);
  }

  function saveApiKeys() {
    const ck = $('#claude-api-key').value.trim();
    const gk = $('#gemini-api-key').value.trim();
    if (ck) localStorage.setItem(LS_CLAUDE_KEY, ck);
    if (gk) localStorage.setItem(LS_GEMINI_KEY, gk);
    updateKeyStatus('claude', ck);
    updateKeyStatus('gemini', gk);
  }

  function updateKeyStatus(type, key) {
    const el = $(`#${type}-key-status`);
    if (key) {
      el.textContent = '\u2713 保存済み';
      el.className = 'api-key-status saved';
    } else {
      el.textContent = '未設定';
      el.className = 'api-key-status unsaved';
    }
  }

  // --- Bulk Input Parsing ---
  async function parseBulkInput() {
    const rawText = $('#bulk-input').value.trim();
    if (!rawText) return showAlert('テキストを入力してください');

    const claudeKey = $('#claude-api-key').value.trim();
    if (!claudeKey) return showAlert('Claude APIキーを設定してください');

    const btn = $('#btn-parse');
    btn.disabled = true;
    btn.textContent = 'AIで分析中...';

    try {
      const resp = await fetch('/lp-nanobanana/api/parse-input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rawText, claudeApiKey: claudeKey }),
      });
      const result = await resp.json();

      if (result.success && result.data) {
        const d = result.data;
        if (d.productName) $('#product-name').value = d.productName;
        if (d.target) $('#target').value = d.target;
        if (d.strength) $('#strength').value = d.strength;
        if (d.price) $('#price').value = d.price;
        if (d.description) $('#description').value = d.description;

        state.bulkParsed = true;

        // Trigger char counter updates
        $$('[data-maxlen]').forEach(input => {
          input.dispatchEvent(new Event('input'));
        });

        showAlert('商品情報を入力欄に反映しました', 'success');
      } else {
        showAlert(result.error || '解析に失敗しました');
      }
    } catch (err) {
      showAlert('解析エラー: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'AIで分析して入力欄に反映';
    }
  }

  // --- API Key Test ---
  async function testApiKeys() {
    const claudeKey = $('#claude-api-key').value.trim();
    const geminiKey = $('#gemini-api-key').value.trim();

    if (!claudeKey && !geminiKey) {
      return showAlert('APIキーを入力してください');
    }

    saveApiKeys();

    const btn = $('#btn-test-keys');
    const resultEl = $('#test-result');
    btn.disabled = true;
    btn.textContent = 'テスト中...';
    resultEl.innerHTML = '';
    resultEl.className = 'test-result';

    try {
      const resp = await fetch('/lp-nanobanana/api/test-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ claudeApiKey: claudeKey, geminiApiKey: geminiKey }),
      });
      const result = await resp.json();

      if (!result.success) {
        resultEl.innerHTML = '<div class="test-fail">テスト失敗: サーバーエラー</div>';
        resultEl.classList.add('active');
        return;
      }

      let html = '';
      const d = result.data;

      if (d.claude) {
        if (d.claude.ok) {
          html += `<div class="test-ok">Claude API: 接続OK (${d.claude.ms}ms)</div>`;
        } else {
          html += `<div class="test-fail">Claude API: 失敗 - ${d.claude.error}</div>`;
        }
      }

      if (d.gemini) {
        if (d.gemini.ok) {
          html += `<div class="test-ok">Gemini API: 接続OK (${d.gemini.ms}ms)</div>`;
        } else {
          html += `<div class="test-fail">Gemini API: 失敗 - ${d.gemini.error}</div>`;
        }
      }

      resultEl.innerHTML = html;
      resultEl.classList.add('active');
    } catch (err) {
      resultEl.innerHTML = `<div class="test-fail">テスト失敗: ${err.message}</div>`;
      resultEl.classList.add('active');
    } finally {
      btn.disabled = false;
      btn.textContent = '接続テスト';
    }
  }

  function setupRadioCards() {
    $$('.radio-card').forEach(card => {
      card.addEventListener('click', () => {
        $$('.radio-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        card.querySelector('input[type="radio"]').checked = true;
      });
    });
    const first = $('.radio-card');
    if (first) { first.classList.add('selected'); first.querySelector('input').checked = true; }
  }

  function setupCharCounters() {
    $$('[data-maxlen]').forEach(input => {
      const max = parseInt(input.dataset.maxlen);
      const counter = input.parentElement.querySelector('.char-count');
      if (!counter) return;
      const update = () => { counter.textContent = `${input.value.length}/${max}`; };
      input.addEventListener('input', update);
      update();
    });
  }

  function setupModal() {
    const overlay = $('#modal-overlay');
    overlay.addEventListener('click', () => overlay.classList.remove('active'));
  }

  function openModal(src) {
    const overlay = $('#modal-overlay');
    $('#modal-image').src = src;
    overlay.classList.add('active');
  }

  // --- Step Flow Management ---
  function setStepState(stepId, stepState) {
    // stepId: 'step-copy', 'step-design', 'step-image'
    // stepState: 'waiting', 'active', 'done', 'error'
    const el = $(`#${stepId}`);
    if (!el) return;

    el.classList.remove('active', 'done', 'error');
    if (stepState === 'active') el.classList.add('active');
    if (stepState === 'done') el.classList.add('done');
    if (stepState === 'error') el.classList.add('error');

    const statusEl = el.querySelector('.step-status');
    if (!statusEl) return;

    switch (stepState) {
      case 'waiting': statusEl.textContent = '待機中'; break;
      case 'active': statusEl.textContent = '処理中...'; break;
      case 'done': statusEl.textContent = '完了'; break;
      case 'error': statusEl.textContent = 'エラー'; break;
    }
  }

  function setStepStatusText(stepId, text) {
    const el = $(`#${stepId}`);
    if (!el) return;
    const statusEl = el.querySelector('.step-status');
    if (statusEl) statusEl.textContent = text;
  }

  // --- Copy Preview ---
  function setCopyPreview(text) {
    const box = $('#copy-preview-box');
    const textEl = $('#copy-preview-text');
    if (!box || !textEl) return;

    box.classList.add('active');
    textEl.textContent = text.length > 400 ? '...' + text.slice(-400) : text;
    textEl.scrollTop = textEl.scrollHeight;
  }

  function hideCopyPreview() {
    const box = $('#copy-preview-box');
    if (box) box.classList.remove('active');
  }

  // --- Progress Panel ---
  function showProgressPanel() {
    const panel = $('#progress-panel');
    if (panel) panel.classList.add('active');

    // Hide placeholder
    const placeholder = $('#col-right-placeholder');
    if (placeholder) placeholder.classList.add('hidden');
  }

  function updateProgressBar(completed, total) {
    const pct = total > 0 ? (completed / total) * 100 : 0;
    const bar = $('.progress-bar');
    if (bar) bar.style.width = pct + '%';
  }

  function updateProgressText(mainText, elapsedStr) {
    const textEl = $('.progress-text');
    if (textEl) {
      textEl.innerHTML = `<span>${mainText}</span><span>経過 ${elapsedStr}</span>`;
    }
  }

  // --- Generation ---
  async function startGeneration() {
    if (state.generating) return;

    const claudeKey = $('#claude-api-key').value.trim();
    const geminiKey = $('#gemini-api-key').value.trim();
    const productName = $('#product-name').value.trim();
    const target = $('#target').value.trim();
    const strength = $('#strength').value.trim();
    const lpType = document.querySelector('input[name="lp-type"]:checked')?.value || 'education';
    const price = $('#price').value.trim();
    const description = $('#description').value.trim();
    const referenceUrl = $('#reference-url').value.trim();

    // Validation
    if (!claudeKey) return showAlert('Claude APIキーを設定してください');
    if (!geminiKey) return showAlert('Gemini APIキーを設定してください');
    if (!productName) return showAlert('商品名を入力してください');
    if (!target) return showAlert('ターゲットを入力してください');
    if (!strength) return showAlert('強み・特徴を入力してください');

    saveApiKeys();

    state.generating = true;
    state.startTime = Date.now();
    state.phaseStartTime = Date.now();
    state.sectionTimes = [];
    state.copyText = '';
    state.sections = {};
    state.currentPhase = 'copy';
    state.copyChunkCount = 0;
    state.imageStartTimes = {};
    state.imageDurations = [];

    // Init section states
    for (let i = 1; i <= 7; i++) {
      state.sections[i] = { status: 'waiting', base64: null, prompt: null, error: null };
    }

    // UI updates
    $('#btn-generate').disabled = true;
    $('#btn-generate').textContent = '生成中...';
    showProgressPanel();
    showResults();
    updateAllSectionCards();
    $('#download-bar').classList.remove('active');

    // Set initial step states
    setStepState('step-copy', 'active');
    setStepState('step-design', 'waiting');
    setStepState('step-image', 'waiting');

    updateProgressBar(0, 100);
    updateProgressText('コピー生成中...', '0:00');

    // Show copy preview box
    setCopyPreview('');

    // Update copy preview header
    const header = $('#copy-preview-box .copy-preview-header span');
    if (header) header.textContent = 'AIがコピーを執筆中...';

    // Start elapsed time timer
    if (state.elapsedTimer) clearInterval(state.elapsedTimer);
    state.elapsedTimer = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
      const phaseElapsed = Math.floor((Date.now() - state.phaseStartTime) / 1000);
      const elapsedStr = formatTime(elapsed);

      let mainText = '';
      let pct = 0;
      switch (state.currentPhase) {
        case 'copy': {
          // Show elapsed time and chunking status — no fake percentage
          if (state.copyChunkCount > 0) {
            pct = 10; // chunks are flowing = ~10% of total
            mainText = `コピー生成中... ${formatTime(phaseElapsed)}経過`;
            setStepStatusText('step-copy', `執筆中... (${state.copyChunkCount}チャンク)`);
          } else {
            pct = 5;
            if (phaseElapsed < 10) {
              mainText = `コピー生成中... API接続中`;
              setStepStatusText('step-copy', 'API接続中...');
            } else {
              mainText = `コピー生成中... ${formatTime(phaseElapsed)}経過 (応答待ち)`;
              setStepStatusText('step-copy', `${formatTime(phaseElapsed)} 応答待ち...`);
            }
          }
          break;
        }
        case 'design': {
          pct = 18;
          if (phaseElapsed < 5) {
            mainText = `デザイン分析中...`;
          } else {
            mainText = `デザイン分析中... ${formatTime(phaseElapsed)}経過`;
          }
          setStepStatusText('step-design', `分析中... ${formatTime(phaseElapsed)}`);
          break;
        }
        case 'image': {
          const completed = Object.values(state.sections).filter(s => s.status === 'complete').length;
          const failed = Object.values(state.sections).filter(s => s.status === 'error').length;
          const done = completed + failed;
          const imgPct = Math.floor((done / 7) * 100);

          // Calculate ETA from actual image generation times
          let etaText = '';
          if (state.imageDurations.length > 0 && done < 7) {
            const avgDuration = state.imageDurations.reduce((a, b) => a + b, 0) / state.imageDurations.length;
            // Also account for currently-generating section's elapsed time
            const remaining = (7 - done) * avgDuration;
            etaText = ` (残り約${formatTime(Math.floor(remaining))})`;
          } else if (done === 0 && phaseElapsed >= 5) {
            // No images done yet, estimate from first image elapsed
            const estPerImage = 25;
            const firstRemain = Math.max(0, estPerImage - phaseElapsed);
            const totalRemain = firstRemain + (6 * estPerImage);
            etaText = ` (残り約${formatTime(Math.floor(totalRemain))})`;
          }

          // Total progress: 25% (copy+design) + 75% * (done/7)
          pct = 25 + Math.floor(75 * done / 7);
          mainText = `画像生成 ${completed}/7完了 ${imgPct}%${etaText}`;
          setStepStatusText('step-image', `${completed}/7 完了 (${imgPct}%)`);
          break;
        }
        case 'done':
          mainText = '完了!';
          pct = 100;
          break;
        default:
          mainText = '準備中...';
          pct = 0;
      }

      updateProgressBar(pct, 100);
      updateProgressText(mainText, elapsedStr);
    }, 1000);

    try {
      const body = {
        productName, target, strength, lpType, price, description, referenceUrl,
        claudeApiKey: claudeKey,
        geminiApiKey: geminiKey,
      };

      console.log('[LP-NB] Starting generation request...');

      const response = await fetch('/lp-nanobanana/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${response.status}`);
      }

      console.log('[LP-NB] SSE stream connected, reading events...');

      // Read SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let receivedComplete = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              console.log('[LP-NB] SSE event:', event.type, event.data?.id || '');
              if (event.type === 'all_complete') receivedComplete = true;
              handleSSEEvent(event);
            } catch (e) {
              console.warn('[LP-NB] Malformed SSE event:', line);
            }
          }
        }
      }

      // Stream ended without all_complete — mark remaining as error
      if (!receivedComplete) {
        console.warn('[LP-NB] Stream ended unexpectedly without all_complete');
        setStepState('step-image', 'error');
        for (let i = 1; i <= 7; i++) {
          if (state.sections[i] && state.sections[i].status === 'waiting') {
            state.sections[i].status = 'error';
            state.sections[i].error = 'サーバー接続が切断されました';
            updateSectionCard(i);
          }
        }
      }
    } catch (err) {
      console.error('[LP-NB] Generation error:', err);
      showAlert('エラー: ' + err.message);
      // Mark current step as error
      if (state.currentPhase === 'copy') setStepState('step-copy', 'error');
      else if (state.currentPhase === 'design') setStepState('step-design', 'error');
      else if (state.currentPhase === 'image') setStepState('step-image', 'error');
      // Mark all waiting sections as error
      for (let i = 1; i <= 7; i++) {
        if (state.sections[i] && state.sections[i].status === 'waiting') {
          state.sections[i].status = 'error';
          state.sections[i].error = err.message;
          updateSectionCard(i);
        }
      }
    } finally {
      state.generating = false;
      if (state.elapsedTimer) { clearInterval(state.elapsedTimer); state.elapsedTimer = null; }
      $('#btn-generate').disabled = false;
      $('#btn-generate').textContent = 'LPを生成する';
    }
  }

  function handleSSEEvent(event) {
    switch (event.type) {
      case 'copy_chunk':
        state.copyText += event.data;
        state.copyChunkCount++;
        setCopyPreview(state.copyText);
        break;

      case 'copy_complete':
        state.currentPhase = 'design';
        state.phaseStartTime = Date.now();
        setStepState('step-copy', 'done');
        setStepStatusText('step-copy', '完了');
        setStepState('step-design', 'active');
        hideCopyPreview();
        break;

      case 'research_start':
        state.currentPhase = 'design';
        state.phaseStartTime = Date.now();
        setStepState('step-design', 'active');
        if (event.data.mode === 'auto-design') {
          setStepStatusText('step-design', '自動デザイン分析中...');
        } else {
          setStepStatusText('step-design', '参考LP分析中...');
        }
        break;

      case 'research_complete':
        setStepState('step-design', 'done');
        if (event.data.warning) {
          setStepStatusText('step-design', 'デフォルト使用');
        } else {
          setStepStatusText('step-design', '完了');
        }
        break;

      case 'image_start': {
        const id = event.data.id;
        if (state.currentPhase !== 'image') {
          state.currentPhase = 'image';
          state.phaseStartTime = Date.now();
        }
        state.sections[id].status = 'generating';
        state.imageStartTimes[id] = Date.now();
        setStepState('step-design', 'done');
        setStepState('step-image', 'active');
        setStepStatusText('step-image', `${id}/7: ${event.data.name} 生成中...`);
        updateSectionCard(id);
        break;
      }

      case 'image_complete': {
        const id = event.data.id;
        state.sections[id].status = 'complete';
        state.sections[id].base64 = event.data.base64;
        state.sectionTimes.push(Date.now());
        // Track duration for ETA calculation
        if (state.imageStartTimes[id]) {
          const duration = (Date.now() - state.imageStartTimes[id]) / 1000;
          state.imageDurations.push(duration);
        }
        updateSectionCard(id);
        const completed = Object.values(state.sections).filter(s => s.status === 'complete').length;
        const pct = Math.floor((completed / 7) * 100);
        setStepStatusText('step-image', `${completed}/7 完了 (${pct}%)`);
        break;
      }

      case 'image_error': {
        const id = event.data.id;
        state.sections[id].status = 'error';
        state.sections[id].error = event.data.error;
        state.sections[id].prompt = event.data.prompt;
        updateSectionCard(id);
        break;
      }

      case 'all_complete':
        state.currentPhase = 'done';
        setStepState('step-image', 'done');
        setStepStatusText('step-image', `${event.data.success}/${event.data.total} 完了`);
        updateProgressBar(100, 100);
        updateProgressText(`完了! ${event.data.success}/${event.data.total}セクション成功`, formatTime(Math.floor((Date.now() - state.startTime) / 1000)));
        if (event.data.success > 0) {
          $('#download-bar').classList.add('active');
        }
        break;

      case 'error':
        // Mark current step as error
        if (state.currentPhase === 'copy') setStepState('step-copy', 'error');
        else if (state.currentPhase === 'design') setStepState('step-design', 'error');
        else setStepState('step-image', 'error');
        // Mark all waiting sections as error
        for (let i = 1; i <= 7; i++) {
          if (state.sections[i] && state.sections[i].status === 'waiting') {
            state.sections[i].status = 'error';
            state.sections[i].error = event.data;
            updateSectionCard(i);
          }
        }
        break;
    }
  }

  // --- UI Updates ---
  function showResults() {
    const container = $('.results-section');
    container.classList.add('active');
    if (!container.querySelector('.lp-section')) {
      let html = '<div class="lp-preview">';
      for (let i = 1; i <= 7; i++) {
        html += `
          <div class="lp-section" data-section="${i}">
            <div class="lp-section-content" data-body="${i}">
              <div class="lp-section-placeholder">
                <div class="placeholder-label">${i}. ${SECTION_NAMES[i - 1]}</div>
                <span class="section-status waiting" data-status="${i}">\u23F3 待機中</span>
              </div>
            </div>
            <div class="lp-section-overlay">
              <span class="overlay-label">${i}. ${SECTION_NAMES[i - 1]}</span>
              <div class="overlay-actions">
                <button class="btn-section-dl" onclick="window.__downloadSection(${i})" title="この画像をダウンロード">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 10.5l-3.5-3.5h2.5v-5h2v5h2.5l-3.5 3.5z"/><path d="M2 12h12v2h-12z"/></svg>
                  保存
                </button>
                <button class="btn-section-zoom" onclick="window.__openModal(document.querySelector('[data-body=&quot;${i}&quot;] img')?.src)" title="拡大表示">
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M6.5 1a5.5 5.5 0 014.38 8.82l3.65 3.65a.75.75 0 01-1.06 1.06l-3.65-3.65A5.5 5.5 0 116.5 1zm0 1.5a4 4 0 100 8 4 4 0 000-8z"/></svg>
                  拡大
                </button>
              </div>
            </div>
          </div>`;
      }
      html += '</div>';
      container.innerHTML = html;
    }
  }

  function updateAllSectionCards() {
    for (let i = 1; i <= 7; i++) updateSectionCard(i);
  }

  function updateSectionCard(id) {
    const sec = state.sections[id];
    if (!sec) return;

    const bodyEl = $(`[data-body="${id}"]`);
    const sectionEl = $(`.lp-section[data-section="${id}"]`);
    if (!bodyEl || !sectionEl) return;

    // Remove all status classes, add current
    sectionEl.classList.remove('is-waiting', 'is-generating', 'is-complete', 'is-error');
    sectionEl.classList.add('is-' + sec.status);

    switch (sec.status) {
      case 'waiting':
        bodyEl.innerHTML = `
          <div class="lp-section-placeholder">
            <div class="placeholder-label">${id}. ${SECTION_NAMES[id - 1]}</div>
            <span class="section-status waiting">\u23F3 待機中</span>
          </div>`;
        break;
      case 'generating':
        bodyEl.innerHTML = `
          <div class="lp-section-placeholder generating">
            <div class="generating-animation">
              <div class="gen-text">${SECTION_NAMES[id - 1]} を生成中<span class="gen-dots"></span></div>
              <div class="running-scene">
                <div class="running-rabbit">
                  <div class="rabbit-body">
                    <div class="rabbit-ear left"></div>
                    <div class="rabbit-ear right"></div>
                    <div class="rabbit-tail"></div>
                    <div class="rabbit-leg front-1"></div>
                    <div class="rabbit-leg front-2"></div>
                    <div class="rabbit-leg back-1"></div>
                    <div class="rabbit-leg back-2"></div>
                  </div>
                </div>
                <div class="sparkle-trail"></div>
                <div class="sparkle-trail"></div>
                <div class="sparkle-trail"></div>
                <div class="sparkle-trail"></div>
              </div>
            </div>
          </div>`;
        break;
      case 'complete':
        bodyEl.innerHTML = `<img src="data:image/png;base64,${sec.base64}" alt="セクション${id}" onclick="window.__openModal(this.src)" />`;
        break;
      case 'error':
        bodyEl.innerHTML = `
          <div class="lp-section-placeholder error">
            <div class="placeholder-label">${id}. ${SECTION_NAMES[id - 1]}</div>
            <div class="error-msg">${sec.error || '不明なエラー'}</div>
            <button class="btn-retry" onclick="window.__retrySection(${id})">リトライ</button>
          </div>`;
        break;
    }
  }

  function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function showAlert(msg, type) {
    const div = document.createElement('div');
    const bgColor = type === 'success' ? '#10b981' : '#ef4444';
    div.style.cssText = `position:fixed;top:16px;left:50%;transform:translateX(-50%);background:${bgColor};color:#fff;padding:12px 24px;border-radius:8px;z-index:9999;font-size:0.9rem;box-shadow:0 4px 12px rgba(0,0,0,0.3);`;
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 4000);
  }

  // --- Retry ---
  window.__retrySection = async function (id) {
    const sec = state.sections[id];
    if (!sec?.prompt) return showAlert('リトライ用のプロンプトがありません');

    const geminiKey = $('#gemini-api-key').value.trim();
    if (!geminiKey) return showAlert('Gemini APIキーを設定してください');

    sec.status = 'generating';
    sec.error = null;
    updateSectionCard(id);

    try {
      const resp = await fetch('/lp-nanobanana/api/retry-section', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sectionId: id, prompt: sec.prompt, geminiApiKey: geminiKey }),
      });
      const result = await resp.json();
      if (result.success) {
        sec.status = 'complete';
        sec.base64 = result.data.base64;
        updateSectionCard(id);
        const anySuccess = Object.values(state.sections).some(s => s.status === 'complete');
        if (anySuccess) $('#download-bar').classList.add('active');
      } else {
        sec.status = 'error';
        sec.error = result.error;
        updateSectionCard(id);
      }
    } catch (err) {
      sec.status = 'error';
      sec.error = err.message;
      updateSectionCard(id);
    }
  };

  // --- Individual Section Download ---
  window.__downloadSection = function (id) {
    const sec = state.sections[id];
    if (!sec?.base64) return showAlert('画像がまだ生成されていません');
    const sectionFileNames = ['first-view', 'problem', 'solution', 'benefit', 'testimonial', 'pricing', 'cta'];
    const binary = atob(sec.base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: 'image/png' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `section_${String(id).padStart(2, '0')}_${sectionFileNames[id - 1]}.png`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // --- Modal ---
  window.__openModal = function (src) {
    if (src) openModal(src);
  };

  // --- Download ZIP ---
  async function downloadZip() {
    const completed = Object.entries(state.sections)
      .filter(([, s]) => s.status === 'complete' && s.base64)
      .map(([id, s]) => ({ id: parseInt(id), base64: s.base64 }));

    if (completed.length === 0) return showAlert('ダウンロードする画像がありません');

    if (typeof JSZip === 'undefined') {
      return showAlert('JSZipが読み込まれていません');
    }

    const sectionNames = ['first-view', 'problem', 'solution', 'benefit', 'testimonial', 'pricing', 'cta'];
    const zip = new JSZip();

    for (const { id, base64 } of completed) {
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      zip.file(`section_${String(id).padStart(2, '0')}_${sectionNames[id - 1]}.png`, bytes);
    }

    const blob = await zip.generateAsync({ type: 'blob' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `lp-images-${$('#product-name').value.trim().slice(0, 20) || 'lp'}.zip`;
    a.click();
    URL.revokeObjectURL(url);
  }
})();
