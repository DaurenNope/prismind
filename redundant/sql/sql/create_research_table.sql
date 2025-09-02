-- Research (Evaluation) Posts Table
CREATE TABLE IF NOT EXISTS public.research_posts (
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
    -- Research specific fields
    research_topic TEXT,
    credibility_score INTEGER DEFAULT 0,
    fact_check_status TEXT DEFAULT 'pending',
    ai_evaluation TEXT,
    sources_cited TEXT,
    research_notes TEXT,
    evaluation_date TIMESTAMP WITH TIME ZONE
);

-- Enable Row Level Security
ALTER TABLE public.research_posts ENABLE ROW LEVEL SECURITY;

-- Create policy for all operations
CREATE POLICY "Allow all operations on research_posts" ON public.research_posts FOR ALL USING (true);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_research_topic ON public.research_posts(research_topic);
CREATE INDEX IF NOT EXISTS idx_research_credibility ON public.research_posts(credibility_score);
CREATE INDEX IF NOT EXISTS idx_research_fact_check ON public.research_posts(fact_check_status);
CREATE INDEX IF NOT EXISTS idx_research_value_score ON public.research_posts(value_score DESC);
CREATE INDEX IF NOT EXISTS idx_research_created_at ON public.research_posts(created_at DESC); 