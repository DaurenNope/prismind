-- Add time sensitivity column to posts table
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS is_time_sensitive BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS time_sensitivity_reason TEXT;

-- Add comments
COMMENT ON COLUMN posts.is_time_sensitive IS 'Indicates if the content is time-sensitive (e.g., news, events)';
COMMENT ON COLUMN posts.time_sensitivity_reason IS 'Reason for time sensitivity (e.g., event date, news relevance)';

-- Create an index for better query performance
CREATE INDEX IF NOT EXISTS idx_posts_time_sensitive ON posts(is_time_sensitive);
