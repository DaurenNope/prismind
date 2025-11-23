-- Fix action_items Column Type Migration
-- =====================================
-- Converts action_items from TEXT to TEXT[] array type
-- Created: 2025-11-22
-- Priority: P0 - Critical (fixes data loss)

-- =====================================================
-- MIGRATION: Convert TEXT to TEXT[]
-- =====================================================

-- Step 1: Convert existing TEXT column to TEXT[] array
-- This handles:
-- - NULL values → empty array
-- - Empty strings → empty array  
-- - Single string → array with one element
-- - JSON array strings → parsed array
-- - Existing arrays → preserved as-is
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
-- VERIFICATION QUERIES
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

-- Check some sample data
SELECT 
    post_id,
    action_items,
    array_length(action_items, 1) as item_count
FROM public.posts 
WHERE action_items IS NOT NULL 
  AND array_length(action_items, 1) > 0
LIMIT 5;

-- =====================================================
-- NOTES
-- =====================================================
/*
Migration Summary:
- Converts action_items from TEXT to TEXT[] array type
- Handles various input formats:
  - NULL → []
  - Empty string → []
  - Single string → [string]
  - JSON array string → parsed array
  - Already array → preserved

Why This Is Needed:
- action_items is generated as a list during analysis
- Must be stored as TEXT[] array in PostgreSQL
- TEXT type causes data loss (lists get converted to strings incorrectly)

After Migration:
- action_items will be properly stored as arrays
- Can use array operators: ANY, ALL, @>, <@
- Proper serialization/deserialization in code
*/






