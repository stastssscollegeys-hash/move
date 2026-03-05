"use strict";
// ============================================================
// Workflow Automation Service
// リマインダ配信 / 自動タグ付け / スコアリング / 条件分岐トリガー
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.generateUnsubscribeUrl = exports.unsubscribeContact = exports.addScore = exports.processReminders = exports.executeWorkflowsForEvent = exports.deleteWorkflow = exports.toggleWorkflow = exports.updateWorkflow = exports.createWorkflow = exports.listWorkflows = void 0;
const db_1 = require("./db");
// ============================================================
// CRUD
// ============================================================
async function listWorkflows(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('workflows').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listWorkflows = listWorkflows;
async function createWorkflow(userId, workflow) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('workflows').insert({
        user_id: userId, name: workflow.name,
        trigger: workflow.trigger, actions: workflow.actions || [],
        is_active: false, execution_count: 0,
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createWorkflow = createWorkflow;
async function updateWorkflow(workflowId, updates) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('workflows').update(updates).eq('id', workflowId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateWorkflow = updateWorkflow;
async function toggleWorkflow(workflowId, isActive) {
    return updateWorkflow(workflowId, { is_active: isActive });
}
exports.toggleWorkflow = toggleWorkflow;
async function deleteWorkflow(workflowId) {
    const db = (0, db_1.getSupabase)();
    const { error } = await db.from('workflows').delete().eq('id', workflowId);
    if (error)
        return { success: false, error: error.message };
    return { success: true };
}
exports.deleteWorkflow = deleteWorkflow;
// ============================================================
// Workflow Execution Engine
// ============================================================
async function executeWorkflowsForEvent(userId, eventType, contactId, eventData = {}) {
    const db = (0, db_1.getSupabase)();
    const { data: workflows } = await db.from('workflows').select('*')
        .eq('user_id', userId).eq('is_active', true);
    for (const workflow of (workflows || [])) {
        if (workflow.trigger?.type !== eventType)
            continue;
        // Check trigger config matches
        if (!matchesTriggerConfig(workflow.trigger, eventData))
            continue;
        // Execute actions
        await executeActions(db, userId, contactId, workflow.actions, eventData);
        // Increment execution count
        await db.from('workflows').update({
            execution_count: (workflow.execution_count || 0) + 1,
        }).eq('id', workflow.id);
    }
}
exports.executeWorkflowsForEvent = executeWorkflowsForEvent;
function matchesTriggerConfig(trigger, eventData) {
    const config = trigger.config || {};
    // Check specific trigger configs
    if (trigger.type === 'tag_added' && config.tag_name) {
        return eventData.tag_name === config.tag_name;
    }
    if (trigger.type === 'purchase' && config.product_id) {
        return eventData.product_id === config.product_id;
    }
    if (trigger.type === 'score_reached' && config.min_score) {
        return eventData.score >= config.min_score;
    }
    return true; // no specific config = always match
}
async function executeActions(db, userId, contactId, actions, eventData) {
    for (const action of actions) {
        switch (action.type) {
            case 'add_tag': {
                const tagName = action.config.tag_name;
                const { data: tag } = await db.from('tags').select('id').eq('user_id', userId).eq('name', tagName).single();
                if (tag) {
                    await db.from('contact_tags').upsert({ contact_id: contactId, tag_id: tag.id });
                }
                break;
            }
            case 'remove_tag': {
                const tagName = action.config.tag_name;
                const { data: tag } = await db.from('tags').select('id').eq('user_id', userId).eq('name', tagName).single();
                if (tag) {
                    await db.from('contact_tags').delete().eq('contact_id', contactId).eq('tag_id', tag.id);
                }
                break;
            }
            case 'add_score': {
                const points = action.config.points || 0;
                const { data: contact } = await db.from('contacts').select('score').eq('id', contactId).single();
                if (contact) {
                    await db.from('contacts').update({ score: (contact.score || 0) + points }).eq('id', contactId);
                }
                break;
            }
            case 'subtract_score': {
                const points = action.config.points || 0;
                const { data: contact } = await db.from('contacts').select('score').eq('id', contactId).single();
                if (contact) {
                    await db.from('contacts').update({ score: Math.max(0, (contact.score || 0) - points) }).eq('id', contactId);
                }
                break;
            }
            case 'enroll_course': {
                const courseId = action.config.course_id;
                if (courseId) {
                    await db.from('enrollments').upsert({ contact_id: contactId, course_id: courseId }, { onConflict: 'contact_id,course_id' });
                }
                break;
            }
            case 'start_scenario': {
                // Queue the contact into a scenario
                const scenarioType = action.config.scenario_type; // 'email' or 'line'
                const scenarioId = action.config.scenario_id;
                if (scenarioId) {
                    const table = scenarioType === 'line' ? 'line_send_logs' : 'email_send_logs';
                    await db.from(table).insert({
                        contact_id: contactId, scenario_id: scenarioId, status: 'queued',
                    });
                }
                break;
            }
            case 'wait': {
                // In production: use job queue with delay
                // For demo: no-op (actions after wait would need async scheduling)
                break;
            }
            case 'condition': {
                const cond = action.config;
                const { data: contact } = await db.from('contacts').select('*').eq('id', contactId).single();
                if (!contact)
                    break;
                const matches = evaluateCondition(contact, cond);
                const nextActions = matches ? cond.then_actions : cond.else_actions;
                if (nextActions?.length) {
                    await executeActions(db, userId, contactId, nextActions, eventData);
                }
                break;
            }
            case 'webhook': {
                const url = action.config.url;
                if (url) {
                    try {
                        await fetch(url, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ contact_id: contactId, event: eventData }),
                            signal: AbortSignal.timeout(10000),
                        });
                    }
                    catch { /* ignore webhook failures */ }
                }
                break;
            }
        }
    }
}
function evaluateCondition(contact, cond) {
    const val = contact[cond.field];
    switch (cond.operator) {
        case 'eq': return val === cond.value;
        case 'neq': return val !== cond.value;
        case 'gt': return typeof val === 'number' && val > Number(cond.value);
        case 'lt': return typeof val === 'number' && val < Number(cond.value);
        case 'contains': return typeof val === 'string' && val.includes(String(cond.value));
        default: return false;
    }
}
// ============================================================
// Reminder Service (イベント前自動リマインド)
// ============================================================
async function processReminders() {
    const db = (0, db_1.getSupabase)();
    const now = new Date();
    let sentCount = 0;
    // Get upcoming events with reminders enabled
    const { data: events } = await db.from('events').select('*')
        .eq('status', 'upcoming').gt('start_at', now.toISOString());
    for (const event of (events || [])) {
        const config = event.reminder_config;
        if (!config?.enabled || !config.timings?.length)
            continue;
        for (const minutesBefore of config.timings) {
            const triggerTime = new Date(new Date(event.start_at).getTime() - minutesBefore * 60000);
            const diff = Math.abs(now.getTime() - triggerTime.getTime());
            // Within 5 minutes of trigger time
            if (diff < 5 * 60000) {
                // Get reservations for this event
                const { data: reservations } = await db.from('event_reservations').select('contact_id, contacts(email, line_user_id, phone)')
                    .eq('event_id', event.id).eq('status', 'confirmed');
                for (const res of (reservations || [])) {
                    const contact = res.contacts;
                    if (!contact)
                        continue;
                    // Check if reminder already sent
                    const reminderKey = `${event.id}_${minutesBefore}_${res.contact_id}`;
                    const { data: existing } = await db.from('reminder_logs').select('id').eq('reminder_key', reminderKey).single();
                    if (existing)
                        continue;
                    // Send reminder via configured channels
                    for (const channel of (config.channels || [])) {
                        if (channel === 'email' && contact.email) {
                            await db.from('email_send_logs').insert({
                                contact_id: res.contact_id, status: 'queued',
                            });
                            sentCount++;
                        }
                        if (channel === 'line' && contact.line_user_id) {
                            await db.from('line_send_logs').insert({
                                contact_id: res.contact_id, status: 'queued',
                            });
                            sentCount++;
                        }
                    }
                    // Mark reminder as sent
                    await db.from('reminder_logs').insert({ reminder_key: reminderKey, event_id: event.id, contact_id: res.contact_id });
                }
            }
        }
    }
    return sentCount;
}
exports.processReminders = processReminders;
// ============================================================
// Auto Scoring (行動ベーススコアリング)
// ============================================================
const SCORE_RULES = {
    email_open: 5,
    email_click: 10,
    line_read: 3,
    page_view: 2,
    form_submit: 15,
    webinar_register: 20,
    webinar_attend: 30,
    purchase: 50,
    optin: 10,
};
async function addScore(contactId, action) {
    const points = SCORE_RULES[action] || 0;
    if (points === 0)
        return;
    const db = (0, db_1.getSupabase)();
    const { data: contact } = await db.from('contacts').select('score, user_id').eq('id', contactId).single();
    if (!contact)
        return;
    const newScore = (contact.score || 0) + points;
    await db.from('contacts').update({ score: newScore }).eq('id', contactId);
    // Check if score threshold workflows should fire
    await executeWorkflowsForEvent(contact.user_id, 'score_reached', contactId, { score: newScore });
}
exports.addScore = addScore;
// ============================================================
// Unsubscribe (配信停止 - 特定電子メール法準拠)
// ============================================================
async function unsubscribeContact(contactId, channel) {
    const db = (0, db_1.getSupabase)();
    if (channel === 'all' || channel === 'email') {
        await db.from('contacts').update({ status: 'unsubscribed' }).eq('id', contactId);
    }
    // Log unsubscribe event
    await db.from('conversion_events').insert({
        contact_id: contactId, event_type: 'unsubscribe',
        event_data: { channel }, occurred_at: new Date().toISOString(),
    });
    return { success: true };
}
exports.unsubscribeContact = unsubscribeContact;
function generateUnsubscribeUrl(contactId, baseUrl) {
    // Simple signed unsubscribe link (in production: use HMAC signature)
    const token = Buffer.from(`${contactId}:${Date.now()}`).toString('base64url');
    return `${baseUrl}/utage/api/unsubscribe?token=${token}&cid=${contactId}`;
}
exports.generateUnsubscribeUrl = generateUnsubscribeUrl;
