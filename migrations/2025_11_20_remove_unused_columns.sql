-- Remove Unused Columns Migration
-- ================================
-- Removes confirmed unused columns from posts table
-- Created: 2025-11-20
-- Priority: P1 - Schema optimization
--
-- IMPORTANT: 
-- 1. BACKUP YOUR DATA FIRST!
--    Run: pg_dump -h <host> -U <user> -d <database> -t posts > backup_posts_$(date +%Y%m%d).sql
-- 2. Run analysis script first:
--    python scripts/database/analyze_unused_columns.py --supabase
-- 3. Check code references:
--    python scripts/database/check_column_references.py --columns summary,num_comments,...
-- 4. Test in staging environment first
--
-- =====================================================
-- BACKUP SECTION (Run before migration)
-- =====================================================
-- 
-- Create backup:
-- pg_dump -h db.<project>.supabase.co -U postgres -d postgres -t public.posts > backup_posts_$(date +%Y%m%d_%H%M%S).sql
--
-- Verify backup:
-- psql -h db.<project>.supabase.co -U postgres -d postgres -c "SELECT COUNT(*) FROM public.posts;"
-- 
-- =====================================================
-- MIGRATION: Remove Unused Columns
-- =====================================================

-- Phase 1: Remove duplicate columns (100% safe)
-- ---------------------------------------------

-- 1. Remove "summary" (duplicate of ai_summary)
-- This column is 100% duplicate of ai_summary according to cleanup_schema.sql
ALTER TABLE public.posts DROP COLUMN IF EXISTS summary;

-- Phase 2: Remove 0% filled columns (safe, but verify first)
-- ---------------------------------------------

-- 2. Remove engagement columns (0% filled, should be in engagement JSON)
-- These should be stored in engagement JSONB field instead
ALTER TABLE public.posts DROP COLUMN IF EXISTS num_comments;
ALTER TABLE public.posts DROP COLUMN IF EXISTS upvote_ratio;

-- 3. Remove unused tracking columns (0% filled)
-- These columns are never populated
ALTER TABLE public.posts DROP COLUMN IF EXISTS saved_at;
ALTER TABLE public.posts DROP COLUMN IF EXISTS content_category;
ALTER TABLE public.posts DROP COLUMN IF EXISTS target_social_media;
ALTER TABLE public.posts DROP COLUMN IF EXISTS time_sensitivity_reason;
ALTER TABLE public.posts DROP COLUMN IF EXISTS is_time_sensitive;

-- Phase 3: Remove deprecated/legacy columns (verify usage first)
-- ---------------------------------------------

-- NOTE: These columns may have some usage, check with analyze_unused_columns.py first
-- Uncomment only after verification:

-- ALTER TABLE public.posts DROP COLUMN IF EXISTS content_summary;  -- Check if different from ai_summary
-- ALTER TABLE public.posts DROP COLUMN IF EXISTS action_items;     -- Verify not used
-- ALTER TABLE public.posts DROP COLUMN IF EXISTS insights;         -- Verify not used
-- ALTER TABLE public.posts DROP COLUMN IF EXISTS recommendations;  -- Verify not used
-- ALTER TABLE public.posts DROP COLUMN IF EXISTS educational_value; -- Verify not used

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Verify removed columns are gone
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public'
  AND column_name IN (
    'summary', 'num_comments', 'upvote_ratio', 'saved_at', 
    'content_category', 'target_social_media', 
    'time_sensitivity_reason', 'is_time_sensitive'
  );
-- Should return 0 rows if successful

-- Check remaining columns count
SELECT COUNT(*) as remaining_columns
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public';

-- List all remaining columns
SELECT column_name, data_type, is_nullable
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public'
ORDER BY ordinal_position;

-- =====================================================
-- ROLLBACK (if needed)
-- =====================================================
-- 
-- To rollback, restore from backup:
-- psql -h db.<project>.supabase.co -U postgres -d postgres < backup_posts_YYYYMMDD_HHMMSS.sql
--
-- Or manually re-add columns (with appropriate defaults):
-- ALTER TABLE public.posts ADD COLUMN summary TEXT;
-- ALTER TABLE public.posts ADD COLUMN num_comments INTEGER;
-- ALTER TABLE public.posts ADD COLUMN upvote_ratio NUMERIC;
-- ALTER TABLE public.posts ADD COLUMN saved_at TIMESTAMPTZ;
-- ALTER TABLE public.posts ADD COLUMN content_category TEXT;
-- ALTER TABLE public.posts ADD COLUMN target_social_media TEXT;
-- ALTER TABLE public.posts ADD COLUMN time_sensitivity_reason TEXT;
-- ALTER TABLE public.posts ADD COLUMN is_time_sensitive BOOLEAN DEFAULT FALSE;

-- =====================================================
-- SUMMARY
-- =====================================================
--
-- Removed Columns (8):
--   - summary (duplicate of ai_summary)
--   - num_comments (0% filled, should be in engagement JSON)
--   - upvote_ratio (0% filled, should be in engagement JSON)
--   - saved_at (0% filled, never used)
--   - content_category (0% filled, duplicate of category)
--   - target_social_media (0% filled, unused feature)
--   - time_sensitivity_reason (0% filled, unused feature)
--   - is_time_sensitive (always false, unused)
--
-- Expected Storage Savings:
--   - ~8 columns × row_count = reduced storage
--   - Faster queries from smaller row size
--   - Improved maintainability
--
-- Next Steps:
--   1. Verify no application errors after migration
--   2. Monitor query performance
--   3. Check for any broken references in application logs
--   4. Update documentation if needed






