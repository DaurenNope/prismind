-- Persona transformations and scheduling tables

CREATE TABLE IF NOT EXISTS mimesis_transformations (
  id BIGSERIAL PRIMARY KEY,
  persona_key TEXT NOT NULL,
  source_post_id TEXT NOT NULL,
  platform TEXT CHECK (platform IN ('twitter','threads','telegram')) NOT NULL,
  content TEXT NOT NULL,
  score REAL DEFAULT 0,
  ready_for_posting BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scheduled_posts (
  id BIGSERIAL PRIMARY KEY,
  persona_key TEXT NOT NULL,
  platform TEXT CHECK (platform IN ('twitter','threads','telegram')) NOT NULL,
  content TEXT NOT NULL,
  content_type TEXT NOT NULL CHECK (content_type IN ('single_tweet', 'thread', 'telegram_message')) DEFAULT 'single_tweet',
  scheduled_time TIMESTAMPTZ NOT NULL,
  status TEXT DEFAULT 'scheduled',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS posted_content (
  id BIGSERIAL PRIMARY KEY,
  scheduled_post_id BIGINT REFERENCES scheduled_posts(id) ON DELETE SET NULL,
  persona_key TEXT NOT NULL,
  platform TEXT CHECK (platform IN ('twitter','threads','telegram')) NOT NULL,
  platform_post_id TEXT,
  posted_at TIMESTAMPTZ DEFAULT NOW(),
  engagement_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_mimesis_transformations_ready ON mimesis_transformations(ready_for_posting);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_when ON scheduled_posts(scheduled_time);


