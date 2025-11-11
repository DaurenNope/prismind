-- Create user_preferences table to silence warnings and enable preference learning
create table if not exists public.user_preferences (
  id bigserial primary key,
  user_id text not null default 'default',
  preference_type text not null,        -- e.g., 'category' | 'source' | 'topic'
  preference_key text not null,         -- e.g., 'AI' | 'twitter' | 'python'
  preference_value numeric not null default 0, -- [-1.0, 1.0]
  interaction_count integer not null default 0,
  last_updated timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create unique index if not exists ux_user_pref_key
  on public.user_preferences(user_id, preference_type, preference_key);

-- Optional: interactions table used for logging (best-effort)
create table if not exists public.user_interactions (
  id bigserial primary key,
  user_id text not null default 'default',
  discovery_id bigint,
  action text not null,                 -- 'save' | 'dismiss' | 'skip' | 'view'
  created_at timestamptz not null default now()
);


