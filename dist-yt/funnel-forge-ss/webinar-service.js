"use strict";
// ============================================================
// Webinar Service (Live / Auto / Evergreen)
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.addPopupOffer = exports.closePoll = exports.votePoll = exports.createPoll = exports.listChatMessages = exports.sendChatMessage = exports.listAttendees = exports.leaveWebinar = exports.joinWebinar = exports.registerAttendee = exports.endWebinar = exports.startWebinar = exports.updateWebinar = exports.getWebinar = exports.createWebinar = exports.listWebinars = void 0;
const db_1 = require("./db");
// --- Webinars ---
async function listWebinars(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinars').select('*, webinar_attendees(id)').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: (data || []).map((w) => ({ ...w, attendee_count: (w.webinar_attendees || []).length })) };
}
exports.listWebinars = listWebinars;
async function createWebinar(userId, webinar) {
    const db = (0, db_1.getSupabase)();
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
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createWebinar = createWebinar;
async function getWebinar(webinarId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinars').select('*').eq('id', webinarId).single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.getWebinar = getWebinar;
async function updateWebinar(webinarId, updates) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinars').update(updates).eq('id', webinarId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateWebinar = updateWebinar;
async function startWebinar(webinarId) {
    return updateWebinar(webinarId, { status: 'live' });
}
exports.startWebinar = startWebinar;
async function endWebinar(webinarId) {
    return updateWebinar(webinarId, { status: 'ended' });
}
exports.endWebinar = endWebinar;
// --- Attendees ---
async function registerAttendee(webinarId, contactId) {
    const db = (0, db_1.getSupabase)();
    // Check max attendees
    const { data: webinar } = await db.from('webinars').select('max_attendees').eq('id', webinarId).single();
    if (webinar?.max_attendees) {
        const { count } = await db.from('webinar_attendees').select('id', { count: 'exact', head: true }).eq('webinar_id', webinarId);
        if ((count || 0) >= webinar.max_attendees)
            return { success: false, error: '定員に達しています' };
    }
    const { data, error } = await db.from('webinar_attendees').upsert({
        webinar_id: webinarId, contact_id: contactId,
    }, { onConflict: 'webinar_id,contact_id' }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.registerAttendee = registerAttendee;
async function joinWebinar(webinarId, contactId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinar_attendees').update({
        status: 'attended', joined_at: new Date().toISOString(),
    }).eq('webinar_id', webinarId).eq('contact_id', contactId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.joinWebinar = joinWebinar;
async function leaveWebinar(webinarId, contactId, watchedSeconds) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinar_attendees').update({
        left_at: new Date().toISOString(), watched_seconds: watchedSeconds,
    }).eq('webinar_id', webinarId).eq('contact_id', contactId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.leaveWebinar = leaveWebinar;
async function listAttendees(webinarId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinar_attendees').select('*, contacts(name, email)').eq('webinar_id', webinarId).order('registered_at');
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listAttendees = listAttendees;
// --- Chat ---
async function sendChatMessage(webinarId, contactId, message) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinar_chats').insert({
        webinar_id: webinarId, contact_id: contactId, message,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.sendChatMessage = sendChatMessage;
async function listChatMessages(webinarId, afterId) {
    const db = (0, db_1.getSupabase)();
    let q = db.from('webinar_chats').select('*, contacts(name)').eq('webinar_id', webinarId).order('sent_at');
    if (afterId) {
        const { data: ref } = await db.from('webinar_chats').select('sent_at').eq('id', afterId).single();
        if (ref)
            q = q.gt('sent_at', ref.sent_at);
    }
    const { data, error } = await q.limit(100);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listChatMessages = listChatMessages;
// --- Polls ---
async function createPoll(webinarId, question, options) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinar_polls').insert({
        webinar_id: webinarId, question, options, results: {}, is_active: true,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createPoll = createPoll;
async function votePoll(pollId, option) {
    const db = (0, db_1.getSupabase)();
    const { data: poll } = await db.from('webinar_polls').select('results, options').eq('id', pollId).single();
    if (!poll)
        return { success: false, error: 'Poll not found' };
    if (!poll.options.includes(option))
        return { success: false, error: 'Invalid option' };
    const results = poll.results || {};
    results[option] = (results[option] || 0) + 1;
    const { data, error } = await db.from('webinar_polls').update({ results }).eq('id', pollId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.votePoll = votePoll;
async function closePoll(pollId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('webinar_polls').update({ is_active: false }).eq('id', pollId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.closePoll = closePoll;
// --- Popup Offers ---
async function addPopupOffer(webinarId, offer) {
    const db = (0, db_1.getSupabase)();
    const { data: webinar } = await db.from('webinars').select('popup_offers').eq('id', webinarId).single();
    const offers = [...(webinar?.popup_offers || []), { id: `offer-${Date.now()}`, ...offer }];
    const { data, error } = await db.from('webinars').update({ popup_offers: offers }).eq('id', webinarId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.addPopupOffer = addPopupOffer;
