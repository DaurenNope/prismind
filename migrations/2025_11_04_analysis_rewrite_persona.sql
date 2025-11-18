-- Analyzer essentials (if missing)
alter table if exists posts
  add column if not exists analyzed_at timestamptz,
  add column if not exists analysis_model text,
  add column if not exists ai_summary text,
  add column if not exists value_score numeric,
  add column if not exists quality_score numeric,
  add column if not exists tags text[],
  add column if not exists key_concepts text[],
  add column if not exists topic text,
  add column if not exists content_type text,
  add column if not exists language text,
  add column if not exists embedding text,
  add column if not exists embedding_model text;

-- Rewrite-focused fields
alter table if exists posts
  add column if not exists rewrite_score numeric,
  add column if not exists rewrite_readiness text,
  add column if not exists rewrite_reasons text[],
  add column if not exists rewrite_risks text[],
  add column if not exists analysis_confidence numeric,
  add column if not exists analysis_depth text,
  add column if not exists needs_deep_analysis boolean;

-- Persona-aware scoring
alter table if exists posts
  add column if not exists persona_fit_scores jsonb,
  add column if not exists persona_fit_reasons jsonb,
  add column if not exists best_persona_key text,
  add column if not exists best_persona_score numeric,
  add column if not exists best_persona_reasons text[];
