# PrisMind Database Schema

## Overview

This document describes the **essential schema** for the PrisMind analyzer, focusing on fields that are:
1. **Required for the rewriter** (main purpose)
2. **Required for discovery method** (future use)

The schema is intentionally **lean** - only necessary data is stored.

---

## Core Tables

### `posts` Table

The primary table for storing collected and analyzed posts.

#### Core Identification Fields
- `post_id` (TEXT, PRIMARY KEY) - Unique post identifier
- `platform` (TEXT) - Source platform: `twitter`, `reddit`, `threads`
- `url` (TEXT) - Original post URL
- `created_at` (TIMESTAMPTZ) - When post was originally created on platform
- `author` (TEXT) - Post author name
- `author_handle` (TEXT) - Author username/handle

#### Content Fields
- `content` (TEXT) - Post text content
- `title` (TEXT) - Post title (if applicable)
- `media_urls` (TEXT[]) - Array of media URLs
- `hashtags` (TEXT[]) - Array of hashtags
- `mentions` (TEXT[]) - Array of mentioned users

#### Essential Analysis Fields (Required)

These fields are **always populated** by the analyzer and are essential for rewrite and discovery:

##### Basic Analysis
- `ai_summary` (TEXT) - AI-generated summary of the post
- `value_score` (NUMERIC) - Overall value score (0-10)
- `quality_score` (NUMERIC) - Content quality score (0-10)
- `tags` (TEXT[]) - Content tags/categories
- `key_concepts` (TEXT[]) - Key concepts extracted from content
- `topic` (TEXT) - Main topic/subject
- `content_type` (TEXT) - Type: `text`, `image`, `video`, `link`, etc.
- `language` (TEXT) - Detected language code (e.g., `en`, `ru`)

##### Metadata
- `analyzed_at` (TIMESTAMPTZ) - When analysis was performed
- `analysis_model` (TEXT) - AI model used (e.g., `gemini-2.0-flash`)

##### Rewrite-Focused Fields (Required for Rewriter)

These fields help determine if a post is suitable for rewriting and for which personas:

- `rewrite_score` (NUMERIC) - Overall rewrite potential (0-10)
- `rewrite_readiness` (TEXT) - Status: `ready`, `needs_work`, `not_suitable`
- `rewrite_reasons` (TEXT[]) - Reasons why this post is good for rewriting
- `rewrite_risks` (TEXT[]) - Potential risks or challenges in rewriting
- `analysis_confidence` (NUMERIC) - Confidence in analysis (0-1)
- `analysis_depth` (TEXT) - Depth: `fast`, `standard`, `deep`
- `needs_deep_analysis` (BOOLEAN) - Flag for requiring deeper analysis

##### Persona-Aware Scoring (Required for Rewriter & Discovery)

These fields enable persona-specific rewrite targeting:

- `persona_fit_scores` (JSONB) - Object mapping persona keys to fit scores (0-10)
  ```json
  {
    "tech_enthusiast": 8.5,
    "startup_founder": 7.2,
    "designer": 6.8
  }
  ```
- `persona_fit_reasons` (JSONB) - Object mapping persona keys to fit reasons
  ```json
  {
    "tech_enthusiast": ["Technical depth", "Practical examples"],
    "startup_founder": ["Business insights", "Growth strategies"]
  }
  ```
- `best_persona_key` (TEXT) - The persona with the highest fit score
- `best_persona_score` (NUMERIC) - The highest persona fit score
- `best_persona_reasons` (TEXT[]) - Reasons why this persona is the best fit

#### Embedding Fields (Optional but Recommended)
- `embedding` (TEXT) - JSON-encoded embedding vector for semantic search
- `embedding_model` (TEXT) - Model used for embedding (e.g., `all-MiniLM-L6-v2`)

#### Legacy/Optional Fields

These fields may exist but are not required for core functionality:
- `sentiment` (TEXT) - Sentiment analysis result
- `engagement` (JSONB) - Engagement metrics
- `is_saved` (BOOLEAN) - Whether post was saved/bookmarked
- `saved_at` (TIMESTAMPTZ) - When post was saved

