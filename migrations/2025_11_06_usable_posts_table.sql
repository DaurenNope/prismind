-- Usable Posts Table - Curated by Agent
-- Only contains actual/fresh or evergreen content suitable for rewriting
-- Created: 2025-11-06

-- Create usable_posts table
CREATE TABLE IF NOT EXISTS usable_posts (
    -- Primary key (same as posts table)
    id BIGSERIAL PRIMARY KEY,
    post_id TEXT NOT NULL,
    platform TEXT NOT NULL,

    -- Core content (essential for rewriter)
    content TEXT NOT NULL,
    title TEXT,
    url TEXT NOT NULL,
    author TEXT,
    author_handle TEXT,
    created_at TIMESTAMPTZ NOT NULL,

    -- Essential analysis fields (required)
    ai_summary TEXT NOT NULL,
    category TEXT NOT NULL,
    fit_categories TEXT[],
    value_score NUMERIC NOT NULL CHECK (value_score > 0),
    quality_score NUMERIC NOT NULL CHECK (quality_score > 0),
    rewrite_score NUMERIC NOT NULL CHECK (rewrite_score > 0),

    -- Time sensitivity
    relevance_window TEXT NOT NULL,
    urgency_score NUMERIC,
    time_sensitive BOOLEAN DEFAULT FALSE,

    -- Persona matching (required for rewriter)
    best_persona_key TEXT,
    best_persona_score NUMERIC,
    persona_fit_scores JSONB,
    persona_fit_reasons JSONB,
    best_persona_reasons TEXT[],

    -- Discovery fields
    tags TEXT[],
    key_concepts TEXT[],
    topic TEXT,
    content_type TEXT,
    language TEXT,
    embedding TEXT,  -- JSON-encoded vector
    embedding_model TEXT,

    -- Rewrite-focused fields
    rewrite_readiness TEXT,
    rewrite_reasons TEXT[],
    rewrite_risks TEXT[],
    analysis_confidence NUMERIC,

    -- Metadata
    analysis_model TEXT NOT NULL,
    analyzed_at TIMESTAMPTZ NOT NULL,

    -- Curation metadata
    included_at TIMESTAMPTZ DEFAULT NOW(),
    inclusion_reason TEXT,  -- Why this post was included (e.g., 'truly_evergreen', 'fresh_time_sensitive')
    commentary_worthy BOOLEAN DEFAULT FALSE,  -- Manual flag for old but valuable posts

    -- Constraints
    UNIQUE(platform, post_id),
    CONSTRAINT valid_relevance_window CHECK (relevance_window IN ('same-day', '24-72h', 'this-week', 'this-month', 'evergreen')),
    CONSTRAINT valid_category CHECK (category != 'DEPRECATED')
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_usable_posts_relevance_window ON usable_posts(relevance_window);
CREATE INDEX IF NOT EXISTS idx_usable_posts_category ON usable_posts(category);
CREATE INDEX IF NOT EXISTS idx_usable_posts_best_persona ON usable_posts(best_persona_key);
CREATE INDEX IF NOT EXISTS idx_usable_posts_rewrite_score ON usable_posts(rewrite_score DESC);
CREATE INDEX IF NOT EXISTS idx_usable_posts_created_at ON usable_posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usable_posts_included_at ON usable_posts(included_at DESC);
CREATE INDEX IF NOT EXISTS idx_usable_posts_platform_post_id ON usable_posts(platform, post_id);
CREATE INDEX IF NOT EXISTS idx_usable_posts_commentary_worthy ON usable_posts(commentary_worthy) WHERE commentary_worthy = TRUE;

-- Add commentary_worthy column to posts table if it doesn't exist
ALTER TABLE posts ADD COLUMN IF NOT EXISTS commentary_worthy BOOLEAN DEFAULT FALSE;

-- Create index on posts.commentary_worthy for faster queries
CREATE INDEX IF NOT EXISTS idx_posts_commentary_worthy ON posts(commentary_worthy) WHERE commentary_worthy = TRUE;

-- Comments
COMMENT ON TABLE usable_posts IS 'Curated table containing only high-quality, evergreen or fresh time-sensitive posts suitable for rewriting';
COMMENT ON COLUMN usable_posts.inclusion_reason IS 'Reason for inclusion: truly_evergreen, fresh_time_sensitive, or commentary_worthy';
COMMENT ON COLUMN usable_posts.commentary_worthy IS 'Manual flag for old posts that are still valuable for commentary/rewriting';

