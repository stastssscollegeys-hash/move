-- ============================================================
-- FunnelForge SS - Full Database Schema
-- Supabase PostgreSQL
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. Users
-- ============================================================
CREATE TABLE system_users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'marketer' CHECK (role IN ('admin', 'marketer')),
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 2. Tags
-- ============================================================
CREATE TABLE tags (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  color TEXT DEFAULT '#6C5CE7',
  auto_assign_rules JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, name)
);

-- ============================================================
-- 3. Contacts (CRM)
-- ============================================================
CREATE TABLE contacts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  email TEXT,
  line_user_id TEXT,
  name TEXT,
  phone TEXT,
  score INTEGER DEFAULT 0,
  custom_fields JSONB DEFAULT '{}',
  source TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  operator_id UUID REFERENCES system_users(id),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'unsubscribed', 'bounced', 'blocked')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contacts_user_id ON contacts(user_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_line_user_id ON contacts(line_user_id);
CREATE INDEX idx_contacts_status ON contacts(status);
CREATE INDEX idx_contacts_source ON contacts(source);
CREATE INDEX idx_contacts_utm ON contacts(utm_source, utm_medium, utm_campaign);

CREATE TABLE contact_tags (
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (contact_id, tag_id)
);

-- ============================================================
-- 4. Media Management
-- ============================================================
CREATE TABLE media_files (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  original_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  file_type TEXT NOT NULL CHECK (file_type IN ('image', 'video', 'pdf', 'audio')),
  size_bytes BIGINT NOT NULL,
  url TEXT NOT NULL,
  thumbnail_url TEXT,
  duration_seconds INTEGER,
  width INTEGER,
  height INTEGER,
  folder TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_media_user_id ON media_files(user_id);
CREATE INDEX idx_media_file_type ON media_files(file_type);

-- ============================================================
-- 5. Funnels
-- ============================================================
CREATE TABLE funnels (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  custom_domain TEXT,
  funnel_map JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE funnel_pages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  funnel_id UUID NOT NULL REFERENCES funnels(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  slug TEXT NOT NULL,
  page_type TEXT NOT NULL CHECK (page_type IN ('lp', 'sales', 'optin', 'thankyou', 'webinar_register', 'video_watch', 'upsell', 'order_form')),
  elements JSONB DEFAULT '[]',
  sort_order INTEGER DEFAULT 0,
  published_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  popup_config JSONB,
  ab_variants JSONB DEFAULT '[]',
  seo_title TEXT,
  seo_description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(funnel_id, slug)
);

CREATE INDEX idx_funnel_pages_funnel_id ON funnel_pages(funnel_id);

CREATE TABLE page_views (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  page_id UUID NOT NULL REFERENCES funnel_pages(id) ON DELETE CASCADE,
  visitor_id TEXT NOT NULL,
  contact_id UUID REFERENCES contacts(id),
  ab_variant_id TEXT,
  ip_address TEXT,
  user_agent TEXT,
  referrer TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  viewed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_page_views_page_id ON page_views(page_id);
CREATE INDEX idx_page_views_viewed_at ON page_views(viewed_at);

-- ============================================================
-- 6. Email
-- ============================================================
CREATE TABLE email_scenarios (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  trigger_type TEXT NOT NULL CHECK (trigger_type IN ('optin', 'tag_added', 'purchase', 'manual', 'date_trigger')),
  trigger_config JSONB DEFAULT '{}',
  status TEXT DEFAULT 'draft' CHECK (status IN ('active', 'paused', 'draft')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_steps (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  scenario_id UUID NOT NULL REFERENCES email_scenarios(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  body_html TEXT NOT NULL,
  body_text TEXT,
  delay_minutes INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER DEFAULT 0,
  ab_subject TEXT,
  ab_body_html TEXT,
  conditions JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_broadcasts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  body_html TEXT NOT NULL,
  segment_id UUID,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'sending', 'sent')),
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  total_sent INTEGER DEFAULT 0,
  total_opened INTEGER DEFAULT 0,
  total_clicked INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_send_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  scenario_id UUID REFERENCES email_scenarios(id),
  broadcast_id UUID REFERENCES email_broadcasts(id),
  step_id UUID REFERENCES email_steps(id),
  status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed')),
  ses_message_id TEXT,
  sent_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_send_logs_contact ON email_send_logs(contact_id);
CREATE INDEX idx_email_send_logs_status ON email_send_logs(status);

-- Email domain auth (DKIM/DMARC/SPF)
CREATE TABLE email_domain_auth (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  domain TEXT NOT NULL,
  dkim_status TEXT DEFAULT 'pending' CHECK (dkim_status IN ('pending', 'verified', 'failed')),
  dmarc_status TEXT DEFAULT 'pending' CHECK (dmarc_status IN ('pending', 'verified', 'failed')),
  spf_status TEXT DEFAULT 'pending' CHECK (spf_status IN ('pending', 'verified', 'failed')),
  dns_records JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 7. LINE
-- ============================================================
CREATE TABLE line_scenarios (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  trigger_type TEXT NOT NULL CHECK (trigger_type IN ('follow', 'tag_added', 'keyword', 'manual', 'date_trigger')),
  trigger_config JSONB DEFAULT '{}',
  status TEXT DEFAULT 'draft' CHECK (status IN ('active', 'paused', 'draft')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE line_steps (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  scenario_id UUID NOT NULL REFERENCES line_scenarios(id) ON DELETE CASCADE,
  message_type TEXT NOT NULL CHECK (message_type IN ('text', 'flex', 'image', 'video', 'richmenu_switch', 'carousel', 'template')),
  content JSONB NOT NULL,
  delay_minutes INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER DEFAULT 0,
  conditions JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE line_broadcasts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  message_type TEXT NOT NULL,
  content JSONB NOT NULL,
  segment_id UUID,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'sending', 'sent')),
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  total_sent INTEGER DEFAULT 0,
  total_read INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE line_send_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  scenario_id UUID REFERENCES line_scenarios(id),
  broadcast_id UUID REFERENCES line_broadcasts(id),
  step_id UUID REFERENCES line_steps(id),
  status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'delivered', 'read', 'failed')),
  line_message_id TEXT,
  sent_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_line_send_logs_contact ON line_send_logs(contact_id);

-- Rich menu
CREATE TABLE rich_menus (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  line_rich_menu_id TEXT,
  image_url TEXT NOT NULL,
  areas JSONB DEFAULT '[]',
  display_conditions JSONB DEFAULT '[]',
  is_default BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Individual chat
CREATE TABLE line_chats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES system_users(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE line_chat_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_id UUID NOT NULL REFERENCES line_chats(id) ON DELETE CASCADE,
  direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
  message_type TEXT NOT NULL CHECK (message_type IN ('text', 'image', 'video', 'sticker')),
  content TEXT NOT NULL,
  sent_at TIMESTAMPTZ DEFAULT NOW()
);

-- LINE settings
CREATE TABLE line_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID UNIQUE NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  channel_id TEXT NOT NULL,
  channel_secret TEXT NOT NULL,
  channel_access_token TEXT NOT NULL,
  webhook_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 8. SMS
-- ============================================================
CREATE TABLE sms_broadcasts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  segment_id UUID,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'scheduled', 'sending', 'sent')),
  scheduled_at TIMESTAMPTZ,
  sent_at TIMESTAMPTZ,
  total_sent INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 9. Products & Orders
-- ============================================================
CREATE TABLE product_groups (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  price INTEGER NOT NULL,
  currency TEXT DEFAULT 'jpy',
  payment_type TEXT NOT NULL CHECK (payment_type IN ('one_time', 'subscription', 'installment')),
  installment_count INTEGER,
  stripe_product_id TEXT,
  stripe_price_id TEXT,
  product_group_id UUID REFERENCES product_groups(id),
  order_bump_product_id UUID REFERENCES products(id),
  upsell_product_id UUID REFERENCES products(id),
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id),
  product_id UUID NOT NULL REFERENCES products(id),
  amount INTEGER NOT NULL,
  currency TEXT DEFAULT 'jpy',
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'refunded')),
  stripe_payment_intent_id TEXT,
  stripe_subscription_id TEXT,
  is_order_bump BOOLEAN DEFAULT FALSE,
  is_upsell BOOLEAN DEFAULT FALSE,
  receipt_url TEXT,
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_contact ON orders(contact_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_paid_at ON orders(paid_at);

-- Stripe settings
CREATE TABLE stripe_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID UNIQUE NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  stripe_secret_key TEXT NOT NULL,
  stripe_publishable_key TEXT NOT NULL,
  stripe_webhook_secret TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 10. Membership Site
-- ============================================================
CREATE TABLE courses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  thumbnail_url TEXT,
  access_type TEXT DEFAULT 'paid' CHECK (access_type IN ('free', 'paid', 'bundle')),
  product_id UUID REFERENCES products(id),
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE lessons (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT DEFAULT '',
  content_type TEXT NOT NULL CHECK (content_type IN ('video', 'pdf', 'text', 'audio')),
  media_id UUID REFERENCES media_files(id),
  content_html TEXT,
  sort_order INTEGER DEFAULT 0,
  drip_days INTEGER,
  is_preview BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE enrollments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
  enrolled_at TIMESTAMPTZ DEFAULT NOW(),
  completed_lessons TEXT[] DEFAULT '{}',
  progress_percent INTEGER DEFAULT 0,
  last_accessed_at TIMESTAMPTZ,
  UNIQUE(contact_id, course_id)
);

CREATE TABLE lesson_comments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  lesson_id UUID NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES contacts(id),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE bundle_courses (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  course_ids UUID[] NOT NULL,
  product_id UUID REFERENCES products(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 11. Events & Reservations
-- ============================================================
CREATE TABLE events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  event_type TEXT NOT NULL CHECK (event_type IN ('seminar_online', 'seminar_offline', 'consultation', 'group_session')),
  venue TEXT,
  meeting_url TEXT,
  meeting_provider TEXT CHECK (meeting_provider IN ('zoom', 'google_meet')),
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  capacity INTEGER,
  price INTEGER DEFAULT 0,
  product_id UUID REFERENCES products(id),
  reminder_config JSONB DEFAULT '{"enabled":false,"channels":[],"timings":[]}',
  status TEXT DEFAULT 'upcoming' CHECK (status IN ('upcoming', 'ongoing', 'ended', 'cancelled')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE event_reservations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES contacts(id),
  status TEXT DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled', 'attended', 'no_show')),
  payment_status TEXT DEFAULT 'free' CHECK (payment_status IN ('free', 'paid', 'pending', 'refunded')),
  order_id UUID REFERENCES orders(id),
  receipt_number TEXT,
  reserved_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(event_id, contact_id)
);

CREATE TABLE calendar_slots (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL,
  available_days INTEGER[] NOT NULL, -- 0=Sun
  available_hours JSONB NOT NULL, -- {"start":"09:00","end":"18:00"}
  buffer_minutes INTEGER DEFAULT 0,
  max_per_day INTEGER DEFAULT 10,
  price INTEGER DEFAULT 0,
  product_id UUID REFERENCES products(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE calendar_bookings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  slot_id UUID NOT NULL REFERENCES calendar_slots(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES contacts(id),
  start_at TIMESTAMPTZ NOT NULL,
  end_at TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'confirmed' CHECK (status IN ('confirmed', 'cancelled', 'completed')),
  meeting_url TEXT,
  order_id UUID REFERENCES orders(id),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 12. Webinars
-- ============================================================
CREATE TABLE webinars (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  webinar_type TEXT NOT NULL CHECK (webinar_type IN ('live', 'auto', 'evergreen')),
  status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'live', 'ended', 'archived')),
  scheduled_at TIMESTAMPTZ,
  zoom_meeting_id TEXT,
  zoom_join_url TEXT,
  video_media_id UUID REFERENCES media_files(id),
  schedule_config JSONB, -- for evergreen
  popup_offers JSONB DEFAULT '[]',
  registration_page_id UUID REFERENCES funnel_pages(id),
  max_attendees INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE webinar_attendees (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  webinar_id UUID NOT NULL REFERENCES webinars(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES contacts(id),
  status TEXT DEFAULT 'registered' CHECK (status IN ('registered', 'attended', 'no_show')),
  joined_at TIMESTAMPTZ,
  left_at TIMESTAMPTZ,
  watched_seconds INTEGER DEFAULT 0,
  registered_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(webinar_id, contact_id)
);

CREATE TABLE webinar_chats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  webinar_id UUID NOT NULL REFERENCES webinars(id) ON DELETE CASCADE,
  contact_id UUID REFERENCES contacts(id),
  message TEXT NOT NULL,
  sent_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE webinar_polls (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  webinar_id UUID NOT NULL REFERENCES webinars(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  options TEXT[] NOT NULL,
  results JSONB DEFAULT '{}',
  is_active BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 13. Affiliate
-- ============================================================
CREATE TABLE affiliate_programs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  commission_type TEXT NOT NULL CHECK (commission_type IN ('fixed', 'percentage')),
  commission_value INTEGER NOT NULL,
  cookie_days INTEGER DEFAULT 30,
  two_tier BOOLEAN DEFAULT FALSE,
  second_tier_rate INTEGER,
  product_ids UUID[] DEFAULT '{}',
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE affiliate_partners (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  program_id UUID NOT NULL REFERENCES affiliate_programs(id) ON DELETE CASCADE,
  contact_id UUID NOT NULL REFERENCES contacts(id),
  affiliate_code TEXT UNIQUE NOT NULL,
  referral_url TEXT NOT NULL,
  parent_partner_id UUID REFERENCES affiliate_partners(id),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'suspended')),
  total_referrals INTEGER DEFAULT 0,
  total_sales INTEGER DEFAULT 0,
  total_commission INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE affiliate_referrals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  partner_id UUID NOT NULL REFERENCES affiliate_partners(id),
  contact_id UUID NOT NULL REFERENCES contacts(id),
  order_id UUID REFERENCES orders(id),
  commission_amount INTEGER NOT NULL,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'paid', 'rejected')),
  approved_at TIMESTAMPTZ,
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 14. Custom Forms
-- ============================================================
CREATE TABLE custom_forms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  form_type TEXT NOT NULL CHECK (form_type IN ('survey', 'application', 'feedback', 'quiz')),
  fields JSONB NOT NULL DEFAULT '[]',
  thank_you_message TEXT DEFAULT 'ご回答ありがとうございます。',
  tag_on_submit TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'closed')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE form_submissions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  form_id UUID NOT NULL REFERENCES custom_forms(id) ON DELETE CASCADE,
  contact_id UUID REFERENCES contacts(id),
  responses JSONB NOT NULL,
  submitted_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 15. Analytics & Tracking
-- ============================================================
CREATE TABLE ad_trackings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  utm_source TEXT NOT NULL,
  utm_medium TEXT NOT NULL,
  utm_campaign TEXT NOT NULL,
  utm_content TEXT,
  tracking_url TEXT NOT NULL,
  clicks INTEGER DEFAULT 0,
  registrations INTEGER DEFAULT 0,
  purchases INTEGER DEFAULT 0,
  revenue INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE link_clicks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID REFERENCES contacts(id),
  url TEXT NOT NULL,
  source_type TEXT NOT NULL CHECK (source_type IN ('email', 'line', 'sms', 'funnel')),
  source_id TEXT NOT NULL,
  clicked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_link_clicks_contact ON link_clicks(contact_id);
CREATE INDEX idx_link_clicks_source ON link_clicks(source_type, source_id);

CREATE TABLE conversion_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id),
  event_type TEXT NOT NULL CHECK (event_type IN ('optin', 'purchase', 'webinar_register', 'webinar_attend', 'course_enroll', 'form_submit')),
  event_data JSONB DEFAULT '{}',
  source TEXT,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversion_events_contact ON conversion_events(contact_id);
CREATE INDEX idx_conversion_events_type ON conversion_events(event_type);
CREATE INDEX idx_conversion_events_occurred ON conversion_events(occurred_at);

-- Segments
CREATE TABLE segments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  conditions JSONB NOT NULL DEFAULT '[]',
  logic TEXT DEFAULT 'AND' CHECK (logic IN ('AND', 'OR')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 16. Webhooks & Integrations
-- ============================================================
CREATE TABLE webhook_endpoints (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  events TEXT[] NOT NULL,
  secret TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE webhook_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
  event TEXT NOT NULL,
  payload JSONB NOT NULL,
  response_status INTEGER,
  response_body TEXT,
  delivered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE google_sheet_exports (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  spreadsheet_id TEXT NOT NULL,
  sheet_name TEXT NOT NULL,
  data_source TEXT NOT NULL CHECK (data_source IN ('contacts', 'orders', 'reservations', 'form_submissions')),
  auto_sync BOOLEAN DEFAULT FALSE,
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 17. Custom Domains
-- ============================================================
CREATE TABLE custom_domains (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  domain TEXT UNIQUE NOT NULL,
  status TEXT DEFAULT 'pending_dns' CHECK (status IN ('pending_dns', 'active', 'error')),
  ssl_status TEXT DEFAULT 'pending' CHECK (ssl_status IN ('pending', 'active', 'error')),
  dns_records JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 18. Email Settings
-- ============================================================
CREATE TABLE email_settings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID UNIQUE NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  from_email TEXT NOT NULL,
  from_name TEXT NOT NULL,
  reply_to TEXT,
  ses_region TEXT DEFAULT 'ap-northeast-1',
  ses_access_key_id TEXT,
  ses_secret_access_key TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Updated_at triggers
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_users_updated BEFORE UPDATE ON system_users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_contacts_updated BEFORE UPDATE ON contacts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_funnels_updated BEFORE UPDATE ON funnels FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_funnel_pages_updated BEFORE UPDATE ON funnel_pages FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_email_scenarios_updated BEFORE UPDATE ON email_scenarios FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_line_scenarios_updated BEFORE UPDATE ON line_scenarios FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_products_updated BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_segments_updated BEFORE UPDATE ON segments FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_courses_updated BEFORE UPDATE ON courses FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_events_updated BEFORE UPDATE ON events FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_webinars_updated BEFORE UPDATE ON webinars FOR EACH ROW EXECUTE FUNCTION update_updated_at();
