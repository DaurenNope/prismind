-- Enable the pgvector extension to work with embedding vectors
create extension if not exists vector;

-- Create a table to store "Knowledge Atoms" - the fundamental unit of agent memory
create table if not exists knowledge_atoms (
  id bigserial primary key,
  content text not null,
  embedding vector(1536), -- OpenAI embedding size (adjust if using different model)
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now(),
  agent_id text, -- Which agent created this memory
  source_id text, -- Link to original post/source
  type text -- 'fact', 'summary', 'contradiction', 'hypothesis'
);

-- Create an index for faster similarity search
create index on knowledge_atoms using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- RPC function for similarity search
create or replace function match_knowledge_atoms (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id bigint,
  content text,
  similarity float,
  type text,
  metadata jsonb
)
language plpgsql
as $$
begin
  return query
  select
    knowledge_atoms.id,
    knowledge_atoms.content,
    1 - (knowledge_atoms.embedding <=> query_embedding) as similarity,
    knowledge_atoms.type,
    knowledge_atoms.metadata
  from knowledge_atoms
  where 1 - (knowledge_atoms.embedding <=> query_embedding) > match_threshold
  order by knowledge_atoms.embedding <=> query_embedding
  limit match_count;
end;
$$;
