-- Programming/Work Posts Table
CREATE TABLE IF NOT EXISTS public.programming_posts (
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
    -- Programming specific fields
    language TEXT,
    framework TEXT,
    difficulty TEXT,
    code_snippets TEXT,
    tools_mentioned TEXT,
    implementation_status TEXT DEFAULT 'not_started'
);

-- Enable Row Level Security
ALTER TABLE public.programming_posts ENABLE ROW LEVEL SECURITY;

-- Create policy for all operations
CREATE POLICY "Allow all operations on programming_posts" ON public.programming_posts FOR ALL USING (true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_programming_language ON public.programming_posts(language);
CREATE INDEX IF NOT EXISTS idx_programming_framework ON public.programming_posts(framework);
CREATE INDEX IF NOT EXISTS idx_programming_difficulty ON public.programming_posts(difficulty);
CREATE INDEX IF NOT EXISTS idx_programming_value_score ON public.programming_posts(value_score DESC);
CREATE INDEX IF NOT EXISTS idx_programming_created_at ON public.programming_posts(created_at DESC); 