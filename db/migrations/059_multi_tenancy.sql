-- 059_multi_tenancy.sql
-- Multi-Tenant SaaS schema: Organizations, Organization Members, and Tenant Scoping.

-- 1. Organizations table
CREATE TABLE IF NOT EXISTS coexistence.organizations (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         TEXT NOT NULL,
  slug         TEXT NOT NULL UNIQUE,
  plan         TEXT NOT NULL DEFAULT 'starter',
  settings     JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active    BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Organization Members table (Multi-user per tenant)
CREATE TABLE IF NOT EXISTS coexistence.organization_members (
  id          BIGSERIAL PRIMARY KEY,
  org_id      UUID NOT NULL REFERENCES coexistence.organizations(id) ON DELETE CASCADE,
  user_id     BIGINT NOT NULL REFERENCES coexistence.forgecrm_users(id) ON DELETE CASCADE,
  role        TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner','admin','member','agent','viewer')),
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user ON coexistence.organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_org ON coexistence.organization_members(org_id);

-- 3. Seed Primary Default Organization ("LINNDEN") if no orgs exist
DO $$
DECLARE
  default_org_id UUID;
  user_rec RECORD;
BEGIN
  -- Insert default org if table is empty
  IF NOT EXISTS (SELECT 1 FROM coexistence.organizations) THEN
    INSERT INTO coexistence.organizations (name, slug, plan, settings)
    VALUES ('LINNDEN', 'linnden', 'enterprise', '{"order_prefix": "LN-", "currency": "INR"}'::jsonb)
    RETURNING id INTO default_org_id;

    -- Attach all existing users to default org
    FOR user_rec IN SELECT id, role FROM coexistence.forgecrm_users LOOP
      INSERT INTO coexistence.organization_members (org_id, user_id, role)
      VALUES (
        default_org_id,
        user_rec.id,
        CASE WHEN user_rec.role = 'admin' THEN 'owner' ELSE 'member' END
      )
      ON CONFLICT (org_id, user_id) DO NOTHING;
    END LOOP;
  ELSE
    SELECT id INTO default_org_id FROM coexistence.organizations ORDER BY created_at ASC LIMIT 1;
  END IF;

  -- 4. Add org_id column to all tenant-scoped tables and backfill to default_org_id

  -- whatsapp_accounts
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='whatsapp_accounts') THEN
    ALTER TABLE coexistence.whatsapp_accounts ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.whatsapp_accounts SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_wa_accounts_org ON coexistence.whatsapp_accounts(org_id);
  END IF;

  -- contacts
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='contacts') THEN
    ALTER TABLE coexistence.contacts ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.contacts SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_contacts_org ON coexistence.contacts(org_id);
  END IF;

  -- chat_history
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='chat_history') THEN
    ALTER TABLE coexistence.chat_history ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.chat_history SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_chat_history_org ON coexistence.chat_history(org_id);
  END IF;

  -- orders
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='orders') THEN
    ALTER TABLE coexistence.orders ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.orders SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_orders_org ON coexistence.orders(org_id);
  END IF;

  -- chatbots (automations / flows)
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='chatbots') THEN
    ALTER TABLE coexistence.chatbots ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.chatbots SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_chatbots_org ON coexistence.chatbots(org_id);
  END IF;

  -- automation_executions
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='automation_executions') THEN
    ALTER TABLE coexistence.automation_executions ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.automation_executions SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_automation_executions_org ON coexistence.automation_executions(org_id);
  END IF;

  -- message_templates
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='message_templates') THEN
    ALTER TABLE coexistence.message_templates ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.message_templates SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_templates_org ON coexistence.message_templates(org_id);
  END IF;

  -- broadcasts
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='broadcasts') THEN
    ALTER TABLE coexistence.broadcasts ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.broadcasts SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_broadcasts_org ON coexistence.broadcasts(org_id);
  END IF;

  -- pipelines, pipeline_stages, deals
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='pipelines') THEN
    ALTER TABLE coexistence.pipelines ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.pipelines SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_pipelines_org ON coexistence.pipelines(org_id);
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='deals') THEN
    ALTER TABLE coexistence.deals ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.deals SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_deals_org ON coexistence.deals(org_id);
  END IF;

  -- agents
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='agents') THEN
    ALTER TABLE coexistence.agents ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.agents SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_agents_org ON coexistence.agents(org_id);
  END IF;

  -- media_library
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='media_library') THEN
    ALTER TABLE coexistence.media_library ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.media_library SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_media_library_org ON coexistence.media_library(org_id);
  END IF;

  -- categories & tags
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='categories') THEN
    ALTER TABLE coexistence.categories ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.categories SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_categories_org ON coexistence.categories(org_id);
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='tags') THEN
    ALTER TABLE coexistence.tags ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    UPDATE coexistence.tags SET org_id = default_org_id WHERE org_id IS NULL;
    CREATE INDEX IF NOT EXISTS idx_tags_org ON coexistence.tags(org_id);
  END IF;

END $$;
