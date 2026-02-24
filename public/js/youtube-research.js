// YouTube Research Tool - Client-side JavaScript

const API_BASE = '/youtube-research/api';

// --- State ---
let searchResultVideos = []; // VideoMeta[] from search
let searchBuzzRanking = [];  // BuzzResult[] from search
let isComposing = false;     // IME composition state

// --- Toast Notification System ---
function showToast(message, type = 'info', duration) {
  // Error messages stay longer (10s), others default to 4s
  if (!duration) duration = type === 'error' ? 10000 : 4000;
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  // Click to dismiss
  toast.style.cursor = 'pointer';
  toast.addEventListener('click', () => {
    toast.classList.remove('toast-show');
    toast.classList.add('toast-hide');
    setTimeout(() => toast.remove(), 300);
  });
  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => toast.classList.add('toast-show'));

  setTimeout(() => {
    toast.classList.remove('toast-show');
    toast.classList.add('toast-hide');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// --- Common API Call Helper ---
async function apiCall(endpoint, body, timeoutMs = 60000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(API_BASE + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorData = await res.json().catch(() => null);
      const msg = errorData?.error || `サーバーエラー (${res.status})`;
      throw new Error(msg);
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('リクエストがタイムアウトしました（60秒）。もう一度お試しください。');
    }
    throw err;
  }
}

// --- API Key Management ---
function getApiKeys() {
  return {
    youtubeApiKey: localStorage.getItem('yt-research-youtube-key') || '',
    anthropicApiKey: localStorage.getItem('yt-research-anthropic-key') || ''
  };
}

function saveApiKeys() {
  const ytKey = document.getElementById('youtube-api-key').value.trim();
  const anKey = document.getElementById('anthropic-api-key').value.trim();
  if (ytKey) localStorage.setItem('yt-research-youtube-key', ytKey);
  if (anKey) localStorage.setItem('yt-research-anthropic-key', anKey);
  updateApiKeyStatus();
  showToast('キーを保存しました', 'success');
}

function updateApiKeyStatus() {
  const keys = getApiKeys();
  const statusEl = document.getElementById('api-key-status');
  if (keys.youtubeApiKey && keys.anthropicApiKey) {
    statusEl.textContent = '設定済み';
    statusEl.className = 'badge badge-good';
  } else if (keys.youtubeApiKey || keys.anthropicApiKey) {
    statusEl.textContent = '一部未設定';
    statusEl.className = 'badge badge-maybe';
  } else {
    statusEl.textContent = '未設定';
    statusEl.className = 'badge badge-low';
  }
}

function loadApiKeys() {
  const keys = getApiKeys();
  document.getElementById('youtube-api-key').value = keys.youtubeApiKey;
  document.getElementById('anthropic-api-key').value = keys.anthropicApiKey;
  updateApiKeyStatus();
}

// --- Loading ---
function showLoading(text, sub) {
  document.getElementById('loading').classList.remove('hidden');
  document.getElementById('loading-text').textContent = text || '処理中...';
  document.getElementById('loading-sub').textContent = sub || '';
}

function hideLoading() {
  document.getElementById('loading').classList.add('hidden');
}

// --- Button state helpers ---
function setSearchButtonLoading(loading) {
  const btn = document.getElementById('btn-search');
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalText = btn.textContent;
    btn.textContent = '検索中...';
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.originalText || '検索';
  }
}

// --- Result Sub-tabs ---
document.querySelectorAll('.result-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const parent = tab.closest('.results') || tab.closest('section');
    parent.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
    parent.querySelectorAll('.result-content').forEach(c => c.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('result-' + tab.dataset.result).classList.add('active');
  });
});

// --- Save Keys ---
document.getElementById('btn-save-keys').addEventListener('click', saveApiKeys);

// --- Selection Management ---
function getSelectedVideos() {
  const checkboxes = document.querySelectorAll('.video-checkbox:checked');
  const selectedIds = new Set(Array.from(checkboxes).map(cb => cb.dataset.videoId));
  return searchBuzzRanking
    .filter(r => selectedIds.has(r.video.id))
    .map(r => r.video);
}

function updateSelectionCount() {
  const count = document.querySelectorAll('.video-checkbox:checked').length;
  document.getElementById('selected-count').textContent = count + '件選択中';
  document.getElementById('btn-trend-selected').disabled = count === 0;
  document.getElementById('btn-analyze-selected').disabled = count === 0;
}

