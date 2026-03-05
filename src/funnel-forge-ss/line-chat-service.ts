// ============================================================
// LINE Individual Chat & Rich Menu Service
// ============================================================

import type { RichMenu, LineIndividualChat, ApiResponse } from './types';
import { getSupabase } from './db';

// ============================================================
// Individual Chat (1対1トーク)
// ============================================================

export async function listChats(userId: string, page = 1, perPage = 20): Promise<ApiResponse<any[]>> {
  const db = getSupabase();
  const { data, error, count } = await db.from('line_chats').select('*, contacts(name, line_user_id)', { count: 'exact' })
    .eq('user_id', userId).order('last_message_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1);
  if (error) return { success: false, error: error.message };
  return { success: true, data, pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}

export async function getChatMessages(contactId: string, page = 1, perPage = 50): Promise<ApiResponse<any[]>> {
  const db = getSupabase();
  const { data, error, count } = await db.from('line_chat_messages').select('*', { count: 'exact' })
    .eq('contact_id', contactId).order('sent_at', { ascending: false })
    .range((page - 1) * perPage, page * perPage - 1);
  if (error) return { success: false, error: error.message };
  // Reverse to show oldest first
  return { success: true, data: (data || []).reverse(), pagination: { page, per_page: perPage, total: count || 0, total_pages: Math.ceil((count || 0) / perPage) } };
}

export async function sendChatMessage(userId: string, contactId: string, messageType: string, content: Record<string, unknown>): Promise<ApiResponse<any>> {
  const db = getSupabase();

  // Store message
  const { data: msg, error } = await db.from('line_chat_messages').insert({
    contact_id: contactId, direction: 'outgoing',
    message_type: messageType, content,
    sent_at: new Date().toISOString(),
  }).select().single();
  if (error) return { success: false, error: error.message };

  // Update chat last_message_at
  await db.from('line_chats').upsert({
    user_id: userId, contact_id: contactId,
    last_message_at: new Date().toISOString(),
    last_message_preview: content.text ? String(content.text).slice(0, 50) : '[メディア]',
  }, { onConflict: 'user_id,contact_id' });

  // In production: send via LINE Messaging API push
  const { data: contact } = await db.from('contacts').select('line_user_id').eq('id', contactId).single();
  if (contact?.line_user_id) {
    const token = process.env.LINE_CHANNEL_ACCESS_TOKEN;
    if (token) {
      try {
        const messages = buildLineMessages(messageType, content);
        await fetch('https://api.line.me/v2/bot/message/push', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
          body: JSON.stringify({ to: contact.line_user_id, messages }),
        });
      } catch { /* log error */ }
    }
  }

  return { success: true, data: msg };
}

function buildLineMessages(type: string, content: Record<string, unknown>): any[] {
  if (type === 'text') return [{ type: 'text', text: content.text }];
  if (type === 'image') return [{ type: 'image', originalContentUrl: content.image_url, previewImageUrl: content.image_url }];
  if (type === 'flex') return [{ type: 'flex', altText: (content.alt_text as string) || 'Message', contents: content.flex }];
  return [{ type: 'text', text: String(content.text || '') }];
}

// ============================================================
// Rich Menu Management (リッチメニュー管理・出し分け)
// ============================================================

export async function listRichMenus(userId: string): Promise<ApiResponse<RichMenu[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('rich_menus').select('*').eq('user_id', userId).order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createRichMenu(userId: string, menu: Partial<RichMenu>): Promise<ApiResponse<RichMenu>> {
  const db = getSupabase();
  const { data, error } = await db.from('rich_menus').insert({
    user_id: userId, name: menu.name, image_url: menu.image_url || '',
    areas: menu.areas || [],
    display_conditions: menu.display_conditions || [],
    is_default: menu.is_default || false,
  }).select().single();
  if (error) return { success: false, error: error.message };

  // In production: create rich menu via LINE API and get line_rich_menu_id
  return { success: true, data };
}

export async function updateRichMenu(menuId: string, updates: Partial<RichMenu>): Promise<ApiResponse<RichMenu>> {
  const db = getSupabase();
  const { data, error } = await db.from('rich_menus').update(updates).eq('id', menuId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function deleteRichMenu(menuId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  const { error } = await db.from('rich_menus').delete().eq('id', menuId);
  if (error) return { success: false, error: error.message };
  return { success: true };
}

export async function setDefaultRichMenu(userId: string, menuId: string): Promise<ApiResponse<RichMenu>> {
  const db = getSupabase();
  // Unset all defaults
  await db.from('rich_menus').update({ is_default: false }).eq('user_id', userId);
  // Set new default
  const { data, error } = await db.from('rich_menus').update({ is_default: true }).eq('id', menuId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// Assign rich menu to contact based on conditions
export async function assignRichMenuToContact(userId: string, contactId: string): Promise<string | null> {
  const db = getSupabase();

  const { data: menus } = await db.from('rich_menus').select('*').eq('user_id', userId).order('created_at');
  const { data: contact } = await db.from('contacts').select('*, contact_tags(tags(name))').eq('id', contactId).single();
  if (!menus || !contact) return null;

  const contactTags = (contact.contact_tags || []).map((ct: any) => ct.tags?.name).filter(Boolean);

  // Find first matching menu by conditions
  for (const menu of menus) {
    if (!menu.display_conditions?.length) continue;

    const matches = menu.display_conditions.every((cond: any) => {
      if (cond.type === 'tag') return contactTags.includes(cond.value);
      if (cond.type === 'score_gt') return (contact.score || 0) > Number(cond.value);
      if (cond.type === 'score_lt') return (contact.score || 0) < Number(cond.value);
      if (cond.type === 'source') return contact.source === cond.value;
      if (cond.type === 'purchase') return true; // would need order check
      return false;
    });

    if (matches) {
      // In production: call LINE API to link rich menu to user
      return menu.id;
    }
  }

  // Fall back to default
  const defaultMenu = menus.find((m: any) => m.is_default);
  return defaultMenu?.id || null;
}

// ============================================================
// CSV Export
// ============================================================

export async function exportContactsCsv(userId: string): Promise<ApiResponse<string>> {
  const db = getSupabase();
  const { data: contacts } = await db.from('contacts').select('*').eq('user_id', userId).order('created_at');
  if (!contacts?.length) return { success: false, error: 'No contacts to export' };

  const headers = ['name', 'email', 'phone', 'line_user_id', 'score', 'source', 'status', 'created_at'];
  const rows = contacts.map((c: any) => headers.map(h => `"${String(c[h] || '').replace(/"/g, '""')}"`).join(','));
  const csv = [headers.join(','), ...rows].join('\n');

  return { success: true, data: csv };
}

export async function exportOrdersCsv(userId: string): Promise<ApiResponse<string>> {
  const db = getSupabase();
  const { data: orders } = await db.from('orders').select('*, contacts(name, email), products(name)')
    .order('created_at', { ascending: false });
  if (!orders?.length) return { success: false, error: 'No orders to export' };

  const headers = ['order_id', 'contact_name', 'contact_email', 'product', 'amount', 'status', 'paid_at', 'created_at'];
  const rows = orders.map((o: any) => [
    o.id, o.contacts?.name || '', o.contacts?.email || '', o.products?.name || '',
    o.amount, o.status, o.paid_at || '', o.created_at,
  ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(','));
  const csv = [headers.join(','), ...rows].join('\n');

  return { success: true, data: csv };
}
