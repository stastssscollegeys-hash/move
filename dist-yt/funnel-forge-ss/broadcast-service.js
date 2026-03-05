"use strict";
// ============================================================
// Broadcast Service (Email / LINE / SMS 一斉配信)
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.sendSmsBroadcast = exports.createSmsBroadcast = exports.listSmsBroadcasts = exports.sendLineBroadcast = exports.createLineBroadcast = exports.listLineBroadcasts = exports.sendEmailBroadcast = exports.scheduleEmailBroadcast = exports.createEmailBroadcast = exports.listEmailBroadcasts = void 0;
const db_1 = require("./db");
const service_1 = require("./service");
// ============================================================
// Email Broadcast
// ============================================================
async function listEmailBroadcasts(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('email_broadcasts').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listEmailBroadcasts = listEmailBroadcasts;
async function createEmailBroadcast(userId, broadcast) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('email_broadcasts').insert({
        user_id: userId, subject: broadcast.subject, body_html: broadcast.body_html,
        segment_id: broadcast.segment_id || null, status: 'draft',
        scheduled_at: broadcast.scheduled_at || null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createEmailBroadcast = createEmailBroadcast;
async function scheduleEmailBroadcast(broadcastId, scheduledAt) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('email_broadcasts').update({
        status: 'scheduled', scheduled_at: scheduledAt,
    }).eq('id', broadcastId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.scheduleEmailBroadcast = scheduleEmailBroadcast;
async function sendEmailBroadcast(broadcastId, userId) {
    const db = (0, db_1.getSupabase)();
    const { data: broadcast } = await db.from('email_broadcasts').select('*').eq('id', broadcastId).single();
    if (!broadcast)
        return { success: false, error: 'Broadcast not found' };
    // Get target contacts (with segment filtering)
    let contacts;
    if (broadcast.segment_id) {
        const { data: segment } = await db.from('segments').select('conditions, logic').eq('id', broadcast.segment_id).single();
        if (segment?.conditions) {
            const segResult = await (0, service_1.evaluateSegment)(userId, segment.conditions, segment.logic || 'AND');
            contacts = (segResult.data || []).filter((c) => c.email && c.status === 'active');
        }
        else {
            const { data: allContacts } = await db.from('contacts').select('id, email').eq('user_id', userId).eq('status', 'active').not('email', 'is', null);
            contacts = allContacts || [];
        }
    }
    else {
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
    if (error)
        return { success: false, error: error.message };
    // In production: enqueue emails to SES via job queue
    // For demo: just mark all as sent
    return { success: true, data: updated };
}
exports.sendEmailBroadcast = sendEmailBroadcast;
// ============================================================
// LINE Broadcast
// ============================================================
async function listLineBroadcasts(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('line_broadcasts').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listLineBroadcasts = listLineBroadcasts;
async function createLineBroadcast(userId, broadcast) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('line_broadcasts').insert({
        user_id: userId, message_type: broadcast.message_type || 'text',
        content: broadcast.content || {}, segment_id: broadcast.segment_id || null,
        status: 'draft', scheduled_at: broadcast.scheduled_at || null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createLineBroadcast = createLineBroadcast;
async function sendLineBroadcast(broadcastId, userId) {
    const db = (0, db_1.getSupabase)();
    const { data: broadcast } = await db.from('line_broadcasts').select('*').eq('id', broadcastId).single();
    if (!broadcast)
        return { success: false, error: 'Broadcast not found' };
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
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: updated };
}
exports.sendLineBroadcast = sendLineBroadcast;
// ============================================================
// SMS Broadcast
// ============================================================
async function listSmsBroadcasts(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('sms_broadcasts').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listSmsBroadcasts = listSmsBroadcasts;
async function createSmsBroadcast(userId, broadcast) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('sms_broadcasts').insert({
        user_id: userId, body: broadcast.body, segment_id: broadcast.segment_id || null,
        status: 'draft', scheduled_at: broadcast.scheduled_at || null,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createSmsBroadcast = createSmsBroadcast;
async function sendSmsBroadcast(broadcastId, userId) {
    const db = (0, db_1.getSupabase)();
    const { data: broadcast } = await db.from('sms_broadcasts').select('*').eq('id', broadcastId).single();
    if (!broadcast)
        return { success: false, error: 'Broadcast not found' };
    const { data: contacts } = await db.from('contacts').select('id, phone')
        .eq('user_id', userId).eq('status', 'active').not('phone', 'is', null);
    const targetContacts = contacts || [];
    // In production: call Twilio API to send SMS
    const { data: updated, error } = await db.from('sms_broadcasts').update({
        status: 'sent', sent_at: new Date().toISOString(), total_sent: targetContacts.length,
    }).eq('id', broadcastId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: updated };
}
exports.sendSmsBroadcast = sendSmsBroadcast;
