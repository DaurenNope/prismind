-- Cleanup Redundant Supabase Columns
-- =====================================
-- Run this in Supabase SQL Editor after verifying you don't need these columns

-- IMPORTANT: Backup your data first!
-- Create a backup: pg_dump or export to CSV

-- 1. Drop "summary" (100% duplicate of ai_summary)
ALTER TABLE posts DROP COLUMN IF EXISTS summary;

-- 2. Drop engagement columns (should be in engagement JSON, 0% filled)
ALTER TABLE posts DROP COLUMN IF EXISTS num_comments;
ALTER TABLE posts DROP COLUMN IF EXISTS upvote_ratio;

-- 3. Drop unused tracking columns (0% filled)
ALTER TABLE posts DROP COLUMN IF EXISTS saved_at;
ALTER TABLE posts DROP COLUMN IF EXISTS content_category;
ALTER TABLE posts DROP COLUMN IF EXISTS target_social_media;
ALTER TABLE posts DROP COLUMN IF EXISTS time_sensitivity_reason;
ALTER TABLE posts DROP COLUMN IF EXISTS is_time_sensitive;

-- 4. Verify dropped columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND column_name IN (
    'summary', 'num_comments', 'upvote_ratio', 'saved_at', 
    'content_category', 'target_social_media', 
    'time_sensitivity_reason', 'is_time_sensitive'
  );
-- Should return 0 rows if successful

-- 5. Check remaining columns
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'posts' 
ORDER BY ordinal_position;

-- Summary of Changes:
-- ====================
-- REMOVED (8 columns):
--   - summary (duplicate of ai_summary)
--   - num_comments (0% filled, should be in engagement JSON)
--   - upvote_ratio (0% filled, should be in engagement JSON)
--   - saved_at (0% filled, never used)
--   - content_category (0% filled, duplicate of category)
--   - target_social_media (0% filled, unused feature)
--   - time_sensitivity_reason (0% filled, unused feature)
--   - is_time_sensitive (always false, unused)
--
-- KEPT (31 columns including new ones):
--   - All core fields (id, post_id, content, url, platform, author, etc.)
--   - All analysis fields (category, tags, value_score, sentiment, etc.)
--   - New fields (embedding, embedding_model, language, analysis_model)
--
-- Space savings: ~8 columns × 430 posts = cleaner, faster queries