document.getElementById('btn-select-all').addEventListener('click', () => {
  document.querySelectorAll('.video-checkbox').forEach(cb => cb.checked = true);
  document.getElementById('check-all').checked = true;
  updateSelectionCount();
});

document.getElementById('btn-select-none').addEventListener('click', () => {
  document.querySelectorAll('.video-checkbox').forEach(cb => cb.checked = false);
  document.getElementById('check-all').checked = false;
  updateSelectionCount();
});

document.getElementById('btn-select-buzz').addEventListener('click', () => {
  document.querySelectorAll('.video-checkbox').forEach(cb => {
    const level = cb.dataset.buzzLevel;
    cb.checked = (level === 'super-buzz' || level === 'buzz' || level === 'good');
  });
  updateSelectionCount();
});

document.getElementById('check-all').addEventListener('change', (e) => {
  document.querySelectorAll('.video-checkbox').forEach(cb => cb.checked = e.target.checked);
  updateSelectionCount();
});

// ========================================
// Step 1: YouTube Search + Buzz
// ========================================
document.getElementById('btn-search').addEventListener('click', doSearch);
document.getElementById('search-query').addEventListener('compositionstart', () => { isComposing = true; });
document.getElementById('search-query').addEventListener('compositionend', () => { isComposing = false; });
document.getElementById('search-query').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !isComposing && !e.isComposing && e.keyCode !== 229) doSearch();
});

