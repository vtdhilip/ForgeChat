-- 062_contact_agent_paused.sql
-- Add agent_paused column to contacts table for close summary sweep filtering
ALTER TABLE coexistence.contacts ADD COLUMN IF NOT EXISTS agent_paused BOOLEAN NOT NULL DEFAULT FALSE;
