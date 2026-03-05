// ============================================================
// FunnelForge SS - Type Definitions
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
  user_id: string;
  email: string | null;
  line_user_id: string | null;
  name: string | null;
  phone: string | null;
  tags: string[];
  score: number;
  custom_fields: Record<string, string>;
  source: string | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  status: 'active' | 'unsubscribed' | 'bounced' | 'blocked';
  operator_id: string | null; // staff assignment
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: string;
  user_id: string;
  name: string;
  color: string;
  auto_assign_rules: AutoTagRule[];
  created_at: string;
}

export interface AutoTagRule {
  trigger: 'page_view' | 'link_click' | 'purchase' | 'form_submit' | 'email_open' | 'line_follow';
  condition: Record<string, unknown>;
}

// --- Media Management ---

export interface MediaFile {
  id: string;
  user_id: string;
  filename: string;
  original_name: string;
  mime_type: string;
  file_type: 'image' | 'video' | 'pdf' | 'audio';
  size_bytes: number;
  url: string;
  thumbnail_url: string | null;
  duration_seconds: number | null; // for video/audio
  width: number | null;
  height: number | null;
  folder: string | null;
  created_at: string;
}

export interface MediaUploadRequest {
  file_type: MediaFile['file_type'];
  original_name: string;
  mime_type: string;
  size_bytes: number;
  folder?: string;
}

export interface MediaUploadResponse {
  upload_url: string; // presigned URL for direct upload
  media_id: string;
  key: string;
}

// --- Funnels ---

export interface Funnel {
  id: string;
  user_id: string;
  name: string;
  status: 'draft' | 'published' | 'archived';
  custom_domain: string | null;
  pages: FunnelPage[];
  funnel_map: FunnelMapNode[];
  created_at: string;
  updated_at: string;
}

export interface FunnelMapNode {
  page_id: string;
  next_page_ids: string[];
  position: { x: number; y: number };
}