async function doSearch() {
  const keyword = document.getElementById('search-query').value.trim();
  const selectedGenres = Array.from(document.querySelectorAll('input[name="filter-genre"]:checked')).map(cb => cb.value);

  if (!keyword && selectedGenres.length === 0) {
    showToast('検索キーワードまたはジャンルを選択してください', 'warning');
    return;
  }

  // Genre keyword mapping for YouTube OR search
  const genreKeywords = {
    education: '教育|学習|勉強|講座|解説|授業|スキルアップ|資格',
    tech: 'テクノロジー|テック|プログラミング|AI|エンジニア|IT|開発|ChatGPT|アプリ',
    business: 'ビジネス|副業|起業|稼ぐ|マーケティング|フリーランス|収益化|投資|ノウハウ|コンサル|物販|せどり|アフィリエイト|ネットビジネス',
    lifestyle: 'ライフスタイル|暮らし|ルーティン|日常|Vlog|生活|ミニマリスト|丁寧な暮らし|モーニングルーティン|ナイトルーティン',
    entertainment: 'エンタメ|バラエティ|面白い|やってみた|検証|ドッキリ|チャレンジ|コント|大食い',
    cooking: '料理|レシピ|グルメ|食べ|作り方|クッキング|簡単レシピ|食レポ|お弁当|スイーツ',
    beauty: '美容|コスメ|メイク|スキンケア|ヘアアレンジ|垢抜け|整形|ダイエット美容|プチプラ',
    fitness: '筋トレ|ダイエット|フィットネス|ワークアウト|エクササイズ|ストレッチ|ヨガ|痩せる|ボディメイク|宅トレ',
    gaming: 'ゲーム|ゲーム実況|プレイ|攻略|配信|eスポーツ|マイクラ|フォートナイト|原神|スプラ',
    music: '音楽|歌ってみた|MV|弾いてみた|カバー|作曲|ピアノ|ギター|DTM|オリジナル曲',
    travel: '旅行|旅|観光|キャンプ|アウトドア|絶景|一人旅|海外旅行|温泉|車中泊|バンライフ',
    pets: 'ペット|犬|猫|動物|かわいい|子犬|子猫|保護猫|多頭飼い|爬虫類',
    parenting: '子育て|育児|ママ|パパ|赤ちゃん|知育|離乳食|幼児教育|小学生|受験',
    spiritual: 'スピリチュアル|引き寄せ|潜在意識|宇宙|波動|目覚め|覚醒|ハイヤーセルフ|アセンション|ツインレイ',
    fortune: '占い|タロット|星座|数秘術|四柱推命|手相|星読み|今週の運勢|誕生日占い|オラクルカード',
    healing: 'ヒーリング|瞑想|周波数|睡眠|リラックス|ソルフェジオ|ASMR|自然音|528Hz|マインドフルネス',
    mental: 'メンタルヘルス|HSP|自己肯定感|うつ|不安|心理学|カウンセリング|アダルトチルドレン|生きづらさ|自分を変える'
  };

  // Genre name mapping for display
  const genreNames = {
    education: '教育・学習', tech: 'テクノロジー', business: 'ビジネス・副業',
    lifestyle: 'ライフスタイル', entertainment: 'エンタメ', cooking: '料理・グルメ',
    beauty: '美容・コスメ', fitness: 'フィットネス・健康', gaming: 'ゲーム',
    music: '音楽', travel: '旅行・アウトドア', pets: 'ペット・動物',
    parenting: '子育て・育児', spiritual: 'スピリチュアル', fortune: '占い・鑑定',
    healing: 'ヒーリング・瞑想', mental: 'メンタルヘルス'
  };

  let query = keyword;
  let displayTitle = keyword; // For display in results header

  if (selectedGenres.length > 0) {
    if (selectedGenres.length === 1) {
      // 1 genre: Full OR search for that genre
      const orTerms = genreKeywords[selectedGenres[0]];
      query = keyword ? keyword + ' ' + orTerms : orTerms;
      displayTitle = keyword
        ? keyword + '（' + genreNames[selectedGenres[0]] + '）'
        : genreNames[selectedGenres[0]];
    } else {
      // Multiple genres: Top 3 keywords from each genre joined with OR
      const multiGenreTerms = selectedGenres.map(g => {
        const kw = genreKeywords[g];
        return kw ? kw.split('|').slice(0, 3).join('|') : null;
      }).filter(Boolean).join('|');
      query = keyword ? keyword + ' ' + multiGenreTerms : multiGenreTerms;
      displayTitle = keyword
        ? keyword + '（' + selectedGenres.map(g => genreNames[g]).join(' + ') + '）'
        : selectedGenres.map(g => genreNames[g]).join(' + ');
    }
  }

  let ytKey = document.getElementById('youtube-api-key').value.trim();
  if (!ytKey) ytKey = getApiKeys().youtubeApiKey;

  if (!ytKey) {
    showToast('YouTube Data API キーを設定してください', 'warning');
    document.getElementById('api-key-toggle').open = true;
    document.getElementById('youtube-api-key').focus();
    return;
  }

  // Length checkboxes: get checked values
  const lengthChecks = Array.from(document.querySelectorAll('input[name="filter-length"]:checked')).map(cb => cb.value);
  let lengthCategory = 'all';
  if (lengthChecks.length === 1) lengthCategory = lengthChecks[0];

  // Period checkboxes: get checked values
  const periodChecks = Array.from(document.querySelectorAll('input[name="filter-period"]:checked')).map(cb => cb.value);

  // Period priority order (narrowest to widest)
  const periodOrder = ['week', '2weeks', 'month', '3months', '6months', 'year'];
  const periodDaysMap = { week: 7, '2weeks': 14, month: 30, '3months': 90, '6months': 180, year: 365 };

  // Use widest checked period for API call, or 'all' if none checked
  let uploadPeriod = 'all';
  if (periodChecks.length > 0) {
    const sorted = periodChecks.sort((a, b) => periodOrder.indexOf(a) - periodOrder.indexOf(b));
    const widest = sorted[sorted.length - 1];
    // Map to backend-compatible values (some periods don't have exact API equivalents)
    const backendMap = { week: 'week', '2weeks': 'month', month: 'month', '3months': '3months', '6months': 'year', year: 'year' };
    uploadPeriod = backendMap[widest] || 'all';

    // Notify user if period was rounded
    if (widest === '2weeks' || widest === '6months') {
      const roundedLabel = widest === '2weeks' ? '1ヶ月以内' : '1年以内';
      showToast(`「${widest === '2weeks' ? '2週間以内' : '半年以内'}」はYouTube APIの仕様上「${roundedLabel}」に丸められます`, 'info', 5000);
    }
  }

  const filters = {
    genre: selectedGenres.length > 0 ? selectedGenres[0] : undefined,
    lengthCategory: lengthCategory,
    uploadPeriod: uploadPeriod,
    regionCode: document.getElementById('filter-region').value
  };
  const maxResults = parseInt(document.getElementById('filter-max-results').value, 10);

  setSearchButtonLoading(true);
  showLoading('YouTubeを検索中...', 'YouTube Data APIで動画を取得し、バズ比率を計算しています');

  // Hide previous results
  document.getElementById('trend-results').classList.add('hidden');
  document.getElementById('analysis-results').classList.add('hidden');

  try {
    const data = await apiCall('/search', { query, filters, maxResults, youtubeApiKey: ytKey, anthropicApiKey: '' });
    hideLoading();
    setSearchButtonLoading(false);

    if (!data.success) {
      showToast(data.error || '不明なエラー', 'error');
      return;
    }

    // Filter by duration if 2 length categories selected (API got 'all', filter here)
    if (lengthChecks.length === 2 && data.data.buzzRanking) {
      data.data.buzzRanking = data.data.buzzRanking.filter(r => {
        const secs = parseDuration(r.video.duration);
        if (secs === null) return true;
        return lengthChecks.some(cat => matchesDurationCategory(secs, cat));
      });
      data.data.videoCount = data.data.buzzRanking.length;
    }

    // Apply period priority sorting if multiple periods checked
    if (periodChecks.length > 1 && data.data.buzzRanking) {
      const now = new Date();
      data.data.buzzRanking.sort((a, b) => {
        const aDate = a.video.uploadDate ? new Date(a.video.uploadDate) : null;
        const bDate = b.video.uploadDate ? new Date(b.video.uploadDate) : null;
        const aDays = aDate ? Math.floor((now - aDate) / (1000 * 60 * 60 * 24)) : 99999;
        const bDays = bDate ? Math.floor((now - bDate) / (1000 * 60 * 60 * 24)) : 99999;

        const sortedPeriods = periodChecks.sort((x, y) => periodOrder.indexOf(x) - periodOrder.indexOf(y));
        let aGroup = sortedPeriods.length;
        let bGroup = sortedPeriods.length;
        for (let i = 0; i < sortedPeriods.length; i++) {
          const days = periodDaysMap[sortedPeriods[i]];
          if (aGroup === sortedPeriods.length && aDays <= days) aGroup = i;
          if (bGroup === sortedPeriods.length && bDays <= days) bGroup = i;
        }

        if (aGroup !== bGroup) return aGroup - bGroup;
        const aBuzz = a.buzzRatio || 0;
        const bBuzz = b.buzzRatio || 0;
        return bBuzz - aBuzz;
      });
    }

    searchResultVideos = data.data.videos;
    searchBuzzRanking = data.data.buzzRanking;
    renderSearchResults(data.data, displayTitle);
  } catch (err) {
    hideLoading();
    setSearchButtonLoading(false);
    showToast('通信エラー: ' + err.message, 'error');
  }
}

