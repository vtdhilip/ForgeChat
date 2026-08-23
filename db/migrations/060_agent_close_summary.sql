-- 060_agent_close_summary.sql
-- Add close summary columns to agents table
ALTER TABLE coexistence.agents ADD COLUMN IF NOT EXISTS close_summary_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE coexistence.agents ADD COLUMN IF NOT EXISTS close_idle_minutes INT NOT NULL DEFAULT 30;
