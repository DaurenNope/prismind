-- Collection metrics for platform freshness and outcomes
create table if not exists collection_metrics (
  platform text primary key,
  last_run_at timestamptz,
  last_count integer default 0,
  last_success boolean default false,
  failure_reason text,
  consecutive_failures integer default 0,
  updated_at timestamptz default now()
);

create index if not exists idx_collection_metrics_updated_at
  on collection_metrics(updated_at desc);


