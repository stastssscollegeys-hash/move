// YouTube Research Tool - Client-side JavaScript

const API_BASE = '/youtube-research/api';

// --- State ---
let searchResultVideos = []; // VideoMeta[] from search
let searchBuzzRanking = [];  // BuzzResult[] from search

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
  alert('キーを保存しました');
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
document.getElementById('search-query').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') doSearch();
});

async function doSearch() {
  const keyword = document.getElementById('search-query').value.trim();
  const genre = document.getElementById('filter-genre').value;

  if (!keyword && !genre) {
    alert('検索キーワードまたはジャンルを選択してください');
    return;
  }

  const genreLabels = {
    education: '教育', tech: 'テクノロジー', business: 'ビジネス',
    lifestyle: 'ライフスタイル', entertainment: 'エンタメ', other: ''
  };

  let query = keyword;
  if (genre && genreLabels[genre]) {
    query = keyword ? keyword + ' ' + genreLabels[genre] : genreLabels[genre];
  }

  let ytKey = document.getElementById('youtube-api-key').value.trim();
  if (!ytKey) ytKey = getApiKeys().youtubeApiKey;

  if (!ytKey) {
    alert('YouTube Data API キーを設定してください');
    document.getElementById('api-key-toggle').open = true;
    document.getElementById('youtube-api-key').focus();
    return;
  }

  const filters = {
    genre: genre || undefined,
    lengthCategory: document.getElementById('filter-length').value,
    uploadPeriod: document.getElementById('filter-period').value,
    regionCode: document.getElementById('filter-region').value
  };
  const maxResults = parseInt(document.getElementById('filter-max-results').value, 10);

  showLoading('YouTubeを検索中...', 'YouTube Data APIで動画を取得し、バズ比率を計算しています');

  // Hide previous results
  document.getElementById('trend-results').classList.add('hidden');
  document.getElementById('analysis-results').classList.add('hidden');

  try {
    const res = await fetch(API_BASE + '/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, filters, maxResults, youtubeApiKey: ytKey, anthropicApiKey: '' })
    });
    const data = await res.json();
    hideLoading();

    if (!data.success) {
      alert('エラー: ' + (data.error || '不明なエラー'));
      return;
    }

    searchResultVideos = data.data.videos;
    searchBuzzRanking = data.data.buzzRanking;
    renderSearchResults(data.data, query);
  } catch (err) {
    hideLoading();
    alert('通信エラー: ' + err.message);
  }
}

function renderSearchResults(data, query) {
  const container = document.getElementById('search-results');
  container.classList.remove('hidden');

  document.getElementById('result-query-title').textContent = '「' + query + '」の検索結果';
  document.getElementById('result-video-count').textContent = data.videoCount + '件';

  const buzz = data.buzzRanking || [];
  const tbody = document.getElementById('video-table-body');
  tbody.innerHTML = buzz.map((r, i) => `<tr class="buzz-row buzz-${r.buzzLevel}">
    <td><input type="checkbox" class="video-checkbox" data-video-id="${escapeAttr(r.video.id)}" data-buzz-level="${r.buzzLevel}" checked></td>
    <td>${i + 1}</td>
    <td class="td-thumb">${r.video.thumbnail ? '<a href="' + escapeAttr(r.video.url) + '" target="_blank"><img src="' + escapeAttr(r.video.thumbnail) + '" alt="" class="video-thumb"></a>' : ''}</td>
    <td>${r.video.url ? '<a href="' + escapeAttr(r.video.url) + '" target="_blank" class="video-link">' + escapeHtml(r.video.title) + '</a>' : escapeHtml(r.video.title)}</td>
    <td class="channel-name">${escapeHtml(r.video.channel)}</td>
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
  if (selected.length === 0) { alert('動画を選択してください'); return; }

  let anKey = document.getElementById('anthropic-api-key').value.trim();
  if (!anKey) anKey = getApiKeys().anthropicApiKey;

  if (!anKey) {
    alert('トレンド判定にはAnthropic APIキーが必要です');
    document.getElementById('api-key-toggle').open = true;
    document.getElementById('anthropic-api-key').focus();
    return;
  }

  // Send video titles directly - Claude will extract the core "企画" from each
  const titles = selected.slice(0, 10).map(v => v.title).filter(t => t && t.length > 0);

  if (titles.length === 0) { alert('動画タイトルが取得できませんでした'); return; }

  showLoading('企画トレンド判定中...', selected.length + '件の動画の企画を分析しています（30秒〜1分）');

  try {
    const res = await fetch(API_BASE + '/trend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ titles, anthropicApiKey: anKey })
    });
    const data = await res.json();
    hideLoading();

    if (!data.success) {
      alert('エラー: ' + (data.error || '不明なエラー'));
      return;
    }

    renderTrendResults(data.data);
  } catch (err) {
    hideLoading();
    alert('通信エラー: ' + err.message);
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
  if (selected.length === 0) { alert('動画を選択してください'); return; }

  let anKey = document.getElementById('anthropic-api-key').value.trim();
  if (!anKey) anKey = getApiKeys().anthropicApiKey;

  if (!anKey) {
    alert('ターゲット＆キーワード分析にはAnthropic APIキーが必要です');
    document.getElementById('api-key-toggle').open = true;
    document.getElementById('anthropic-api-key').focus();
    return;
  }

  showLoading(
    selected.length + '件の動画を分析中...',
    'タイトル・概要欄・タグからターゲット層とキーワードを抽出しています（30秒〜1分）'
  );

  try {
    const res = await fetch(API_BASE + '/analyze-selected', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ videos: selected, anthropicApiKey: anKey })
    });
    const data = await res.json();
    hideLoading();

    if (!data.success) {
      alert('エラー: ' + (data.error || '不明なエラー'));
      return;
    }

    renderAnalysisResults(data.data, selected.length + '件の動画');
  } catch (err) {
    hideLoading();
    alert('通信エラー: ' + err.message);
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

function copyReport() {
  const el = document.querySelector('.full-report');
  if (el) {
    navigator.clipboard.writeText(el.textContent).then(() => alert('コピーしました'));
  }
}

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
  loadApiKeys();
});
