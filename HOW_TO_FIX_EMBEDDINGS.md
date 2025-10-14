# How To Fix Embeddings - Simple Guide

## The Problem
Your system has everything for embeddings EXCEPT:
1. Supabase doesn't have `embedding` column
2. Embeddings not generated during collection

## The Solution (2 steps)

### Step 1: Add Embedding Column to Supabase

Go to: https://supabase.com/dashboard/project/_/sql

Paste and run:
```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column (384 dimensions for sentence-transformers/all-MiniLM-L6-v2)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding vector(384);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'all-MiniLM-L6-v2';

-- Create index for similarity search
CREATE INDEX IF NOT EXISTS posts_embedding_idx 
ON posts USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Verify it worked
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'posts' AND column_name = 'embedding';
```

### Step 2: Generate Embeddings

You have two options:

#### Option A: Automatic (during collection)
The collectors call `analyze_and_store_post()` which should generate embeddings.

Check if it's working:
1. Collect a new post
2. Check if it has embedding in Supabase

If not, the IndexerAgent needs to be called. Let me know and I'll integrate it.

#### Option B: Manual Backfill (for existing posts)

Check if there's a backfill command:
```bash
# Look for indexer commands
python -m src.core.indexing.indexer_agent --help
```

Or create a simple backfill script:
```python
from src.core.indexing.indexer_agent import IndexerAgent
from src.supabase_manager import SupabaseManager

# Get posts without embeddings
sm = SupabaseManager()
posts = sm.client.table('posts').select('*').is_('embedding', 'null').limit(50).execute()

# Generate embeddings
indexer = IndexerAgent()
for post_data in posts.data:
    # Convert to SocialPost object
    from src.core.extraction.social_extractor_base import SocialPost
    from datetime import datetime
    
    post = SocialPost(
        platform=post_data['platform'],
        author=post_data['author'],
        author_handle=post_data.get('author_handle', ''),
        content=post_data['content'],
        created_at=datetime.fromisoformat(post_data['created_at']),
        url=post_data['url'],
        post_type=post_data.get('post_type', 'post'),
        post_id=post_data['post_id']
    )
    
    # Generate embedding
    indexer.index_content(post)
    
    print(f"Generated embedding for {post_data['post_id']}")
```

## How To Test

### Test Semantic Search
After embeddings are generated:

```python
from src.core.research.semantic_search_engine import SemanticSearchEngine

engine = SemanticSearchEngine()
results = engine.search("AI agents and automation", limit=5)

for result in results:
    print(f"- {result['title']} (score: {result['similarity']})")
```

## Current Status

- ✅ EmbeddingService works (uses sentence-transformers, local, free)
- ✅ IndexerAgent exists (generates and stores embeddings)
- ✅ SemanticSearchEngine exists (searches by meaning)
- ❌ Supabase missing embedding column (DO STEP 1)
- ❌ Embeddings not being generated (DO STEP 2)

That's it! Once you run the SQL, the system is 100% ready for semantic search.
