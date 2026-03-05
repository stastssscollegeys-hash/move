"use strict";
// ============================================================
// Funnel Page HTML Renderer & A/B Test Engine
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.servePublishedPage = exports.renderPage = exports.recordVariantConversion = exports.recordVariantView = exports.selectVariant = void 0;
const db_1 = require("./db");
// ============================================================
// A/B Test: Variant Selection
// ============================================================
function selectVariant(page, visitorId) {
    if (!page.ab_variants?.length) {
        return { elements: page.elements, variantId: null };
    }
    // Deterministic selection based on visitor ID (consistent experience)
    const hash = simpleHash(visitorId + page.id);
    const totalWeight = page.ab_variants.reduce((sum, v) => sum + v.weight, 0);
    let target = hash % totalWeight;
    for (const variant of page.ab_variants) {
        target -= variant.weight;
        if (target < 0) {
            return { elements: variant.elements, variantId: variant.id };
        }
    }
    // Fallback to original
    return { elements: page.elements, variantId: null };
}
exports.selectVariant = selectVariant;
function simpleHash(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash |= 0;
    }
    return Math.abs(hash);
}
// Record A/B test view
async function recordVariantView(pageId, variantId) {
    if (!variantId)
        return;
    const db = (0, db_1.getSupabase)();
    // In production: use atomic increment via RPC
    const { data: page } = await db.from('funnel_pages').select('ab_variants').eq('id', pageId).single();
    if (!page?.ab_variants)
        return;
    const variants = page.ab_variants.map((v) => {
        if (v.id === variantId)
            return { ...v, views: (v.views || 0) + 1 };
        return v;
    });
    await db.from('funnel_pages').update({ ab_variants: variants }).eq('id', pageId);
}
exports.recordVariantView = recordVariantView;
async function recordVariantConversion(pageId, variantId) {
    if (!variantId)
        return;
    const db = (0, db_1.getSupabase)();
    const { data: page } = await db.from('funnel_pages').select('ab_variants').eq('id', pageId).single();
    if (!page?.ab_variants)
        return;
    const variants = page.ab_variants.map((v) => {
        if (v.id === variantId)
            return { ...v, conversions: (v.conversions || 0) + 1 };
        return v;
    });
    await db.from('funnel_pages').update({ ab_variants: variants }).eq('id', pageId);
}
exports.recordVariantConversion = recordVariantConversion;
// ============================================================
// Funnel Page HTML Renderer
// ============================================================
function renderPage(page, elements) {
    const bodyHtml = elements.map(el => renderElement(el)).join('\n');
    return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${escapeHtml(page.seo_title || page.title)}</title>
  ${page.seo_description ? `<meta name="description" content="${escapeHtml(page.seo_description)}">` : ''}
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Hiragino Sans', 'Segoe UI', sans-serif; line-height: 1.6; color: #333; }
    .page-container { max-width: 960px; margin: 0 auto; padding: 20px; }
    .el-text { margin-bottom: 16px; }
    .el-text h1 { font-size: 2em; margin-bottom: 12px; }
    .el-text h2 { font-size: 1.5em; margin-bottom: 10px; }
    .el-text p { margin-bottom: 8px; }
    .el-image { margin-bottom: 16px; text-align: center; }
    .el-image img { max-width: 100%; height: auto; border-radius: 8px; }
    .el-video { margin-bottom: 16px; text-align: center; }
    .el-video iframe { max-width: 100%; aspect-ratio: 16/9; border: none; border-radius: 8px; }
    .el-button { margin-bottom: 16px; text-align: center; }
    .el-button a {
      display: inline-block; padding: 16px 40px; font-size: 18px; font-weight: 700;
      color: #fff; background: #E74C3C; border-radius: 8px; text-decoration: none;
      transition: background 0.2s; cursor: pointer;
    }
    .el-button a:hover { background: #C0392B; }
    .el-form { margin-bottom: 24px; padding: 24px; background: #f8f9fa; border-radius: 12px; }
    .el-form input, .el-form select { display: block; width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #ddd; border-radius: 6px; font-size: 16px; }
    .el-form button { display: block; width: 100%; padding: 14px; background: #27AE60; color: #fff; border: none; border-radius: 6px; font-size: 18px; font-weight: 700; cursor: pointer; }
    .el-countdown { text-align: center; margin-bottom: 16px; padding: 16px; background: #FEF3C7; border-radius: 8px; font-size: 24px; font-weight: 700; color: #92400E; }
    .el-spacer { height: 32px; }
    .el-divider { border-top: 1px solid #e0e0e0; margin: 24px 0; }
    .el-progress { margin-bottom: 16px; }
    .el-progress-bar { height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; }
    .el-progress-fill { height: 100%; background: #3498DB; border-radius: 4px; }
    .el-accordion { margin-bottom: 16px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }
    .el-accordion summary { padding: 16px; font-weight: 700; cursor: pointer; background: #f8f9fa; }
    .el-accordion .content { padding: 16px; }
    .el-payment-form { background: #f0f7ff; padding: 24px; border-radius: 12px; margin-bottom: 24px; }
    .el-line-btn { text-align: center; margin-bottom: 16px; }
    .el-line-btn a { display: inline-block; padding: 14px 32px; background: #00B900; color: #fff; border-radius: 8px; font-weight: 700; text-decoration: none; }
  </style>
</head>
<body>
  <div class="page-container">
    ${bodyHtml}
  </div>
  ${page.popup_config?.enabled ? renderPopup(page.popup_config) : ''}
  <script>
  // Countdown timers
  document.querySelectorAll('.el-countdown[data-end]').forEach(el => {
    const end = new Date(el.dataset.end).getTime();
    if (!end) return;
    function tick() {
      const diff = end - Date.now();
      if (diff <= 0) { el.textContent = '終了しました'; return; }
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      el.textContent = (d > 0 ? d + '日 ' : '') + h + '時間 ' + m + '分 ' + s + '秒';
    }
    tick();
    setInterval(tick, 1000);
  });
  </script>
</body>
</html>`;
}
exports.renderPage = renderPage;
function renderElement(el) {
    const p = el.props;
    switch (el.type) {
        case 'text':
            return `<div class="el-text">${p.html || escapeHtml(String(p.text || ''))}</div>`;
        case 'image':
            return `<div class="el-image"><img src="${escapeHtml(String(p.src || ''))}" alt="${escapeHtml(String(p.alt || ''))}"></div>`;
        case 'video':
            if (String(p.url || '').includes('youtube')) {
                const vid = extractYouTubeId(String(p.url));
                return `<div class="el-video"><iframe width="560" height="315" src="https://www.youtube.com/embed/${vid}" allowfullscreen></iframe></div>`;
            }
            return `<div class="el-video"><video src="${escapeHtml(String(p.url || ''))}" controls style="max-width:100%"></video></div>`;
        case 'button':
            return `<div class="el-button"><a href="${escapeHtml(String(p.url || '#'))}" ${p.new_tab ? 'target="_blank"' : ''}>${escapeHtml(String(p.text || 'Click'))}</a></div>`;
        case 'form':
            return renderFormElement(p);
        case 'countdown':
            return `<div class="el-countdown" data-end="${escapeHtml(String(p.end_time || ''))}">${escapeHtml(String(p.text || '残り時間'))}</div>`;
        case 'spacer':
            return `<div class="el-spacer" style="height:${p.height || 32}px"></div>`;
        case 'divider':
            return '<div class="el-divider"></div>';
        case 'progress_bar':
            return `<div class="el-progress"><div class="el-progress-bar"><div class="el-progress-fill" style="width:${p.percent || 0}%"></div></div></div>`;
        case 'accordion':
            return `<details class="el-accordion"><summary>${escapeHtml(String(p.title || ''))}</summary><div class="content">${p.content_html || escapeHtml(String(p.content || ''))}</div></details>`;
        case 'line_add_button':
            return `<div class="el-line-btn"><a href="${escapeHtml(String(p.url || ''))}" target="_blank">LINE友だち追加</a></div>`;
        case 'payment_form':
            return `<div class="el-payment-form"><h3>${escapeHtml(String(p.product_name || '商品'))}</h3><p>¥${Number(p.price || 0).toLocaleString()}</p><button onclick="location.href='${escapeHtml(String(p.checkout_url || '#'))}'">購入する</button></div>`;
        case 'order_bump':
            return `<div style="border:2px dashed #F39C12;padding:16px;margin:16px 0;border-radius:8px"><label><input type="checkbox"> <strong>${escapeHtml(String(p.title || 'こちらも追加'))}</strong> - ¥${Number(p.price || 0).toLocaleString()}</label><p style="font-size:14px;color:#666;margin-top:8px">${escapeHtml(String(p.description || ''))}</p></div>`;
        default:
            return `<!-- unknown element: ${el.type} -->`;
    }
}
function renderFormElement(p) {
    const fields = p.fields || [
        { type: 'text', name: 'name', label: 'お名前', required: true },
        { type: 'email', name: 'email', label: 'メールアドレス', required: true },
    ];
    const fieldHtml = fields.map((f) => `<input type="${f.type || 'text'}" name="${escapeHtml(f.name)}" placeholder="${escapeHtml(f.label)}" ${f.required ? 'required' : ''}>`).join('\n');
    return `<div class="el-form"><form method="POST" action="${escapeHtml(String(p.action || ''))}">${fieldHtml}<button type="submit">${escapeHtml(String(p.submit_text || '送信'))}</button></form></div>`;
}
function renderPopup(config) {
    const triggerJs = config.trigger === 'timer'
        ? `setTimeout(showPopup, ${(config.trigger_value || 5) * 1000})`
        : config.trigger === 'exit_intent'
            ? `document.addEventListener('mouseleave',e=>{if(e.clientY<0)showPopup()},{once:true})`
            : '';
    return `
<div id="page-popup" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;justify-content:center;align-items:center">
  <div style="background:#fff;padding:32px;border-radius:12px;max-width:500px;width:90%;position:relative">
    <button onclick="document.getElementById('page-popup').style.display='none'" style="position:absolute;top:12px;right:12px;border:none;background:none;font-size:24px;cursor:pointer">&times;</button>
    <div>${(config.content_elements || []).map((el) => renderElement(el)).join('')}</div>
  </div>
</div>
<script>function showPopup(){document.getElementById('page-popup').style.display='flex'}${triggerJs}</script>`;
}
function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function extractYouTubeId(url) {
    const m = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|embed\/))([a-zA-Z0-9_-]{11})/);
    return m ? m[1] : '';
}
// ============================================================
// Serve Published Page
// ============================================================
async function servePublishedPage(slug, visitorId) {
    const db = (0, db_1.getSupabase)();
    const { data: page } = await db.from('funnel_pages').select('*').eq('slug', slug).single();
    if (!page)
        return { success: false, error: 'Page not found' };
    // Check expiry
    if (page.expires_at && new Date(page.expires_at) < new Date()) {
        return { success: false, error: 'This page has expired' };
    }
    // A/B test variant selection
    const { elements, variantId } = selectVariant(page, visitorId);
    // Record page view
    await db.from('page_views').insert({
        page_id: page.id, visitor_id: visitorId,
        variant_id: variantId, viewed_at: new Date().toISOString(),
    });
    // Record A/B view
    if (variantId)
        await recordVariantView(page.id, variantId);
    const html = renderPage(page, elements);
    return { success: true, data: html };
}
exports.servePublishedPage = servePublishedPage;
