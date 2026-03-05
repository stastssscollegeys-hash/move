// ============================================================
// UTAGE System SS - Core Services
// Phase 1 MVP: CRM + Funnel + Email + LINE + Payment
// ============================================================

import type {
  Contact, ContactListQuery, Tag, Funnel, FunnelPage,
  EmailScenario, EmailStep, LineScenario, LineStep,
  Product, Order, DashboardStats, Segment, SegmentCondition,
  ApiResponse,
} from './types';

// --- Supabase Client (lazy init) ---

let supabase: any = null;

function getSupabase() {
  if (!supabase) {
    // Dynamic import to avoid issues when Supabase isn't configured yet
    const { createClient } = require('@supabase/supabase-js');
    const url = process.env.SUPABASE_URL;
    const key = process.env.SUPABASE_SERVICE_KEY;
    if (!url || !key) {
      throw new Error('SUPABASE_URL and SUPABASE_SERVICE_KEY are required');
    }
    supabase = createClient(url, key);
  }
  return supabase;
}

// ============================================================
// CRM: Contacts
// ============================================================

export async function listContacts(userId: string, query: ContactListQuery): Promise<ApiResponse<Contact[]>> {
  const db = getSupabase();
  const page = query.page || 1;
  const perPage = query.per_page || 20;
  const offset = (page - 1) * perPage;

  let q = db.from('contacts').select('*, contact_tags(tag_id, tags(name, color))', { count: 'exact' })
    .eq('user_id', userId)
    .range(offset, offset + perPage - 1);

  if (query.status) q = q.eq('status', query.status);
  if (query.search) q = q.or(`name.ilike.%${query.search}%,email.ilike.%${query.search}%`);

  const sortBy = query.sort_by || 'created_at';
  const sortOrder = query.sort_order === 'asc';
  q = q.order(sortBy, { ascending: sortOrder });

  const { data, error, count } = await q;
  if (error) return { success: false, error: error.message };

  const contacts: Contact[] = (data || []).map((row: any) => ({
    ...row,
    tags: (row.contact_tags || []).map((ct: any) => ct.tags?.name).filter(Boolean),
  }));

  return {
    success: true,
    data: contacts,
    pagination: {
      page, per_page: perPage,
      total: count || 0,
      total_pages: Math.ceil((count || 0) / perPage),
    },
  };
}

export async function createContact(userId: string, data: Partial<Contact>): Promise<ApiResponse<Contact>> {
  const db = getSupabase();
  const { data: contact, error } = await db.from('contacts')
    .insert({ user_id: userId, email: data.email, line_user_id: data.line_user_id, name: data.name, phone: data.phone, source: data.source })
    .select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: contact };
}

export async function getContact(userId: string, contactId: string): Promise<ApiResponse<Contact>> {
  const db = getSupabase();
  const { data, error } = await db.from('contacts')
    .select('*, contact_tags(tag_id, tags(name, color))')
    .eq('id', contactId).eq('user_id', userId).single();
  if (error) return { success: false, error: error.message };
  return {
    success: true,
    data: { ...data, tags: (data.contact_tags || []).map((ct: any) => ct.tags?.name).filter(Boolean) },
  };
}

export async function addTagToContact(contactId: string, tagId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  const { error } = await db.from('contact_tags').upsert({ contact_id: contactId, tag_id: tagId });
  if (error) return { success: false, error: error.message };
  return { success: true };
}

export async function removeTagFromContact(contactId: string, tagId: string): Promise<ApiResponse<null>> {
  const db = getSupabase();
  const { error } = await db.from('contact_tags').delete().eq('contact_id', contactId).eq('tag_id', tagId);
  if (error) return { success: false, error: error.message };
  return { success: true };
}

// ============================================================
// CRM: Tags
// ============================================================

