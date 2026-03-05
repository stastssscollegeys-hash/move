"use strict";
// ============================================================
// FunnelForge SS - Core Services
// Phase 1 MVP: CRM + Funnel + Email + LINE + Payment
// ============================================================
Object.defineProperty(exports, "__esModule", { value: true });
exports.verifyDomain = exports.addDomainAuth = exports.listDomainAuth = exports.previewSegment = exports.deleteSegment = exports.updateSegment = exports.createSegment = exports.listSegments = exports.evaluateSegment = exports.getDashboardStats = exports.updateOrderStatus = exports.createOrder = exports.createProduct = exports.listProducts = exports.createLineScenario = exports.listLineScenarios = exports.addEmailStep = exports.createEmailScenario = exports.listEmailScenarios = exports.getPublishedPage = exports.createFunnelPage = exports.updateFunnelPage = exports.createFunnel = exports.listFunnels = exports.createTag = exports.listTags = exports.removeTagFromContact = exports.addTagToContact = exports.getContact = exports.createContact = exports.listContacts = void 0;
const db_1 = require("./db");
// ============================================================
// CRM: Contacts
// ============================================================
async function listContacts(userId, query) {
    const db = (0, db_1.getSupabase)();
    const page = query.page || 1;
    const perPage = query.per_page || 20;
    const offset = (page - 1) * perPage;
    let q = db.from('contacts').select('*, contact_tags(tag_id, tags(name, color))', { count: 'exact' })
        .eq('user_id', userId)
        .range(offset, offset + perPage - 1);
    if (query.status)
        q = q.eq('status', query.status);
    if (query.search)
        q = q.or(`name.ilike.%${query.search}%,email.ilike.%${query.search}%`);
    const sortBy = query.sort_by || 'created_at';
    const sortOrder = query.sort_order === 'asc';
    q = q.order(sortBy, { ascending: sortOrder });
    const { data, error, count } = await q;
    if (error)
        return { success: false, error: error.message };
    const contacts = (data || []).map((row) => ({
        ...row,
        tags: (row.contact_tags || []).map((ct) => ct.tags?.name).filter(Boolean),
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
exports.listContacts = listContacts;
async function createContact(userId, data) {
    const db = (0, db_1.getSupabase)();
    const { data: contact, error } = await db.from('contacts')
        .insert({ user_id: userId, email: data.email, line_user_id: data.line_user_id, name: data.name, phone: data.phone, source: data.source })
        .select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: contact };
}
exports.createContact = createContact;
async function getContact(userId, contactId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('contacts')
        .select('*, contact_tags(tag_id, tags(name, color))')
        .eq('id', contactId).eq('user_id', userId).single();
    if (error)
        return { success: false, error: error.message };
    return {
        success: true,
        data: { ...data, tags: (data.contact_tags || []).map((ct) => ct.tags?.name).filter(Boolean) },
    };
}
exports.getContact = getContact;
async function addTagToContact(contactId, tagId) {
    const db = (0, db_1.getSupabase)();
    const { error } = await db.from('contact_tags').upsert({ contact_id: contactId, tag_id: tagId });
    if (error)
        return { success: false, error: error.message };
    return { success: true };
}
exports.addTagToContact = addTagToContact;
async function removeTagFromContact(contactId, tagId) {
    const db = (0, db_1.getSupabase)();
    const { error } = await db.from('contact_tags').delete().eq('contact_id', contactId).eq('tag_id', tagId);
    if (error)
        return { success: false, error: error.message };
    return { success: true };
}
exports.removeTagFromContact = removeTagFromContact;
// ============================================================
// CRM: Tags
// ============================================================
async function listTags(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('tags').select('*').eq('user_id', userId).order('name');
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listTags = listTags;
async function createTag(userId, name, color) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('tags').insert({ user_id: userId, name, color: color || '#6C5CE7' }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createTag = createTag;
// ============================================================
// Funnels
// ============================================================
async function listFunnels(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('funnels').select('*, funnel_pages(*)').eq('user_id', userId).order('updated_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: (data || []).map((f) => ({ ...f, pages: f.funnel_pages || [] })) };
}
exports.listFunnels = listFunnels;
async function createFunnel(userId, name) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('funnels').insert({ user_id: userId, name }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: { ...data, pages: [] } };
}
exports.createFunnel = createFunnel;
async function updateFunnelPage(pageId, updates) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('funnel_pages').update(updates).eq('id', pageId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateFunnelPage = updateFunnelPage;
async function createFunnelPage(funnelId, page) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('funnel_pages')
        .insert({ funnel_id: funnelId, title: page.title, slug: page.slug, page_type: page.page_type, elements: page.elements || [], sort_order: page.sort_order || 0 })
        .select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createFunnelPage = createFunnelPage;
async function getPublishedPage(slug) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('funnel_pages')
        .select('*, funnels!inner(status)')
        .eq('slug', slug)
        .eq('funnels.status', 'published')
        .not('published_at', 'is', null)
        .single();
    if (error)
        return { success: false, error: 'Page not found' };
    return { success: true, data };
}
exports.getPublishedPage = getPublishedPage;
// ============================================================
// Email Scenarios
// ============================================================
async function listEmailScenarios(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('email_scenarios').select('*, email_steps(*)').eq('user_id', userId).order('updated_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: (data || []).map((s) => ({ ...s, steps: s.email_steps || [] })) };
}
exports.listEmailScenarios = listEmailScenarios;
async function createEmailScenario(userId, scenario) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('email_scenarios')
        .insert({ user_id: userId, name: scenario.name, trigger_type: scenario.trigger || 'optin' })
        .select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: { ...data, steps: [] } };
}
exports.createEmailScenario = createEmailScenario;
async function addEmailStep(scenarioId, step) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('email_steps')
        .insert({ scenario_id: scenarioId, subject: step.subject, body_html: step.body_html, delay_minutes: step.delay_minutes || 0, sort_order: step.sort_order || 0 })
        .select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.addEmailStep = addEmailStep;
// ============================================================
// LINE Scenarios
// ============================================================
async function listLineScenarios(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('line_scenarios').select('*, line_steps(*)').eq('user_id', userId).order('updated_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: (data || []).map((s) => ({ ...s, steps: s.line_steps || [] })) };
}
exports.listLineScenarios = listLineScenarios;
async function createLineScenario(userId, scenario) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('line_scenarios')
        .insert({ user_id: userId, name: scenario.name, trigger_type: scenario.trigger || 'follow' })
        .select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data: { ...data, steps: [] } };
}
exports.createLineScenario = createLineScenario;
// ============================================================
// Products & Orders (Stripe)
// ============================================================
async function listProducts(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('products').select('*').eq('user_id', userId).eq('status', 'active').order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listProducts = listProducts;
async function createProduct(userId, product) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('products')
        .insert({ user_id: userId, name: product.name, description: product.description, price: product.price, payment_type: product.payment_type || 'one_time' })
        .select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createProduct = createProduct;
async function createOrder(contactId, productId, amount) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('orders')
        .insert({ contact_id: contactId, product_id: productId, amount })
        .select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createOrder = createOrder;
async function updateOrderStatus(orderId, status, stripeData) {
    const db = (0, db_1.getSupabase)();
    const updates = { status };
    if (status === 'paid')
        updates.paid_at = new Date().toISOString();
    if (stripeData?.payment_intent_id)
        updates.stripe_payment_intent_id = stripeData.payment_intent_id;
    if (stripeData?.subscription_id)
        updates.stripe_subscription_id = stripeData.subscription_id;
    const { data, error } = await db.from('orders').update(updates).eq('id', orderId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateOrderStatus = updateOrderStatus;
// ============================================================
// Dashboard Stats
// ============================================================
async function getDashboardStats(userId) {
    const db = (0, db_1.getSupabase)();
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const todayISO = today.toISOString();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1).toISOString();
    const [contacts, newToday, revenue, revenueMonth, funnels, emailSentToday, lineSentToday, webinars, courses, affiliateComm] = await Promise.all([
        db.from('contacts').select('id', { count: 'exact', head: true }).eq('user_id', userId),
        db.from('contacts').select('id', { count: 'exact', head: true }).eq('user_id', userId).gte('created_at', todayISO),
        db.from('orders').select('amount').eq('status', 'paid'),
        db.from('orders').select('amount').eq('status', 'paid').gte('paid_at', monthStart),
        db.from('funnels').select('id', { count: 'exact', head: true }).eq('user_id', userId).eq('status', 'published'),
        db.from('email_send_logs').select('id', { count: 'exact', head: true }).gte('created_at', todayISO),
        db.from('line_send_logs').select('id', { count: 'exact', head: true }).gte('created_at', todayISO),
        db.from('webinars').select('id', { count: 'exact', head: true }).eq('user_id', userId).eq('status', 'live'),
        db.from('courses').select('id', { count: 'exact', head: true }).eq('user_id', userId),
        db.from('affiliate_referrals').select('commission_amount').eq('status', 'approved').gte('created_at', monthStart),
    ]);
    const totalRevenue = (revenue.data || []).reduce((sum, o) => sum + (o.amount || 0), 0);
    const monthRevenue = (revenueMonth.data || []).reduce((sum, o) => sum + (o.amount || 0), 0);
    const totalCommission = (affiliateComm.data || []).reduce((sum, r) => sum + (r.commission_amount || 0), 0);
    // Calculate conversion rate: orders / contacts
    const convRate = (contacts.count || 0) > 0
        ? Math.round(((revenue.data || []).length / (contacts.count || 1)) * 10000) / 100
        : 0;
    return {
        success: true,
        data: {
            total_contacts: contacts.count || 0,
            new_contacts_today: newToday.count || 0,
            total_revenue: totalRevenue,
            revenue_this_month: monthRevenue,
            email_sent_today: emailSentToday.count || 0,
            email_open_rate: 0, // requires tracking pixel integration
            line_sent_today: lineSentToday.count || 0,
            line_read_rate: 0, // requires LINE webhook read events
            active_funnels: funnels.count || 0,
            conversion_rate: convRate,
            active_webinars: webinars.count || 0,
            active_courses: courses.count || 0,
            affiliate_commission_this_month: totalCommission,
        },
    };
}
exports.getDashboardStats = getDashboardStats;
// ============================================================
// Segments
// ============================================================
async function evaluateSegment(userId, conditions, logic) {
    const db = (0, db_1.getSupabase)();
    // Start with all contacts for this user
    let q = db.from('contacts').select('*, contact_tags(tag_id, tags(name))').eq('user_id', userId);
    // For AND logic, chain filters
    if (logic === 'AND') {
        for (const cond of conditions) {
            q = applyCondition(q, cond);
        }
    }
    const { data, error } = await q;
    if (error)
        return { success: false, error: error.message };
    let results = data || [];
    // For OR logic, we need post-filter (Supabase doesn't support OR across different columns easily)
    if (logic === 'OR' && conditions.length > 0) {
        results = results.filter((contact) => conditions.some(cond => matchesCondition(contact, cond)));
    }
    return { success: true, data: results };
}
exports.evaluateSegment = evaluateSegment;
function applyCondition(query, cond) {
    switch (cond.field) {
        case 'score':
            if (cond.operator === 'gt')
                return query.gt('score', cond.value);
            if (cond.operator === 'lt')
                return query.lt('score', cond.value);
            if (cond.operator === 'eq')
                return query.eq('score', cond.value);
            break;
        case 'source':
            if (cond.operator === 'eq')
                return query.eq('source', cond.value);
            if (cond.operator === 'contains')
                return query.ilike('source', `%${cond.value}%`);
            break;
        case 'status':
            return query.eq('status', cond.value);
        case 'email':
            if (cond.operator === 'contains')
                return query.ilike('email', `%${cond.value}%`);
            break;
    }
    return query;
}
function matchesCondition(contact, cond) {
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
// ============================================================
// Segment CRUD
// ============================================================
async function listSegments(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('segments').select('*').eq('user_id', userId).order('created_at', { ascending: false });
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listSegments = listSegments;
async function createSegment(userId, segment) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('segments').insert({
        user_id: userId, name: segment.name,
        conditions: segment.conditions || [], logic: segment.logic || 'AND',
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.createSegment = createSegment;
async function updateSegment(segmentId, updates) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('segments').update(updates).eq('id', segmentId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.updateSegment = updateSegment;
async function deleteSegment(segmentId) {
    const db = (0, db_1.getSupabase)();
    const { error } = await db.from('segments').delete().eq('id', segmentId);
    if (error)
        return { success: false, error: error.message };
    return { success: true };
}
exports.deleteSegment = deleteSegment;
async function previewSegment(userId, conditions, logic) {
    const result = await evaluateSegment(userId, conditions, logic);
    if (!result.success)
        return { success: false, error: result.error };
    const contacts = result.data || [];
    return { success: true, data: { count: contacts.length, sample: contacts.slice(0, 5) } };
}
exports.previewSegment = previewSegment;
// ============================================================
// Email Domain Authentication (SPF/DKIM)
// ============================================================
async function listDomainAuth(userId) {
    const db = (0, db_1.getSupabase)();
    const { data, error } = await db.from('email_domain_auth').select('*').eq('user_id', userId);
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.listDomainAuth = listDomainAuth;
async function addDomainAuth(userId, domain) {
    const db = (0, db_1.getSupabase)();
    // Generate DKIM selector and DNS records to verify
    const dkimSelector = `ff${Date.now().toString(36)}`;
    const { data, error } = await db.from('email_domain_auth').insert({
        user_id: userId, domain,
        spf_record: `v=spf1 include:amazonses.com ~all`,
        dkim_selector: dkimSelector,
        dkim_public_key: '(SESから自動生成されます)',
        verification_status: 'pending',
        dns_records: [
            { type: 'TXT', name: `_dmarc.${domain}`, value: `v=DMARC1; p=none; rua=mailto:dmarc@${domain}` },
            { type: 'TXT', name: domain, value: `v=spf1 include:amazonses.com ~all` },
            { type: 'CNAME', name: `${dkimSelector}._domainkey.${domain}`, value: `${dkimSelector}.dkim.amazonses.com` },
        ],
    }).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.addDomainAuth = addDomainAuth;
async function verifyDomain(domainId) {
    const db = (0, db_1.getSupabase)();
    // In production: call SES VerifyDomainIdentity API and check DNS records
    const { data, error } = await db.from('email_domain_auth').update({
        verification_status: 'verified', verified_at: new Date().toISOString(),
    }).eq('id', domainId).select().single();
    if (error)
        return { success: false, error: error.message };
    return { success: true, data };
}
exports.verifyDomain = verifyDomain;
