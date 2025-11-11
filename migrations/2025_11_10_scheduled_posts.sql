-- Scheduled Posts Table
-- Stores posts queued for publishing to social media platforms

CREATE TABLE IF NOT EXISTS scheduled_posts (
  id BIGSERIAL PRIMARY KEY,
  profile TEXT NOT NULL,
  platform TEXT NOT NULL,
  content TEXT NOT NULL,
  scheduled_at TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'pending',
  published_at TIMESTAMPTZ,
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for efficient querying of pending posts
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status, scheduled_at);

-- Index for querying by profile
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_profile ON scheduled_posts(profile, created_at DESC);

COMMENT ON TABLE scheduled_posts IS 'Queue of social media posts scheduled for publishing';
COMMENT ON COLUMN scheduled_posts.profile IS 'Profile key (e.g., qronoya, aspandead)';
COMMENT ON COLUMN scheduled_posts.platform IS 'Target platform (threads, telegram, twitter)';
COMMENT ON COLUMN scheduled_posts.status IS 'Status: pending, published, failed';
