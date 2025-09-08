-- Non-destructive migration to a single canonical table: posts_v2
-- Run this in Supabase SQL editor.

-- 1) Create canonical table
CREATE TABLE IF NOT EXISTS public.posts_v2 (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  platform TEXT NOT NULL CHECK (platform IN ('reddit','twitter','threads','other')),
  post_id TEXT NOT NULL,
  url TEXT,
  author TEXT,
  author_handle TEXT,
  title TEXT,
  content TEXT,
  category TEXT,
  folder_category TEXT,
  is_saved BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  saved_at TIMESTAMPTZ,
  value_score DOUBLE PRECISION,
  engagement_score DOUBLE PRECISION,
  num_comments INTEGER,
  sentiment TEXT,
  smart_tags TEXT,
  ai_summary TEXT,
  key_concepts JSONB,
  media_urls JSONB,
  domain TEXT GENERATED ALWAYS AS (NULLIF(split_part(url,'/',3),'')) STORED,
  UNIQUE (platform, post_id)
);

-- 2) Helpful indexes for performance/readability
CREATE INDEX IF NOT EXISTS idx_posts_v2_created_at ON public.posts_v2(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_v2_platform ON public.posts_v2(platform);
CREATE INDEX IF NOT EXISTS idx_posts_v2_category ON public.posts_v2(category);
CREATE INDEX IF NOT EXISTS idx_posts_v2_domain ON public.posts_v2(domain);
CREATE INDEX IF NOT EXISTS idx_posts_v2_value_score ON public.posts_v2(value_score DESC);

-- 3) Copy data from current table (public.posts) into posts_v2 (idempotent)
--    Attempt to normalize/align columns; ignore conflicts on (platform, post_id)
INSERT INTO public.posts_v2 (
  platform, post_id, url, author, author_handle, title, content, category, folder_category,
  is_saved, created_at, saved_at, value_score, engagement_score, num_comments, sentiment,
  smart_tags, ai_summary, key_concepts, media_urls
)
SELECT 
  COALESCE(p.platform,'other') AS platform,
  RIGHT(COALESCE(p.url,''), 64) AS post_id,
  p.url,
  p.author,
  p.author_handle,
  NULLIF(p.title,'') AS title,
  p.content,
  p.category,
  p.folder_category,
  TRUE AS is_saved,
  COALESCE(p.created_at, NOW()) AS created_at,
  NULL::timestamptz AS saved_at,
  (CASE 
     WHEN p.value_score IS NULL THEN NULL
     WHEN p.value_score::text = '' THEN NULL
     ELSE p.value_score::double precision
   END) AS value_score,
  (CASE 
     WHEN p.engagement_score IS NULL THEN NULL
     WHEN p.engagement_score::text = '' THEN NULL
     ELSE p.engagement_score::double precision
   END) AS engagement_score,
  (CASE 
     WHEN p.num_comments IS NULL THEN NULL
     WHEN p.num_comments::text = '' THEN NULL
     ELSE p.num_comments::int
   END) AS num_comments,
  p.sentiment,
  p.smart_tags,
  p.ai_summary,
  NULL::jsonb AS key_concepts,
  NULL::jsonb AS media_urls
FROM public.posts p
ON CONFLICT (platform, post_id) DO NOTHING;

-- 4) Readable materialized view on top of posts_v2
CREATE MATERIALIZED VIEW IF NOT EXISTS public.posts_v2_readable AS
SELECT 
  id,
  platform,
  COALESCE(title, smart_tags, LEFT(COALESCE(content,''),120)) AS title,
  author,
  url,
  COALESCE(category, folder_category) AS category,
  value_score,
  COALESCE(engagement_score, num_comments) AS engagement,
  created_at,
  is_saved,
  domain
FROM public.posts_v2
ORDER BY created_at DESC, id DESC;

CREATE INDEX IF NOT EXISTS idx_posts_v2_readable_created_at ON public.posts_v2_readable(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_v2_readable_platform ON public.posts_v2_readable(platform);

-- 5) Optional: refresh helper
-- REFRESH MATERIALIZED VIEW CONCURRENTLY public.posts_v2_readable;