function renderSearchResults(data, displayTitle) {
  const container = document.getElementById('search-results');
  container.classList.remove('hidden');

  document.getElementById('result-query-title').textContent = '「' + displayTitle + '」の検索結果';
  document.getElementById('result-video-count').textContent = data.videoCount + '件';

  const buzz = data.buzzRanking || [];
  const tbody = document.getElementById('video-table-body');
  tbody.innerHTML = buzz.map((r, i) => `<tr class="buzz-row buzz-${r.buzzLevel}">
    <td><input type="checkbox" class="video-checkbox" data-video-id="${escapeAttr(r.video.id)}" data-buzz-level="${r.buzzLevel}" checked></td>
    <td>${i + 1}</td>
    <td class="td-thumb">${r.video.thumbnail ? '<a href="' + escapeAttr(r.video.url) + '" target="_blank"><img src="' + escapeAttr(r.video.thumbnail) + '" alt="" class="video-thumb"></a>' : ''}</td>
    <td>${r.video.url ? '<a href="' + escapeAttr(r.video.url) + '" target="_blank" class="video-link">' + escapeHtml(r.video.title) + '</a>' : escapeHtml(r.video.title)}</td>
    <td class="channel-name">${escapeHtml(r.video.channel)}</td>
    <td class="td-upload-date">${formatUploadDate(r.video.uploadDate)}</td>
    <td class="td-elapsed">${formatElapsed(r.video.uploadDate)}</td>
    <td>${r.video.views != null ? r.video.views.toLocaleString() : '-'}</td>
    <td>${r.video.subscribers != null ? r.video.subscribers.toLocaleString() : '-'}</td>
    <td class="buzz-ratio">${r.buzzRatio != null ? r.buzzRatio.toFixed(1) + 'x' : '-'}</td>
    <td>${buzzBadge(r.buzzLevel)}</td>
  </tr>`).join('');

  // Attach checkbox listeners
  document.querySelectorAll('.video-checkbox').forEach(cb => {
    cb.addEventListener('change', updateSelectionCount);
  });
  document.getElementById('check-all').checked = true;
  updateSelectionCount();

  container.scrollIntoView({ behavior: 'smooth' });
}

