-- 067_multi_tenant_isolation_fix.sql
-- Fix cross-tenant isolation by ensuring all tenant tables have org_id,
-- backfilling legacy unassigned rows to the primary organization, and adding indexes.

DO $$
DECLARE
  default_org_id UUID;
BEGIN
  -- 1. Identify primary organization
  SELECT id INTO default_org_id FROM coexistence.organizations ORDER BY created_at ASC LIMIT 1;

  -- 2. Add org_id to tables that were missing it
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='contact_field_definitions') THEN
    ALTER TABLE coexistence.contact_field_definitions
      ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    IF default_org_id IS NOT NULL THEN
      UPDATE coexistence.contact_field_definitions SET org_id = default_org_id WHERE org_id IS NULL;
    END IF;
    CREATE INDEX IF NOT EXISTS idx_contact_fields_org ON coexistence.contact_field_definitions(org_id);
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='team_members') THEN
    ALTER TABLE coexistence.team_members
      ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    IF default_org_id IS NOT NULL THEN
      UPDATE coexistence.team_members SET org_id = default_org_id WHERE org_id IS NULL;
    END IF;
    CREATE INDEX IF NOT EXISTS idx_team_members_org ON coexistence.team_members(org_id);
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='ai_models') THEN
    ALTER TABLE coexistence.ai_models
      ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    IF default_org_id IS NOT NULL THEN
      UPDATE coexistence.ai_models SET org_id = default_org_id WHERE org_id IS NULL;
    END IF;
    CREATE INDEX IF NOT EXISTS idx_ai_models_org ON coexistence.ai_models(org_id);
  END IF;

  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='coexistence' AND table_name='conversation_reads') THEN
    ALTER TABLE coexistence.conversation_reads
      ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES coexistence.organizations(id) ON DELETE CASCADE;
    IF default_org_id IS NOT NULL THEN
      UPDATE coexistence.conversation_reads SET org_id = default_org_id WHERE org_id IS NULL;
    END IF;
    CREATE INDEX IF NOT EXISTS idx_conversation_reads_org ON coexistence.conversation_reads(org_id);
  END IF;

  -- 3. Backfill legacy NULL org_id across existing tables
  IF default_org_id IS NOT NULL THEN
    UPDATE coexistence.whatsapp_accounts SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.contacts SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.chat_history SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.orders SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.chatbots SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.automation_executions SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.message_templates SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.broadcasts SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.pipelines SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.deals SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.agents SET org_id = default_org_id WHERE org_id IS NULL;
    UPDATE coexistence.media_library SET org_id = default_org_id WHERE org_id IS NULL;
  END IF;

END $$;
