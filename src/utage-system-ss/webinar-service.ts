// ============================================================
// Webinar Service (Live / Auto / Evergreen)
// ============================================================

import type { Webinar, WebinarAttendee, WebinarChat, WebinarPoll, ApiResponse } from './types';

let supabase: any = null;
function getSupabase() {
  if (!supabase) {
    const { createClient } = require('@supabase/supabase-js');
    supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_KEY!);
  }
  return supabase;
}

// --- Webinars ---

export async function listWebinars(userId: string): Promise<ApiResponse<Webinar[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinars').select('*, webinar_attendees(id)').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data: (data || []).map((w: any) => ({ ...w, attendee_count: (w.webinar_attendees || []).length })) };
}

export async function createWebinar(userId: string, webinar: Partial<Webinar>): Promise<ApiResponse<Webinar>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinars').insert({
    user_id: userId, name: webinar.name, description: webinar.description || '',
    webinar_type: webinar.webinar_type || 'live',
    scheduled_at: webinar.scheduled_at || null,
    video_media_id: webinar.video_media_id || null,
    schedule_config: webinar.schedule_config || null,
    popup_offers: webinar.popup_offers || [],
    registration_page_id: webinar.registration_page_id || null,
    max_attendees: webinar.max_attendees || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function getWebinar(webinarId: string): Promise<ApiResponse<Webinar>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinars').select('*').eq('id', webinarId).single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateWebinar(webinarId: string, updates: Partial<Webinar>): Promise<ApiResponse<Webinar>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinars').update(updates).eq('id', webinarId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function startWebinar(webinarId: string): Promise<ApiResponse<Webinar>> {
  return updateWebinar(webinarId, { status: 'live' } as any);
}

export async function endWebinar(webinarId: string): Promise<ApiResponse<Webinar>> {
  return updateWebinar(webinarId, { status: 'ended' } as any);
}

// --- Attendees ---

export async function registerAttendee(webinarId: string, contactId: string): Promise<ApiResponse<WebinarAttendee>> {
  const db = getSupabase();

  // Check max attendees
  const { data: webinar } = await db.from('webinars').select('max_attendees').eq('id', webinarId).single();
  if (webinar?.max_attendees) {
    const { count } = await db.from('webinar_attendees').select('id', { count: 'exact', head: true }).eq('webinar_id', webinarId);
    if ((count || 0) >= webinar.max_attendees) return { success: false, error: '定員に達しています' };
  }

  const { data, error } = await db.from('webinar_attendees').upsert({
    webinar_id: webinarId, contact_id: contactId,
  }, { onConflict: 'webinar_id,contact_id' }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function joinWebinar(webinarId: string, contactId: string): Promise<ApiResponse<WebinarAttendee>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinar_attendees').update({
    status: 'attended', joined_at: new Date().toISOString(),
  }).eq('webinar_id', webinarId).eq('contact_id', contactId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function leaveWebinar(webinarId: string, contactId: string, watchedSeconds: number): Promise<ApiResponse<WebinarAttendee>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinar_attendees').update({
    left_at: new Date().toISOString(), watched_seconds: watchedSeconds,
  }).eq('webinar_id', webinarId).eq('contact_id', contactId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listAttendees(webinarId: string): Promise<ApiResponse<WebinarAttendee[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinar_attendees').select('*, contacts(name, email)').eq('webinar_id', webinarId).order('registered_at');
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Chat ---

export async function sendChatMessage(webinarId: string, contactId: string | null, message: string): Promise<ApiResponse<WebinarChat>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinar_chats').insert({
    webinar_id: webinarId, contact_id: contactId, message,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function listChatMessages(webinarId: string, afterId?: string): Promise<ApiResponse<WebinarChat[]>> {
  const db = getSupabase();
  let q = db.from('webinar_chats').select('*, contacts(name)').eq('webinar_id', webinarId).order('sent_at');
  if (afterId) {
    const { data: ref } = await db.from('webinar_chats').select('sent_at').eq('id', afterId).single();
    if (ref) q = q.gt('sent_at', ref.sent_at);
  }
  const { data, error } = await q.limit(100);
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Polls ---

export async function createPoll(webinarId: string, question: string, options: string[]): Promise<ApiResponse<WebinarPoll>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinar_polls').insert({
    webinar_id: webinarId, question, options, results: {}, is_active: true,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function votePoll(pollId: string, option: string): Promise<ApiResponse<WebinarPoll>> {
  const db = getSupabase();
  const { data: poll } = await db.from('webinar_polls').select('results, options').eq('id', pollId).single();
  if (!poll) return { success: false, error: 'Poll not found' };
  if (!poll.options.includes(option)) return { success: false, error: 'Invalid option' };

  const results = poll.results || {};
  results[option] = (results[option] || 0) + 1;

  const { data, error } = await db.from('webinar_polls').update({ results }).eq('id', pollId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function closePoll(pollId: string): Promise<ApiResponse<WebinarPoll>> {
  const db = getSupabase();
  const { data, error } = await db.from('webinar_polls').update({ is_active: false }).eq('id', pollId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// --- Popup Offers ---

export async function addPopupOffer(webinarId: string, offer: any): Promise<ApiResponse<Webinar>> {
  const db = getSupabase();
  const { data: webinar } = await db.from('webinars').select('popup_offers').eq('id', webinarId).single();
  const offers = [...(webinar?.popup_offers || []), { id: `offer-${Date.now()}`, ...offer }];
  const { data, error } = await db.from('webinars').update({ popup_offers: offers }).eq('id', webinarId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}