// ========================================
// Step 2: Trend Check (selected videos)
// ========================================
document.getElementById('btn-trend-selected').addEventListener('click', doTrendCheck);

async function doTrendCheck() {
  const selected = getSelectedVideos();
  if (selected.length === 0) { showToast('動画を選択してください', 'warning'); return; }

  let anKey = document.getElementById('anthropic-api-key').value.trim();
  if (!anKey) anKey = getApiKeys().anthropicApiKey;

  if (!anKey) {
    showToast('トレンド判定にはAnthropic APIキーが必要です', 'warning');
    document.getElementById('api-key-toggle').open = true;
    document.getElementById('anthropic-api-key').focus();
    return;
  }

  // Limit to 10 titles for trend check
  const titles = selected.slice(0, 10).map(v => v.title).filter(t => t && t.length > 0);

  if (titles.length === 0) { showToast('動画タイトルが取得できませんでした', 'error'); return; }

  // Notify if selection was capped
  if (selected.length > 10) {
    showToast('トレンド判定は最大10本までです。先頭10本を分析します。', 'info', 5000);
  }

  const btnTrend = document.getElementById('btn-trend-selected');
  btnTrend.disabled = true;
  showLoading('企画トレンド判定中...', titles.length + '件の動画の企画を分析しています（30秒〜1分）');

  try {
    const data = await apiCall('/trend', { titles, anthropicApiKey: anKey }, 120000);
    hideLoading();
    btnTrend.disabled = false;

    if (!data.success) {
      showToast(data.error || '不明なエラー', 'error');
      return;
    }

    renderTrendResults(data.data);
  } catch (err) {
    hideLoading();
    btnTrend.disabled = false;
    showToast('通信エラー: ' + err.message, 'error');
  }
}

function renderTrendResults(data) {
  const container = document.getElementById('trend-results');
  container.classList.remove('hidden');

  document.getElementById('trend-results-body').innerHTML = `
    <table>
      <thead>
        <tr>
          <th>動画タイトル</th>
          <th>企画テーマ</th>
          <th>検索トレンド</th>
          <th>YouTube上の動向</th>
          <th>競合度</th>
          <th>総合判定</th>
          <th>判定理由</th>
        </tr>
      </thead>
      <tbody>
        ${data.results.map(r => `<tr>
          <td style="font-size:12px;max-width:200px">${escapeHtml(r.originalTitle || '')}</td>
          <td><strong>${escapeHtml(r.topic)}</strong></td>
          <td class="${trendClass(r.googleTrends)}">${trendLabel(r.googleTrends)}</td>
          <td class="${trendClass(r.youtubeSearch)}">${trendLabel(r.youtubeSearch)}</td>
          <td>${compLabel(r.competition)}</td>
          <td>${verdictBadge(r.verdict)}</td>
          <td class="hint" style="font-size:12px;max-width:250px">${escapeHtml(r.reasoning || '')}</td>
        </tr>`).join('')}
      </tbody>
    </table>
    ${data.summary ? '<div class="card" style="margin-top:12px"><h3>まとめ</h3><p>' + escapeHtml(data.summary) + '</p></div>' : ''}
  `;

  container.scrollIntoView({ behavior: 'smooth' });
}

// ========================================
// Step 3: Analyze (Single or Selected)
// ========================================

