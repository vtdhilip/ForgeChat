-- 063_agent_handoff.sql
-- Add handoff configuration columns to coexistence.agents
ALTER TABLE coexistence.agents 
  ADD COLUMN IF NOT EXISTS handoff_enabled BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS handoff_user_ids JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS handoff_keywords JSONB DEFAULT '[]'::jsonb;
