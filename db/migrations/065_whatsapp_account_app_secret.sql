-- 065_whatsapp_account_app_secret.sql
-- Store optional per-account Meta App Secret (AES-256-GCM encrypted) so multi-tenant
-- WhatsApp accounts using separate client Meta Apps verify webhook signatures independently.
ALTER TABLE coexistence.whatsapp_accounts
  ADD COLUMN IF NOT EXISTS meta_app_secret_encrypted TEXT;
