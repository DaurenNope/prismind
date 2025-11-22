-- Persona drafts table for human-in-the-loop workflow

create table if not exists persona_drafts (
    id uuid primary key default gen_random_uuid(),
    persona_key text not null,
    platform text not null default 'twitter',
    content text not null,
    notes text,
    status text not null default 'submitted',
    created_by text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    approved_by text,
    approved_at timestamptz,
    last_generated_at timestamptz,
    metadata jsonb default '{}'::jsonb
);

create index if not exists idx_persona_drafts_persona_key
    on persona_drafts(persona_key);