export interface FunnelPage {
  id: string;
  funnel_id: string;
  title: string;
  slug: string;
  page_type: 'lp' | 'sales' | 'optin' | 'thankyou' | 'webinar_register' | 'video_watch' | 'upsell' | 'order_form';
  elements: PageElement[];
  sort_order: number;
  published_at: string | null;
  expires_at: string | null; // display period limit
  popup_config: PopupConfig | null;
  ab_variants: ABVariant[];
  seo_title: string | null;
  seo_description: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageElement {
  id: string;
  type: 'text' | 'image' | 'video' | 'button' | 'form' | 'countdown' | 'spacer' | 'divider'
    | 'progress_bar' | 'accordion' | 'carousel' | 'line_add_button' | 'payment_form'
    | 'order_bump' | 'popup' | 'video_player' | 'audio_player' | 'pdf_viewer';
  props: Record<string, unknown>;
  position: { x: number; y: number; w: number; h: number };
}

export interface PopupConfig {
  enabled: boolean;
  trigger: 'timer' | 'scroll' | 'exit_intent' | 'click';
  trigger_value: number; // seconds or scroll %
  content_elements: PageElement[];
}

export interface ABVariant {
  id: string;
  name: string;
  weight: number; // percentage 0-100
  elements: PageElement[];
  views: number;
  conversions: number;
}

// --- Email ---

export interface EmailScenario {
  id: string;
  user_id: string;
  name: string;
  trigger: 'optin' | 'tag_added' | 'purchase' | 'manual' | 'date_trigger';
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
  body_text: string | null;
  delay_minutes: number;
  sort_order: number;
  ab_subject: string | null; // A/B test alternative subject
  ab_body_html: string | null;
  conditions: StepCondition[];
}

export interface StepCondition {
  type: 'tag_exists' | 'tag_not_exists' | 'opened_previous' | 'clicked_previous' | 'purchased';
  value: string;
}

export interface EmailBroadcast {
  id: string;
  user_id: string;
  subject: string;
  body_html: string;
  segment_id: string | null;
  status: 'draft' | 'scheduled' | 'sending' | 'sent';
  scheduled_at: string | null;
  sent_at: string | null;
  total_sent: number;
  total_opened: number;
  total_clicked: number;
  created_at: string;
}

export interface EmailSendLog {
  id: string;
  contact_id: string;
  scenario_id: string | null;
  broadcast_id: string | null;
  step_id: string | null;
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
  trigger: 'follow' | 'tag_added' | 'keyword' | 'manual' | 'date_trigger';
  trigger_config: Record<string, unknown>; // e.g. { keyword: "資料" }
  status: 'active' | 'paused' | 'draft';
  steps: LineStep[];
  created_at: string;
  updated_at: string;
}

export interface LineStep {
  id: string;
  scenario_id: string;
  message_type: 'text' | 'flex' | 'image' | 'video' | 'richmenu_switch' | 'carousel' | 'template';
  content: Record<string, unknown>;
  delay_minutes: number;
  sort_order: number;
  conditions: StepCondition[];
}

export interface LineBroadcast {
  id: string;
  user_id: string;
  message_type: LineStep['message_type'];
  content: Record<string, unknown>;
  segment_id: string | null;
  status: 'draft' | 'scheduled' | 'sending' | 'sent';
  scheduled_at: string | null;
  sent_at: string | null;
  total_sent: number;
  total_read: number;
  created_at: string;
}

export interface LineSendLog {
  id: string;
  contact_id: string;
  scenario_id: string | null;
  broadcast_id: string | null;
  step_id: string | null;
  status: 'queued' | 'sent' | 'delivered' | 'read' | 'failed';
  sent_at: string | null;
  read_at: string | null;
}

export interface RichMenu {
  id: string;
  user_id: string;
  name: string;
  line_rich_menu_id: string | null;
  image_url: string;
  areas: RichMenuArea[];
  display_conditions: RichMenuCondition[];
  is_default: boolean;
  created_at: string;
}

export interface RichMenuArea {
  bounds: { x: number; y: number; width: number; height: number };
  action_type: 'url' | 'message' | 'tag_add' | 'richmenu_switch';
  action_value: string;
}

export interface RichMenuCondition {
  type: 'tag' | 'score_gt' | 'score_lt' | 'source' | 'purchase';
  value: string;
}

export interface LineIndividualChat {
  id: string;
  contact_id: string;
  user_id: string;
  messages: ChatMessage[];
}

export interface ChatMessage {
  id: string;
  direction: 'inbound' | 'outbound';
  message_type: 'text' | 'image' | 'video' | 'sticker';
  content: string;
  sent_at: string;
}

// --- SMS ---

export interface SmsBroadcast {
  id: string;
  user_id: string;
  body: string;
  segment_id: string | null;
  status: 'draft' | 'scheduled' | 'sending' | 'sent';
  scheduled_at: string | null;
  sent_at: string | null;
  total_sent: number;
  created_at: string;
}

// --- Payment (Stripe) ---

export interface Product {
  id: string;
  user_id: string;
  name: string;
  description: string;
  price: number;
  currency: 'jpy';
  payment_type: 'one_time' | 'subscription' | 'installment';
  installment_count: number | null; // for installment
  stripe_product_id: string | null;
  stripe_price_id: string | null;
  product_group_id: string | null;
  order_bump_product_id: string | null; // order bump
  upsell_product_id: string | null; // upsell after purchase
  status: 'active' | 'archived';
  created_at: string;
  updated_at: string;
}

export interface ProductGroup {
  id: string;
  user_id: string;
  name: string;
  product_ids: string[];
  created_at: string;
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
  is_order_bump: boolean;
  is_upsell: boolean;
  receipt_url: string | null;
  paid_at: string | null;
  created_at: string;
}

// --- Membership Site ---

export interface Course {
  id: string;
  user_id: string;
  name: string;
  description: string;
  thumbnail_url: string | null;
  access_type: 'free' | 'paid' | 'bundle';
  product_id: string | null; // linked product for paid access
  status: 'draft' | 'published' | 'archived';
  lessons: Lesson[];
  created_at: string;
  updated_at: string;
}

export interface Lesson {
  id: string;
  course_id: string;
  title: string;
  description: string;
  content_type: 'video' | 'pdf' | 'text' | 'audio';
  media_id: string | null;
  content_html: string | null;
  sort_order: number;
  drip_days: number | null; // days after enrollment to unlock
  is_preview: boolean;
  created_at: string;
}

export interface Enrollment {
  id: string;
  contact_id: string;
  course_id: string;
  enrolled_at: string;
  completed_lessons: string[]; // lesson_ids
  progress_percent: number;
  last_accessed_at: string | null;
}

export interface LessonComment {
  id: string;
  lesson_id: string;
  contact_id: string;
  content: string;
  created_at: string;
}

export interface BundleCourse {
  id: string;
  user_id: string;
  name: string;
  course_ids: string[];
  product_id: string | null;
  created_at: string;
}

// --- Events & Reservations ---

export interface Event {
  id: string;
  user_id: string;
  name: string;
  description: string;
  event_type: 'seminar_online' | 'seminar_offline' | 'consultation' | 'group_session';
  venue: string | null; // physical location or online URL
  meeting_url: string | null; // Zoom/Google Meet
  meeting_provider: 'zoom' | 'google_meet' | null;
  start_at: string;
  end_at: string;
  capacity: number | null;
  price: number; // 0 for free
  product_id: string | null;
  reminder_config: ReminderConfig;
  status: 'upcoming' | 'ongoing' | 'ended' | 'cancelled';
  created_at: string;
  updated_at: string;
}

export interface ReminderConfig {
  enabled: boolean;
  channels: ('email' | 'line' | 'sms')[];
  timings: number[]; // minutes before event (e.g. [1440, 60] = 1 day and 1 hour before)
}

export interface EventReservation {
  id: string;
  event_id: string;
  contact_id: string;
  status: 'confirmed' | 'cancelled' | 'attended' | 'no_show';
  payment_status: 'free' | 'paid' | 'pending' | 'refunded';
  order_id: string | null;
  receipt_number: string | null;
  reserved_at: string;
}

export interface CalendarSlot {
  id: string;
  user_id: string;
  name: string; // e.g. "個別相談30分"
  duration_minutes: number;
  available_days: number[]; // 0=Sun, 1=Mon, ...
  available_hours: { start: string; end: string }; // "09:00" - "18:00"
  buffer_minutes: number; // between appointments
  max_per_day: number;
  price: number;
  product_id: string | null;
  created_at: string;
}

export interface CalendarBooking {
  id: string;
  slot_id: string;
  contact_id: string;
  start_at: string;
  end_at: string;
  status: 'confirmed' | 'cancelled' | 'completed';
  meeting_url: string | null;
  order_id: string | null;
  created_at: string;
}

// --- Webinar ---

export interface Webinar {
  id: string;
  user_id: string;
  name: string;
  description: string;
  webinar_type: 'live' | 'auto' | 'evergreen';
  status: 'scheduled' | 'live' | 'ended' | 'archived';
  // Live webinar
  scheduled_at: string | null;
  zoom_meeting_id: string | null;
  zoom_join_url: string | null;
  // Auto/Evergreen webinar
  video_media_id: string | null;
  schedule_config: EverGreenConfig | null;
  // Popup offer
  popup_offers: WebinarPopupOffer[];
  // Registration
  registration_page_id: string | null; // funnel page
  max_attendees: number | null;
  created_at: string;
  updated_at: string;
}

export interface EverGreenConfig {
  available_times: string[]; // ["10:00", "14:00", "20:00"]
  available_days: number[];
  fake_live: boolean; // simulate live experience
  chat_replay: ChatReplayMessage[];
}

export interface ChatReplayMessage {
  offset_seconds: number;
  name: string;
  message: string;
}

export interface WebinarPopupOffer {
  id: string;
  trigger_seconds: number; // seconds into the webinar
  product_id: string;
  headline: string;
  description: string;
  cta_text: string;
  duration_seconds: number; // how long to show
}

export interface WebinarAttendee {
  id: string;
  webinar_id: string;
  contact_id: string;
  status: 'registered' | 'attended' | 'no_show';
  joined_at: string | null;
  left_at: string | null;
  watched_seconds: number;
  registered_at: string;
}

export interface WebinarChat {
  id: string;
  webinar_id: string;
  contact_id: string | null; // null for system messages
  message: string;
  sent_at: string;
}

export interface WebinarPoll {
  id: string;
  webinar_id: string;
  question: string;
  options: string[];
  results: Record<string, number>; // option -> count
  is_active: boolean;
  created_at: string;
}

// --- Affiliate / Partner ---

export interface AffiliateProgram {
  id: string;
  user_id: string;
  name: string;
  commission_type: 'fixed' | 'percentage';
  commission_value: number; // fixed JPY or percentage
  cookie_days: number; // tracking cookie duration
  two_tier: boolean; // second-tier affiliate
  second_tier_rate: number | null;
  product_ids: string[]; // applicable products
  status: 'active' | 'paused';
  created_at: string;
}

export interface AffiliatePartner {
  id: string;
  program_id: string;
  contact_id: string;
  affiliate_code: string;
  referral_url: string;
  parent_partner_id: string | null; // for two-tier
  status: 'pending' | 'approved' | 'rejected' | 'suspended';
  total_referrals: number;
  total_sales: number;
  total_commission: number;
  created_at: string;
}

export interface AffiliateReferral {
  id: string;
  partner_id: string;
  contact_id: string; // referred contact
  order_id: string | null;
  commission_amount: number;
  status: 'pending' | 'approved' | 'paid' | 'rejected';
  approved_at: string | null;
  paid_at: string | null;
  created_at: string;
}

// --- Forms ---

export interface CustomForm {
  id: string;
  user_id: string;
  name: string;
  form_type: 'survey' | 'application' | 'feedback' | 'quiz';
  fields: FormField[];
  thank_you_message: string;
  tag_on_submit: string | null;
  status: 'active' | 'closed';
  created_at: string;
}

export interface FormField {
  id: string;
  type: 'text' | 'textarea' | 'select' | 'radio' | 'checkbox' | 'date' | 'email' | 'phone' | 'rating';
  label: string;
  required: boolean;
  options: string[];
  placeholder: string | null;
}

export interface FormSubmission {
  id: string;
  form_id: string;
  contact_id: string | null;
  responses: Record<string, string>;
  submitted_at: string;
}

// --- Analytics ---

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
  active_webinars: number;
  active_courses: number;
  affiliate_commission_this_month: number;
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

export interface AdTracking {
  id: string;
  user_id: string;
  name: string; // e.g. "Facebook広告_セミナー"
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
  utm_content: string | null;
  tracking_url: string;
  clicks: number;
  registrations: number;
  purchases: number;
  revenue: number;
  created_at: string;
}

export interface LinkClick {
  id: string;
  contact_id: string | null;
  url: string;
  source_type: 'email' | 'line' | 'sms' | 'funnel';
  source_id: string;
  clicked_at: string;
}

export interface ConversionEvent {
  id: string;
  contact_id: string;
  event_type: 'optin' | 'purchase' | 'webinar_register' | 'webinar_attend' | 'course_enroll' | 'form_submit';
  event_data: Record<string, unknown>;
  source: string | null;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  occurred_at: string;
}

export interface CrossAnalysisQuery {
  axis_x: 'source' | 'utm_source' | 'utm_medium' | 'utm_campaign' | 'tag';
  axis_y: 'optin' | 'purchase' | 'revenue' | 'webinar_attend';
  period: '7d' | '30d' | '90d' | 'all';
}

export interface CrossAnalysisResult {
  labels: string[];
  datasets: { label: string; data: number[] }[];
}

// --- Webhooks & Integrations ---

export interface WebhookEndpoint {
  id: string;
  user_id: string;
  name: string;
  url: string;
  events: string[]; // 'contact.created', 'order.paid', etc.
  secret: string;
  is_active: boolean;
  created_at: string;
}

export interface WebhookLog {
  id: string;
  endpoint_id: string;
  event: string;
  payload: Record<string, unknown>;
  response_status: number | null;
  response_body: string | null;
  delivered_at: string | null;
  created_at: string;
}

export interface GoogleSheetExport {
  id: string;
  user_id: string;
  name: string;
  spreadsheet_id: string;
  sheet_name: string;
  data_source: 'contacts' | 'orders' | 'reservations' | 'form_submissions';
  auto_sync: boolean;
  last_synced_at: string | null;
  created_at: string;
}

// --- Domain Settings ---

export interface CustomDomain {
  id: string;
  user_id: string;
  domain: string;
  status: 'pending_dns' | 'active' | 'error';
  ssl_status: 'pending' | 'active' | 'error';
  dns_records: { type: string; name: string; value: string }[];
  created_at: string;
}

// --- Email Settings ---

export interface EmailDomainAuth {
  id: string;
  user_id: string;
  domain: string;
  dkim_status: 'pending' | 'verified' | 'failed';
  dmarc_status: 'pending' | 'verified' | 'failed';
  spf_status: 'pending' | 'verified' | 'failed';
  dns_records: { type: string; name: string; value: string }[];
  created_at: string;
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
  field: string;
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
