// ============================================================
// Broadcast Service (Email / LINE / SMS 一斉配信)
// ============================================================

import type { EmailBroadcast, LineBroadcast, SmsBroadcast, SegmentCondition, ApiResponse } from './types';
import { getSupabase } from './db';
import { evaluateSegment } from './service';

// ============================================================
// Email Broadcast
// ============================================================

export async function listEmailBroadcasts(userId: string): Promise<ApiResponse<EmailBroadcast[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('email_broadcasts').select('*').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createEmailBroadcast(userId: string, broadcast: Partial<EmailBroadcast>): Promise<ApiResponse<EmailBroadcast>> {
  const db = getSupabase();
  const { data, error } = await db.from('email_broadcasts').insert({
    user_id: userId, subject: broadcast.subject, body_html: broadcast.body_html,
    segment_id: broadcast.segment_id || null, status: 'draft',
    scheduled_at: broadcast.scheduled_at || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function scheduleEmailBroadcast(broadcastId: string, scheduledAt: string): Promise<ApiResponse<EmailBroadcast>> {
  const db = getSupabase();
  const { data, error } = await db.from('email_broadcasts').update({
    status: 'scheduled', scheduled_at: scheduledAt,
  }).eq('id', broadcastId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function sendEmailBroadcast(broadcastId: string, userId: string): Promise<ApiResponse<EmailBroadcast>> {
  const db = getSupabase();

  const { data: broadcast } = await db.from('email_broadcasts').select('*').eq('id', broadcastId).single();
  if (!broadcast) return { success: false, error: 'Broadcast not found' };

  // Get target contacts (with segment filtering)
  let contacts: any[];
  if (broadcast.segment_id) {
    const { data: segment } = await db.from('segments').select('conditions, logic').eq('id', broadcast.segment_id).single();
    if (segment?.conditions) {
      const segResult = await evaluateSegment(userId, segment.conditions, segment.logic || 'AND');
      contacts = (segResult.data || []).filter((c: any) => c.email && c.status === 'active');
    } else {
      const { data: allContacts } = await db.from('contacts').select('id, email').eq('user_id', userId).eq('status', 'active').not('email', 'is', null);
      contacts = allContacts || [];
    }
  } else {
    const { data: allContacts } = await db.from('contacts').select('id, email').eq('user_id', userId).eq('status', 'active').not('email', 'is', null);
    contacts = allContacts || [];
  }

  // Create send logs
  for (const contact of contacts) {
    await db.from('email_send_logs').insert({
      contact_id: contact.id, broadcast_id: broadcastId,
      status: 'queued',
    });
  }

  // Update broadcast status
  const { data: updated, error } = await db.from('email_broadcasts').update({
    status: 'sent', sent_at: new Date().toISOString(),
    total_sent: contacts.length,
  }).eq('id', broadcastId).select().single();
  if (error) return { success: false, error: error.message };

  // In production: enqueue emails to SES via job queue
  // For demo: just mark all as sent
  return { success: true, data: updated };
}

// ============================================================
// LINE Broadcast
// ============================================================

export async function listLineBroadcasts(userId: string): Promise<ApiResponse<LineBroadcast[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('line_broadcasts').select('*').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createLineBroadcast(userId: string, broadcast: Partial<LineBroadcast>): Promise<ApiResponse<LineBroadcast>> {
  const db = getSupabase();
  const { data, error } = await db.from('line_broadcasts').insert({
    user_id: userId, message_type: broadcast.message_type || 'text',
    content: broadcast.content || {}, segment_id: broadcast.segment_id || null,
    status: 'draft', scheduled_at: broadcast.scheduled_at || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function sendLineBroadcast(broadcastId: string, userId: string): Promise<ApiResponse<LineBroadcast>> {
  const db = getSupabase();

  const { data: broadcast } = await db.from('line_broadcasts').select('*').eq('id', broadcastId).single();
  if (!broadcast) return { success: false, error: 'Broadcast not found' };

  // Get target contacts with LINE user ID
  const { data: contacts } = await db.from('contacts').select('id, line_user_id')
    .eq('user_id', userId).eq('status', 'active').not('line_user_id', 'is', null);

  const targetContacts = contacts || [];

  // Create send logs
  for (const contact of targetContacts) {
    await db.from('line_send_logs').insert({
      contact_id: contact.id, broadcast_id: broadcastId, status: 'queued',
    });
  }

  // In production: call LINE Messaging API multicast endpoint
  const { data: updated, error } = await db.from('line_broadcasts').update({
    status: 'sent', sent_at: new Date().toISOString(), total_sent: targetContacts.length,
  }).eq('id', broadcastId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: updated };
}

// ============================================================
// SMS Broadcast
// ============================================================

export async function listSmsBroadcasts(userId: string): Promise<ApiResponse<SmsBroadcast[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('sms_broadcasts').select('*').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createSmsBroadcast(userId: string, broadcast: Partial<SmsBroadcast>): Promise<ApiResponse<SmsBroadcast>> {
  const db = getSupabase();
  const { data, error } = await db.from('sms_broadcasts').insert({
    user_id: userId, body: broadcast.body, segment_id: broadcast.segment_id || null,
    status: 'draft', scheduled_at: broadcast.scheduled_at || null,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function sendSmsBroadcast(broadcastId: string, userId: string): Promise<ApiResponse<SmsBroadcast>> {
  const db = getSupabase();

  const { data: broadcast } = await db.from('sms_broadcasts').select('*').eq('id', broadcastId).single();
  if (!broadcast) return { success: false, error: 'Broadcast not found' };

  const { data: contacts } = await db.from('contacts').select('id, phone')
    .eq('user_id', userId).eq('status', 'active').not('phone', 'is', null);

  const targetContacts = contacts || [];

  // In production: call Twilio API to send SMS
  const { data: updated, error } = await db.from('sms_broadcasts').update({
    status: 'sent', sent_at: new Date().toISOString(), total_sent: targetContacts.length,
  }).eq('id', broadcastId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: updated };
}
