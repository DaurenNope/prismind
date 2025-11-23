-- Add analysis quality tracking fields to posts table
-- This allows tracking validation results and common issues

ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS analysis_quality TEXT;

ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS analysis_quality_issues JSONB;

-- Add index for filtering by quality
CREATE INDEX IF NOT EXISTS idx_posts_analysis_quality 
ON posts(analysis_quality) 
WHERE analysis_quality IS NOT NULL;

-- Rollback (for reference):
-- ALTER TABLE posts DROP COLUMN IF EXISTS analysis_quality;
-- ALTER TABLE posts DROP COLUMN IF EXISTS analysis_quality_issues;
-- DROP INDEX IF EXISTS idx_posts_analysis_quality;

