# Simplified Supabase Schema Design

## Current State Analysis
- **Total columns**: 50
- **Essential columns**: 8 (16%)
- **Unused/empty columns**: 37 (74%)
- **Metadata columns**: 5 (10%)

## Proposed Simplified Schema

### Core Posts Table (Simplified)

```sql
-- Essential columns only
CREATE TABLE IF NOT EXISTS public.posts (
    id BIGSERIAL PRIMARY KEY,
    post_id TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT NOT NULL,
    author TEXT NOT NULL,
    author_handle TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    language TEXT DEFAULT 'en',
    
    -- Optional analysis fields (only when needed)
    ai_summary TEXT,
    value_score REAL,
    quality_score REAL,
    sentiment TEXT,
    key_concepts TEXT[], -- Array of strings
    tags TEXT[], -- Array of strings
    category TEXT,
    
    -- System fields
    is_saved BOOLEAN DEFAULT true,
    created_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_posts_platform ON public.posts (platform);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON public.posts (created_at);
CREATE INDEX IF NOT EXISTS idx_posts_value_score ON public.posts (value_score);
CREATE INDEX IF NOT EXISTS idx_posts_language ON public.posts (language);
```

### What We're Removing (37 columns)

**Analysis Fields (Mostly Empty)**:
- action_items, actionable_insights, ai_service_used
- analysis_timestamp, analyzed_at, content_summary
- educational_value, insights, intelligence_analysis
- recommendations, sentiment_analysis, smart_tags

**Metadata Fields (Unused)**:
- deleted, processed, engagement, metadata
- folder_category, hashtags, mentions, media_urls
- subreddit, title, topic, content_type
- rewrite_*, source

**Timestamp Fields (Redundant)**:
- saved_at (use created_timestamp)

### Benefits of Simplification

1. **Performance**: Faster queries, smaller indexes
2. **Maintainability**: Easier to understand and modify
3. **Storage**: Significantly reduced storage requirements
4. **Development**: Simpler API, fewer edge cases
5. **Cost**: Lower Supabase costs (fewer columns)

### Migration Strategy

1. **Create new simplified table**
2. **Migrate essential data**
3. **Update application code**
4. **Drop old table**

## Alternative: Minimal Schema

If you want to go even simpler:

```sql
-- Ultra-minimal schema
CREATE TABLE IF NOT EXISTS public.posts (
    id BIGSERIAL PRIMARY KEY,
    post_id TEXT NOT NULL UNIQUE,
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    url TEXT NOT NULL,
    author TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    language TEXT DEFAULT 'en',
    ai_summary TEXT,
    value_score REAL,
    created_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

This reduces from 50 columns to just 11 columns (78% reduction)!

