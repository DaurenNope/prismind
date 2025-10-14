# Supabase Schema Redesign & Enhancement Plan

## 🎯 Goals

1. **Clean up redundant/unused fields**
2. **Add pgvector for semantic search**
3. **Ensure ALL posts are auto-analyzed on insert**
4. **Standardize categories and organization**
5. **Make schema useful for other projects**

## 📊 Current Issues

### ❌ Redundant Fields (Remove/Consolidate)
- `summary` + `ai_summary` (same thing, keep `ai_summary`)
- `category` + `subcategory` + `topic` + `folder_category` + `content_category` (5 ways to categorize! Pick 1-2)
- `tags` + `smart_tags` + `key_concepts` (consolidate into `tags` array)
- `is_rewrite_candidate` + `target_social_media` (not core functionality, remove)
- `is_time_sensitive` + `time_sensitivity_reason` (rarely used, remove)
- `engagement` field missing but `num_comments` + `upvote_ratio` exist (consolidate)

### ⚠️ Missing Critical Fields
- **`embedding`** - pgvector for semantic search (CRITICAL!)
- **`embedding_model`** - track which model generated embedding
- **`language`** - auto-detected language
- **`topics`** - array of detected topics (not single topic)
- **`entities`** - extracted people/orgs/locations
- **`quality_metrics`** - JSON with readability, info density, etc.

### 🔧 Fields to Keep & Improve

**Core Identity:**
- `id` (UUID, auto)
- `post_id` (external ID)
- `platform`
- `url`
- `created_at`

**Content:**
- `title` (auto-generated from content)
- `content` (full text)
- `author`
- `author_handle`

**Metadata:**
- `post_type` (tweet/thread/post/article)
- `content_type` (text/video/image/link)
- `media_urls` (array)
- `hashtags` (array)
- `mentions` (array)
- `language` (NEW - auto-detected)

**AI Analysis (Auto-populated on insert!):**
- `embedding` (vector(1536) - NEW!)
- `embedding_model` (text - NEW!)
- `ai_summary` (concise summary)
- `sentiment` (positive/negative/neutral)
- `topics` (array - NEW! replaces topic/category mess)
- `tags` (array - consolidate smart_tags + key_concepts)
- `entities` (array - NEW! people/orgs mentioned)
- `value_score` (0-10, usefulness rating)
- `quality_score` (0-10, content quality)
- `analyzed_at` (timestamp)
- `analysis_model` (which AI model used)

**Organization (Simplified):**
- `category` (single: tech/finance/personal/news/etc)
- `is_saved` (bookmarked)
- `is_deleted` (soft delete)

**Engagement:**
- `engagement` (JSONB with likes/comments/shares)

**System:**
- `saved_at`
- `updated_at`

## 🗑️ Fields to REMOVE

```sql
-- Remove redundant/unused fields
ALTER TABLE posts DROP COLUMN IF EXISTS summary;  -- Use ai_summary
ALTER TABLE posts DROP COLUMN IF EXISTS subcategory;  -- Use topics array
ALTER TABLE posts DROP COLUMN IF EXISTS topic;  -- Use topics array
ALTER TABLE posts DROP COLUMN IF EXISTS folder_category;  -- Use category
ALTER TABLE posts DROP COLUMN IF EXISTS content_category;  -- Use category
ALTER TABLE posts DROP COLUMN IF EXISTS smart_tags;  -- Consolidate into tags
ALTER TABLE posts DROP COLUMN IF EXISTS key_concepts;  -- Consolidate into tags
ALTER TABLE posts DROP COLUMN IF EXISTS is_rewrite_candidate;  -- Not core
ALTER TABLE posts DROP COLUMN IF EXISTS is_time_sensitive;  -- Rarely used
ALTER TABLE posts DROP COLUMN IF EXISTS time_sensitivity_reason;  -- Rarely used
ALTER TABLE posts DROP COLUMN IF EXISTS target_social_media;  -- Not core
ALTER TABLE posts DROP COLUMN IF EXISTS content_quality_score;  -- Use quality_score
ALTER TABLE posts DROP COLUMN IF EXISTS num_comments;  -- Move to engagement JSONB
ALTER TABLE posts DROP COLUMN IF EXISTS upvote_ratio;  -- Move to engagement JSONB
```

## ➕ Fields to ADD

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding for semantic search
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE posts ADD COLUMN IF NOT EXISTS embedding_model text DEFAULT 'text-embedding-3-small';

-- Add language detection
ALTER TABLE posts ADD COLUMN IF NOT EXISTS language text;

-- Add structured topics (replaces category mess)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS topics text[];

-- Add entity extraction
ALTER TABLE posts ADD COLUMN IF NOT EXISTS entities jsonb;

-- Add quality score (rename content_quality_score)
ALTER TABLE posts ADD COLUMN IF NOT EXISTS quality_score integer DEFAULT 0;

