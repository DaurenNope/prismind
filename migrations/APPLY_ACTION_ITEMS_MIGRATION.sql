-- =====================================================
-- COPY THIS SQL TO SUPABASE DASHBOARD
-- =====================================================
-- URL: https://supabase.com/dashboard/project/ahlbudltabimzxegdkfc/sql/new
-- =====================================================

-- Fix action_items Column Type: TEXT → TEXT[]
-- Converts existing TEXT column to TEXT[] array type
-- Created: 2025-11-22
-- Priority: P0 - Critical (fixes data loss)

ALTER TABLE public.posts 
    ALTER COLUMN action_items TYPE TEXT[]
    USING CASE 
        WHEN action_items IS NULL THEN ARRAY[]::TEXT[]
        WHEN action_items = '' THEN ARRAY[]::TEXT[]
        WHEN action_items LIKE '[%]' THEN 
            -- Try to parse as JSON array
            COALESCE(
                (SELECT array_agg(value::text) 
                 FROM json_array_elements_text(action_items::json)),
                ARRAY[]::TEXT[]
            )
        ELSE 
            -- Single string → array with one element
            ARRAY[action_items]::TEXT[]
    END;

-- =====================================================
-- VERIFICATION (Run after applying above)
-- =====================================================

-- Verify column type is now TEXT[]
SELECT 
    column_name, 
    data_type,
    udt_name
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public'
  AND column_name = 'action_items';
-- Should show: data_type = 'ARRAY', udt_name = '_text'

-- Check sample data
SELECT 
    post_id,
    action_items,
    array_length(action_items, 1) as item_count
FROM public.posts 
WHERE action_items IS NOT NULL 
LIMIT 5;