export async function listTags(userId: string): Promise<ApiResponse<Tag[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('tags').select('*').eq('user_id', userId).order('name');
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createTag(userId: string, name: string, color?: string): Promise<ApiResponse<Tag>> {
  const db = getSupabase();
  const { data, error } = await db.from('tags').insert({ user_id: userId, name, color: color || '#6C5CE7' }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// ============================================================
// Funnels
// ============================================================

export async function listFunnels(userId: string): Promise<ApiResponse<Funnel[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('funnels').select('*, funnel_pages(*)').eq('user_id', userId).order('updated_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data: (data || []).map((f: any) => ({ ...f, pages: f.funnel_pages || [] })) };
}

export async function createFunnel(userId: string, name: string): Promise<ApiResponse<Funnel>> {
  const db = getSupabase();
  const { data, error } = await db.from('funnels').insert({ user_id: userId, name }).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: { ...data, pages: [] } };
}

export async function updateFunnelPage(pageId: string, updates: Partial<FunnelPage>): Promise<ApiResponse<FunnelPage>> {
  const db = getSupabase();
  const { data, error } = await db.from('funnel_pages').update(updates).eq('id', pageId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createFunnelPage(funnelId: string, page: Partial<FunnelPage>): Promise<ApiResponse<FunnelPage>> {
  const db = getSupabase();
  const { data, error } = await db.from('funnel_pages')
    .insert({ funnel_id: funnelId, title: page.title, slug: page.slug, page_type: page.page_type, elements: page.elements || [], sort_order: page.sort_order || 0 })
    .select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function getPublishedPage(slug: string): Promise<ApiResponse<FunnelPage>> {
  const db = getSupabase();
  const { data, error } = await db.from('funnel_pages')
    .select('*, funnels!inner(status)')
    .eq('slug', slug)
    .eq('funnels.status', 'published')
    .not('published_at', 'is', null)
    .single();
  if (error) return { success: false, error: 'Page not found' };
  return { success: true, data };
}

// ============================================================
// Email Scenarios
// ============================================================

export async function listEmailScenarios(userId: string): Promise<ApiResponse<EmailScenario[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('email_scenarios').select('*, email_steps(*)').eq('user_id', userId).order('updated_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data: (data || []).map((s: any) => ({ ...s, steps: s.email_steps || [] })) };
}

export async function createEmailScenario(userId: string, scenario: Partial<EmailScenario>): Promise<ApiResponse<EmailScenario>> {
  const db = getSupabase();
  const { data, error } = await db.from('email_scenarios')
    .insert({ user_id: userId, name: scenario.name, trigger_type: scenario.trigger || 'optin' })
    .select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: { ...data, steps: [] } };
}

export async function addEmailStep(scenarioId: string, step: Partial<EmailStep>): Promise<ApiResponse<EmailStep>> {
  const db = getSupabase();
  const { data, error } = await db.from('email_steps')
    .insert({ scenario_id: scenarioId, subject: step.subject, body_html: step.body_html, delay_minutes: step.delay_minutes || 0, sort_order: step.sort_order || 0 })
    .select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// ============================================================
// LINE Scenarios
// ============================================================

export async function listLineScenarios(userId: string): Promise<ApiResponse<LineScenario[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('line_scenarios').select('*, line_steps(*)').eq('user_id', userId).order('updated_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data: (data || []).map((s: any) => ({ ...s, steps: s.line_steps || [] })) };
}

export async function createLineScenario(userId: string, scenario: Partial<LineScenario>): Promise<ApiResponse<LineScenario>> {
  const db = getSupabase();
  const { data, error } = await db.from('line_scenarios')
    .insert({ user_id: userId, name: scenario.name, trigger_type: scenario.trigger || 'follow' })
    .select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data: { ...data, steps: [] } };
}

// ============================================================
// Products & Orders (Stripe)
// ============================================================

export async function listProducts(userId: string): Promise<ApiResponse<Product[]>> {
  const db = getSupabase();
  const { data, error } = await db.from('products').select('*').eq('user_id', userId).eq('status', 'active').order('created_at', { ascending: false });
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createProduct(userId: string, product: Partial<Product>): Promise<ApiResponse<Product>> {
  const db = getSupabase();
  const { data, error } = await db.from('products')
    .insert({ user_id: userId, name: product.name, description: product.description, price: product.price, payment_type: product.payment_type || 'one_time' })
    .select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function createOrder(contactId: string, productId: string, amount: number): Promise<ApiResponse<Order>> {
  const db = getSupabase();
  const { data, error } = await db.from('orders')
    .insert({ contact_id: contactId, product_id: productId, amount })
    .select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

export async function updateOrderStatus(orderId: string, status: Order['status'], stripeData?: { payment_intent_id?: string; subscription_id?: string }): Promise<ApiResponse<Order>> {
  const db = getSupabase();
  const updates: any = { status };
  if (status === 'paid') updates.paid_at = new Date().toISOString();
  if (stripeData?.payment_intent_id) updates.stripe_payment_intent_id = stripeData.payment_intent_id;
  if (stripeData?.subscription_id) updates.stripe_subscription_id = stripeData.subscription_id;

  const { data, error } = await db.from('orders').update(updates).eq('id', orderId).select().single();
  if (error) return { success: false, error: error.message };
  return { success: true, data };
}

// ============================================================
// Dashboard Stats
// ============================================================

export async function getDashboardStats(userId: string): Promise<ApiResponse<DashboardStats>> {
  const db = getSupabase();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayISO = today.toISOString();

  const monthStart = new Date(today.getFullYear(), today.getMonth(), 1).toISOString();

  const [contacts, newToday, revenue, revenueMonth, funnels] = await Promise.all([
    db.from('contacts').select('id', { count: 'exact', head: true }).eq('user_id', userId),
    db.from('contacts').select('id', { count: 'exact', head: true }).eq('user_id', userId).gte('created_at', todayISO),
    db.from('orders').select('amount').eq('status', 'paid').in('product_id',
      db.from('products').select('id').eq('user_id', userId)
    ),
    db.from('orders').select('amount').eq('status', 'paid').gte('paid_at', monthStart).in('product_id',
      db.from('products').select('id').eq('user_id', userId)
    ),
    db.from('funnels').select('id', { count: 'exact', head: true }).eq('user_id', userId).eq('status', 'published'),
  ]);

  const totalRevenue = (revenue.data || []).reduce((sum: number, o: any) => sum + o.amount, 0);
  const monthRevenue = (revenueMonth.data || []).reduce((sum: number, o: any) => sum + o.amount, 0);

  return {
    success: true,
    data: {
      total_contacts: contacts.count || 0,
      new_contacts_today: newToday.count || 0,
      total_revenue: totalRevenue,
      revenue_this_month: monthRevenue,
      email_sent_today: 0, // TODO: aggregate from email_send_logs
      email_open_rate: 0,
      line_sent_today: 0,
      line_read_rate: 0,
      active_funnels: funnels.count || 0,
      conversion_rate: 0,
    },
  };
}

// ============================================================
// Segments
// ============================================================

export async function evaluateSegment(userId: string, conditions: SegmentCondition[], logic: 'AND' | 'OR'): Promise<ApiResponse<Contact[]>> {
  const db = getSupabase();

  // Start with all contacts for this user
  let q = db.from('contacts').select('*, contact_tags(tag_id, tags(name))').eq('user_id', userId);

  // For AND logic, chain filters
  if (logic === 'AND') {
    for (const cond of conditions) {
      q = applyCondition(q, cond);
    }
  }

  const { data, error } = await q;
  if (error) return { success: false, error: error.message };

  let results = data || [];

  // For OR logic, we need post-filter (Supabase doesn't support OR across different columns easily)
  if (logic === 'OR' && conditions.length > 0) {
    results = results.filter((contact: any) =>
      conditions.some(cond => matchesCondition(contact, cond))
    );
  }

  return { success: true, data: results };
}

function applyCondition(query: any, cond: SegmentCondition): any {
  switch (cond.field) {
    case 'score':
      if (cond.operator === 'gt') return query.gt('score', cond.value);
      if (cond.operator === 'lt') return query.lt('score', cond.value);
      if (cond.operator === 'eq') return query.eq('score', cond.value);
      break;
    case 'source':
      if (cond.operator === 'eq') return query.eq('source', cond.value);
      if (cond.operator === 'contains') return query.ilike('source', `%${cond.value}%`);
      break;
    case 'status':
      return query.eq('status', cond.value);
    case 'email':
      if (cond.operator === 'contains') return query.ilike('email', `%${cond.value}%`);
      break;
  }
  return query;
}

function matchesCondition(contact: any, cond: SegmentCondition): boolean {
  const val = contact[cond.field];
  switch (cond.operator) {
    case 'eq': return val === cond.value;
    case 'neq': return val !== cond.value;
    case 'gt': return typeof val === 'number' && val > Number(cond.value);
    case 'lt': return typeof val === 'number' && val < Number(cond.value);
    case 'contains': return typeof val === 'string' && val.includes(String(cond.value));
    case 'in': return Array.isArray(cond.value) && cond.value.includes(val);
    default: return false;
  }
}
