-- Post operations and quality metrics tracking for monitoring
-- These tables enable DatabaseAgent to track all post saves/updates and quality metrics

-- Track individual post operations (inserts/updates)
create table if not exists post_operations (
  id bigserial primary key,
  post_id text not null,
  platform text not null,
  operation text not null, -- 'insert' or 'update'
  quality_score numeric,
  value_score numeric,
  has_analysis boolean default false,
  timestamp timestamptz not null default now()
);

create index if not exists idx_post_ops_post_id on post_operations(post_id);
create index if not exists idx_post_ops_platform on post_operations(platform);
create index if not exists idx_post_ops_timestamp on post_operations(timestamp desc);
create index if not exists idx_post_ops_operation on post_operations(operation);

-- Track quality metrics over time for monitoring and alerting
create table if not exists quality_metrics (
  id bigserial primary key,
  platform text not null,
  quality_score numeric not null,
  value_score numeric,
  timestamp timestamptz not null default now()
);

create index if not exists idx_quality_platform on quality_metrics(platform);
create index if not exists idx_quality_timestamp on quality_metrics(timestamp desc);
create index if not exists idx_quality_score on quality_metrics(quality_score);

-- Add comment for documentation
comment on table post_operations is 'Tracks all post insert and update operations for monitoring';
comment on table quality_metrics is 'Tracks quality scores over time for quality control and alerting';



