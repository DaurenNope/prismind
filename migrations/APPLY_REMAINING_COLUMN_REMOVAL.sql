-- =====================================================
-- COPY THIS SQL TO SUPABASE DASHBOARD
-- =====================================================
-- URL: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new
-- =====================================================
-- 
-- ⚠️  WARNING: These columns have code references!
-- Code updates will be needed after running this migration.
-- See docs/TICKET_7_2_REMAINING_COLUMNS.md for details.
-- =====================================================

-- Remove Remaining Unused Columns
-- Removes 4 additional columns (after safe subset)
-- Created: 2025-11-22
-- Priority: P1 - Schema optimization

-- 1. summary (duplicate of ai_summary)
-- Note: 440 references found, but most are false positives (word "summary" in strings)
-- The actual database column is a duplicate of ai_summary
ALTER TABLE public.posts DROP COLUMN IF EXISTS summary;

-- 2. num_comments (should be in engagement JSONB)
-- Note: References use engagement.get("num_comments") which is JSONB, not the column
-- Column is 0% filled
ALTER TABLE public.posts DROP COLUMN IF EXISTS num_comments;

-- 3. saved_at (code references in queries)
-- ⚠️  CODE UPDATE NEEDED: src/database/queries.py uses saved_at in ORDER BY
-- Will need to change: ORDER BY COALESCE(saved_at, created_at, ...)
-- To: ORDER BY COALESCE(created_at, updated_timestamp, ...)
ALTER TABLE public.posts DROP COLUMN IF EXISTS saved_at;

-- 4. is_time_sensitive (calculated field, can use urgency_score instead)
-- ⚠️  CODE UPDATE NEEDED: src/core/analysis/analysis_components.py calculates this
-- Uses: is_time_sensitive = urgency >= 0.35
-- Can just calculate directly without storing in DB
ALTER TABLE public.posts DROP COLUMN IF EXISTS is_time_sensitive;

-- =====================================================
-- VERIFICATION (Run after applying above)
-- =====================================================

-- Verify removed columns are gone (should return 0 rows)
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public'
  AND column_name IN (
    'summary',
    'num_comments',
    'saved_at',
    'is_time_sensitive'
  );

-- Check remaining columns count
SELECT COUNT(*) as remaining_columns
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public';






