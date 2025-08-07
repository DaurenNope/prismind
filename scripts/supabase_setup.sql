-- Create the posts table in Supabase
-- Run this in your Supabase SQL editor

CREATE TABLE IF NOT EXISTS public.posts (
    id INTEGER PRIMARY KEY,
    title TEXT,
    content TEXT,
    platform TEXT,
    author TEXT,
    author_handle TEXT,
    url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    summary TEXT,
    value_score INTEGER DEFAULT 0,
    smart_tags TEXT,
    ai_summary TEXT,
    folder_category TEXT,
    category TEXT
);

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
INSERT INTO public.posts (id, title, content, platform, author, author_handle, url, summary, value_score, smart_tags, ai_summary, folder_category, category)
VALUES (
    999999,
    'Test Post',
    'This is a test post to verify the table structure.',
    'test',
    'Test Author',
    '@testauthor',
    'https://example.com/test',
    'Test summary',
    5,
    '["test", "verification"]',
    'This is a test AI summary.',
    'test',
    'test'
) ON CONFLICT (id) DO NOTHING; 