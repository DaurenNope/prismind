-- Add post verification fields to posted_content table
ALTER TABLE posted_content
ADD COLUMN IF NOT EXISTS verification_status TEXT DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS verification_result JSONB;

-- Add index for faster filtering by verification status
CREATE INDEX IF NOT EXISTS idx_posted_content_verification_status 
ON posted_content(verification_status);

-- Rollback (for reference):
-- ALTER TABLE posted_content DROP COLUMN IF EXISTS verification_status;
-- ALTER TABLE posted_content DROP COLUMN IF EXISTS verified_at;
-- ALTER TABLE posted_content DROP COLUMN IF EXISTS verification_result;
-- DROP INDEX IF EXISTS idx_posted_content_verification_status;

