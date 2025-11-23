-- ============================================================================
-- Security and Performance Optimization: Add Indexes
-- Migration Date: 2025-01-11
-- ============================================================================
-- 
-- This migration adds indexes for commonly queried columns to improve
-- query performance and prevent N+1 query patterns.
-- 
-- Rationale:
-- - Indexes on frequently filtered/joined columns speed up queries
-- - Composite indexes for common query patterns (e.g., platform + created_at)
-- - Full-text search indexes for content searching
-- ============================================================================

-- Indexes for posts table (Supabase/PostgreSQL)
-- These should be created in Supabase SQL Editor

-- Platform filtering (very common)
CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);

-- Created at for sorting/date filtering
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);

-- Author lookups
CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author);

-- URL lookups (for duplicate detection)
CREATE INDEX IF NOT EXISTS idx_posts_url ON posts(url) WHERE url IS NOT NULL;

-- Value score for top posts queries
CREATE INDEX IF NOT EXISTS idx_posts_value_score ON posts(value_score DESC NULLS LAST);

-- Quality score
CREATE INDEX IF NOT EXISTS idx_posts_quality_score ON posts(quality_score DESC NULLS LAST);

-- Composite index for common query: platform + created_at
CREATE INDEX IF NOT EXISTS idx_posts_platform_created_at 
ON posts(platform, created_at DESC);

-- Composite index for common query: platform + value_score
CREATE INDEX IF NOT EXISTS idx_posts_platform_value_score 
ON posts(platform, value_score DESC NULLS LAST);

-- Analyzed posts filtering
CREATE INDEX IF NOT EXISTS idx_posts_analyzed_at 
ON posts(analyzed_at) WHERE analyzed_at IS NOT NULL;

-- Unanalyzed posts filtering (null check)
CREATE INDEX IF NOT EXISTS idx_posts_analyzed_at_null 
ON posts(created_at DESC) WHERE analyzed_at IS NULL;

-- Platform + unanalyzed posts (common pattern)
CREATE INDEX IF NOT EXISTS idx_posts_platform_unanalyzed 
ON posts(platform, created_at DESC) WHERE analyzed_at IS NULL;

-- Post ID lookups (if not already primary key)
CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id) WHERE post_id IS NOT NULL;

-- Author handle for user lookups
CREATE INDEX IF NOT EXISTS idx_posts_author_handle 
ON posts(author_handle) WHERE author_handle IS NOT NULL;

-- Language filtering
CREATE INDEX IF NOT EXISTS idx_posts_language ON posts(language) WHERE language IS NOT NULL;

-- Full-text search index (GIN index for text search)
-- This enables fast text search on title and content
CREATE INDEX IF NOT EXISTS idx_posts_title_content_fts 
ON posts USING gin(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(content, '')));

-- ============================================================================
-- Indexes for SQLite (beyondlines.db)
-- Run these if using SQLite as primary storage
-- ============================================================================

-- Note: SQLite indexes can be added via ALTER TABLE or separate CREATE INDEX
-- These are already created in src/database/operations.py, but included here
-- for reference and migration purposes.

-- Platform filtering
-- CREATE INDEX IF NOT EXISTS idx_platform ON posts(platform);

-- Author lookups  
-- CREATE INDEX IF NOT EXISTS idx_author ON posts(author);

-- Created at for sorting
-- CREATE INDEX IF NOT EXISTS idx_created_at ON posts(created_at);

-- ============================================================================
-- Performance Notes:
-- ============================================================================
-- 
-- 1. Indexes improve SELECT performance but slow down INSERT/UPDATE slightly
--    This is usually a good trade-off for read-heavy workloads
-- 
-- 2. Monitor index usage with:
--    SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';
-- 
-- 3. Consider dropping unused indexes if they're not helping
-- 
-- 4. For very large tables, consider partial indexes (WHERE clauses)
--    to reduce index size and maintenance overhead
-- 
-- 5. The composite indexes (platform + created_at, etc.) are optimized
--    for common query patterns in the codebase
-- 
-- ============================================================================





