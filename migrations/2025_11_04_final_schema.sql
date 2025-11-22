-- Final Schema Migration - Apply to Supabase
-- ============================================
-- This migration adds ALL required fields for the analyzer
-- Run this in Supabase SQL Editor

-- 1. Basic analysis fields (if missing)
ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS analyzed_at timestamptz,
  ADD COLUMN IF NOT EXISTS analysis_model text,
  ADD COLUMN IF NOT EXISTS ai_summary text,
  ADD COLUMN IF NOT EXISTS value_score numeric,
  ADD COLUMN IF NOT EXISTS quality_score numeric,
  ADD COLUMN IF NOT EXISTS tags text[],
  ADD COLUMN IF NOT EXISTS key_concepts text[],
  ADD COLUMN IF NOT EXISTS topic text,
  ADD COLUMN IF NOT EXISTS content_type text,
  ADD COLUMN IF NOT EXISTS language text,
  ADD COLUMN IF NOT EXISTS embedding text,
  ADD COLUMN IF NOT EXISTS embedding_model text;

-- 2. Rewrite-focused fields (REQUIRED for rewriter)
ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS rewrite_score numeric,
  ADD COLUMN IF NOT EXISTS rewrite_readiness text,
  ADD COLUMN IF NOT EXISTS rewrite_reasons text[],
  ADD COLUMN IF NOT EXISTS rewrite_risks text[],
  ADD COLUMN IF NOT EXISTS analysis_confidence numeric,
  ADD COLUMN IF NOT EXISTS analysis_depth text,
  ADD COLUMN IF NOT EXISTS needs_deep_analysis boolean DEFAULT false;

-- 3. Persona-aware scoring (REQUIRED for rewriter & discovery)
ALTER TABLE posts
  ADD COLUMN IF NOT EXISTS persona_fit_scores jsonb,
  ADD COLUMN IF NOT EXISTS persona_fit_reasons jsonb,
  ADD COLUMN IF NOT EXISTS best_persona_key text,
  ADD COLUMN IF NOT EXISTS best_persona_score numeric,
  ADD COLUMN IF NOT EXISTS best_persona_reasons text[];

-- Verify the columns exist
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'posts'
  AND column_name IN (
    'rewrite_score', 'rewrite_readiness', 'rewrite_reasons', 'rewrite_risks',
    'persona_fit_scores', 'persona_fit_reasons', 'best_persona_key',
    'best_persona_score', 'best_persona_reasons', 'analysis_confidence',
    'analysis_depth', 'needs_deep_analysis'
  )
ORDER BY column_name;




