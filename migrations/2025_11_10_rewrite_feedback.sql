-- User feedback on rewrites for quality improvement

create table if not exists rewrite_feedback (
  id bigserial primary key,
  rewrite_id text not null,
  rating integer not null,
  feedback_type text not null default 'rating',
  notes text,
  metadata jsonb,
  created_at timestamptz default now()
);

create index if not exists idx_feedback_rewrite_id
  on rewrite_feedback(rewrite_id);

create index if not exists idx_feedback_rating
  on rewrite_feedback(rating desc);

create index if not exists idx_feedback_created_at
  on rewrite_feedback(created_at desc);

create index if not exists idx_feedback_type
  on rewrite_feedback(feedback_type);

-- Index on metadata for persona/platform filtering (if using JSONB queries)
create index if not exists idx_feedback_metadata
  on rewrite_feedback using gin(metadata);
