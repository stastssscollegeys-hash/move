"use strict";
// ============================================================
// Analytics & Tracking Service
// ============================================================
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.listWebhookLogs = exports.fireWebhook = exports.createWebhookEndpoint = exports.listWebhookEndpoints = exports.listFormSubmissions = exports.submitForm = exports.createForm = exports.listForms = exports.crossAnalysis = exports.getConversionStats = exports.trackConversion = exports.getClickStats = exports.trackClick = exports.incrementAdClick = exports.createAdTracking = exports.listAdTrackings = void 0;
const crypto_1 = __importDefault(require("crypto"));
const db_1 = require("./db");
// ============================================================
// Ad Tracking
// ============================================================
async function listAdTrackings(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('ad_trackings').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listAdTrackings = listAdTrackings;
async function createAdTracking(userId, tracking) {
    const db = (0, db_1.getSupabase)();
    const baseUrl = process.env.APP_URL || 'https://example.com';
    const trackingUrl = `${baseUrl}?utm_source=${encodeURIComponent(tracking.utm_source || '')}&utm_medium=${encodeURIComponent(tracking.utm_medium || '')}&utm_campaign=${encodeURIComponent(tracking.utm_campaign || '')}`;
    const { data, error } = await db.from('ad_trackings').insert({
        user_id: userId, name: tracking.name,
        utm_source: tracking.utm_source, utm_medium: tracking.utm_medium,
        utm_campaign: tracking.utm_campaign, utm_content: tracking.utm_content || null,
        tracking_url: trackingUrl,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createAdTracking = createAdTracking;
async function incrementAdClick(utmSource, utmMedium, utmCampaign) {
    const db = (0, db_1.getSupabase)();
    await db.rpc('increment_ad_click', { p_source: utmSource, p_medium: utmMedium, p_campaign: utmCampaign });
}
exports.incrementAdClick = incrementAdClick;
// ============================================================
// Link Click Tracking
// ============================================================
async function trackClick(contactId, url, sourceType, sourceId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('link_clicks').insert({
        contact_id: contactId, url, source_type: sourceType, source_id: sourceId,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.trackClick = trackClick;
async function getClickStats(userId, sourceType, period) {
    const db = (0, db_1.getSupabase)();
    let q = db.from('link_clicks').select('url, source_type, clicked_at');
    if (sourceType)
        q = q.eq('source_type', sourceType);
    if (period) {
        const since = new Date();
        if (period === '7d')
            since.setDate(since.getDate() - 7);
        else if (period === '30d')
            since.setDate(since.getDate() - 30);
        q = q.gte('clicked_at', since.toISOString());
    }
    const { data, error } = await q;
    if (error)
        return { success: false, error: error.message };
    // Aggregate by URL
    const stats = {};
    (data || []).forEach((c) => { stats[c.url] = (stats[c.url] || 0) + 1; });
    return { success: true, data: Object.entries(stats).map(([url, count]) => ({ url, count })).sort((a, b) => b.count - a.count) };
}
exports.getClickStats = getClickStats;
// ============================================================
// Conversion Events
// ============================================================
async function trackConversion(contactId, eventType, eventData, source, utm) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('conversion_events').insert({
        contact_id: contactId, event_type: eventType, event_data: eventData,
        source: source || null,
        utm_source: utm?.source || null, utm_medium: utm?.medium || null, utm_campaign: utm?.campaign || null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.trackConversion = trackConversion;
async function getConversionStats(userId, period) {
    const db = (0, db_1.getSupabase)();
    const since = new Date();
    if (period === '7d')
        since.setDate(since.getDate() - 7);
    else if (period === '30d')
        since.setDate(since.getDate() - 30);
    else if (period === '90d')
        since.setDate(since.getDate() - 90);
    const { data, error } = await db.from('conversion_events')
        .select('event_type, utm_source, occurred_at')
        .gte('occurred_at', since.toISOString());
    if (error)
        return { success: false, error: error.message };
    const byType = {};
    const bySource = {};
    (data || []).forEach((e) => {
        byType[e.event_type] = (byType[e.event_type] || 0) + 1;
        if (e.utm_source)
            bySource[e.utm_source] = (bySource[e.utm_source] || 0) + 1;
    });
    return { success: true, data: { by_type: byType, by_source: bySource, total: (data || []).length } };
}
exports.getConversionStats = getConversionStats;
// ============================================================
// Cross Analysis
// ============================================================
async function crossAnalysis(userId, query) {
    const db = (0, db_1.getSupabase)();
    const since = new Date();
    if (query.period === '7d')
        since.setDate(since.getDate() - 7);
    else if (query.period === '30d')
        since.setDate(since.getDate() - 30);
    else if (query.period === '90d')
        since.setDate(since.getDate() - 90);
    // Get conversion events
    const { data: events } = await db.from('conversion_events')
        .select('event_type, utm_source, utm_medium, utm_campaign, contact_id, event_data')
        .eq('event_type', query.axis_y)
        .gte('occurred_at', since.toISOString());
    // Get contacts for tag-based analysis
    const contactIds = [...new Set((events || []).map((e) => e.contact_id))];
    let contacts = [];
    if (query.axis_x === 'tag' && contactIds.length > 0) {
        const { data } = await db.from('contacts').select('id, contact_tags(tags(name))').in('id', contactIds);
        contacts = data || [];
    }
    // Build cross table
    const matrix = {};
    (events || []).forEach((e) => {
        let xValue = '';
        if (query.axis_x === 'utm_source')
            xValue = e.utm_source || 'direct';
        else if (query.axis_x === 'utm_medium')
            xValue = e.utm_medium || 'none';
        else if (query.axis_x === 'utm_campaign')
            xValue = e.utm_campaign || 'none';
        else if (query.axis_x === 'source')
            xValue = e.utm_source || 'direct';
        else if (query.axis_x === 'tag') {
            const contact = contacts.find((c) => c.id === e.contact_id);
            const tags = (contact?.contact_tags || []).map((ct) => ct.tags?.name).filter(Boolean);
            tags.forEach((t) => { matrix[t] = (matrix[t] || 0) + 1; });
            return;
        }
        matrix[xValue] = (matrix[xValue] || 0) + 1;
    });
    const labels = Object.keys(matrix);
    return {
        success: true,
        data: { labels, datasets: [{ label: query.axis_y, data: labels.map(l => matrix[l]) }] },
    };
}
exports.crossAnalysis = crossAnalysis;
// ============================================================
// Custom Forms
// ============================================================
async function listForms(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('custom_forms').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listForms = listForms;
async function createForm(userId, form) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('custom_forms').insert({
        user_id: userId, name: form.name, form_type: form.form_type || 'survey',
        fields: form.fields || [], thank_you_message: form.thank_you_message || 'ご回答ありがとうございます。',
        tag_on_submit: form.tag_on_submit || null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createForm = createForm;
async function submitForm(formId, contactId, responses) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('form_submissions').insert({
        form_id: formId, contact_id: contactId, responses,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    // Auto-tag on submit
    if (contactId) {
        const { data: form } = await db.from('custom_forms').select('tag_on_submit').eq('id', formId).single();
        if (form?.tag_on_submit) {
            const { data: tag } = await db.from('tags').select('id').eq('name', form.tag_on_submit).single();
            if (tag)
                await db.from('contact_tags').upsert({ contact_id: contactId, tag_id: tag.id });
        }
    }
    return { success: true, data };
}
exports.submitForm = submitForm;
async function listFormSubmissions(formId, page = 1, perPage = 20) {
    const db = (0, db_1.getSupabase)();
    const { data, error, count } = await db.from('form_submissions').select('*, contacts(name, email)', { count: 'exact' })
        .eq('form_id', formId).order('submitted_at', { ascending: false })
        .range((page - 1) * perPage, page * perPage - 1);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}
exports.listFormSubmissions = listFormSubmissions;
// ============================================================
// Webhooks
// ============================================================
async function listWebhookEndpoints(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webhook_endpoints').select('*').eq('user_id', userId);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listWebhookEndpoints = listWebhookEndpoints;
async function createWebhookEndpoint(userId, endpoint) {
    const db = (0, db_1.getSupabase)();
    const secret = `whsec_${crypto_1.default.randomBytes(24).toString('hex')}`;
    const { data, error } = await db.from('webhook_endpoints').insert({
        user_id: userId, name: endpoint.name, url: endpoint.url,
        events: endpoint.events || [], secret, is_active: true,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createWebhookEndpoint = createWebhookEndpoint;
async function fireWebhook(userId, event, payload) {
    const db = (0, db_1.getSupabase)();
    const { data: endpoints } = await db.from('webhook_endpoints').select('*')
        .eq('user_id', userId).eq('is_active', true)
        .contains('events', [event]);
    for (const ep of (endpoints || [])) {
        const body = JSON.stringify({ event, data: payload, timestamp: new Date().toISOString() });
        const signature = crypto_1.default.createHmac('sha256', ep.secret).update(body).digest('hex');
        try {
            const res = await fetch(ep.url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-Webhook-Signature': signature },
                body,
                signal: AbortSignal.timeout(10000),
            });
            await db.from('webhook_logs').insert({
                endpoint_id: ep.id, event, payload,
                response_status: res.status, response_body: (await res.text()).slice(0, 1000),
                delivered_at: new Date().toISOString(),
            });
        }
        catch (err) {
            await db.from('webhook_logs').insert({
                endpoint_id: ep.id, event, payload,
                response_status: null, response_body: err.message,
            });
        }
    }
}
exports.fireWebhook = fireWebhook;
async function listWebhookLogs(endpointId, page = 1, perPage = 20) {
    const db = (0, db_1.getSupabase)();
    const { data, error, count } = await db.from('webhook_logs').select('*', { count: 'exact' })
        .eq('endpoint_id', endpointId).order('created_at', { ascending: false })
        .range((page - 1) * perPage, page * perPage - 1);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}
exports.listWebhookLogs = listWebhookLogs;