---

## Schema Principles

### 1. **Essential Fields Only**
- Only store fields that are actively used by the rewriter or discovery system
- Avoid redundant or derived fields that can be computed on-demand

### 2. **Always Filled**
- The analyzer **must** fill all essential fields, even if with default/placeholder values
- Use `_coerce_analysis` to ensure completeness

### 3. **Type Consistency**
- Lists stored as `TEXT[]` in Supabase, JSON strings in SQLite
- Numeric scores as `NUMERIC` (not integer) for precision
- JSONB for complex nested structures (persona scores/reasons)

### 4. **Rewrite-Centric**
- Scoring focuses on **rewrite quality** and **persona fit**, not just content quality
- `rewrite_score` reflects how well a post can be adapted for different personas
- `persona_fit_scores` enable targeted rewriting for specific audiences

### 5. **Discovery-Ready**
- Fields like `tags`, `key_concepts`, `topic`, and `embedding` support future discovery features
- Persona matching enables personalized content discovery

---

## Migration Guide

### Adding New Essential Fields

1. **Update Supabase schema** via migration:
   ```sql
   ALTER TABLE posts
     ADD COLUMN IF NOT EXISTS new_field TEXT;
   ```

2. **Update SQLite schema** in `src/database/operations.py`:
   - Add to `_ensure_posts_schema` column definitions
   - Add to `update_post` JSON serialization if needed

3. **Update analyzer** in `src/core/analysis/intelligent_content_analyzer.py`:
   - Add to `_create_analysis_prompt` JSON schema
   - Add to `_coerce_analysis` to ensure it's always filled

4. **Update persistence** in `src/services/analysis/post_analyzer.py`:
   - Add to `essential_fields` dict

---

## Field Completeness

### Required Fill Rate: 100%

All essential fields must be populated. The analyzer uses `_coerce_analysis` to:
- Fill missing fields with heuristics
- Provide default values when AI model omits them
- Ensure schema consistency

### Monitoring

Use `DatabaseAgent().get_id_format_health()` and analyzer fill-rate metrics to monitor:
- Schema completeness
- Field population rates
- Data quality issues

---

## Example Post Record

```json
{
  "post_id": "1onqx6t",
  "platform": "reddit",
  "url": "https://reddit.com/r/programming/comments/1onqx6t/...",
  "content": "Here's how I optimized my API...",
  "ai_summary": "Post discusses API optimization techniques...",
  "value_score": 8.5,
  "quality_score": 8.0,
  "tags": ["programming", "api", "optimization"],
  "key_concepts": ["API design", "performance", "caching"],
  "topic": "Software Engineering",
  "content_type": "text",
  "language": "en",
  "analyzed_at": "2025-11-04T22:00:00Z",
  "analysis_model": "gemini-2.0-flash",
  "rewrite_score": 9.0,
  "rewrite_readiness": "ready",
  "rewrite_reasons": ["Clear structure", "Actionable insights"],
  "rewrite_risks": ["Technical jargon"],
  "analysis_confidence": 0.95,
  "analysis_depth": "standard",
  "needs_deep_analysis": false,
  "persona_fit_scores": {
    "tech_enthusiast": 9.5,
    "startup_founder": 7.0,
    "designer": 4.0
  },
  "persona_fit_reasons": {
    "tech_enthusiast": ["Technical depth", "Practical examples"],
    "startup_founder": ["Performance optimization", "Scalability"]
  },
  "best_persona_key": "tech_enthusiast",
  "best_persona_score": 9.5,
  "best_persona_reasons": ["Highly technical content", "Strong practical value"]
}
```

---

## Notes

- **Supabase is the primary database** - SQLite is a local cache
- **Analysis is always performed** before rewrite attempts
- **Persona matching is built into analysis** - not a separate step
- **Schema is versioned** via `analysis_model` and `analysis_depth` fields







