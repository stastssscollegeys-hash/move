"use strict";
// ============================================================
// Demo In-Memory Store (works without Supabase)
// ============================================================
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.demoSupabase = exports.query = void 0;
const crypto_1 = __importDefault(require("crypto"));
const uuid = () => crypto_1.default.randomUUID();
const now = () => new Date().toISOString();
// --- Storage ---
const store = {
    contacts: [], tags: [], contact_tags: [], funnels: [], funnel_pages: [],
    email_scenarios: [], email_steps: [], email_broadcasts: [],
    line_scenarios: [], line_steps: [],
    products: [], orders: [], product_groups: [],
    courses: [], lessons: [], enrollments: [], lesson_comments: [],
    events: [], event_reservations: [], calendar_slots: [], calendar_bookings: [],
    webinars: [], webinar_attendees: [], webinar_chats: [], webinar_polls: [],
    affiliate_programs: [], affiliate_partners: [], affiliate_referrals: [],
    custom_forms: [], form_submissions: [],
    media_files: [], ad_trackings: [], link_clicks: [], conversion_events: [],
    webhook_endpoints: [], webhook_logs: [],
    page_views: [],
    line_broadcasts: [], line_send_logs: [], email_send_logs: [],
    sms_broadcasts: [], segments: [],
    line_chats: [], line_chat_messages: [], line_settings: [],
    rich_menus: [], stripe_settings: [],
    workflows: [], reminder_logs: [],
    email_domain_auth: [], custom_domains: [],
    bundle_courses: [], google_sheet_exports: [],
    // Enrolly tables
    enrolly_courses: [], enrolly_modules: [], enrolly_lessons: [],
    enrolly_enrollments: [], enrolly_lesson_progress: [], enrolly_videos: [],
    enrolly_quizzes: [], enrolly_quiz_attempts: [],
    enrolly_discussions: [], enrolly_discussion_replies: [],
    enrolly_certificates: [], enrolly_issued_certificates: [],
};
// Seed demo data
function seed() {
    if (store.contacts.length > 0)
        return;
    const userId = 'demo-user-001';
    // Tags
    const tags = [
        { id: uuid(), user_id: userId, name: 'VIP', color: '#E74C3C', created_at: now() },
        { id: uuid(), user_id: userId, name: 'セミナー参加済み', color: '#2ECC71', created_at: now() },
        { id: uuid(), user_id: userId, name: 'メルマガ登録', color: '#3498DB', created_at: now() },
        { id: uuid(), user_id: userId, name: 'LINE友だち', color: '#00B900', created_at: now() },
        { id: uuid(), user_id: userId, name: '購入者', color: '#F39C12', created_at: now() },
    ];
    store.tags.push(...tags);
    // Contacts
    const contacts = [
        { id: uuid(), user_id: userId, name: '田中太郎', email: 'tanaka@example.com', line_user_id: 'U001', phone: '090-1234-5678', score: 85, custom_fields: {}, source: 'Instagram広告', utm_source: 'instagram', utm_medium: 'paid', utm_campaign: 'seminar2026', status: 'active', created_at: '2026-02-01T10:00:00Z', updated_at: now() },
        { id: uuid(), user_id: userId, name: '鈴木花子', email: 'suzuki@example.com', line_user_id: 'U002', phone: '080-2345-6789', score: 120, custom_fields: {}, source: 'Google検索', utm_source: 'google', utm_medium: 'organic', utm_campaign: null, status: 'active', created_at: '2026-02-05T14:30:00Z', updated_at: now() },
        { id: uuid(), user_id: userId, name: '佐藤健一', email: 'sato@example.com', line_user_id: null, phone: null, score: 30, custom_fields: {}, source: 'Facebook広告', utm_source: 'facebook', utm_medium: 'paid', utm_campaign: 'ebook2026', status: 'active', created_at: '2026-02-15T09:00:00Z', updated_at: now() },
        { id: uuid(), user_id: userId, name: '高橋美咲', email: 'takahashi@example.com', line_user_id: 'U004', phone: '070-3456-7890', score: 200, custom_fields: {}, source: 'YouTube', utm_source: 'youtube', utm_medium: 'organic', utm_campaign: null, status: 'active', created_at: '2026-01-20T16:00:00Z', updated_at: now() },
        { id: uuid(), user_id: userId, name: '伊藤勇気', email: 'ito@example.com', line_user_id: 'U005', phone: null, score: 55, custom_fields: {}, source: 'Twitter', utm_source: 'twitter', utm_medium: 'organic', utm_campaign: null, status: 'active', created_at: '2026-03-01T11:00:00Z', updated_at: now() },
        { id: uuid(), user_id: userId, name: '渡辺さくら', email: 'watanabe@example.com', line_user_id: null, phone: '090-4567-8901', score: 10, custom_fields: {}, source: 'アフィリエイト', utm_source: 'affiliate', utm_medium: 'referral', utm_campaign: null, status: 'active', created_at: now(), updated_at: now() },
    ];
    store.contacts.push(...contacts);
    // Contact-Tag assignments
    store.contact_tags.push({ contact_id: contacts[0].id, tag_id: tags[2].id }, { contact_id: contacts[0].id, tag_id: tags[3].id }, { contact_id: contacts[1].id, tag_id: tags[0].id }, { contact_id: contacts[1].id, tag_id: tags[1].id }, { contact_id: contacts[1].id, tag_id: tags[4].id }, { contact_id: contacts[3].id, tag_id: tags[0].id }, { contact_id: contacts[3].id, tag_id: tags[1].id }, { contact_id: contacts[3].id, tag_id: tags[3].id }, { contact_id: contacts[3].id, tag_id: tags[4].id }, { contact_id: contacts[4].id, tag_id: tags[2].id });
    // Products
    const products = [
        { id: uuid(), user_id: userId, name: 'マーケティング基礎講座', description: 'マーケティングの基礎を学ぶ動画講座', price: 29800, currency: 'jpy', payment_type: 'one_time', status: 'active', created_at: '2026-01-15T00:00:00Z', updated_at: now() },
        { id: uuid(), user_id: userId, name: 'プレミアム会員', description: '月額制の全コンテンツアクセス', price: 9800, currency: 'jpy', payment_type: 'subscription', status: 'active', created_at: '2026-02-01T00:00:00Z', updated_at: now() },
        { id: uuid(), user_id: userId, name: 'コンサルティング（3回）', description: '1on1コンサルティング 3回パック', price: 98000, currency: 'jpy', payment_type: 'installment', installment_count: 3, status: 'active', created_at: '2026-02-10T00:00:00Z', updated_at: now() },
    ];
    store.products.push(...products);
    // Orders
    store.orders.push({ id: uuid(), contact_id: contacts[1].id, product_id: products[0].id, amount: 29800, currency: 'jpy', status: 'paid', paid_at: '2026-02-10T10:00:00Z', created_at: '2026-02-10T10:00:00Z' }, { id: uuid(), contact_id: contacts[3].id, product_id: products[0].id, amount: 29800, currency: 'jpy', status: 'paid', paid_at: '2026-02-15T14:00:00Z', created_at: '2026-02-15T14:00:00Z' }, { id: uuid(), contact_id: contacts[3].id, product_id: products[1].id, amount: 9800, currency: 'jpy', status: 'paid', paid_at: '2026-03-01T09:00:00Z', created_at: '2026-03-01T09:00:00Z' }, { id: uuid(), contact_id: contacts[1].id, product_id: products[2].id, amount: 98000, currency: 'jpy', status: 'paid', paid_at: '2026-03-03T16:00:00Z', created_at: '2026-03-03T16:00:00Z' });
    // Funnels
    const funnel1 = { id: uuid(), user_id: userId, name: '無料セミナー集客ファネル', status: 'published', created_at: '2026-02-01T00:00:00Z', updated_at: now() };
    const funnel2 = { id: uuid(), user_id: userId, name: '電子書籍ダウンロードファネル', status: 'published', created_at: '2026-02-20T00:00:00Z', updated_at: now() };
    store.funnels.push(funnel1, funnel2);
    store.funnel_pages.push({ id: uuid(), funnel_id: funnel1.id, title: 'セミナーLP', slug: 'seminar-lp', page_type: 'lp', elements: [], sort_order: 0, published_at: '2026-02-01T00:00:00Z', created_at: now(), updated_at: now() }, { id: uuid(), funnel_id: funnel1.id, title: '登録フォーム', slug: 'seminar-register', page_type: 'optin', elements: [], sort_order: 1, published_at: '2026-02-01T00:00:00Z', created_at: now(), updated_at: now() }, { id: uuid(), funnel_id: funnel1.id, title: 'サンクスページ', slug: 'seminar-thanks', page_type: 'thankyou', elements: [], sort_order: 2, published_at: '2026-02-01T00:00:00Z', created_at: now(), updated_at: now() }, { id: uuid(), funnel_id: funnel2.id, title: 'eBook LP', slug: 'ebook-lp', page_type: 'lp', elements: [], sort_order: 0, published_at: '2026-02-20T00:00:00Z', created_at: now(), updated_at: now() });
    // Email scenarios
    const emailScenario = { id: uuid(), user_id: userId, name: 'セミナー登録後ステップ', trigger_type: 'optin', status: 'active', created_at: '2026-02-01T00:00:00Z', updated_at: now() };
    store.email_scenarios.push(emailScenario);
    store.email_steps.push({ id: uuid(), scenario_id: emailScenario.id, subject: 'セミナーへのご登録ありがとうございます', body_html: '<p>ご登録ありがとうございます。</p>', delay_minutes: 0, sort_order: 0 }, { id: uuid(), scenario_id: emailScenario.id, subject: '明日のセミナーのご案内', body_html: '<p>明日のセミナーの詳細をお送りします。</p>', delay_minutes: 1440, sort_order: 1 }, { id: uuid(), scenario_id: emailScenario.id, subject: 'セミナー資料のダウンロード', body_html: '<p>セミナー資料はこちらからダウンロードできます。</p>', delay_minutes: 4320, sort_order: 2 });
    // LINE scenarios
    store.line_scenarios.push({
        id: uuid(), user_id: userId, name: '友だち追加ステップ', trigger_type: 'follow', trigger_config: {}, status: 'active', created_at: '2026-02-01T00:00:00Z', updated_at: now(),
    });
    // Courses
    const course = { id: uuid(), user_id: userId, name: 'マーケティング基礎講座', description: '全10回のマーケティング動画講座', access_type: 'paid', product_id: products[0].id, status: 'published', created_at: '2026-02-01T00:00:00Z', updated_at: now() };
    store.courses.push(course);
    for (let i = 1; i <= 5; i++) {
        store.lessons.push({ id: uuid(), course_id: course.id, title: `レッスン${i}: マーケティング概論${i}`, description: `第${i}回の講義内容`, content_type: 'video', sort_order: i - 1, drip_days: (i - 1) * 7, is_preview: i === 1, created_at: now() });
    }
    // Events
    store.events.push({
        id: uuid(), user_id: userId, name: '無料マーケティングセミナー', description: 'マーケティングの基礎を90分で学ぶ',
        event_type: 'seminar_online', meeting_provider: 'zoom', meeting_url: 'https://zoom.us/j/123456789',
        start_at: '2026-03-15T14:00:00Z', end_at: '2026-03-15T15:30:00Z',
        capacity: 100, price: 0, status: 'upcoming',
        reminder_config: { enabled: true, channels: ['email', 'line'], timings: [1440, 60] },
        created_at: now(), updated_at: now(),
    });
    // Webinars
    store.webinars.push({
        id: uuid(), user_id: userId, name: 'セールスファネル構築マスター講座', description: 'エバーグリーンウェビナー',
        webinar_type: 'evergreen', status: 'scheduled', max_attendees: 500,
        popup_offers: [{ id: 'offer-1', trigger_seconds: 2700, product_id: products[0].id, headline: '今だけ特別価格！', description: 'ウェビナー参加者限定で50%OFF', cta_text: '特別価格で申し込む', duration_seconds: 300 }],
        created_at: now(), updated_at: now(),
    });
    // Page views (demo analytics)
    for (let i = 0; i < 150; i++) {
        store.page_views.push({
            id: uuid(), page_id: store.funnel_pages[0].id,
            visitor_id: `visitor-${Math.floor(Math.random() * 80)}`,
            utm_source: ['instagram', 'google', 'facebook', 'twitter', 'youtube'][Math.floor(Math.random() * 5)],
            viewed_at: new Date(Date.now() - Math.random() * 30 * 86400000).toISOString(),
        });
    }
    // Conversion events
    const sources = ['instagram', 'google', 'facebook', 'twitter', 'youtube'];
    for (let i = 0; i < 40; i++) {
        store.conversion_events.push({
            id: uuid(), contact_id: contacts[Math.floor(Math.random() * contacts.length)].id,
            event_type: ['optin', 'purchase', 'webinar_register'][Math.floor(Math.random() * 3)],
            event_data: {}, utm_source: sources[Math.floor(Math.random() * sources.length)],
            occurred_at: new Date(Date.now() - Math.random() * 30 * 86400000).toISOString(),
        });
    }
}
seed();
// ============================================================
// Query Interface (mimics Supabase client)
// ============================================================
// Result wrapper - makes mutation results chainable like Supabase
function mutationResult(rows) {
    return {
        data: rows,
        error: null,
        count: rows.length,
        select: (_fields) => {
            return {
                data: rows,
                error: null,
                count: rows.length,
                single: () => ({ data: rows[0] || null, error: rows[0] ? null : { message: 'Not found' } }),
                then(resolve) { resolve({ data: rows, error: null, count: rows.length }); },
            };
        },
        single: () => ({ data: rows[0] || null, error: rows[0] ? null : { message: 'Not found' } }),
        then(resolve) { resolve({ data: rows, error: null, count: rows.length }); },
    };
}
function query(table) {
    return new QueryBuilder(table);
}
exports.query = query;
class QueryBuilder {
    constructor(table) {
        this._filters = [];
        this._selectFields = null;
        this._orderField = null;
        this._orderAsc = true;
        this._limitVal = null;
        this._offsetVal = 0;
        this._isSingle = false;
        this._isCount = false;
        this._isHead = false;
        this._table = table;
    }
    select(fields, opts) {
        this._selectFields = fields || '*';
        if (opts?.count)
            this._isCount = true;
        if (opts?.head)
            this._isHead = true;
        return this;
    }
    eq(field, value) { this._filters.push(row => row[field] === value); return this; }
    neq(field, value) { this._filters.push(row => row[field] !== value); return this; }
    gt(field, value) { this._filters.push(row => row[field] > value); return this; }
    lt(field, value) { this._filters.push(row => row[field] < value); return this; }
    gte(field, value) { this._filters.push(row => row[field] >= value); return this; }
    lte(field, value) { this._filters.push(row => row[field] <= value); return this; }
    ilike(field, pattern) {
        const re = new RegExp(pattern.replace(/%/g, '.*'), 'i');
        this._filters.push(row => re.test(row[field] || ''));
        return this;
    }
    in(field, values) { this._filters.push(row => (Array.isArray(values) ? values : []).includes(row[field])); return this; }
    not(field, op, value) {
        if (op === 'is')
            this._filters.push(row => row[field] !== value);
        return this;
    }
    contains(field, value) { this._filters.push(row => JSON.stringify(row[field] || []).includes(JSON.stringify(value))); return this; }
    or(expr) { return this; } // simplified
    order(field, opts) { this._orderField = field; this._orderAsc = opts?.ascending ?? true; return this; }
    range(from, to) { this._offsetVal = from; this._limitVal = to - from + 1; return this; }
    limit(n) { this._limitVal = n; return this; }
    single() { this._isSingle = true; return this; }
    // Thenable - makes `await queryBuilder` work
    then(resolve, reject) {
        try {
            resolve(this._execute());
        }
        catch (e) {
            reject?.(e);
        }
    }
    _execute() {
        let rows = [...(store[this._table] || [])];
        for (const f of this._filters)
            rows = rows.filter(f);
        const count = rows.length;
        if (this._orderField) {
            const field = this._orderField;
            const asc = this._orderAsc;
            rows.sort((a, b) => {
                const av = a[field], bv = b[field];
                const cmp = av < bv ? -1 : av > bv ? 1 : 0;
                return asc ? cmp : -cmp;
            });
        }
        if (this._offsetVal > 0)
            rows = rows.slice(this._offsetVal);
        if (this._limitVal)
            rows = rows.slice(0, this._limitVal);
        if (this._isHead)
            return { count, error: null };
        if (this._isSingle)
            return { data: rows[0] || null, error: rows[0] ? null : { message: 'Not found' }, count };
        return { data: rows, error: null, count };
    }
    _applyFilters() {
        let rows = store[this._table] || [];
        for (const f of this._filters)
            rows = rows.filter(f);
        return rows;
    }
    // Mutations - return MutationBuilder that supports chaining .eq()/.select()/.single()
    insert(row) {
        return new MutationBuilder(this._table, 'insert', row, [...this._filters]);
    }
    update(updates) {
        return new MutationBuilder(this._table, 'update', updates, [...this._filters]);
    }
    upsert(row, opts) {
        return new MutationBuilder(this._table, 'upsert', row, [...this._filters]);
    }
    delete() {
        return new MutationBuilder(this._table, 'delete', null, [...this._filters]);
    }
}
// Chainable mutation builder - supports .eq()/.select()/.single() after insert/update/upsert/delete
class MutationBuilder {
    constructor(table, op, payload, filters) {
        this._executed = false;
        this._resultRows = [];
        this._table = table;
        this._op = op;
        this._payload = payload;
        this._filters = filters;
    }
    eq(field, value) { this._filters.push(row => row[field] === value); return this; }
    neq(field, value) { this._filters.push(row => row[field] !== value); return this; }
    not(field, op, value) {
        if (op === 'is')
            this._filters.push(row => row[field] !== value);
        return this;
    }
    in(field, values) { this._filters.push(row => values.includes(row[field])); return this; }
    _exec() {
        if (this._executed)
            return;
        this._executed = true;
        if (!store[this._table])
            store[this._table] = [];
        if (this._op === 'insert') {
            const newRow = { id: uuid(), ...this._payload, created_at: this._payload?.created_at || now(), updated_at: now() };
            store[this._table].push(newRow);
            this._resultRows = [newRow];
        }
        else if (this._op === 'update') {
            let rows = store[this._table];
            for (const f of this._filters)
                rows = rows.filter(f);
            rows.forEach(row => { Object.assign(row, this._payload, { updated_at: now() }); });
            this._resultRows = rows;
        }
        else if (this._op === 'upsert') {
            let rows = store[this._table];
            for (const f of this._filters)
                rows = rows.filter(f);
            if (rows.length > 0) {
                Object.assign(rows[0], this._payload, { updated_at: now() });
                this._resultRows = [rows[0]];
            }
            else {
                const newRow = { id: uuid(), ...this._payload, created_at: this._payload?.created_at || now(), updated_at: now() };
                store[this._table].push(newRow);
                this._resultRows = [newRow];
            }
        }
        else if (this._op === 'delete') {
            let toDelete = store[this._table];
            for (const f of this._filters)
                toDelete = toDelete.filter(f);
            store[this._table] = store[this._table].filter(r => !toDelete.includes(r));
            this._resultRows = [];
        }
    }
    select(_fields) {
        this._exec();
        return this;
    }
    single() {
        this._exec();
        const row = this._resultRows[0] || null;
        return { data: row, error: row ? null : { message: 'Not found' }, then(resolve) { resolve({ data: row, error: row ? null : { message: 'Not found' } }); } };
    }
    then(resolve, reject) {
        try {
            this._exec();
            if (this._op === 'delete') {
                resolve({ error: null });
            }
            else {
                resolve({ data: this._resultRows, error: null, count: this._resultRows.length });
            }
        }
        catch (e) {
            reject?.(e);
        }
    }
}
// ============================================================
// Demo Supabase-compatible client
// ============================================================
exports.demoSupabase = {
    from: (table) => query(table),
    storage: {
        from: (_bucket) => ({
            createSignedUploadUrl: async (key) => ({ data: { signedUrl: `/demo-upload/${key}` }, error: null }),
            getPublicUrl: (key, _opts) => ({ data: { publicUrl: `/demo-media/${key}` } }),
            remove: async (_keys) => ({ error: null }),
        }),
    },
    rpc: async (_fn, _params) => ({ data: null, error: null }),
};
