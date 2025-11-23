-- =====================================================
-- COPY THIS SQL TO SUPABASE DASHBOARD
-- =====================================================
-- URL: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new
-- =====================================================

-- Remove Unused Columns Migration (SAFE SUBSET)
-- Removes only confirmed unused columns with no code references
-- Created: 2025-11-22
-- Priority: P1 - Schema optimization

-- 1. upvote_ratio (0% filled, no code references)
ALTER TABLE public.posts DROP COLUMN IF EXISTS upvote_ratio;

-- 2. content_category (0% filled, no code references)
ALTER TABLE public.posts DROP COLUMN IF EXISTS content_category;

-- 3. target_social_media (0% filled, no code references)
ALTER TABLE public.posts DROP COLUMN IF EXISTS target_social_media;

-- 4. time_sensitivity_reason (0% filled, no code references)
ALTER TABLE public.posts DROP COLUMN IF EXISTS time_sensitivity_reason;

-- =====================================================
-- VERIFICATION (Run after applying above)
-- =====================================================

-- Verify removed columns are gone (should return 0 rows)
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

-- Check remaining columns count
SELECT COUNT(*) as remaining_columns
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public';