// Selected videos bulk analyze
document.getElementById('btn-analyze-selected').addEventListener('click', async () => {
  const selected = getSelectedVideos();
  if (selected.length === 0) { showToast('動画を選択してください', 'warning'); return; }

  let anKey = document.getElementById('anthropic-api-key').value.trim();
  if (!anKey) anKey = getApiKeys().anthropicApiKey;

  if (!anKey) {
    showToast('ターゲット＆キーワード分析にはAnthropic APIキーが必要です', 'warning');
    document.getElementById('api-key-toggle').open = true;
    document.getElementById('anthropic-api-key').focus();
    return;
  }

  const btnAnalyze = document.getElementById('btn-analyze-selected');
  btnAnalyze.disabled = true;
  showLoading(
    selected.length + '件の動画を分析中...',
    'タイトル・概要欄・タグからターゲット層とキーワードを抽出しています（30秒〜1分）'
  );

  try {
    const data = await apiCall('/analyze-selected', { videos: selected, anthropicApiKey: anKey }, 120000);
    hideLoading();
    btnAnalyze.disabled = false;

    if (!data.success) {
      showToast(data.error || '不明なエラー', 'error');
      return;
    }

    renderAnalysisResults(data.data, selected.length + '件の動画');
  } catch (err) {
    hideLoading();
    btnAnalyze.disabled = false;
    showToast('通信エラー: ' + err.message, 'error');
  }
});


function renderAnalysisResults(data, videoTitle) {
  const container = document.getElementById('analysis-results');
  container.classList.remove('hidden');

  // Show which video was analyzed
  document.getElementById('analysis-title').textContent = videoTitle
    ? '「' + videoTitle + '」の分析結果'
    : 'ターゲット＆キーワード分析結果';

  // Target Audience
  const audience = data.audience;
  if (audience) {
    let contentAngleHtml = '';
    if (audience.contentAngle) {
      contentAngleHtml = `
        <div class="card">
          <h3>コンテンツの切り口提案</h3>
          <p style="color:var(--text);font-size:14px">${escapeHtml(audience.contentAngle)}</p>
        </div>
      `;
    }

    document.getElementById('result-target').innerHTML = `
      <div class="card">
        <h3>デモグラフィック</h3>
        <table>
          <tr><td style="width:100px;font-weight:600">年齢層</td><td>${escapeHtml(audience.demographics.ageRange)}</td></tr>
          <tr><td style="font-weight:600">性別</td><td>${escapeHtml(audience.demographics.gender)}</td></tr>
          <tr><td style="font-weight:600">職業</td><td>${escapeHtml(audience.demographics.occupation)}</td></tr>
        </table>
      </div>
      <div class="card">
        <h3>興味・関心</h3>
        <ul>${(audience.psychographics.interests || []).map(i => '<li>' + escapeHtml(i) + '</li>').join('')}</ul>
      </div>
      <div class="card">
        <h3>課題・悩み（= コンテンツで解決すべきテーマ）</h3>
        <ul>${(audience.painPoints || []).map(p => '<li>' + escapeHtml(p) + '</li>').join('')}</ul>
      </div>
      <div class="card">
        <h3>視聴動機</h3>
        <ul>${(audience.viewingMotivation || []).map(m => '<li>' + escapeHtml(m) + '</li>').join('')}</ul>
      </div>
      <div class="card">
        <h3>購買行動（= 売れる商品・サービスのヒント）</h3>
        <ul>${(audience.purchaseBehavior || []).map(b => '<li>' + escapeHtml(b) + '</li>').join('')}</ul>
      </div>
      ${contentAngleHtml}
    `;
  }

  // Keywords
  const kws = data.keywords || [];
  document.getElementById('result-keywords').innerHTML = `
    <table>
      <thead>
        <tr>
          <th>キーワード</th>
          <th>カテゴリ</th>
          <th>ボリューム</th>
          <th>競合度</th>
          <th>用途</th>
        </tr>
      </thead>
      <tbody>
        ${kws.map(k => `<tr>
          <td><strong>${escapeHtml(k.keyword)}</strong></td>
          <td>${categoryLabel(k.category)}</td>
          <td>${volumeBadge(k.estimatedVolume)}</td>
          <td>${compBadge(k.competition)}</td>
          <td>${(k.suggestedUse || []).map(escapeHtml).join(', ')}</td>
        </tr>`).join('')}
      </tbody>
    </table>
  `;

  // Recommendations
  const recs = data.recommendations || [];
  document.getElementById('result-recommendations').innerHTML = `
    <h3 style="margin-bottom:12px">推奨アクション</h3>
    ${recs.map(r => '<div class="rec-card">' + escapeHtml(r) + '</div>').join('')}
  `;

  // Full Report
  document.getElementById('result-full-report').innerHTML = `
    <div class="full-report">${escapeHtml(data.fullReport || '')}</div>
    <button onclick="copyReport()" style="margin-top:12px" class="btn-secondary">レポートをコピー</button>
  `;

  container.scrollIntoView({ behavior: 'smooth' });
}

