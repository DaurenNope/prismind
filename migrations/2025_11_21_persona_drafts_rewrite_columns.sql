-- Add rewrite storage columns to persona_drafts

alter table if exists persona_drafts
    add column if not exists rewrite_content text,
    add column if not exists rewrite_quality numeric,
    add column if not exists rewrite_voice_score numeric,
    add column if not exists rewrite_fact_score numeric,
    add column if not exists rewrite_metadata jsonb default '{}'::jsonb;



