# Schema Analysis COMPLETE - Here's What To Do

## ✅ Analysis Complete

I've verified:
1. **Current Supabase schema** - 39 columns, 12 always filled, 18 mostly filled, 9 rarely filled
2. **What analyzer produces** - IntelligentContentAnalyzer outputs ~15 fields
3. **What embedding service needs** - Just content, title, hashtags, author
4. **What collectors send** - PostInserter maps all fields properly

## ❌ Issues Found

1. **Missing dependency:** `sentence-transformers` not installed
2. **Missing column:** `embedding` vector(384) not in Supabase
3. **Missing column:** `embedding_model` text not in Supabase
4. **Missing column:** `language` text not in Supabase (useful for filtering)
5. **Not populated:** `analysis_model` column exists but = 0% filled
6. **Not generated:** Embeddings not created during analysis
7. **Redundant:** `summary` and `ai_summary` seem to duplicate

## 🎯 Recommended Actions (In Order)

### Step 1: Install Dependencies
```bash
pip install sentence-transformers
```

This will download ~80MB of the all-MiniLM-L6-v2 model. It's LOCAL and FREE (no API needed).

### Step 2: Run THIS SQL in Supabase

Safe to run - only ADDS columns, doesn't remove anything:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding columns
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding vector(384);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'all-MiniLM-L6-v2';

-- Add language detection column
ALTER TABLE posts ADD COLUMN IF NOT EXISTS language text DEFAULT 'en';

-- Create index for similarity search (this enables fast semantic search)
CREATE INDEX IF NOT EXISTS posts_embedding_idx 
ON posts USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Verify it worked
SELECT 
    column_name, 
    data_type, 
    udt_name 
FROM information_schema.columns 
WHERE table_name = 'posts' 
  AND column_name IN ('embedding', 'embedding_model', 'language')
ORDER BY column_name;

-- Should show:
-- embedding       | USER-DEFINED | vector
-- embedding_model | text         | text
-- language        | text         | text
```

### Step 3: Integrate Embedding Generation

I'll add this to `src/services/analysis/post_analyzer.py` after the AI analysis (line ~125):

```python
# After analysis_result is received, add:

# Generate embedding for semantic search
from src.core.indexing.embedding_service import get_embedding_service

embedding_service = get_embedding_service()
if embedding_service.is_available():
    try:
        # Prepare content (uses: content, title, hashtags, author)
        content_for_embedding = embedding_service.prepare_content_for_embedding(enhanced_post)
        
        # Generate embedding vector
        embedding = embedding_service.generate_embedding(content_for_embedding)
        
        if embedding:
            enhanced_post['embedding'] = embedding
            enhanced_post['embedding_model'] = embedding_service.model_name
            log(f"Generated embedding ({len(embedding)} dims)", "success")
        else:
            log(f"Failed to generate embedding", "warning")
    except Exception as e:
        log(f"Embedding generation error: {e}", "warning")
else:
    log("Embedding service not available (install sentence-transformers)", "debug")

# Also track which AI service was used
if 'ai_service' in analysis_result:
    enhanced_post['analysis_model'] = analysis_result['ai_service']
```

### Step 4: Update PostInserter Mapping

Add to `src/services/supabase/post_inserter.py` optional_fields list (around line 125):

```python
optional_fields = [
    'category', 'subcategory', 'topic', 'summary', 'ai_summary',
    'sentiment', 'value_score', 'content_quality_score',
    'folder_category', 'saved_at', 'analyzed_at', 'key_concepts', 
    'tags', 'analysis_model', 'num_comments', 'upvote_ratio',
    'time_sensitivity_reason',
    'embedding', 'embedding_model', 'language'  # ADD THESE
]
```

Also handle embedding specially (it's a vector, not a string):

```python
# After the for field in optional_fields loop, add:

