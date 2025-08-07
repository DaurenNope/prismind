-- Copywriting (Content Creation) Posts Table
CREATE TABLE IF NOT EXISTS public.copywriting_posts (
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
    category TEXT,
    -- Copywriting specific fields
    content_type TEXT, -- 'social_media', 'blog', 'insight', 'rant', 'idea'
    target_platform TEXT, -- 'twitter', 'linkedin', 'instagram', etc.
    rewrite_instructions TEXT,
    tone TEXT, -- 'casual', 'professional', 'humorous', etc.
    call_to_action TEXT,
    hashtags TEXT,
    publish_status TEXT DEFAULT 'draft'
);

-- Enable Row Level Security
ALTER TABLE public.copywriting_posts ENABLE ROW LEVEL SECURITY;

-- Create policy for all operations
CREATE POLICY "Allow all operations on copywriting_posts" ON public.copywriting_posts FOR ALL USING (true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_copywriting_content_type ON public.copywriting_posts(content_type);
CREATE INDEX IF NOT EXISTS idx_copywriting_target_platform ON public.copywriting_posts(target_platform);
CREATE INDEX IF NOT EXISTS idx_copywriting_publish_status ON public.copywriting_posts(publish_status);
CREATE INDEX IF NOT EXISTS idx_copywriting_value_score ON public.copywriting_posts(value_score DESC);
CREATE INDEX IF NOT EXISTS idx_copywriting_created_at ON public.copywriting_posts(created_at DESC); 