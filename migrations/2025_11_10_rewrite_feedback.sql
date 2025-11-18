-- Create rewrite_feedback table for storing user feedback on rewrites
CREATE TABLE IF NOT EXISTS public.rewrite_feedback (
    id bigserial primary key,
    rewrite_id text not null,
    rating integer,
    feedback_type text,
    notes text,
    metadata jsonb,
    created_at timestamptz default now()
);

CREATE INDEX IF NOT EXISTS idx_rewrite_feedback_rewrite_id ON public.rewrite_feedback (rewrite_id);
CREATE INDEX IF NOT EXISTS idx_rewrite_feedback_created_at ON public.rewrite_feedback (created_at);
