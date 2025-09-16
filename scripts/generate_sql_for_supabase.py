def generate_sql():
    """
    Generate SQL commands to update the posts table in Supabase.
    Copy and paste these commands into the Supabase SQL editor.
    """
    sql_commands = """
-- Add new columns to posts table
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS is_rewrite_candidate BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS content_quality_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS target_social_media TEXT[] DEFAULT '{}'::TEXT[],
ADD COLUMN IF NOT EXISTS content_category TEXT,
ADD COLUMN IF NOT EXISTS ai_summary TEXT DEFAULT '';

-- Add comments to explain the new columns
COMMENT ON COLUMN posts.is_rewrite_candidate IS 'Flag indicating if this content is suitable for rewriting';
COMMENT ON COLUMN posts.content_quality_score IS 'Numeric score (0-1) indicating content quality';
COMMENT ON COLUMN posts.target_social_media IS 'Array of target social media platforms for this content';
COMMENT ON COLUMN posts.content_category IS 'Category of content (e.g., educational, promotional, news)';
COMMENT ON COLUMN posts.ai_summary IS 'AI-generated summary of the content';

-- Create an index on the new columns for better query performance
CREATE INDEX IF NOT EXISTS idx_posts_rewrite_candidate ON posts(is_rewrite_candidate);
CREATE INDEX IF NOT EXISTS idx_posts_content_quality ON posts(content_quality_score);
CREATE INDEX IF NOT EXISTS idx_posts_content_category ON posts(content_category);

-- Example update to set some initial values (modify as needed)
-- UPDATE posts 
-- SET 
--     is_rewrite_candidate = (length(content) > 500),  -- Example: mark long posts as rewrite candidates
--     content_quality_score = 0.7,                     -- Example: set initial quality score
--     target_social_media = ARRAY['twitter', 'linkedin'], -- Example: target platforms
--     content_category = 'educational';                 -- Example: default category
"""
    
    # Print the SQL commands
    print("="*80)
    print("COPY THE FOLLOWING SQL COMMANDS TO SUPABASE SQL EDITOR")
    print("="*80)
    print(sql_commands)
    print("="*80)
    print("1. Go to your Supabase dashboard")
    print("2. Click on 'SQL Editor' in the left sidebar")
    print("3. Click 'New Query'")
    print("4. Paste the SQL commands above")
    print("5. Click 'Run' or press Cmd+Enter (Mac) / Ctrl+Enter (Windows/Linux)")
    print("="*80)

if __name__ == "__main__":
    generate_sql()
