"use strict";
// ============================================================
// LINE Webhook Handler
// ============================================================
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.sendLineMessage = exports.handleWebhook = exports.verifySignature = void 0;
const crypto_1 = __importDefault(require("crypto"));
const db_1 = require("./db");
function getLineConfig() {
    return {
        channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN || '',
        channelSecret: process.env.LINE_CHANNEL_SECRET || '',
    };
}
// --- Signature Verification ---
function verifySignature(body, signature) {
    const { channelSecret } = getLineConfig();
    if (!channelSecret)
        return false;
    const hash = crypto_1.default.createHmac('SHA256', channelSecret).update(body).digest('base64');
    return hash === signature;
}
exports.verifySignature = verifySignature;
// --- Webhook Event Handler ---
async function handleWebhook(events) {
    const db = (0, db_1.getSupabase)();
    for (const event of events) {
        switch (event.type) {
            case 'follow': {
                // New friend added
                const lineUserId = event.source.userId;
                // Get profile
                const profile = await getProfile(lineUserId);
                // Create or update contact
                const { data: existing } = await db.from('contacts').select('id').eq('line_user_id', lineUserId).single();
                if (!existing) {
                    await db.from('contacts').insert({
                        line_user_id: lineUserId,
                        name: profile?.displayName || 'LINE User',
                        source: 'LINE',
                        status: 'active',
                    });
                }
                // Trigger follow scenario
                await triggerLineScenario(lineUserId, 'follow');
                break;
            }
            case 'unfollow': {
                const lineUserId = event.source.userId;
                await db.from('contacts').update({ status: 'blocked' }).eq('line_user_id', lineUserId);
                break;
            }
            case 'message': {
                const lineUserId = event.source.userId;
                if (event.message.type === 'text') {
                    // Store message in chat
                    const { data: contact } = await db.from('contacts').select('id').eq('line_user_id', lineUserId).single();
                    if (contact) {
                        await db.from('line_chat_messages').insert({
                            contact_id: contact.id,
                            direction: 'incoming',
                            message_type: 'text',
                            content: { text: event.message.text },
                        });
                    }
                    // Check for keyword triggers
                    await checkKeywordTrigger(lineUserId, event.message.text);
                }
                break;
            }
            case 'postback': {
                // Rich menu or button postback
                const lineUserId = event.source.userId;
                const postbackData = event.postback.data;
                // Parse action from postback data
                const params = new URLSearchParams(postbackData);
                const action = params.get('action');
                if (action === 'tag') {
                    const tagName = params.get('tag');
                    if (tagName) {
                        const { data: contact } = await db.from('contacts').select('id').eq('line_user_id', lineUserId).single();
                        const { data: tag } = await db.from('tags').select('id').eq('name', tagName).single();
                        if (contact && tag) {
                            await db.from('contact_tags').upsert({ contact_id: contact.id, tag_id: tag.id });
                        }
                    }
                }
                break;
            }
        }
    }
}
exports.handleWebhook = handleWebhook;
// --- LINE API Calls ---
async function getProfile(lineUserId) {
    const { channelAccessToken } = getLineConfig();
    if (!channelAccessToken)
        return null;
    try {
        const res = await fetch(`https://api.line.me/v2/bot/profile/${lineUserId}`, {
            headers: { 'Authorization': `Bearer ${channelAccessToken}` },
        });
        if (!res.ok)
            return null;
        return await res.json();
    }
    catch {
        return null;
    }
}
async function sendLineMessage(lineUserId, messages) {
    const { channelAccessToken } = getLineConfig();
    if (!channelAccessToken)
        return false;
    try {
        const res = await fetch('https://api.line.me/v2/bot/message/push', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${channelAccessToken}`,
            },
            body: JSON.stringify({ to: lineUserId, messages }),
        });
        return res.ok;
    }
    catch {
        return false;
    }
}
exports.sendLineMessage = sendLineMessage;
// --- Scenario Triggers ---
async function triggerLineScenario(lineUserId, triggerType) {
    const db = (0, db_1.getSupabase)();
    const { data: scenarios } = await db.from('line_scenarios').select('*, line_steps(*)')
        .eq('trigger_type', triggerType).eq('status', 'active');
    if (!scenarios?.length)
        return;
    for (const scenario of scenarios) {
        const steps = (scenario.line_steps || []).sort((a, b) => a.sort_order - b.sort_order);
        if (steps.length === 0)
            continue;
        // Send first step immediately
        const firstStep = steps[0];
        await sendStepMessage(lineUserId, firstStep);
        // Schedule remaining steps
        for (let i = 1; i < steps.length; i++) {
            const step = steps[i];
            if (step.delay_minutes > 0) {
                // In production, this would use a job queue (Temporal, BullMQ, etc.)
                // For now, use setTimeout as a simple demo
                setTimeout(() => sendStepMessage(lineUserId, step), step.delay_minutes * 60000);
            }
        }
    }
}
async function sendStepMessage(lineUserId, step) {
    const messages = [];
    if (step.message_type === 'text') {
        messages.push({ type: 'text', text: step.content?.text || '' });
    }
    else if (step.message_type === 'image') {
        messages.push({
            type: 'image',
            originalContentUrl: step.content?.image_url,
            previewImageUrl: step.content?.image_url,
        });
    }
    else if (step.message_type === 'flex') {
        messages.push({ type: 'flex', altText: step.content?.alt_text || 'Message', contents: step.content?.flex });
    }
    if (messages.length > 0) {
        const db = (0, db_1.getSupabase)();
        const sent = await sendLineMessage(lineUserId, messages);
        // Log
        const { data: contact } = await db.from('contacts').select('id').eq('line_user_id', lineUserId).single();
        if (contact) {
            await db.from('line_send_logs').insert({
                step_id: step.id, contact_id: contact.id,
                status: sent ? 'sent' : 'failed',
                sent_at: sent ? new Date().toISOString() : null,
            });
        }
    }
}
async function checkKeywordTrigger(lineUserId, text) {
    const db = (0, db_1.getSupabase)();
    const { data: scenarios } = await db.from('line_scenarios').select('*, line_steps(*)')
        .eq('trigger_type', 'keyword').eq('status', 'active');
    for (const scenario of (scenarios || [])) {
        const keywords = scenario.trigger_config?.keywords || [];
        if (keywords.some((kw) => text.includes(kw))) {
            await triggerLineScenario(lineUserId, 'keyword');
            break;
        }
    }
}
