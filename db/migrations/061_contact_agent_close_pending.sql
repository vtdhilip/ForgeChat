-- 061_contact_agent_close_pending.sql
-- Add agent_close_pending and agent_last_run_at to contacts table for close summary sweeps
ALTER TABLE coexistence.contacts ADD COLUMN IF NOT EXISTS agent_close_pending BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE coexistence.contacts ADD COLUMN IF NOT EXISTS agent_last_run_at TIMESTAMPTZ;
