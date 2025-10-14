-- ============================================================================
-- Supabase Schema Migration: Add AI Analysis & Vector Search
-- ============================================================================

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add new AI analysis fields
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'text-embedding-3-small';
ALTER TABLE posts ADD COLUMN IF NOT EXISTS language text;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS topics text[];
ALTER TABLE posts ADD COLUMN IF NOT EXISTS entities jsonb;
ALTER TABLE posts ADD COLUMN IF NOT EXISTS quality_score integer;

-- Create indexes
CREATE INDEX IF NOT EXISTS posts_embedding_idx ON posts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS posts_topics_idx ON posts USING gin(topics);
CREATE INDEX IF NOT EXISTS posts_language_idx ON posts (language);
CREATE INDEX IF NOT EXISTS posts_quality_idx ON posts (quality_score, value_score);
