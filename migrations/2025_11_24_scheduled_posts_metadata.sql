-- Add metadata JSONB column to scheduled_posts table
-- This allows storing priority, viral_potential, time_sensitivity, and other scheduling metadata

-- Add metadata column if it doesn't exist
ALTER TABLE scheduled_posts 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Add index on metadata for efficient queries
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_metadata_priority 
ON scheduled_posts((metadata->>'priority'));

-- Add index on metadata time_sensitivity for filtering
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_metadata_time_sensitivity 
ON scheduled_posts((metadata->>'time_sensitivity'));

-- Add comment explaining the metadata structure
COMMENT ON COLUMN scheduled_posts.metadata IS 'JSONB field storing scheduling metadata: priority, viral_potential, time_sensitivity, trend_relevance, author_authority, scheduling_reason, persona, scheduled_by, scheduled_at';

