# Supabase Schema Analysis & Recommendations

## Current Schema Analysis (100 posts sample)

### ✅ ALWAYS FILLED (12 columns) - KEEP THESE
- `id`, `post_id`, `platform`, `url`, `created_at`, `updated_at` - Core identity
- `content` - Main content (always present)
- `is_saved`, `is_deleted`, `is_rewrite_candidate`, `is_time_sensitive` - Flags (default to false)
- `content_quality_score` - Default 0

### ⚠️ MOSTLY FILLED (18 columns) - KEEP, THESE ARE FROM ANALYZER
- `author` (98%), `author_handle` (93%), `title` (99%) - Identity (getting better with fixes)
- `ai_summary` (93%), `category` (93%), `sentiment` (82%) - AI analysis output
- `value_score` (94%), `post_type` (93%), `content_type` (93%) - Classification
- `smart_tags` (85%), `tags` (50%), `key_concepts` (82%) - Searchability
- `topic` (82%), `subcategory` (82%), `folder_category` (87%) - Organization
- `analyzed_at` (82%) - Tracking
- `summary` (87%) - Often same as ai_summary (REDUNDANT?)
- `media_urls` (56%) - Only when media exists

### ❌ RARELY FILLED (9 columns) - CONSIDER REMOVING
- `analysis_model` (0%) - Should be filled but isn't
- `content_category` (0%) - Duplicate of category?
- `hashtags` (2%), `mentions` (8%) - Mostly empty (Twitter has them)
- `num_comments` (0%), `upvote_ratio` (0%) - Should be in engagement JSON
- `saved_at` (0%) - Not being set
- `target_social_media` (0%) - Unused feature
- `time_sensitivity_reason` (0%) - Unused feature

## What IntelligentContentAnalyzer Produces

Based on code analysis (`_create_analysis_prompt`), the analyzer returns:
```json
{
  "category": "Technology",
  "subcategory": "AI/ML",
  "content_type": "Tutorial",
  "topics": ["ai", "automation"],
  "key_concepts": ["agents", "prompts"],
  "summary": "2-3 sentence summary",
  "why_valuable": "Why bookmark this",
  "sentiment": "Positive",
  "complexity_level": "Intermediate",
  "time_to_consume": "5 minutes",
  "actionable_items": ["action1", "action2"],
  "learning_value": "What you learn",
  "practical_applications": ["how to apply"],
  "related_skills": ["skill1"],
  "follow_up_research": ["next steps"],
  "quality_indicators": ["why quality"],
  "tags": ["searchable", "keywords"],
  "confidence_score": 0.85
}
```

**ISSUE:** Many of these fields (actionable_items, learning_value, practical_applications, etc.) are NOT in the Supabase schema!

## What EmbeddingService Needs

```python
# Only uses these fields:
- content (required)
- title (optional)
- hashtags (optional)
- author (optional)
```

Generates:
- `embedding` - vector(384) for all-MiniLM-L6-v2 model
- `embedding_model` - text (model name)

**ISSUE:** `sentence-transformers` is NOT installed! Need to run:
```bash
pip install sentence-transformers
```

## Recommended SQL Migration

### Option A: Minimal (Just add what's DEFINITELY needed)

```sql
-- 1. Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add embedding columns
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding vector(384);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'all-MiniLM-L6-v2';

-- 3. Add language detection (useful for filtering)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS language text DEFAULT 'en';

-- 4. Create index for similarity search
CREATE INDEX IF NOT EXISTS posts_embedding_idx 
ON posts USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 5. Fix analysis_model (should be filled but isn't)
-- This will be populated retroactively
```

### Option B: Aggressive Cleanup (Remove unused columns)

```sql
-- WARNING: This removes data! Only do if you're sure these aren't used

-- Remove completely unused columns
ALTER TABLE posts DROP COLUMN IF EXISTS content_category;
ALTER TABLE posts DROP COLUMN IF EXISTS saved_at;
ALTER TABLE posts DROP COLUMN IF EXISTS target_social_media;
ALTER TABLE posts DROP COLUMN IF EXISTS time_sensitivity_reason;
ALTER TABLE posts DROP COLUMN IF EXISTS is_time_sensitive;

-- Remove engagement columns (should be in engagement JSONB)
ALTER TABLE posts DROP COLUMN IF EXISTS num_comments;
ALTER TABLE posts DROP COLUMN IF EXISTS upvote_ratio;

-- Consider: Remove summary (duplicate of ai_summary)
-- ALTER TABLE posts DROP COLUMN IF EXISTS summary;
```

## Recommended Actions

### 1. Install Dependencies First
```bash
pip install sentence-transformers
```

### 2. Run Minimal SQL (Safe - adds columns only)
Run the SQL from **Option A** above in Supabase.

### 3. Test Embedding Generation
```python
from src.core.indexing.embedding_service import get_embedding_service

service = get_embedding_service()
print(f"Ready: {service.is_available()}")  # Should be True now

test_embedding = service.generate_embedding("test content")
print(f"Works: {len(test_embedding) == 384}")  # Should be True
```

### 4. Fix Analysis Model Tracking
The analyzer should set `analysis_model` but doesn't. Check if this needs fixing in:
- `src/services/analysis/post_analyzer.py` line ~125

### 5. Update PostInserter Mapping
Check `src/services/supabase/post_inserter.py` to ensure new fields are mapped:
- `embedding` → from EmbeddingService
- `embedding_model` → from EmbeddingService  
- `language` → detect from content
- `analysis_model` → from analyzer (currently missing!)

## What Collectors Need To Do

Current flow:
1. Collector extracts posts → `SocialPost` object
2. Saves to local DB → `db_manager.add_post()`
3. Optionally analyzes → `analyze_and_store_post()` 
4. Syncs to Supabase → `supabase_adapter.save_post()`

**Missing:** Embedding generation! Should happen after analysis, before Supabase sync.

### Recommended Integration Point

In `src/services/analysis/post_analyzer.py`, after line 125 (AI analysis), add:

```python
# Generate embedding
from src.core.indexing.embedding_service import get_embedding_service

embedding_service = get_embedding_service()
if embedding_service.is_available():
    content_for_embedding = embedding_service.prepare_content_for_embedding(enhanced_post)
    embedding = embedding_service.generate_embedding(content_for_embedding)
    if embedding:
        enhanced_post['embedding'] = embedding
        enhanced_post['embedding_model'] = embedding_service.model_name
```

## Summary

**Safe to add NOW:**
- ✅ `embedding` vector(384)
- ✅ `embedding_model` text
- ✅ `language` text
- ✅ Index for similarity search

**Need to install first:**
- ❌ `pip install sentence-transformers`

**Need to verify in code:**
- ⚠️ Is `analysis_model` being set?
- ⚠️ Are embeddings generated during analysis?
- ⚠️ Is language detection happening?

**Optional cleanup (after data migration):**
- Remove 9 rarely-used columns
- Consolidate `summary` into `ai_summary`
- Move `num_comments`/`upvote_ratio` to engagement JSON

**My recommendation:** Run Option A (minimal), install sentence-transformers, then we integrate embedding generation into the analyzer.
