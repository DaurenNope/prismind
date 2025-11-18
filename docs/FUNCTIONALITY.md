# BEYONDLINES FUNCTIONALITY

This document describes the working core: Collect → Analyze → Store → Surface, the orchestrator API, data contracts, and feature flags.

## Golden Path
1) Collect from sources (RSS, Reddit, Twitter; optional Threads, GitHub trending)
2) Analyze posts (AI providers) to enrich with consistent fields
3) Store (Supabase primary; optional SQLite cache mirror)
4) Surface via Svelte UI, Telegram bot, CLI (and optional Research API)
5) Present digestible news-format summaries with drill-down

## Orchestrator API
- `collect_all(platforms?: list[str]) -> { platform: count, total, errors }`
- `collect_{platform}() -> int`
- `autonomous_discover() -> { saved, sources, ... }`
- `analyze_batch(limit=20) -> int`
- `generate_digest() -> { date, top_stories, trending_topics, by_source }`
- `build_news_feed(limit=50) -> list[dict]`  (flattened, readable items with links and summaries)

All interfaces call the orchestrator; no direct collector calls.

## Data Contracts
Post fields (minimum):
- `id` (stable id)
- `post_id`, `platform`, `source`
- `title`, `content`, `url`, `author`, `created_at`

AI fields (defaults guaranteed):
- `key_concepts: list` ([])
- `suggested_tags: list` ([])
- `action_items: list` ([])
- `value_score: float` (0..10)
- `quality_score: float` (0..10)
- `summary: str` ("")

## Storage
- Supabase primary: all writes go to Supabase
- SQLite optional cache (flag): mirrors writes and supports local reads when offline

## Feature Flags (via `.env` or `config/collection.json`)
- `ENABLE_THREADS` (default: false)
- `ENABLE_GITHUB_TRENDING` (default: false)
- `ENABLE_ANALYSIS` (default: true)
- `ENABLE_SQLITE_CACHE` (default: true)
- `SUPABASE_ENABLED` (default: true)
- `RESEARCH_API_ENABLED` (default: false)

## Cookies
- Normalized under `cookies/`: `twitter.json`, `threads.json`

## Commands
- Web UI: `svelte run src/web/app.py`
- Telegram Bot: `python src/services/telegram_bot.py`
- Full Collection: `python run_full_collection.py`

## Notes
- Optional sources (Threads, GitHub trending) are disabled by default until stabilized.
- Orchestrator is the single integration entry for UI/Bot/CLI/API.

# BEYONDLINES Core Functionality

## Overview

BEYONDLINES is an autonomous intelligence system that discovers, analyzes, and curates content from various sources with zero manual bookmarking. This document describes the core functionality that is working and should be maintained.

## Core Components

### 1. Content Collection

The system collects content from multiple sources:

1. **RSS Feeds**: 60+ curated RSS feeds across diverse categories including technology, business, science, health, spirituality, and alternative topics
2. **Reddit**: Posts from relevant subreddits
3. **Social Bookmarks**: User bookmarks from Twitter, Reddit, and Threads (manual collection)

### 2. Content Analysis

Collected content is processed through several analysis steps:

1. **Quality Filtering**: Basic quality scoring to filter out low-value content
2. **Topic Matching**: Content is matched against user's topics of interest
3. **Deduplication**: Duplicate content is removed
4. **Storage**: Processed content is stored in a Supabase database

### 3. User Interfaces

Users can interact with BEYONDLINES through:

1. **Web Dashboard**: Svelte-based interface for browsing content and system status
2. **Telegram Bot**: Command-based interface for controlling the system and receiving updates
3. **CLI Tools**: Command-line tools for running collection and analysis tasks

## Data Flow

```
┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Sources   │───▶│  Collection  │───▶│  Analysis    │───▶│   Storage    │
└─────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
       │                   │                    │                  │
       ▼                   ▼                    ▼                  ▼
  RSS/Reddit        ArticleExtractor    Quality/Relevance    Supabase DB
  Social BMK        Multi-topic logic   Deduplication         discoveries table

┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│Interfaces   │◀───│  Processing  │◀───│   Database   │
└─────────────┘    └──────────────┘    └──────────────┘
 Web/Telegram      Analysis Engine      Query Layer
 CLI Tools         AI Enhancements      Stats/Reports
```

## Key Files and Modules

### Core Collection
- [src/core/extraction/multi_topic_sources.py](file:///Users/mac/Documents/Development/beyondlines/src/core/extraction/multi_topic_sources.py) - Defines content sources across categories
- [src/core/extraction/article_extractor.py](file:///Users/mac/Documents/Development/beyondlines/src/core/extraction/article_extractor.py) - RSS feed processing
- [run_full_collection.py](file:///Users/mac/Documents/Development/beyondlines/run_full_collection.py) - Main collection pipeline

### Analysis and Storage
- [src/services/autonomous_discovery.py](file:///Users/mac/Documents/Development/beyondlines/src/services/autonomous_discovery.py) - Core discovery logic
- [src/services/new_database_manager.py](file:///Users/mac/Documents/Development/beyondlines/src/services/new_database_manager.py) - Database operations abstraction
- [src/supabase_manager.py](file:///Users/mac/Documents/Development/beyondlines/src/supabase_manager.py) - Supabase integration

### User Interfaces
- [src/web/app.py](file:///Users/mac/Documents/Development/beyondlines/src/web/app.py) - Main web dashboard
- [src/services/telegram_bot.py](file:///Users/mac/Documents/Development/beyondlines/src/services/telegram_bot.py) - Telegram bot implementation
- [main.py](file:///Users/mac/Documents/Development/beyondlines/main.py) - Main entry point

## Working Features

### Content Collection
- RSS feed processing from 60+ sources
- Reddit post collection
- Social bookmark extraction (manual)
- Content deduplication

### Analysis
- Basic quality filtering
- Topic matching against user interests
- Content storage with metadata

### User Interface
- Web dashboard with content browsing
- Telegram bot with basic commands
- CLI execution of collection pipeline

## Simplification Plan

To address the complexity and make the system maintainable, we should:

1. **Remove incomplete features**: Eliminate partially implemented components that don't add value
2. **Consolidate similar modules**: Merge multiple discovery engines into one cohesive system
3. **Focus on core workflow**: Prioritize the RSS → Analysis → Storage → UI workflow
4. **Improve documentation**: Create clear documentation of the simplified system
