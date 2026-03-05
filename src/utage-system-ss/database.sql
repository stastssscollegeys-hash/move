-- ============================================================
-- UTAGE System SS - Database Schema (Supabase PostgreSQL)
-- Phase 1 MVP
-- ============================================================

-- Enable UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. Users (system_users)
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
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'unsubscribed', 'bounced', 'blocked')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contacts_user_id ON contacts(user_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_line_user_id ON contacts(line_user_id);
CREATE INDEX idx_contacts_status ON contacts(status);

-- Contact-Tag junction
CREATE TABLE contact_tags (
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
  assigned_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (contact_id, tag_id)
);

-- ============================================================
-- 4. Funnels
-- ============================================================
CREATE TABLE funnels (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE funnel_pages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  funnel_id UUID NOT NULL REFERENCES funnels(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  slug TEXT NOT NULL,
  page_type TEXT NOT NULL CHECK (page_type IN ('lp', 'sales', 'optin', 'thankyou', 'webinar_register')),
  elements JSONB DEFAULT '[]',
  sort_order INTEGER DEFAULT 0,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(funnel_id, slug)
);

CREATE INDEX idx_funnel_pages_funnel_id ON funnel_pages(funnel_id);

-- Page view tracking
CREATE TABLE page_views (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  page_id UUID NOT NULL REFERENCES funnel_pages(id) ON DELETE CASCADE,
  visitor_id TEXT NOT NULL, -- anonymous or contact_id
  contact_id UUID REFERENCES contacts(id),
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
-- 5. Email Scenarios (Step Mail)
-- ============================================================
CREATE TABLE email_scenarios (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  trigger_type TEXT NOT NULL CHECK (trigger_type IN ('optin', 'tag_added', 'purchase', 'manual')),
  trigger_config JSONB DEFAULT '{}', -- e.g. { "tag_id": "xxx" }
  status TEXT DEFAULT 'draft' CHECK (status IN ('active', 'paused', 'draft')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_steps (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  scenario_id UUID NOT NULL REFERENCES email_scenarios(id) ON DELETE CASCADE,
  subject TEXT NOT NULL,
  body_html TEXT NOT NULL,
  delay_minutes INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_send_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  scenario_id UUID NOT NULL REFERENCES email_scenarios(id),
  step_id UUID NOT NULL REFERENCES email_steps(id),
  status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed')),
  ses_message_id TEXT,
  sent_at TIMESTAMPTZ,
  opened_at TIMESTAMPTZ,
  clicked_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_email_send_logs_contact_id ON email_send_logs(contact_id);
CREATE INDEX idx_email_send_logs_status ON email_send_logs(status);
CREATE INDEX idx_email_send_logs_sent_at ON email_send_logs(sent_at);

-- ============================================================
-- 6. LINE Scenarios (Step Delivery)
-- ============================================================
CREATE TABLE line_scenarios (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  trigger_type TEXT NOT NULL CHECK (trigger_type IN ('follow', 'tag_added', 'keyword', 'manual')),
  trigger_config JSONB DEFAULT '{}',
  status TEXT DEFAULT 'draft' CHECK (status IN ('active', 'paused', 'draft')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE line_steps (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  scenario_id UUID NOT NULL REFERENCES line_scenarios(id) ON DELETE CASCADE,
  message_type TEXT NOT NULL CHECK (message_type IN ('text', 'flex', 'image', 'video', 'richmenu_switch')),
  content JSONB NOT NULL,
  delay_minutes INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE line_send_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  contact_id UUID NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
  scenario_id UUID NOT NULL REFERENCES line_scenarios(id),
  step_id UUID NOT NULL REFERENCES line_steps(id),
  status TEXT DEFAULT 'queued' CHECK (status IN ('queued', 'sent', 'delivered', 'read', 'failed')),
  line_message_id TEXT,
  sent_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_line_send_logs_contact_id ON line_send_logs(contact_id);
CREATE INDEX idx_line_send_logs_status ON line_send_logs(status);

-- ============================================================
-- 7. Products & Orders (Stripe)
-- ============================================================
CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES system_users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  price INTEGER NOT NULL, -- JPY
  currency TEXT DEFAULT 'jpy',
  payment_type TEXT NOT NULL CHECK (payment_type IN ('one_time', 'subscription', 'installment')),
  stripe_product_id TEXT,
  stripe_price_id TEXT,
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
  paid_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_contact_id ON orders(contact_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_paid_at ON orders(paid_at);

-- ============================================================
-- 8. Segments
-- ============================================================
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
-- 9. LINE Settings (per user)
-- ============================================================
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
-- 10. Email Settings (per user)
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
-- 11. Stripe Settings (per user)
-- ============================================================
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
-- Updated_at trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_system_users_updated BEFORE UPDATE ON system_users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_contacts_updated BEFORE UPDATE ON contacts FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_funnels_updated BEFORE UPDATE ON funnels FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_funnel_pages_updated BEFORE UPDATE ON funnel_pages FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_email_scenarios_updated BEFORE UPDATE ON email_scenarios FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_line_scenarios_updated BEFORE UPDATE ON line_scenarios FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_products_updated BEFORE UPDATE ON products FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER tr_segments_updated BEFORE UPDATE ON segments FOR EACH ROW EXECUTE FUNCTION update_updated_at();
