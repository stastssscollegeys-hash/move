// ============================================================
// Workflow Automation Service
// リマインダ配信 / 自動タグ付け / スコアリング / 条件分岐トリガー
// ============================================================

import type { ApiResponse } from './types';
import { getSupabase } from './db';

// ============================================================
// Workflow Definitions
// ============================================================

export interface WorkflowTrigger {
  type: 'tag_added' | 'tag_removed' | 'purchase' | 'optin' | 'page_view'
    | 'email_opened' | 'email_clicked' | 'line_follow' | 'form_submit'
    | 'webinar_register' | 'webinar_attend' | 'score_reached' | 'date_trigger';
  config: Record<string, unknown>;
}

export interface WorkflowAction {
  type: 'add_tag' | 'remove_tag' | 'send_email' | 'send_line' | 'send_sms'
    | 'add_score' | 'subtract_score' | 'enroll_course' | 'start_scenario'
    | 'webhook' | 'wait' | 'condition';
  config: Record<string, unknown>;
}

export interface WorkflowCondition {
  field: string;
  operator: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'has_tag' | 'no_tag';
  value: string | number;
  then_actions: WorkflowAction[];
  else_actions: WorkflowAction[];
}

export interface Workflow {
  id: string;
  user_id: string;
  name: string;
  trigger: WorkflowTrigger;
  actions: WorkflowAction[];
  is_active: boolean;
  execution_count: number;
  created_at: string;
  updated_at: string;
}

// ============================================================
// CRUD
// ============================================================

