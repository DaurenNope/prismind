-- Time Sensitivity fields for analyzer
-- Adds columns to indicate if content is time-sensitive and how urgent it is

ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS time_sensitive boolean,
  ADD COLUMN IF NOT EXISTS urgency_score numeric,
  ADD COLUMN IF NOT EXISTS relevance_window text,
  ADD COLUMN IF NOT EXISTS time_sensitive_reasons text[];