// --- Helper Functions ---

function categoryLabel(cat) {
  const labels = {
    'main': 'メイン', 'sub': 'サブ', 'longtail': 'ロングテール',
    'related': '関連', 'buying-intent': '購買意図', 'question': '質問系', 'trending': 'トレンド'
  };
  return labels[cat] || cat;
}

function volumeBadge(vol) {
  const colors = { high: '#2ecc71', medium: '#f1c40f', low: '#95a5a6' };
  return `<span style="color:${colors[vol] || '#aaa'}">${vol === 'high' ? '高' : vol === 'medium' ? '中' : '低'}</span>`;
}

function compBadge(comp) {
  const colors = { high: '#e74c3c', medium: '#f1c40f', low: '#2ecc71' };
  return `<span style="color:${colors[comp] || '#aaa'}">${comp === 'high' ? '高' : comp === 'medium' ? '中' : '低'}</span>`;
}

function buzzBadge(level) {
  const map = {
    'super-buzz': '<span class="badge badge-super">超バズ</span>',
    'buzz': '<span class="badge badge-buzz">バズ</span>',
    'good': '<span class="badge badge-good">好調</span>',
    'average': '<span class="badge badge-avg">平均</span>',
    'low': '<span class="badge badge-low">低調</span>',
    'unknown': '-'
  };
  return map[level] || '-';
}

function trendLabel(t) {
  return { rising: '↑ 上昇', stable: '→ 横ばい', declining: '↓ 下降', unknown: '?' }[t] || '?';
}

function trendClass(t) {
  return { rising: 'trend-up', stable: 'trend-stable', declining: 'trend-down' }[t] || '';
}

function compLabel(c) {
  return { low: '少 ○', medium: '普通 △', high: '多 ×', unknown: '?' }[c] || '?';
}

function verdictBadge(v) {
  const map = {
    'go-now': '<span class="badge badge-go">今すぐ出すべき!</span>',
    'chance-but-competitive': '<span class="badge badge-maybe">チャンスだが競争激しい</span>',
    'first-mover': '<span class="badge badge-go">先行者優位を取れる</span>',
    'niche-stable': '<span class="badge badge-maybe">ニッチで安定的</span>',
    'too-late': '<span class="badge badge-late">タイミング遅い</span>',
    'unknown': '-'
  };
  return map[v] || '-';
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
  if (!str) return '';
  return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function parseDuration(iso) {
  if (!iso) return null;
  const m = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!m) return null;
  return (parseInt(m[1] || 0) * 3600) + (parseInt(m[2] || 0) * 60) + parseInt(m[3] || 0);
}

function matchesDurationCategory(secs, cat) {
  if (cat === 'short') return secs <= 240;
  if (cat === 'medium') return secs > 240 && secs <= 1200;
  if (cat === 'long') return secs > 1200;
  return true;
}

function formatUploadDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  return d.getFullYear() + '/' + String(d.getMonth() + 1).padStart(2, '0') + '/' + String(d.getDate()).padStart(2, '0');
}

function formatElapsed(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return '-';
  const now = new Date();
  const diffMs = now - d;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays < 1) return '今日';
  if (diffDays === 1) return '1日前';
  if (diffDays < 7) return diffDays + '日前';
  if (diffDays < 30) {
    const diffWeeks = Math.floor(diffDays / 7);
    return diffWeeks + '週間前';
  }
  const diffMonths = Math.floor(diffDays / 30);
  if (diffMonths < 12) return diffMonths + 'ヶ月前';
  const diffYears = Math.floor(diffDays / 365);
  return diffYears + '年前';
}

function copyReport() {
  const el = document.querySelector('.full-report');
  if (el) {
    navigator.clipboard.writeText(el.textContent).then(() => showToast('レポートをコピーしました', 'success'));
  }
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  loadApiKeys();
});