-- Create vector similarity search index
CREATE INDEX IF NOT EXISTS posts_embedding_idx ON posts USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create GIN index for array searches
CREATE INDEX IF NOT EXISTS posts_topics_idx ON posts USING gin(topics);
CREATE INDEX IF NOT EXISTS posts_tags_idx ON posts USING gin(tags);
```

## 🤖 Auto-Analysis Pipeline

### Trigger on INSERT/UPDATE

```python
# src/services/auto_analyzer.py

async def auto_analyze_post(post_data: dict) -> dict:
    """
    Automatically analyze post on insert/update
    Returns enriched post data with AI analysis
    """
    content = post_data.get('content', '')
    
    # 1. Generate embedding (CRITICAL for semantic search)
    embedding = await generate_embedding(content)
    
    # 2. Detect language
    language = detect_language(content)
    
    # 3. Generate summary
    ai_summary = await generate_summary(content)
    
    # 4. Sentiment analysis
    sentiment = analyze_sentiment(content)
    
    # 5. Extract topics (AI-powered)
    topics = await extract_topics(content)
    
    # 6. Extract tags/keywords
    tags = extract_keywords(content)
    
    # 7. Extract entities (people, orgs, locations)
    entities = extract_entities(content)
    
    # 8. Calculate value score
    value_score = calculate_value_score(content, topics, entities)
    
    # 9. Calculate quality score
    quality_score = calculate_quality_score(content)
    
    return {
        **post_data,
        'embedding': embedding,
        'embedding_model': 'text-embedding-3-small',
        'language': language,
        'ai_summary': ai_summary,
        'sentiment': sentiment,
        'topics': topics,
        'tags': tags,
        'entities': entities,
        'value_score': value_score,
        'quality_score': quality_score,
        'analyzed_at': datetime.now().isoformat(),
        'analysis_model': 'gpt-4o-mini'
    }
```

### Integration Point

```python
# Modify src/storage/supabase_adapter.py

def save_post(self, post: Dict[str, Any]) -> bool:
    try:
        # 1. Auto-analyze if not already analyzed
        if not post.get('analyzed_at'):
            post = await auto_analyze_post(post)
        
        # 2. Use PostInserter to properly map data
        result = self.post_inserter.insert_post(post)
        return bool(result)
    except Exception:
        return False
```

## 📈 New Capabilities Unlocked

### 1. Semantic Search
```sql
-- Find similar posts using vector similarity
SELECT post_id, title, 1 - (embedding <=> $query_embedding) as similarity
FROM posts
WHERE 1 - (embedding <=> $query_embedding) > 0.8
ORDER BY embedding <=> $query_embedding
LIMIT 10;
```

### 2. Topic-Based Discovery
```sql
-- Find posts by topic
SELECT * FROM posts WHERE 'AI' = ANY(topics);

-- Find posts with multiple topics
SELECT * FROM posts WHERE topics @> ARRAY['AI', 'crypto'];
```

### 3. Entity-Based Search
```sql
-- Find posts mentioning specific person
SELECT * FROM posts WHERE entities->>'people' @> '["Elon Musk"]';
```

### 4. Quality Filtering
```sql
-- Get high-quality posts only
SELECT * FROM posts 
WHERE quality_score >= 7 
AND value_score >= 8
ORDER BY created_at DESC;
```

### 5. Smart Categorization
```sql
-- Group by category and topics
SELECT category, unnest(topics) as topic, COUNT(*)
FROM posts
GROUP BY category, topic
ORDER BY count DESC;
```

## 🎯 Standardized Categories

Instead of 5 different category fields, use ONE with clear taxonomy:

```python
CATEGORIES = {
    'tech': ['AI', 'crypto', 'programming', 'tools', 'startups'],
    'finance': ['trading', 'investing', 'markets', 'defi'],
    'learning': ['tutorials', 'resources', 'courses', 'tips'],
    'news': ['industry', 'announcements', 'updates'],
    'personal': ['productivity', 'health', 'mindset'],
    'entertainment': ['memes', 'humor', 'misc']
}
```

## 🚀 Migration Plan

### Phase 1: Add New Fields (Non-breaking)
1. Add pgvector extension
2. Add new columns (embedding, language, topics, entities, quality_score)
3. Create indexes

### Phase 2: Backfill Existing Data
1. Run analysis on all existing posts
2. Generate embeddings for all posts
3. Extract topics/entities from existing content

### Phase 3: Consolidate Fields
1. Migrate data from old fields to new
2. Remove redundant columns

### Phase 4: Update Application Code
1. Modify collectors to use auto-analysis
2. Update queries to use new fields
3. Add semantic search endpoints

## 📝 Next Steps

1. **Create migration SQL script** - Add new fields safely
2. **Build auto-analyzer service** - AI analysis on every insert
3. **Create backfill script** - Analyze all existing posts
4. **Update PostInserter** - Use new schema
5. **Add search API** - Leverage pgvector for semantic search

This will make Supabase a **powerful, AI-enhanced knowledge base** that's useful for:
- Semantic search across all saved content
- Smart categorization and discovery
- Quality filtering
- Cross-project data sharing
- Building AI apps on top of your data
