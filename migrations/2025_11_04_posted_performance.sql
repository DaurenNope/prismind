-- Posted content and time-series metrics for performance analytics

create table if not exists posted_content (
  id bigserial primary key,
  platform text not null,
  platform_post_id text not null,
  persona text,
  content_hash text,
  url text,
  posted_at timestamptz not null default now(),
  initial_text text,
  topic text,
  tags text[],
  has_media boolean default false,
  lang text,
  total_views bigint default 0,
  total_likes bigint default 0,
  total_comments bigint default 0,
  total_shares bigint default 0,
  total_bookmarks bigint default 0,
  engagement_score numeric default 0,
  created_at timestamptz default now()
);

create unique index if not exists ux_posted_platform_id
  on posted_content(platform, platform_post_id);

create index if not exists idx_posted_posted_at
  on posted_content(posted_at desc);

create table if not exists posted_metrics (
  id bigserial primary key,
  posted_content_id bigint not null references posted_content(id) on delete cascade,
  snapshot_at timestamptz not null default now(),
  views bigint,
  likes bigint,
  comments bigint,
  shares bigint,
  bookmarks bigint
);

create unique index if not exists ux_metrics_point
  on posted_metrics(posted_content_id, snapshot_at);

create index if not exists idx_metrics_recent
  on posted_metrics(snapshot_at desc);