export async function listWorkflows(userId: string): Promise<ApiResponse<Workflow[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('workflows').select('*').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createWorkflow(userId: string, workflow: Partial<Workflow>): Promise<ApiResponse<Workflow>> {
  const db = getSupabase();
  const { data, error } = await db.from('workflows').insert({
    user_id: userId, name: workflow.name,
    trigger: workflow.trigger, actions: workflow.actions || [],
    is_active: false, execution_count: 0,
  }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateWorkflow(workflowId: string, updates: Partial<Workflow>): Promise<ApiResponse<Workflow>> {
  const db = getSupabase();
  const { data, error } = await db.from('workflows').update(updates).eq('id', workflowId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function toggleWorkflow(workflowId: string, isActive: boolean): Promise<ApiResponse<Workflow>> {
  return updateWorkflow(workflowId, { is_active: isActive } as any);
}

export async function deleteWorkflow(workflowId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  const { error } = await db.from('workflows').delete().eq('id', workflowId);
  if (error) return { success: false, error: error.message };
  return { success: true };
}

// ============================================================
// Workflow Execution Engine
// ============================================================

export async function executeWorkflowsForEvent(
  userId: string,
  eventType: WorkflowTrigger['type'],
  contactId: string,
  eventData: Record<string, unknown> = {},
): Promise<void> {
  const db = getSupabase();

  const { data: workflows } = await db.from('workflows').select('*')
    .eq('user_id', userId).eq('is_active', true);

  for (const workflow of (workflows || [])) {
    if (workflow.trigger?.type !== eventType) continue;

    // Check trigger config matches
    if (!matchesTriggerConfig(workflow.trigger, eventData)) continue;

    // Execute actions
    await executeActions(db, userId, contactId, workflow.actions, eventData);

    // Increment execution count
    await db.from('workflows').update({
      execution_count: (workflow.execution_count || 0) + 1,
    }).eq('id', workflow.id);
  }
}

function matchesTriggerConfig(trigger: WorkflowTrigger, eventData: Record<string, unknown>): boolean {
  const config = trigger.config || {};
  // Check specific trigger configs
  if (trigger.type === 'tag_added' && config.tag_name) {
    return eventData.tag_name === config.tag_name;
  }
  if (trigger.type === 'purchase' && config.product_id) {
    return eventData.product_id === config.product_id;
  }
  if (trigger.type === 'score_reached' && config.min_score) {
    return (eventData.score as number) >= (config.min_score as number);
  }
  return true; // no specific config = always match
}

async function executeActions(
  db: any, userId: string, contactId: string,
  actions: WorkflowAction[], eventData: Record<string, unknown>,
): Promise<void> {
  for (const action of actions) {
    switch (action.type) {
      case 'add_tag': {
        const tagName = action.config.tag_name as string;
        const { data: tag } = await db.from('tags').select('id').eq('user_id', userId).eq('name', tagName).single();
        if (tag) {
          await db.from('contact_tags').upsert({ contact_id: contactId, tag_id: tag.id });
        }
        break;
      }
      case 'remove_tag': {
        const tagName = action.config.tag_name as string;
        const { data: tag } = await db.from('tags').select('id').eq('user_id', userId).eq('name', tagName).single();
        if (tag) {
          await db.from('contact_tags').delete().eq('contact_id', contactId).eq('tag_id', tag.id);
        }
        break;
      }
      case 'add_score': {
        const points = action.config.points as number || 0;
        const { data: contact } = await db.from('contacts').select('score').eq('id', contactId).single();
        if (contact) {
          await db.from('contacts').update({ score: (contact.score || 0) + points }).eq('id', contactId);
        }
        break;
      }
      case 'subtract_score': {
        const points = action.config.points as number || 0;
        const { data: contact } = await db.from('contacts').select('score').eq('id', contactId).single();
        if (contact) {
          await db.from('contacts').update({ score: Math.max(0, (contact.score || 0) - points) }).eq('id', contactId);
        }
        break;
      }
      case 'enroll_course': {
        const courseId = action.config.course_id as string;
        if (courseId) {
          await db.from('enrollments').upsert({ contact_id: contactId, course_id: courseId }, { onConflict: 'contact_id,course_id' });
        }
        break;
      }
      case 'start_scenario': {
        // Queue the contact into a scenario
        const scenarioType = action.config.scenario_type as string; // 'email' or 'line'
        const scenarioId = action.config.scenario_id as string;
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
        const cond = action.config as unknown as WorkflowCondition;
        const { data: contact } = await db.from('contacts').select('*').eq('id', contactId).single();
        if (!contact) break;

        const matches = evaluateCondition(contact, cond);
        const nextActions = matches ? cond.then_actions : cond.else_actions;
        if (nextActions?.length) {
          await executeActions(db, userId, contactId, nextActions, eventData);
        }
        break;
      }
      case 'webhook': {
        const url = action.config.url as string;
        if (url) {
          try {
            await fetch(url, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ contact_id: contactId, event: eventData }),
              signal: AbortSignal.timeout(10000),
            });
          } catch { /* ignore webhook failures */ }
        }
        break;
      }
    }
  }
}

function evaluateCondition(contact: any, cond: WorkflowCondition): boolean {
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

export async function processReminders(): Promise<number> {
  const db = getSupabase();
  const now = new Date();
  let sentCount = 0;

  // Get upcoming events with reminders enabled
  const { data: events } = await db.from('events').select('*')
    .eq('status', 'upcoming').gt('start_at', now.toISOString());

  for (const event of (events || [])) {
    const config = event.reminder_config;
    if (!config?.enabled || !config.timings?.length) continue;

    for (const minutesBefore of config.timings) {
      const triggerTime = new Date(new Date(event.start_at).getTime() - minutesBefore * 60000);
      const diff = Math.abs(now.getTime() - triggerTime.getTime());

      // Within 5 minutes of trigger time
      if (diff < 5 * 60000) {
        // Get reservations for this event
        const { data: reservations } = await db.from('event_reservations').select('contact_id, contacts(email, line_user_id, phone)')
          .eq('event_id', event.id).eq('status', 'confirmed');

        for (const res of (reservations || [])) {
          const contact = (res as any).contacts;
          if (!contact) continue;

          // Check if reminder already sent
          const reminderKey = `${event.id}_${minutesBefore}_${res.contact_id}`;
          const { data: existing } = await db.from('reminder_logs').select('id').eq('reminder_key', reminderKey).single();
          if (existing) continue;

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

// ============================================================
// Auto Scoring (行動ベーススコアリング)
// ============================================================

const SCORE_RULES: Record<string, number> = {
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

export async function addScore(contactId: string, action: string): Promise<void> {
  const points = SCORE_RULES[action] || 0;
  if (points === 0) return;

  const db = getSupabase();
  const { data: contact } = await db.from('contacts').select('score, user_id').eq('id', contactId).single();
  if (!contact) return;

  const newScore = (contact.score || 0) + points;
  await db.from('contacts').update({ score: newScore }).eq('id', contactId);

  // Check if score threshold workflows should fire
  await executeWorkflowsForEvent(contact.user_id, 'score_reached', contactId, { score: newScore });
}

// ============================================================
// Unsubscribe (配信停止 - 特定電子メール法準拠)
// ============================================================

export async function unsubscribeContact(contactId: string, channel: 'email' | 'line' | 'all'): Promise<ApiResponse<null>> {
  const db = getSupabase();

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

export function generateUnsubscribeUrl(contactId: string, baseUrl: string): string {
  // Simple signed unsubscribe link (in production: use HMAC signature)
  const token = Buffer.from(`${contactId}:${Date.now()}`).toString('base64url');
  return `${baseUrl}/utage/api/unsubscribe?token=${token}&cid=${contactId}`;
}
