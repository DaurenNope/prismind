-- Database Performance Indexes Migration
-- =====================================
-- Adds missing indexes for common query patterns
-- Created: 2025-11-20
-- Priority: P0 - Critical for query performance

-- =====================================================
-- PART 1: SUPABASE INDEXES (PostgreSQL)
-- =====================================================

-- 1. Compound index for platform + created_at queries
-- This is the most common query pattern: filter by platform and order by time
-- Example: WHERE platform = 'twitter' ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_posts_platform_created_at 
ON public.posts (platform, created_at DESC);

-- 2. Ensure created_at index exists (may already exist, but ensures it)
-- This index exists in 2025_11_16_consolidated_schema.sql but we verify it here
CREATE INDEX IF NOT EXISTS idx_posts_created_at 
ON public.posts (created_at DESC);

-- 3. Ensure value_score index exists for quality sorting
-- This index exists in 2025_11_16_consolidated_schema.sql but we verify it here
CREATE INDEX IF NOT EXISTS idx_posts_value_score 
ON public.posts (value_score DESC);

-- 4. Ensure rewrite_score index exists for rewrite prioritization
-- This index exists in 2025_11_16_consolidated_schema.sql but we verify it here
CREATE INDEX IF NOT EXISTS idx_posts_rewrite_score 
ON public.posts (rewrite_score DESC);

-- 5. Additional compound index for common filters + sorting
-- Useful for queries like: WHERE platform = X AND value_score >= Y ORDER BY created_at DESC
CREATE INDEX IF NOT EXISTS idx_posts_platform_value_score 
ON public.posts (platform, value_score DESC, created_at DESC);

-- 6. Index for rewrite candidates with scores
-- Useful for: WHERE is_rewrite_candidate = TRUE ORDER BY rewrite_score DESC
CREATE INDEX IF NOT EXISTS idx_posts_rewrite_candidate_score 
ON public.posts (is_rewrite_candidate, rewrite_score DESC) 
WHERE is_rewrite_candidate = TRUE;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Check all indexes on posts table (run this to verify indexes were created)
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'posts' 
  AND schemaname = 'public'
ORDER BY indexname;

-- =====================================================
-- NOTES
-- =====================================================
/*
Index Usage Guidelines:

1. idx_posts_platform_created_at
   - Use for: WHERE platform IN (...) ORDER BY created_at DESC
   - Most common query pattern in the codebase

2. idx_posts_platform_value_score
   - Use for: WHERE platform = X AND value_score >= Y ORDER BY created_at DESC
   - Good for filtering high-quality content by platform

3. idx_posts_rewrite_candidate_score
   - Use for: WHERE is_rewrite_candidate = TRUE ORDER BY rewrite_score DESC
   - Optimized with partial index (only indexes TRUE values)

4. Existing indexes from consolidated_schema.sql:
   - idx_posts_created_at - Single column index
   - idx_posts_value_score - Single column index  
   - idx_posts_rewrite_score - Single column index

These compound indexes will significantly improve query performance
on large datasets, especially when filtering by platform and sorting by time.
*/
