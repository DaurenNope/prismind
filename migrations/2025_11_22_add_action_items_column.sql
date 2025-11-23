-- =====================================================
-- Add action_items Column Migration
-- =====================================================
-- Adds action_items column to posts table if missing
-- Converts existing TEXT column to TEXT[] array type if it exists
-- Created: 2025-11-22
-- Priority: P0 - Critical (fixes analysis pipeline empty fields)

-- =====================================================
-- STEP 1: Add column if it doesn't exist
-- =====================================================

ALTER TABLE public.posts 
ADD COLUMN IF NOT EXISTS action_items TEXT[];

-- =====================================================
-- STEP 2: Convert existing TEXT column to TEXT[] if needed
-- =====================================================

-- Only convert if column exists as TEXT type
DO $$ 
BEGIN
    -- Check if action_items exists as TEXT type (not array)
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'posts' 
          AND table_schema = 'public'
          AND column_name = 'action_items' 
          AND data_type = 'text'
          AND udt_name = 'text'
    ) THEN
        -- Convert TEXT column to TEXT[] array
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
    END IF;
END $$;

-- =====================================================
-- VERIFICATION QUERIES (Run after migration)
-- =====================================================

-- Verify column exists and is correct type
SELECT 
    column_name, 
    data_type,
    udt_name
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND table_schema = 'public'
  AND column_name = 'action_items';
-- Expected: data_type = 'ARRAY', udt_name = '_text'

-- Check sample data (if any exists)
SELECT 
    post_id,
    action_items,
    array_length(action_items, 1) as item_count
FROM public.posts 
WHERE action_items IS NOT NULL 
  AND array_length(action_items, 1) > 0
LIMIT 5;






