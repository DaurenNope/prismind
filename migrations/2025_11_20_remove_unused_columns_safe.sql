-- Remove Unused Columns Migration (SAFE SUBSET)
-- ===============================================
-- Removes only confirmed unused columns with no code references
-- Created: 2025-11-22
-- Priority: P1 - Schema optimization
--
-- This migration removes only columns that:
-- 1. Have zero code references
-- 2. Are confirmed unused
-- 3. Are safe to remove immediately
--
-- IMPORTANT: 
-- This is the safe subset. Full migration in 2025_11_20_remove_unused_columns.sql
-- contains additional columns that need code updates first.

-- =====================================================
-- SAFE COLUMNS TO REMOVE (No code references)
-- =====================================================

-- 1. upvote_ratio (0% filled, no code references)
-- This should be stored in engagement JSONB field instead
ALTER TABLE public.posts DROP COLUMN IF EXISTS upvote_ratio;

-- 2. content_category (0% filled, no code references)
-- Unused column, never populated
ALTER TABLE public.posts DROP COLUMN IF EXISTS content_category;

-- 3. target_social_media (0% filled, no code references)
-- Unused feature, never populated
ALTER TABLE public.posts DROP COLUMN IF EXISTS target_social_media;

-- 4. time_sensitivity_reason (0% filled, no code references)
-- Unused column, never populated
ALTER TABLE public.posts DROP COLUMN IF EXISTS time_sensitivity_reason;

-- =====================================================
-- VERIFICATION QUERIES
-- =====================================================

-- Verify removed columns are gone
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public'
  AND column_name IN (
    'upvote_ratio', 
    'content_category', 
    'target_social_media', 
    'time_sensitivity_reason'
  );
-- Should return 0 rows if successful

-- Check remaining columns count
SELECT COUNT(*) as remaining_columns
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public';

-- =====================================================
-- NOTES
-- =====================================================
/*
Removed Columns (4 - Safe Subset):
  - upvote_ratio: 0% filled, should be in engagement JSONB
  - content_category: 0% filled, unused
  - target_social_media: 0% filled, unused feature
  - time_sensitivity_reason: 0% filled, unused

Columns NOT removed (need code updates first):
  - summary: Has references (but mostly false positives in strings)
  - num_comments: Used via engagement.get("num_comments") (JSONB, not column)
  - saved_at: Active code references, needs code refactor first
  - is_time_sensitive: Active code references, needs code refactor first

Expected Storage Savings:
  - ~4 columns × row_count = reduced storage
  - Faster queries from smaller row size
  - Improved maintainability

Next Steps:
  1. Update code to remove saved_at references, then remove column
  2. Update code to use urgency calculation instead of is_time_sensitive
  3. Verify summary column usage and potentially remove after code update
  4. Apply full migration after code refactoring
*/






