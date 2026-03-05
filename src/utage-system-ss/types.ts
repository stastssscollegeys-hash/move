// ============================================================
// UTAGE System SS - Type Definitions
// Phase 1 MVP: Funnel + Email/LINE + Payment + CRM + Dashboard
// ============================================================

// --- Auth & Users ---

export interface SystemUser {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'marketer';
  created_at: string;
  updated_at: string;
}

// --- Contacts (CRM) ---

export interface Contact {
  id: string;
  user_id: string; // owner (marketer)
  email: string | null;
  line_user_id: string | null;
  name: string | null;
  phone: string | null;
  tags: string[];
  score: number;
  custom_fields: Record<string, string>;
  source: string | null; // utm_source etc.
  status: 'active' | 'unsubscribed' | 'bounced' | 'blocked';
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  user_id: string;
  name: string;
  color: string;
  created_at: string;
}

// --- Funnels ---

export interface Funnel {
  id: string;
  user_id: string;
  name: string;
  status: 'draft' | 'published' | 'archived';
  pages: FunnelPage[];
  created_at: string;
  updated_at: string;
}

export interface FunnelPage {
  id: string;
  funnel_id: string;
  title: string;
  slug: string;
  page_type: 'lp' | 'sales' | 'optin' | 'thankyou' | 'webinar_register';
  elements: PageElement[];
  sort_order: number;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageElement {
  id: string;
  type: 'text' | 'image' | 'video' | 'button' | 'form' | 'countdown' | 'spacer' | 'divider';
  props: Record<string, unknown>;
  position: { x: number; y: number; w: number; h: number };
}

// --- Email ---

export interface EmailScenario {
  id: string;
  user_id: string;
  name: string;
  trigger: 'optin' | 'tag_added' | 'purchase' | 'manual';
  status: 'active' | 'paused' | 'draft';
  steps: EmailStep[];
  created_at: string;
  updated_at: string;
}

export interface EmailStep {
  id: string;
  scenario_id: string;
  subject: string;
  body_html: string;
  delay_minutes: number; // 0 = immediately, 1440 = 1 day
  sort_order: number;
}

export interface EmailSendLog {
  id: string;
  contact_id: string;
  scenario_id: string;
  step_id: string;
  status: 'queued' | 'sent' | 'delivered' | 'opened' | 'clicked' | 'bounced' | 'failed';
  sent_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
}

// --- LINE ---

export interface LineScenario {
  id: string;
  user_id: string;
  name: string;
  trigger: 'follow' | 'tag_added' | 'keyword' | 'manual';
  status: 'active' | 'paused' | 'draft';
  steps: LineStep[];
  created_at: string;
  updated_at: string;
}

export interface LineStep {
  id: string;
  scenario_id: string;
  message_type: 'text' | 'flex' | 'image' | 'video' | 'richmenu_switch';
  content: Record<string, unknown>;
  delay_minutes: number;
  sort_order: number;
}

export interface LineSendLog {
  id: string;
  contact_id: string;
  scenario_id: string;
  step_id: string;
  status: 'queued' | 'sent' | 'delivered' | 'read' | 'failed';
  sent_at: string | null;
  read_at: string | null;
}

// --- Payment (Stripe) ---

export interface Product {
  id: string;
  user_id: string;
  name: string;
  description: string;
  price: number; // JPY
  currency: 'jpy';
  payment_type: 'one_time' | 'subscription' | 'installment';
  stripe_product_id: string | null;
  stripe_price_id: string | null;
  status: 'active' | 'archived';
  created_at: string;
  updated_at: string;
}

export interface Order {
  id: string;
  contact_id: string;
  product_id: string;
  amount: number;
  currency: 'jpy';
  status: 'pending' | 'paid' | 'failed' | 'refunded';
  stripe_payment_intent_id: string | null;
  stripe_subscription_id: string | null;
  paid_at: string | null;
  created_at: string;
}

// --- Dashboard / Analytics ---

export interface DashboardStats {
  total_contacts: number;
  new_contacts_today: number;
  total_revenue: number;
  revenue_this_month: number;
  email_sent_today: number;
  email_open_rate: number;
  line_sent_today: number;
  line_read_rate: number;
  active_funnels: number;
  conversion_rate: number;
}

export interface FunnelAnalytics {
  funnel_id: string;
  page_views: number;
  unique_visitors: number;
  optins: number;
  purchases: number;
  conversion_rate: number;
  period: 'today' | '7d' | '30d' | 'all';
}

// --- API Request/Response ---

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  pagination?: {
    page: number;
    per_page: number;
    total: number;
    total_pages: number;
  };
}

export interface ContactListQuery {
  page?: number;
  per_page?: number;
  tags?: string[];
  status?: Contact['status'];
  search?: string;
  sort_by?: 'created_at' | 'score' | 'name';
  sort_order?: 'asc' | 'desc';
}

export interface SegmentCondition {
  field: string; // 'tag', 'score', 'email_opened', 'purchased', 'source'
  operator: 'eq' | 'neq' | 'gt' | 'lt' | 'contains' | 'in';
  value: string | number | string[];
}

export interface Segment {
  id: string;
  user_id: string;
  name: string;
  conditions: SegmentCondition[];
  logic: 'AND' | 'OR';
  contact_count: number;
  created_at: string;
  updated_at: string;
}
