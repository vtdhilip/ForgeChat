-- 064: Replace legacy single-tenant unique indexes on whatsapp_accounts with per-org indexes.
--
-- Migration 041 added `whatsapp_accounts_singleton` (UNIQUE ((TRUE))) and migration 013
-- added `idx_whatsapp_accounts_one_default` (UNIQUE (is_default) WHERE is_default = TRUE).
-- Both were global across the entire table. After migration 059 introduced multi-tenancy
-- (org_id), any second organization attempting to connect its own WhatsApp number hit a
-- 23505 unique violation on those legacy global indexes.
--
-- Note: `whatsapp_accounts_phone_number_id_key` (UNIQUE (phone_number_id)) remains global
-- because Meta webhooks route incoming messages by phone_number_id.

DROP INDEX IF EXISTS coexistence.whatsapp_accounts_singleton;
DROP INDEX IF EXISTS coexistence.idx_whatsapp_accounts_one_default;

CREATE UNIQUE INDEX IF NOT EXISTS idx_whatsapp_accounts_one_per_org
  ON coexistence.whatsapp_accounts(org_id)
  WHERE org_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_whatsapp_accounts_one_default
  ON coexistence.whatsapp_accounts(org_id)
  WHERE is_default = TRUE AND org_id IS NOT NULL;