# Handle embedding vector specially (don't convert to PG array)
if 'embedding' in post_data and post_data['embedding']:
    # Embedding is already a list of floats, keep as-is
    mapped_data['embedding'] = post_data['embedding']
```

### Step 5: Test End-to-End

```bash
# 1. Collect one new post
python -m src.pipeline.orchestrator twitter --limit 1

# 2. Check if it has embedding
python -c "
from src.supabase_manager import SupabaseManager
sm = SupabaseManager()
result = sm.client.table('posts').select('post_id, embedding, embedding_model, analysis_model').order('created_at', desc=True).limit(1).execute()
post = result.data[0]
print(f'Post: {post[\"post_id\"]}')
print(f'Has embedding: {post.get(\"embedding\") is not None}')
print(f'Embedding model: {post.get(\"embedding_model\")}')
print(f'Analysis model: {post.get(\"analysis_model\")}')
"
```

Expected output:
```
Post: 1234567890
Has embedding: True
Embedding model: all-MiniLM-L6-v2
Analysis model: ollama
```

### Step 6: Backfill Existing Posts

Once working, backfill the 326 existing posts:

```python
# Create: scripts/backfill_embeddings_simple.py

from src.supabase_manager import SupabaseManager
from src.core.indexing.embedding_service import get_embedding_service
import time

sm = SupabaseManager()
embedding_service = get_embedding_service()

if not embedding_service.is_available():
    print("❌ Install sentence-transformers first!")
    exit(1)

# Get posts without embeddings
posts = sm.client.table('posts').select('*').is_('embedding', 'null').limit(50).execute()

print(f"Backfilling {len(posts.data)} posts...")

for i, post in enumerate(posts.data, 1):
    try:
        # Prepare content
        content_for_embedding = embedding_service.prepare_content_for_embedding(post)
        
        # Generate embedding
        embedding = embedding_service.generate_embedding(content_for_embedding)
        
        if embedding:
            # Update in Supabase
            sm.client.table('posts').update({
                'embedding': embedding,
                'embedding_model': 'all-MiniLM-L6-v2'
            }).eq('post_id', post['post_id']).execute()
            
            print(f"✅ [{i}/{len(posts.data)}] {post['post_id']}")
        else:
            print(f"⚠️ [{i}/{len(posts.data)}] Failed: {post['post_id']}")
        
        time.sleep(0.1)  # Rate limiting
        
    except Exception as e:
        print(f"❌ [{i}/{len(posts.data)}] Error: {e}")

print("Done!")
```

Then run:
```bash
python scripts/backfill_embeddings_simple.py
```

### Step 7: Test Semantic Search

```python
from src.core.research.semantic_search_engine import SemanticSearchEngine

engine = SemanticSearchEngine()
results = engine.search("AI agents and automation", limit=5)

for result in results:
    print(f"[{result.get('similarity', 0):.2f}] {result.get('title', 'No title')[:60]}")
```

## Summary

**What needs to be added to Supabase:**
- ✅ `embedding` vector(384) - For semantic search
- ✅ `embedding_model` text - Track which model
- ✅ `language` text - For filtering by language
- ✅ Index on embedding - For fast similarity search

**What needs to be installed:**
- ✅ `sentence-transformers` package

**What needs code changes:**
- ✅ `post_analyzer.py` - Generate embeddings after analysis
- ✅ `post_inserter.py` - Map embedding fields to Supabase
- ✅ Set `analysis_model` field (currently not set)

**What columns can be removed later (optional):**
- `content_category` (0% filled, duplicate of category)
- `saved_at` (0% filled, not being set)
- `target_social_media` (0% filled, unused feature)
- `time_sensitivity_reason` (0% filled, unused feature)
- `num_comments`, `upvote_ratio` (should be in engagement JSON)

**All the code changes are safe** - they only ADD functionality, don't break existing features. If embedding fails, it just logs a warning and continues.

**Ready to proceed?** Run Step 1 and Step 2, then I'll make the code changes for Step 3-4.
