-- Fix database schema to handle large Twitter post IDs
-- Run this in your Supabase SQL editor

-- First, drop the existing table and recreate it with BIGINT
-- Non-destructive improvements for readability & performance
-- Run in Supabase SQL editor

-- 1) Ensure created_at exists and default
ALTER TABLE public.posts
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 2) Backfill created_at from saved_at or existing timestamp columns
UPDATE public.posts
SET created_at = COALESCE(public.posts.created_at, NULLIF(public.posts.saved_at, ''), public.posts.created_timestamp, NOW())
WHERE public.posts.created_at IS NULL;

-- 3) Create helpful indexes
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON public.posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_platform ON public.posts(platform);
CREATE INDEX IF NOT EXISTS idx_posts_category ON public.posts(category);

-- Enable Row Level Security (RLS) - optional but recommended
ALTER TABLE public.posts ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations (for development)
-- You can make this more restrictive later
CREATE POLICY "Allow all operations on posts" ON public.posts
    FOR ALL USING (true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_posts_platform ON public.posts(platform);
CREATE INDEX IF NOT EXISTS idx_posts_category ON public.posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON public.posts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_value_score ON public.posts(value_score DESC);

-- Insert a test record to verify the table works
-- 4) Optional: create a materialized view for data readability
CREATE MATERIALIZED VIEW IF NOT EXISTS public.posts_readable AS
SELECT 
  id,
  platform,
  COALESCE(title, smart_title, LEFT(COALESCE(content,''), 120)) AS title,
  author,
  url,
  COALESCE(category, folder_category) AS category,
  value_score,
  COALESCE(engagement_score, num_comments) AS engagement,
  COALESCE(created_at, NOW()) AS created_at,
  is_saved
FROM public.posts
ORDER BY created_at DESC, id DESC;

CREATE INDEX IF NOT EXISTS idx_posts_readable_created_at ON public.posts_readable(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_readable_platform ON public.posts_readable(platform);
