-- Update Supabase posts table schema to match application requirements
-- Adding missing columns that the application is trying to insert

ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS content_summary TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS action_items TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS insights TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS recommendations TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS educational_value TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS intelligence_analysis TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS actionable_insights TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS quality_score DOUBLE PRECISION;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS sentiment_analysis TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS analysis_timestamp TIMESTAMP WITH TIME ZONE;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS ai_service_used TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS is_rewrite_candidate BOOLEAN DEFAULT FALSE;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS rewrite_status TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS rewritten_content TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS rewrite_notes TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS engagement JSONB;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS created_timestamp TIMESTAMP WITH TIME ZONE;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS updated_timestamp TIMESTAMP WITH TIME ZONE;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS analyzed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS analysis_version TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS topics TEXT[];
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS summary TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS why_valuable TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS complexity_level TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS time_to_consume INTEGER;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS actionable_items TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS learning_value TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS practical_applications TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS related_skills TEXT[];
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS follow_up_research TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS quality_indicators TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS confidence_score DOUBLE PRECISION;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS sentiment_scores JSONB;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS ai_service TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS intelligent_value_score DOUBLE PRECISION;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS content_quality_score DOUBLE PRECISION;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS learning_recommendations TEXT;
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS suggested_tags TEXT[];
ALTER TABLE public.posts ADD COLUMN IF NOT EXISTS collected_at TIMESTAMP WITH TIME ZONE;

-- Update existing indexes to include new columns if needed
CREATE INDEX IF NOT EXISTS idx_posts_analyzed_at ON public.posts (analyzed_at);
CREATE INDEX IF NOT EXISTS idx_posts_value_score ON public.posts (value_score);
CREATE INDEX IF NOT EXISTS idx_posts_quality_score ON public.posts (quality_score);
CREATE INDEX IF NOT EXISTS idx_posts_collected_at ON public.posts (collected_at);
