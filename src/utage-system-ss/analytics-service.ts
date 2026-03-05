// ============================================================
// Analytics & Tracking Service
// ============================================================

import type { AdTracking, LinkClick, ConversionEvent, CrossAnalysisQuery, CrossAnalysisResult, CustomForm, FormSubmission, WebhookEndpoint, WebhookLog, ApiResponse } from './types';
import crypto from 'crypto';

import { getSupabase } from './db';

// ============================================================
// Ad Tracking
// ============================================================

export async function listAdTrackings(userId: string): Promise<ApiResponse<AdTracking[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('ad_trackings').select('*').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createAdTracking(userId: string, tracking: Partial<AdTracking>): Promise<ApiResponse<AdTracking>> {
  const db = getSupabase();
  const baseUrl = process.env.APP_URL || 'https://example.com';
  const trackingUrl = `${baseUrl}?utm_source=${encodeURIComponent(tracking.utm_source || '')}&utm_medium=${encodeURIComponent(tracking.utm_medium || '')}&utm_campaign=${encodeURIComponent(tracking.utm_campaign || '')}`;

  const { data, error } = await db.from('ad_trackings').insert({
    user_id: userId, name: tracking.name,
    utm_source: tracking.utm_source, utm_medium: tracking.utm_medium,
    utm_campaign: tracking.utm_campaign, utm_content: tracking.utm_content || null,
    tracking_url: trackingUrl,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function incrementAdClick(utmSource: string, utmMedium: string, utmCampaign: string): Promise<void> {
  const db = getSupabase();
  await db.rpc('increment_ad_click', { p_source: utmSource, p_medium: utmMedium, p_campaign: utmCampaign });
}

// ============================================================
// Link Click Tracking
// ============================================================

export async function trackClick(contactId: string | null, url: string, sourceType: string, sourceId: string): Promise<ApiResponse<LinkClick>> {
  const db = getSupabase();
  const { data, error } = await db.from('link_clicks').insert({
    contact_id: contactId, url, source_type: sourceType, source_id: sourceId,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function getClickStats(userId: string, sourceType?: string, period?: string): Promise<ApiResponse<any>> {
  const db = getSupabase();
  let q = db.from('link_clicks').select('url, source_type, clicked_at');
  if (sourceType) q = q.eq('source_type', sourceType);
  if (period) {
    const since = new Date();
    if (period === '7d') since.setDate(since.getDate() - 7);
    else if (period === '30d') since.setDate(since.getDate() - 30);
    q = q.gte('clicked_at', since.toISOString());
  }
  const { data, error } = await q;
  if (error) return { success: false, error: error.message };

  // Aggregate by URL
  const stats: Record<string, number> = {};
  (data || []).forEach((c: any) => { stats[c.url] = (stats[c.url] || 0) + 1; });
  return { success: true, data: Object.entries(stats).map(([url, count]) => ({ url, count })).sort((a, b) => b.count - a.count) };
}

// ============================================================
// Conversion Events
// ============================================================

export async function trackConversion(contactId: string, eventType: string, eventData: Record<string, unknown>, source?: string, utm?: { source?: string; medium?: string; campaign?: string }): Promise<ApiResponse<ConversionEvent>> {
  const db = getSupabase();
  const { data, error } = await db.from('conversion_events').insert({
    contact_id: contactId, event_type: eventType, event_data: eventData,
    source: source || null,
    utm_source: utm?.source || null, utm_medium: utm?.medium || null, utm_campaign: utm?.campaign || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function getConversionStats(userId: string, period: string): Promise<ApiResponse<any>> {
  const db = getSupabase();
  const since = new Date();
  if (period === '7d') since.setDate(since.getDate() - 7);
  else if (period === '30d') since.setDate(since.getDate() - 30);
  else if (period === '90d') since.setDate(since.getDate() - 90);

  const { data, error } = await db.from('conversion_events')
    .select('event_type, utm_source, occurred_at')
    .gte('occurred_at', since.toISOString());
  if (error) return { success: false, error: error.message };

  const byType: Record<string, number> = {};
  const bySource: Record<string, number> = {};
  (data || []).forEach((e: any) => {
    byType[e.event_type] = (byType[e.event_type] || 0) + 1;
    if (e.utm_source) bySource[e.utm_source] = (bySource[e.utm_source] || 0) + 1;
  });

  return { success: true, data: { by_type: byType, by_source: bySource, total: (data || []).length } };
}

// ============================================================
// Cross Analysis
// ============================================================

export async function crossAnalysis(userId: string, query: CrossAnalysisQuery): Promise<ApiResponse<CrossAnalysisResult>> {
  const db = getSupabase();
  const since = new Date();
  if (query.period === '7d') since.setDate(since.getDate() - 7);
  else if (query.period === '30d') since.setDate(since.getDate() - 30);
  else if (query.period === '90d') since.setDate(since.getDate() - 90);

  // Get conversion events
  const { data: events } = await db.from('conversion_events')
    .select('event_type, utm_source, utm_medium, utm_campaign, contact_id, event_data')
    .eq('event_type', query.axis_y)
    .gte('occurred_at', since.toISOString());

  // Get contacts for tag-based analysis
  const contactIds = [...new Set((events || []).map((e: any) => e.contact_id))];
  let contacts: any[] = [];
  if (query.axis_x === 'tag' && contactIds.length > 0) {
    const { data } = await db.from('contacts').select('id, contact_tags(tags(name))').in('id', contactIds);
    contacts = data || [];
  }

  // Build cross table
  const matrix: Record<string, number> = {};
  (events || []).forEach((e: any) => {
    let xValue = '';
    if (query.axis_x === 'utm_source') xValue = e.utm_source || 'direct';
    else if (query.axis_x === 'utm_medium') xValue = e.utm_medium || 'none';
    else if (query.axis_x === 'utm_campaign') xValue = e.utm_campaign || 'none';
    else if (query.axis_x === 'source') xValue = e.utm_source || 'direct';
    else if (query.axis_x === 'tag') {
      const contact = contacts.find((c: any) => c.id === e.contact_id);
      const tags = (contact?.contact_tags || []).map((ct: any) => ct.tags?.name).filter(Boolean);
      tags.forEach((t: string) => { matrix[t] = (matrix[t] || 0) + 1; });
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

// ============================================================
// Custom Forms
// ============================================================

export async function listForms(userId: string): Promise<ApiResponse<CustomForm[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('custom_forms').select('*').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createForm(userId: string, form: Partial<CustomForm>): Promise<ApiResponse<CustomForm>> {
  const db = getSupabase();
  const { data, error } = await db.from('custom_forms').insert({
    user_id: userId, name: form.name, form_type: form.form_type || 'survey',
    fields: form.fields || [], thank_you_message: form.thank_you_message || 'ご回答ありがとうございます。',
    tag_on_submit: form.tag_on_submit || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function submitForm(formId: string, contactId: string | null, responses: Record<string, string>): Promise<ApiResponse<FormSubmission>> {
  const db = getSupabase();
  const { data, error } = await db.from('form_submissions').insert({
    form_id: formId, contact_id: contactId, responses,
  }).select().single();
  if (error) return { success: false, error: error.message };

  // Auto-tag on submit
  if (contactId) {
    const { data: form } = await db.from('custom_forms').select('tag_on_submit').eq('id', formId).single();
    if (form?.tag_on_submit) {
      const { data: tag } = await db.from('tags').select('id').eq('name', form.tag_on_submit).single();
      if (tag) await db.from('contact_tags').upsert({ contact_id: contactId, tag_id: tag.id });
    }
  }

  return { success: true, data };
}

export async function listFormSubmissions(formId: string, page = 1, perPage = 20): Promise<ApiResponse<FormSubmission[]>> {
  const db = getSupabase();
  const { data, error, count } = await db.from('form_submissions').select('*, contacts(name, email)', { count: 'exact' })
    .eq('form_id', formId).order('submitted_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1);
  if (error) return { success: false, error: error.message };
  return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}

// ============================================================
// Webhooks
// ============================================================

export async function listWebhookEndpoints(userId: string): Promise<ApiResponse<WebhookEndpoint[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('webhook_endpoints').select('*').eq('user_id', userId);
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createWebhookEndpoint(userId: string, endpoint: Partial<WebhookEndpoint>): Promise<ApiResponse<WebhookEndpoint>> {
  const db = getSupabase();
  const secret = `whsec_${crypto.randomBytes(24).toString('hex')}`;
  const { data, error } = await db.from('webhook_endpoints').insert({
    user_id: userId, name: endpoint.name, url: endpoint.url,
    events: endpoint.events || [], secret, is_active: true,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function fireWebhook(userId: string, event: string, payload: Record<string, unknown>): Promise<void> {
  const db = getSupabase();
  const { data: endpoints } = await db.from('webhook_endpoints').select('*')
    .eq('user_id', userId).eq('is_active', true)
    .contains('events', [event]);

  for (const ep of (endpoints || [])) {
    const body = JSON.stringify({ event, data: payload, timestamp: new Date().toISOString() });
    const signature = crypto.createHmac('sha256', ep.secret).update(body).digest('hex');

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
    } catch (err: any) {
      await db.from('webhook_logs').insert({
        endpoint_id: ep.id, event, payload,
        response_status: null, response_body: err.message,
      });
    }
  }
}

export async function listWebhookLogs(endpointId: string, page = 1, perPage = 20): Promise<ApiResponse<WebhookLog[]>> {
  const db = getSupabase();
  const { data, error, count } = await db.from('webhook_logs').select('*', { count: 'exact' })
    .eq('endpoint_id', endpointId).order('created_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1);
  if (error) return { success: false, error: error.message };
  return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}
