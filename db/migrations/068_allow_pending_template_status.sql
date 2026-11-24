-- 068: Allow PENDING in message_templates_status_check
-- Expands status check constraint to accept PENDING in addition to SUBMITTED
-- to prevent constraint violation errors when syncing or saving Meta template states.

ALTER TABLE coexistence.message_templates
  DROP CONSTRAINT IF EXISTS message_templates_status_check;

ALTER TABLE coexistence.message_templates
  ADD CONSTRAINT message_templates_status_check
  CHECK (status IN ('DRAFT','SUBMITTED','PENDING','APPROVED','REJECTED','PAUSED','DISABLED'));
