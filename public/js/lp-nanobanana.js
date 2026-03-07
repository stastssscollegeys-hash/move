// ===== LP NanoBanana Creator - Frontend Logic (Polling + Dynamic Sections) =====

(function () {
  'use strict';

  // --- State ---
  const state = {
    generating: false,
    sections: {},      // { 1: { status, base64, prompt, error }, ... }
    sectionDefs: [],   // [{ id, name, nameJa }, ...] — set from server response
    copyText: '',
    startTime: null,
    bulkParsed: false,
    elapsedTimer: null,
    pollTimer: null,
    jobId: null,
    receivedSections: new Set(),
    lastPhase: null,
    lpType: 'education',
  };

  // --- Per-LP-type section definitions (mirrors server types.ts) ---
  const SECTION_DEFS_BY_TYPE = {
    'education': [
      { id: 1, name: 'headline',      nameJa: 'ヘッドライン' },
      { id: 2, name: 'problem',       nameJa: '問題提起' },
      { id: 3, name: 'solution',      nameJa: '解決策提示' },
      { id: 4, name: 'authority',     nameJa: '権威性確立' },
      { id: 5, name: 'details',       nameJa: '詳細説明' },
      { id: 6, name: 'social-proof',  nameJa: '社会的証明' },
      { id: 7, name: 'urgency',       nameJa: '緊急性演出' },
      { id: 8, name: 'pricing',       nameJa: '価格戦略' },
      { id: 9, name: 'cta',           nameJa: '行動促進' },
    ],
    'product-interest': [
      { id: 1, name: 'first-view',    nameJa: 'ファーストビュー' },
      { id: 2, name: 'testimonial',   nameJa: 'お客様の声' },
      { id: 3, name: 'problem',       nameJa: '問題提起と共感' },
      { id: 4, name: 'story',         nameJa: '開発者ストーリー' },
      { id: 5, name: 'solution',      nameJa: '解決策・商品紹介' },
      { id: 6, name: 'cta',           nameJa: '行動喚起' },
    ],
    'expose': [
      { id: 1, name: 'denial',        nameJa: '現状否定と疑念' },
      { id: 2, name: 'truth',         nameJa: '真実の存在示唆' },
      { id: 3, name: 'special',       nameJa: '読者の特別性認定' },
      { id: 4, name: 'urgency',       nameJa: '希少性と緊急性' },
      { id: 5, name: 'decision',      nameJa: '最終決断の促進' },
    ],
    'cutting-edge': [
      { id: 1, name: 'headline',      nameJa: 'ヘッドライン' },
      { id: 2, name: 'problem',       nameJa: '問題提起・共感' },
      { id: 3, name: 'crisis',        nameJa: '危機感の増幅' },
      { id: 4, name: 'gap',           nameJa: '経済的格差の提示' },
      { id: 5, name: 'solution',      nameJa: '解決策の提示' },
      { id: 6, name: 'offer',         nameJa: '無料オファーと特典' },
      { id: 7, name: 'urgency',       nameJa: '緊急性と価格' },
      { id: 8, name: 'cta',           nameJa: 'CTA' },
      { id: 9, name: 'postscript',    nameJa: '追伸' },
    ],
  };

  const POLL_INTERVAL = 2000;

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
    updateSectionPreview();

    $('#btn-generate').addEventListener('click', startGeneration);
    $('#btn-stop').addEventListener('click', stopGeneration);
    $('#btn-download').addEventListener('click', downloadZip);
    $('#btn-parse').addEventListener('click', parseBulkInput);
    $('#btn-test-keys').addEventListener('click', testApiKeys);
    $('#btn-regenerate-all').addEventListener('click', regenerateAll);
    setupCtaRadios();

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

  // --- Section preview when LP type changes ---
  function updateSectionPreview() {
    const lpType = document.querySelector('input[name="lp-type"]:checked')?.value || 'education';
    const defs = SECTION_DEFS_BY_TYPE[lpType] || SECTION_DEFS_BY_TYPE['education'];
    const previewEl = $('#section-preview');
    if (!previewEl) return;

    previewEl.innerHTML = `<span class="section-preview-label">${defs.length}セクション構成:</span> ` +
      defs.map(d => `<span class="section-preview-tag">${d.id}. ${d.nameJa}</span>`).join(' ');
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
        updateSectionPreview();
      });
    });
    const first = $('.radio-card');
    if (first) { first.classList.add('selected'); first.querySelector('input').checked = true; }
  }

  function setupCtaRadios() {
    const select = $('#cta-text-select');
    const customInput = $('#cta-custom-text');
    if (!select) return;
    select.addEventListener('change', () => {
      const isCustom = select.value === 'custom';
      customInput.style.display = isCustom ? 'block' : 'none';
      if (isCustom) customInput.focus();
    });
  }

  /** Get selected CTA text */
  function getCtaText() {
    const select = $('#cta-text-select');
    if (!select) return '';
    if (select.value === 'custom') {
      return $('#cta-custom-text').value.trim() || '';
    }
    return select.value;
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

  /** Get section name by id from current sectionDefs */
  function getSectionName(id) {
    const def = state.sectionDefs.find(d => d.id === id);
    return def ? def.nameJa : `セクション${id}`;
  }

  /** Get section file name by id from current sectionDefs */
  function getSectionFileName(id) {
    const def = state.sectionDefs.find(d => d.id === id);
    return def ? def.name : `section${id}`;
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
    const claudeModel = $('#claude-model').value;
    const geminiModel = $('#gemini-model').value;
    const referenceUrl = $('#reference-url').value.trim();

    // Validation
    if (!claudeKey) return showAlert('Claude APIキーを設定してください');
    if (!geminiKey) return showAlert('Gemini APIキーを設定してください');
    if (!productName) return showAlert('商品名を入力してください');
    if (!target) return showAlert('ターゲットを入力してください');
    if (!strength) return showAlert('強み・特徴を入力してください');

    saveApiKeys();

    // Set section defs for this LP type
    state.lpType = lpType;
    state.sectionDefs = SECTION_DEFS_BY_TYPE[lpType] || SECTION_DEFS_BY_TYPE['education'];

    state.generating = true;
    state.startTime = Date.now();
    state.copyText = '';
    state.sections = {};
    state.jobId = null;
    state.receivedSections = new Set();
    state.lastPhase = null;

    // Init section states based on LP type
    for (const def of state.sectionDefs) {
      state.sections[def.id] = { status: 'waiting', base64: null, prompt: null, error: null };
    }

    // UI updates
    $('#btn-generate').disabled = true;
    $('#btn-generate').textContent = '生成中...';
    $('#btn-stop').style.display = 'inline-flex';
    showProgressPanel();
    showResults();
    updateAllSectionCards();
    $('#download-bar').classList.remove('active');
    $('#feedback-bar').classList.remove('active');

    // Set initial step states
    setStepState('step-copy', 'active');
    setStepState('step-design', 'waiting');
    setStepState('step-image', 'waiting');

    updateProgressBar(0, 100);
    updateProgressText('コピー生成中...', '0:00');

    // Show copy preview box
    setCopyPreview('');
    const header = $('#copy-preview-box .copy-preview-header span');
    if (header) header.textContent = 'AIがコピーを執筆中...';

    // Start elapsed time display timer
    if (state.elapsedTimer) clearInterval(state.elapsedTimer);
    state.elapsedTimer = setInterval(updateElapsedDisplay, 1000);

    try {
      // POST to start the job
      const resp = await fetch('/lp-nanobanana/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          productName, target, strength, lpType, price, description, referenceUrl,
          ctaText: getCtaText(),
          claudeApiKey: claudeKey,
          claudeModel,
          geminiApiKey: geminiKey,
          geminiModel,
        }),
      });

      const result = await resp.json();

      if (!result.success) {
        showAlert(result.error || 'サーバーエラー');
        finishGeneration();
        return;
      }

      state.jobId = result.jobId;

      // Use server-provided section defs if available
      if (result.sectionDefs) {
        state.sectionDefs = result.sectionDefs;
      }

      console.log('[LP-NB] Job started:', state.jobId, 'sections:', state.sectionDefs.length);

      // Start polling
      state.pollTimer = setInterval(pollStatus, POLL_INTERVAL);
      pollStatus();

    } catch (err) {
      console.error('[LP-NB] Failed to start generation:', err);
      showAlert('エラー: ' + err.message);
      finishGeneration();
    }
  }

  /** Poll job status */
  async function pollStatus() {
    if (!state.jobId) return;

    try {
      const receivedParam = state.receivedSections.size > 0
        ? '?received=' + Array.from(state.receivedSections).join(',')
        : '';

      const resp = await fetch(`/lp-nanobanana/api/status/${state.jobId}${receivedParam}`);
      const result = await resp.json();

      if (!result.success) {
        console.warn('[LP-NB] Poll error:', result.error);
        return;
      }

      const data = result.data;
      applyJobState(data);

      // Stop polling when done or error
      if (data.phase === 'done' || data.phase === 'error') {
        stopPolling();
        finishGeneration();
      }
    } catch (err) {
      console.warn('[LP-NB] Poll request failed:', err.message);
    }
  }

  /** Apply server job state to UI */
  function applyJobState(data) {
    const phase = data.phase;
    const totalSections = state.sectionDefs.length;

    // Update step states based on phase transitions
    if (phase !== state.lastPhase) {
      switch (phase) {
        case 'copy':
          setStepState('step-copy', 'active');
          break;
        case 'design':
          setStepState('step-copy', 'done');
          setStepState('step-design', 'active');
          hideCopyPreview();
          break;
        case 'image':
          setStepState('step-copy', 'done');
          setStepState('step-design', 'done');
          setStepState('step-image', 'active');
          hideCopyPreview();
          break;
        case 'done':
          setStepState('step-copy', 'done');
          setStepState('step-design', 'done');
          setStepState('step-image', 'done');
          hideCopyPreview();
          break;
        case 'error':
          if (state.lastPhase === 'copy' || !state.lastPhase) setStepState('step-copy', 'error');
          else if (state.lastPhase === 'design') setStepState('step-design', 'error');
          else setStepState('step-image', 'error');
          break;
      }
      state.lastPhase = phase;
    }

    // Update status text for current phase
    if (data.statusText) {
      if (phase === 'copy') setStepStatusText('step-copy', data.statusText);
      else if (phase === 'design') setStepStatusText('step-design', data.statusText);
      else if (phase === 'image') setStepStatusText('step-image', data.statusText);
    }

    // Copy preview
    if (data.copyText && data.copyText !== state.copyText) {
      state.copyText = data.copyText;
      setCopyPreview(state.copyText);
    }

    // Update sections
    for (const [idStr, sec] of Object.entries(data.sections)) {
      const id = parseInt(idStr);
      const localSec = state.sections[id];
      if (!localSec) continue;

      // Always update prompt if server provides it (even for already-received sections)
      if (sec.prompt && !localSec.prompt) {
        localSec.prompt = sec.prompt;
      }

      if (sec.status !== localSec.status) {
        localSec.status = sec.status;

        if (sec.status === 'complete' && sec.base64) {
          localSec.base64 = sec.base64;
          if (sec.prompt) localSec.prompt = sec.prompt;
          state.receivedSections.add(id);
        }
        if (sec.status === 'error') {
          localSec.error = sec.error;
          if (sec.prompt) localSec.prompt = sec.prompt;
        }

        updateSectionCard(id);
      }
    }

    // Show feedback bar as soon as any section is complete (even during generation)
    const anySuccess = Object.values(state.sections).some(s => s.status === 'complete');
    if (anySuccess) {
      $('#feedback-bar').classList.add('active');
    }

    // Download bar only when fully done
    if (phase === 'done' && anySuccess) {
      $('#download-bar').classList.add('active');
    }
  }

  /** Update elapsed display (runs on a 1s timer) */
  function updateElapsedDisplay() {
    if (!state.startTime) return;

    const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
    const elapsedStr = formatTime(elapsed);
    const totalSections = state.sectionDefs.length;

    const phase = state.lastPhase || 'copy';
    let mainText = '';
    let pct = 0;

    switch (phase) {
      case 'copy':
        pct = 5;
        mainText = `コピー生成中... ${elapsedStr}経過`;
        break;
      case 'design':
        pct = 18;
        mainText = `デザイン分析中... ${elapsedStr}経過`;
        break;
      case 'image': {
        const completed = Object.values(state.sections).filter(s => s.status === 'complete').length;
        const failed = Object.values(state.sections).filter(s => s.status === 'error').length;
        const done = completed + failed;
        pct = 25 + Math.floor(75 * done / totalSections);
        mainText = `画像生成 ${completed}/${totalSections}完了`;
        break;
      }
      case 'done':
        pct = 100;
        const successCount = Object.values(state.sections).filter(s => s.status === 'complete').length;
        mainText = `完了! ${successCount}/${totalSections}セクション成功`;
        break;
      case 'error':
        mainText = 'エラーが発生しました';
        break;
    }

    updateProgressBar(pct, 100);
    updateProgressText(mainText, elapsedStr);
  }

  function stopPolling() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function finishGeneration() {
    state.generating = false;
    stopPolling();
    if (state.elapsedTimer) { clearInterval(state.elapsedTimer); state.elapsedTimer = null; }
    $('#btn-generate').disabled = false;
    $('#btn-generate').textContent = 'LPを生成する';
    $('#btn-stop').style.display = 'none';

    // Stop all generating animations (replace with stopped state)
    for (const [idStr, sec] of Object.entries(state.sections)) {
      if (sec.status === 'generating') {
        sec.status = 'error';
        sec.error = '生成が停止されました';
        updateSectionCard(parseInt(idStr));
      }
    }

    updateElapsedDisplay();
  }

  /** Stop generation — cancel the running job */
  async function stopGeneration() {
    if (!state.jobId) return;

    const btn = $('#btn-stop');
    btn.disabled = true;
    btn.textContent = '停止中...';

    try {
      await fetch(`/lp-nanobanana/api/cancel/${state.jobId}`, { method: 'POST' });
      showAlert('生成を停止しました', 'success');
    } catch (err) {
      console.error('[LP-NB] Cancel failed:', err);
      showAlert('停止に失敗しました: ' + err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = '生成を停止';
    }
  }

  // --- UI Updates ---
  function showResults() {
    const container = $('.results-section');
    container.classList.add('active');

    // Always rebuild section cards based on current LP type
    let html = '<div class="lp-preview">';
    for (const def of state.sectionDefs) {
      const i = def.id;
      html += `
        <div class="lp-section" data-section="${i}">
          <div class="lp-section-content" data-body="${i}">
            <div class="lp-section-placeholder">
              <div class="placeholder-label">${i}. ${def.nameJa}</div>
              <span class="section-status waiting" data-status="${i}">\u23F3 待機中</span>
            </div>
          </div>
          <div class="lp-section-overlay">
            <span class="overlay-label">${i}. ${def.nameJa}</span>
            <div class="overlay-actions">
              <button class="btn-section-dl" onclick="window.__downloadSection(${i})" title="この画像をダウンロード">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M8 10.5l-3.5-3.5h2.5v-5h2v5h2.5l-3.5 3.5z"/><path d="M2 12h12v2h-12z"/></svg>
                保存
              </button>
              <button class="btn-section-zoom" onclick="window.__openModal(document.querySelector('[data-body=&quot;${i}&quot;] img')?.src)" title="拡大表示">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M6.5 1a5.5 5.5 0 014.38 8.82l3.65 3.65a.75.75 0 01-1.06 1.06l-3.65-3.65A5.5 5.5 0 116.5 1zm0 1.5a4 4 0 100 8 4 4 0 000-8z"/></svg>
                拡大
              </button>
              <button class="btn-section-prompt" onclick="window.__showPrompt(${i})" title="プロンプトを表示">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M2 3h12v1H2zm0 3h10v1H2zm0 3h12v1H2zm0 3h8v1H2z"/></svg>
                プロンプト
              </button>
              <button class="btn-section-regen" onclick="window.__regenerateSection(${i})" title="フィードバック付き再生成">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor"><path d="M13.65 2.35a8 8 0 10.35 11.3l-1.41-1.41a6 6 0 11-.27-8.47L10 6h6V0l-2.35 2.35z"/></svg>
                再生成
              </button>
            </div>
          </div>
        </div>`;
    }
    html += '</div>';
    container.innerHTML = html;
  }

  function updateAllSectionCards() {
    for (const def of state.sectionDefs) updateSectionCard(def.id);
  }

  function updateSectionCard(id) {
    const sec = state.sections[id];
    if (!sec) return;

    const name = getSectionName(id);
    const bodyEl = $(`[data-body="${id}"]`);
    const sectionEl = $(`.lp-section[data-section="${id}"]`);
    if (!bodyEl || !sectionEl) return;

    sectionEl.classList.remove('is-waiting', 'is-generating', 'is-complete', 'is-error');
    sectionEl.classList.add('is-' + sec.status);

    switch (sec.status) {
      case 'waiting':
        bodyEl.innerHTML = `
          <div class="lp-section-placeholder">
            <div class="placeholder-label">${id}. ${name}</div>
            <span class="section-status waiting">\u23F3 待機中</span>
          </div>`;
        break;
      case 'generating':
        bodyEl.innerHTML = `
          <div class="lp-section-placeholder generating">
            <div class="generating-animation">
              <div class="gen-text">${name} を生成中<span class="gen-dots"></span></div>
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
        bodyEl.innerHTML = `<img src="data:image/png;base64,${sec.base64}" alt="${name}" onclick="window.__openModal(this.src)" />`;
        break;
      case 'error':
        bodyEl.innerHTML = `
          <div class="lp-section-placeholder error">
            <div class="placeholder-label">${id}. ${name}</div>
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

  // --- Show Prompt (editable + regenerate) ---
  window.__showPrompt = function (id) {
    const sec = state.sections[id];
    if (!sec?.prompt) return showAlert('プロンプトがまだありません');

    const name = getSectionName(id);

    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    const modal = document.createElement('div');
    modal.style.cssText = 'background:#1e1e2e;color:#e0e0e0;border-radius:12px;max-width:700px;width:100%;max-height:80vh;display:flex;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,0.5);';

    const headerEl = document.createElement('div');
    headerEl.style.cssText = 'display:flex;justify-content:space-between;align-items:center;padding:16px 20px;border-bottom:1px solid #333;';
    headerEl.innerHTML = `<span style="font-weight:600;font-size:1rem;">Section ${id}: ${name} のプロンプト</span>`;

    const btnGroup = document.createElement('div');
    btnGroup.style.cssText = 'display:flex;gap:8px;';

    const copyBtn = document.createElement('button');
    copyBtn.textContent = 'コピー';
    copyBtn.style.cssText = 'background:#3b82f6;color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:0.85rem;';
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(textarea.value).then(() => {
        copyBtn.textContent = 'コピー済み!';
        setTimeout(() => { copyBtn.textContent = 'コピー'; }, 2000);
      });
    });

    const regenBtn = document.createElement('button');
    regenBtn.textContent = 'このプロンプトで再生成';
    regenBtn.style.cssText = 'background:linear-gradient(135deg,#f97316,#ea580c);color:#fff;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:0.85rem;font-weight:600;';
    regenBtn.addEventListener('click', async () => {
      const geminiKey = $('#gemini-api-key').value.trim();
      if (!geminiKey) { showAlert('Gemini APIキーを設定してください'); return; }

      const editedPrompt = textarea.value.trim();
      if (!editedPrompt) { showAlert('プロンプトが空です'); return; }

      regenBtn.disabled = true;
      regenBtn.textContent = '生成中...';

      sec.prompt = editedPrompt;
      sec.status = 'generating';
      sec.error = null;
      updateSectionCard(id);

      try {
        const resp = await fetch('/lp-nanobanana/api/retry-section', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            sectionId: id,
            lpType: state.lpType,
            prompt: editedPrompt,
            geminiApiKey: geminiKey,
            geminiModel: $('#gemini-model').value,
          }),
        });
        const result = await resp.json();
        if (result.success) {
          sec.status = 'complete';
          sec.base64 = result.data.base64;
          updateSectionCard(id);
          showAlert(`${name} の再生成が完了しました`, 'success');
          const anySuccess = Object.values(state.sections).some(s => s.status === 'complete');
          if (anySuccess) $('#download-bar').classList.add('active');
        } else {
          sec.status = 'error';
          sec.error = result.error;
          updateSectionCard(id);
          showAlert(result.error || '再生成に失敗しました');
        }
      } catch (err) {
        sec.status = 'error';
        sec.error = err.message;
        updateSectionCard(id);
        showAlert('再生成エラー: ' + err.message);
      }

      regenBtn.disabled = false;
      regenBtn.textContent = 'このプロンプトで再生成';
      overlay.remove();
    });

    btnGroup.appendChild(copyBtn);
    btnGroup.appendChild(regenBtn);
    headerEl.appendChild(btnGroup);

    const textarea = document.createElement('textarea');
    textarea.style.cssText = 'padding:20px;margin:0;flex:1;font-size:0.8rem;line-height:1.6;white-space:pre-wrap;word-break:break-word;font-family:monospace;background:#1e1e2e;color:#e0e0e0;border:none;resize:none;outline:none;overflow:auto;';
    textarea.value = sec.prompt;

    modal.appendChild(headerEl);
    modal.appendChild(textarea);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
  };

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
        body: JSON.stringify({
          sectionId: id,
          lpType: state.lpType,
          prompt: sec.prompt,
          geminiApiKey: geminiKey,
          geminiModel: $('#gemini-model').value,
        }),
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
    const fileName = getSectionFileName(id);
    const binary = atob(sec.base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: 'image/png' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `section_${String(id).padStart(2, '0')}_${fileName}.png`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // --- Modal ---
  window.__openModal = function (src) {
    if (src) openModal(src);
  };

  // --- Regenerate All with Feedback ---
  async function regenerateAll() {
    const feedback = $('#feedback-text').value.trim();
    if (!feedback) return showAlert('修正リクエストを入力してください');

    const geminiKey = $('#gemini-api-key').value.trim();
    if (!geminiKey) return showAlert('Gemini APIキーを設定してください');

    const sectionsWithPrompt = Object.entries(state.sections)
      .filter(([, s]) => s.prompt)
      .map(([id]) => parseInt(id));

    if (sectionsWithPrompt.length === 0) return showAlert('再生成できるセクションがありません');

    const btn = $('#btn-regenerate-all');
    btn.disabled = true;
    btn.textContent = '再生成中...';

    for (const id of sectionsWithPrompt) {
      await regenerateSectionWithFeedback(id, feedback);
    }

    btn.disabled = false;
    btn.textContent = '全セクション再生成';
    showAlert(`${sectionsWithPrompt.length}セクションの再生成が完了しました`, 'success');
  }

  /** Regenerate a single section with feedback appended to prompt */
  async function regenerateSectionWithFeedback(id, feedback) {
    const sec = state.sections[id];
    if (!sec?.prompt) return;

    const geminiKey = $('#gemini-api-key').value.trim();
    if (!geminiKey) return;

    const modifiedPrompt = sec.prompt + `\n\n【ユーザーからの修正リクエスト】\n以下のフィードバックを反映して画像を改善してください:\n${feedback}`;

    sec.status = 'generating';
    sec.error = null;
    updateSectionCard(id);

    try {
      const resp = await fetch('/lp-nanobanana/api/retry-section', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sectionId: id,
          lpType: state.lpType,
          prompt: modifiedPrompt,
          geminiApiKey: geminiKey,
          geminiModel: $('#gemini-model').value,
        }),
      });
      const result = await resp.json();
      if (result.success) {
        sec.status = 'complete';
        sec.base64 = result.data.base64;
        updateSectionCard(id);
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
  }

  // --- Per-section Regenerate with Feedback ---
  window.__regenerateSection = function (id) {
    const sec = state.sections[id];
    if (!sec?.prompt) return showAlert('プロンプトがまだありません');

    const geminiKey = $('#gemini-api-key').value.trim();
    if (!geminiKey) return showAlert('Gemini APIキーを設定してください');

    const name = getSectionName(id);

    // Show feedback input dialog
    const overlay = document.createElement('div');
    overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:10000;display:flex;align-items:center;justify-content:center;padding:20px;';
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

    const modal = document.createElement('div');
    modal.style.cssText = 'background:#1e1e2e;color:#e0e0e0;border-radius:12px;max-width:500px;width:100%;box-shadow:0 8px 32px rgba(0,0,0,0.5);';

    const headerEl = document.createElement('div');
    headerEl.style.cssText = 'padding:16px 20px;border-bottom:1px solid #333;font-weight:600;font-size:1rem;';
    headerEl.textContent = `${id}. ${name} を再生成`;

    const bodyEl = document.createElement('div');
    bodyEl.style.cssText = 'padding:20px;';

    const textarea = document.createElement('textarea');
    textarea.rows = 3;
    textarea.placeholder = '修正したいポイントを入力（例: もっと高級感を出して / 文字を大きく）';
    textarea.style.cssText = 'width:100%;padding:10px 14px;border:1px solid #444;border-radius:8px;font-size:0.9rem;font-family:inherit;background:#2a2a3e;color:#e0e0e0;resize:vertical;';

    // Pre-fill from main feedback textarea if it has content
    const mainFeedback = $('#feedback-text').value.trim();
    if (mainFeedback) textarea.value = mainFeedback;

    const btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:10px;margin-top:14px;';

    const regenBtn = document.createElement('button');
    regenBtn.textContent = '再生成する';
    regenBtn.style.cssText = 'flex:1;padding:10px;background:linear-gradient(135deg,#f97316,#ea580c);color:#fff;border:none;border-radius:8px;font-size:0.9rem;font-weight:600;cursor:pointer;';
    regenBtn.addEventListener('click', async () => {
      const fb = textarea.value.trim();
      if (!fb) { showAlert('修正ポイントを入力してください'); return; }
      overlay.remove();
      await regenerateSectionWithFeedback(id, fb);
      showAlert(`${name} の再生成が完了しました`, 'success');
    });

    const cancelBtn = document.createElement('button');
    cancelBtn.textContent = 'キャンセル';
    cancelBtn.style.cssText = 'padding:10px 20px;background:#444;color:#e0e0e0;border:none;border-radius:8px;font-size:0.9rem;cursor:pointer;';
    cancelBtn.addEventListener('click', () => overlay.remove());

    btnRow.appendChild(regenBtn);
    btnRow.appendChild(cancelBtn);
    bodyEl.appendChild(textarea);
    bodyEl.appendChild(btnRow);
    modal.appendChild(headerEl);
    modal.appendChild(bodyEl);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);
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

    const zip = new JSZip();

    for (const { id, base64 } of completed) {
      const fileName = getSectionFileName(id);
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      zip.file(`section_${String(id).padStart(2, '0')}_${fileName}.png`, bytes);
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
