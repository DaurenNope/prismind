# 🗺️ BEYONDLINES Project Map - Files, Features & Tests

**Complete mapping of codebase → features → tests**

---

## 📂 Root Directory Structure

```
beyondlines/
├── 📁 backups/          # Database backups
├── 📁 config/           # Configuration files
├── 📁 cookies/          # Authentication cookies
├── 📁 data/             # Application data (books, etc.)
├── 📁 docs/             # Documentation
├── 📁 library/          # Library files
├── 📁 logs/             # Application logs
├── 📁 migrations/       # SQL schema migrations
├── 📁 scripts/          # Utility scripts
├── 📁 src/              # ⭐ MAIN SOURCE CODE
├── 📁 tests/            # ⭐ TEST SUITE
├── 📁 var/              # Variable runtime data (sessions)
│
├── main.py              # ⭐ Primary entry point
├── run_full_collection.py  # Quick collection runner
├── start_web.sh         # Web UI launcher
├── run_telegram_bot.sh  # Telegram bot launcher
└── beyondlines.db          # SQLite database
```

---

## 🎯 Feature → File → Test Mapping

### 1. 🌐 WEB DASHBOARD (Svelte UI)

#### Feature: Main Web Application
**Files:**
- `src/web/app.py` - Main Svelte application entry point
- `src/web/__main__.py` - Module entry point

**Components:**
- `src/web/components/sidebar.py` - Navigation sidebar
- `src/web/components/tabs.py` - Tab rendering (dashboard, browse, settings)
- `src/web/components/dashboard.py` - Main dashboard view
- `src/web/components/dashboard_posts.py` - Posts display component
- `src/web/components/dashboard_analytics.py` - Analytics widgets
- `src/web/components/dashboard_settings.py` - Settings panel

**Tests:**
- ❌ No direct web UI tests (manual testing required)
- Could add: `tests/test_web_components.py`

**How to Run:**
```bash
svelte run src/web/app.py
# Or
./start_web.sh
```

---

#### Feature: Discoveries Tab (RSS/Reddit/GitHub)
**Files:**
- `src/web/components/discoveries_tab.py` - Autonomous discovery feed
- `src/services/autonomous_discovery.py` - Discovery engine
- `src/core/extraction/edgy_sources.py` - 60 curated RSS sources
- `src/core/extraction/reddit_extractor.py` - Reddit hot posts

**Tests:**
- `tests/test_reddit_collector.py` - Tests Reddit extraction
- Could add: `tests/test_discoveries_ui.py`

**Database Tables:**
- `discoveries` - Discovered content
- `supabase.discoveries` - Synced discoveries

**How it Works:**
1. `AutonomousDiscovery.discover_content()` fetches from RSS/Reddit/GitHub
2. Quality filtering (score > 0.7)
3. Deduplication
4. Store in `discoveries` table
5. Display in UI with dismiss/save actions

---

#### Feature: Telegram Tab (Russian Crypto Intelligence)
**Files:**
- `src/web/components/telegram_tab.py` - Telegram feed UI
- `src/core/extraction/telegram_channel_extractor.py` - Telegram scraper
- `config/telegram_channels.txt` - Channel list

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_telegram_ui.py`

**Database Tables:**
- `telegram_messages` - Scraped messages
- `supabase.telegram_messages` - Synced messages

**How to Run:**
```bash
./run_telegram_bot.sh
```

---

#### Feature: Unified Feed Tab
**Files:**
- `src/web/components/unified_feed_tab.py` - Combined feed view

**Tests:**
- ❌ No dedicated tests

---

#### Feature: Automation Tab
**Files:**
- `src/web/components/automation_tab.py` - Scheduled collection UI
- `src/services/intelligence_automation.py` - Automation service

**Tests:**
- ❌ No dedicated tests

---

#### Feature: Rewriter Tab
**Files:**
- `src/web/components/rewriter_tab.py` - Content rewriting UI
- `src/services/content_rewriter.py` - LLM-based rewriting

**Tests:**
- ❌ No dedicated tests

---

#### Feature: Sources Tab
**Files:**
- `src/web/components/sources_tab.py` - Source management UI

**Tests:**
- ❌ No dedicated tests

---

### 2. 🤖 TELEGRAM BOT

#### Feature: Telegram Bot (13 Commands)
**Files:**
- `src/services/telegram_bot.py` - Main bot with commands
- `src/services/telegram_bot_agents_extension.py` - Advanced agent features
- `src/services/telegram_formatting.py` - Message formatting

**Commands:**
- `/start` - Initialize bot
- `/help` - Show commands
- `/status` - System status
- `/collect` - Run collection
- `/latest [N]` - Show N latest
- `/search <query>` - Search discoveries
- `/ask <question>` - Research question
- `/recommend` - Personalized recommendations
- `/curate <topic>` - Curate by topic
- `/digest` - Daily digest
- `/insights` - Content insights
- `/feed` - News feed
- `/discoveries` - Recent discoveries

**Tests:**
- ❌ No telegram bot tests
- Could add: `tests/test_telegram_bot.py`

**How to Run:**
```bash
./run_telegram_bot.sh
# Or
python src/services/telegram_bot.py
```

---

### 3. 📱 SOCIAL MEDIA COLLECTORS

#### Feature: Twitter/X Bookmarks Collection
**Files:**
- `src/core/extraction/twitter_extractor_playwright.py` - Main Twitter extractor
- `src/core/extraction/twitter/` - Twitter extraction modules
  - `twitter_auth.py` - Authentication
  - `twitter_data_extractor.py` - Data extraction
  - `twitter_extractor_main.py` - Main logic
  - `tweet_engagement_analyzer.py` - Engagement analysis
  - `tweet_field_extractors.py` - Field extraction
- `cookies/twitter_cookies_cryptoniard.json` - Auth cookies

**Tests:**
- `tests/test_twitter_collector.py` - Twitter collector tests
- `tests/test_collectors.py` - General collector tests

**Database Tables:**
- `posts` - All collected posts
- `supabase.posts` - Synced posts

**How it Works:**
1. Load cookies from JSON
2. Navigate to bookmarks page
3. Scroll and extract tweets
4. Parse tweet data (author, content, engagement)
5. Download media (images/videos)
6. Store in database

**Status:** ✅ WORKING

---

#### Feature: Reddit Saved Posts Collection
**Files:**
- `src/core/extraction/reddit_extractor.py` - Reddit extractor
- `cookies/config/reddit.json` - Auth cookies

**Tests:**
- `tests/test_reddit_collector.py` - Reddit collector tests

**Database Tables:**
- `posts` - All collected posts
- `supabase.posts` - Synced posts

**Environment Variables:**
```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=beyondlines:v1.0
```

**How it Works:**
1. Authenticate with Reddit API (PRAW)
2. Fetch saved posts
3. Extract post data (title, content, subreddit, score)
4. Store in database

**Status:** ✅ WORKING

---

#### Feature: Threads.net Posts Collection
**Files:**
- `src/core/extraction/threads_extractor.py` - Threads extractor (923 lines)
- `cookies/threads_cookies.json` - Auth cookies

**Tests:**
- `tests/test_threads_collector.py` - Threads collector tests

**Database Tables:**
- `posts` - All collected posts
- `supabase.posts` - Synced posts

**How it Works:**
1. Load cookies from JSON
2. Navigate to Threads profile/post
3. Extract JSON data from page
4. Parse thread data
5. Store in database

**Status:** ⚠️ NEEDS FIXING
**Issues:**
- Cookie authentication may be stale
- Threads HTML structure changes frequently
- Needs updated selectors

---

### 4. 🔍 AUTONOMOUS DISCOVERY

#### Feature: RSS Feed Discovery (60 Sources)
**Files:**
- `src/services/autonomous_discovery.py` - Main discovery engine
- `src/core/extraction/edgy_sources.py` - 60 curated RSS sources
- `src/core/extraction/multi_topic_sources.py` - Multi-topic sources
- `src/core/extraction/underground_sources.py` - Underground sources
- `src/core/extraction/article_extractor.py` - Article parsing

**Tests:**
- `tests/test_collection.py` - Collection tests
- `tests/test_all_components.py` - Integration tests

**Sources Categories:**
1. **Crypto Alpha** (5 sources)
2. **Underground Tech** (7 sources)
3. **Conspiracy/Esoteric** (8 sources)
4. **Financial Edge** (6 sources)
5. **AI Cutting Edge** (6 sources)
6. **Longevity/Biohacking** (5 sources)
7. **Startup Intelligence** (5 sources)
8. **Advanced DeFi** (8 sources)
9. **Psychedelics** (5 sources)
10. **Alternative News** (5 sources)

**How to Run:**
```bash
python run_full_collection.py
```

**Status:** ✅ WORKING

---

#### Feature: Active Discovery (Dynamic Search)
**Files:**
- `src/core/discovery/active_discovery.py` - Active discovery
- `src/core/discovery/web_crawler.py` - Web crawling
- `src/core/discovery/discovery_engine.py` - Discovery engine
- `src/core/discovery/deep_discovery.py` - Deep discovery
- `src/core/discovery/comprehensive_discovery.py` - Comprehensive discovery
- `src/core/discovery/topic_tracker.py` - Topic tracking
- `src/core/discovery/profile_manager.py` - User profile management
- `src/core/discovery/ai_scorer.py` - AI-powered scoring

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_active_discovery.py`

**Status:** 🔄 PARTIAL (needs enhancement per roadmap)

---

### 5. 🧠 AI ANALYSIS & INTELLIGENCE

#### Feature: Content Analysis
**Files:**
- `src/core/analysis/intelligent_content_analyzer.py` - Main AI analyzer
- `src/core/analysis/content_analyzer_core.py` - Core analysis logic
- `src/core/analysis/social_content_analyzer.py` - Social content analysis
- `src/core/analysis/ai_service_manager.py` - AI service management
- `src/services/analysis_service.py` - Analysis service

**Tests:**
- `tests/test_ai_analyzer.py` - AI analyzer tests
- `tests/test_post_analyzer.py` - Post analyzer tests
- `tests/test_analysis_only.py` - Analysis-only tests

**AI Services Used:**
- OpenAI GPT-4
- Google Gemini
- Anthropic Claude

**Analysis Features:**
- Category detection (crypto, AI, tech, etc.)
- Sentiment analysis
- Key concept extraction
- Quality scoring
- Topic classification

**Status:** ✅ WORKING

---

#### Feature: Value Scoring
**Files:**
- `src/core/analysis/value_scorer.py` - Main value scorer
- `src/core/analysis/value_scorer_patterns.py` - Pattern-based scoring

**Tests:**
- Covered by `tests/test_ai_analyzer.py`

**Scoring Factors:**
- Content quality
- Engagement metrics
- Source authority
- Novelty
- Relevance to interests

**Status:** ✅ WORKING

---

#### Feature: Thread Summarization
**Files:**
- `src/core/analysis/thread_summarizer.py` - Thread summarizer
- `src/core/analysis/thread_summarizer_ai.py` - AI-powered summarization
- `src/core/analysis/thread_summarizer_parser.py` - Parser logic
- `src/core/analysis/thread_summary.py` - Summary data models

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_thread_summarizer.py`

**Status:** ✅ WORKING

---

#### Feature: Media Analysis
**Files:**
- `src/core/analysis/media_analyzer.py` - Main media analyzer
- `src/core/analysis/media_ai_analyzer.py` - AI-powered media analysis
- `src/core/analysis/media_ocr_analyzer.py` - OCR for images
- `src/core/analysis/local_media_analyzer.py` - Local media processing

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_media_analyzer.py`

**Features:**
- Image analysis
- Video thumbnail extraction
- OCR text extraction
- Content moderation

**Status:** ⚠️ PARTIAL (pytesseract optional)

---

### 6. 🎓 INTELLIGENT CURATION

#### Feature: Smart Organizer
**Files:**
- `src/core/learning/smart_organizer.py` - Main organizer
- `src/core/learning/intelligent_curator.py` - Intelligent curation
- `src/core/learning/content_organizer.py` - Content organization
- `src/core/learning/preference_learner.py` - Preference learning

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_intelligent_curator.py`

**Features:**
- Auto-categorization
- Pattern learning
- Preference tracking
- Content recommendations

**Status:** ✅ WORKING

---

### 7. 🔬 RESEARCH ENGINE

#### Feature: Semantic Search
**Files:**
- `src/core/research/semantic_search.py` - Semantic search (core module)
- `src/core/research/semantic_search_engine.py` - Search engine
- `src/core/research/search_methods.py` - Search methods
- `src/core/research/search_filters.py` - Search filters
- `src/core/research/search_types.py` - Search type definitions
- `src/core/research/semantic_encoder.py` - Embedding encoder
- `src/research/semantic_search.py` - Top-level semantic search

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_semantic_search.py`

**Features:**
- Vector similarity search
- Semantic query understanding
- Context-aware retrieval
- Multi-field search

**Status:** 🔄 PARTIAL (needs embedding setup)

---

#### Feature: Research Engine
**Files:**
- `src/core/research/research_engine.py` - Main research engine
- `src/core/async_research_engine.py` - Async research engine
- `src/research/academic_research.py` - Academic research
- `src/research/book_research.py` - Book research

**Tests:**
- ❌ No dedicated tests

**Status:** 🔄 IN DEVELOPMENT

---

#### Feature: Content Analytics
**Files:**
- `src/core/research/content_analyzer.py` - Content analysis
- `src/core/research/content_quality_analyzer.py` - Quality analysis
- `src/core/research/content_keyword_analyzer.py` - Keyword extraction
- `src/core/research/content_trend_analyzer.py` - Trend analysis
- `src/core/research/content_gap_analysis.py` - Gap analysis
- `src/core/research/content_insights.py` - Content insights
- `src/core/research/quality_metrics.py` - Quality metrics
- `src/core/research/trend_analysis.py` - Trend analysis

**Tests:**
- ❌ No dedicated tests

**Status:** 🔄 IN DEVELOPMENT

---

### 8. 🤖 AI AGENTS

#### Feature: Research Agents
**Files:**
- `src/agents/research_agent.py` - Basic research agent
- `src/agents/enhanced_research_agent.py` - Enhanced research
- `src/agents/github_research_agent.py` - GitHub research
- `src/agents/autonomous_research_orchestrator.py` - Research orchestration

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_research_agents.py`

**Status:** 🔄 IN DEVELOPMENT

---

#### Feature: Librarian Agents
**Files:**
- `src/agents/librarian_agent.py` - Basic librarian
- `src/agents/enhanced_librarian_agent.py` - Enhanced librarian
- `src/agents/librarian_book_agent.py` - Book management

**Tests:**
- ❌ No dedicated tests

**Status:** 🔄 IN DEVELOPMENT

---

### 9. 📚 BOOK LIBRARY

#### Feature: Book Research & Management
**Files:**
- `src/research/private_book_library.py` - Private library
- `src/research/book_library_operations.py` - Library operations
- `src/research/book_models.py` - Book data models
- `src/research/book_content_analyzer.py` - Book content analysis

**Tests:**
- ❌ No dedicated tests

**Database:**
- `data/books/` - Book storage

**Status:** 🔄 IN DEVELOPMENT

---

### 10. 💾 DATABASE & STORAGE

#### Feature: Database Management
**Files:**
- `src/services/new_database_manager.py` - Main DB manager
- `src/services/database_operations.py` - DB operations
- `src/services/database_queries.py` - Query helpers
- `src/services/database_analysis.py` - DB analysis
- `src/storage/db.py` - Database abstraction
- `src/storage/sqlite_adapter.py` - SQLite adapter
- `src/storage/supabase_adapter.py` - Supabase adapter
- `src/supabase_manager.py` - Supabase manager
- `src/scrape_state_database.py` - Scrape state tracking
- `src/scrape_state_manager.py` - Scrape state manager

**Tests:**
- `tests/test_supabase_insert.py` - Supabase tests
- `tests/test_duplicate_handling.py` - Duplicate detection

**Database Files:**
- `beyondlines.db` - SQLite database (708 KB)
- `backups/beyondlines_20241009.db` - Backup

**Tables:**
- `posts` - All collected posts
- `discoveries` - RSS/Reddit/GitHub discoveries
- `telegram_messages` - Telegram messages
- `scrape_state` - Scraping progress tracking
- `user_preferences` - User preferences

**Status:** ✅ WORKING

---

#### Feature: Supabase Sync
**Files:**
- `src/supabase_manager.py` - Supabase sync
- `src/services/supabase/post_inserter.py` - Post insertion
- `migrations/*.sql` - Database migrations

**Tests:**
- `tests/test_supabase_insert.py`

**Supabase Tables:**
- `posts` - Synced posts
- `discoveries` - Synced discoveries
- `telegram_messages` - Synced messages

**Status:** ✅ WORKING

---

### 11. 🎛️ COLLECTION ORCHESTRATION

#### Feature: Collection Service
**Files:**
- `src/services/collection_service.py` - Main collection service
- `src/services/collector_runner.py` - Collector runner
- `src/services/collection/collection_orchestrator.py` - Orchestration
- `src/services/collection/platform_collectors.py` - Platform-specific collectors
- `src/pipeline/orchestrator.py` - Pipeline orchestrator

**Tests:**
- `tests/test_collection.py` - Collection tests
- `tests/test_collection_only.py` - Collection-only tests
- `tests/test_collectors.py` - Collector tests
- `tests/test_orchestrator.py` - Orchestrator tests

**How it Works:**
1. Orchestrator manages collection pipeline
2. Platform collectors fetch content
3. Deduplication check
4. Analysis (if enabled)
5. Store in database
6. Sync to Supabase

**Status:** ✅ WORKING

---

#### Feature: Universal Collector
**Files:**
- `src/core/collection/universal_collector.py` - Universal collector

**Tests:**
- Covered by `tests/test_collectors.py`

**Status:** ✅ WORKING

---

### 12. ⚙️ CORE UTILITIES

#### Feature: Configuration Management
**Files:**
- `src/utils/config.py` - Configuration loader
- `config/collection.json` - Collection settings
- `config/content_sources.json` - Content sources
- `config/telegram_channels.txt` - Telegram channels

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

#### Feature: Logging
**Files:**
- `src/utils/logging.py` - Logging configuration
- `logs/` - Log files

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

#### Feature: Duplicate Detection
**Files:**
- `src/utils/duplicate_detector.py` - Duplicate detection

**Tests:**
- `tests/test_duplicate_handling.py`

**Status:** ✅ WORKING

---

#### Feature: GitHub Metadata
**Files:**
- `src/utils/github_metadata.py` - GitHub metadata extraction

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

### 13. 🔒 RATE LIMITING

#### Feature: Intelligent Rate Limiting
**Files:**
- `src/core/rate_limiting/intelligent_limiter.py` - Main limiter
- `src/core/rate_limiting/domain_limiter.py` - Per-domain limiting
- `src/core/rate_limiting/rate_limit_config.py` - Configuration

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_rate_limiting.py`

**Status:** ✅ WORKING

---

### 14. ✅ CONTENT VALIDATION

#### Feature: Content Quality Validation
**Files:**
- `src/core/validation/content_validator.py` - Content validator
- `src/core/validation/content_quality_metrics.py` - Quality metrics

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

### 15. 🔄 NORMALIZATION

#### Feature: Content Normalization
**Files:**
- `src/core/normalization/markitdown_normalizer.py` - Markdown normalization

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

### 16. 🔢 VECTOR INDEXING

#### Feature: Vector Database & Embeddings
**Files:**
- `src/core/indexing/vector_db_manager.py` - Vector DB management
- `src/core/indexing/embedding_service.py` - Embedding generation
- `src/core/indexing/indexer_agent.py` - Indexing agent

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_vector_indexing.py`

**Status:** 🔄 PARTIAL (needs pgvector setup)

---

### 17. 📊 SERVICES & AUTOMATION

#### Feature: Digest Generation
**Files:**
- `src/services/digest_generator.py` - Daily digest creation

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

#### Feature: AI Summarization
**Files:**
- `src/services/ai_summarizer.py` - AI summarization service

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

#### Feature: Health Monitoring
**Files:**
- `src/services/health_monitor.py` - System health monitoring

**Tests:**
- ❌ No dedicated tests

**Dependencies:** Requires `psutil`

**Status:** ✅ WORKING

---

#### Feature: Intelligence Automation
**Files:**
- `src/services/intelligence_automation.py` - Automated intelligence tasks

**Tests:**
- ❌ No dedicated tests

**Status:** ✅ WORKING

---

#### Feature: Content Posting
**Files:**
- `src/services/posting_service.py` - Automated posting

**Tests:**
- ❌ No dedicated tests

**Status:** 🔄 IN DEVELOPMENT

---

#### Feature: Webhook Support
**Files:**
- `src/services/supabase_webhook.py` - Supabase webhooks

**Tests:**
- ❌ No dedicated tests

**Status:** 🔄 IN DEVELOPMENT

---

### 18. 🌐 API

#### Feature: REST API
**Files:**
- `src/api/main.py` - FastAPI application

**Tests:**
- ❌ No dedicated tests
- Could add: `tests/test_api.py`

**Endpoints:**
- TBD (needs implementation)

**Status:** 🔄 IN DEVELOPMENT

---

## 🧪 Test Suite Summary

### Existing Tests (18 files)
1. ✅ `test_ai_analyzer.py` - AI analysis tests
2. ✅ `test_ai_fix.py` - AI fix tests
3. ✅ `test_all_components.py` - Integration tests
4. ✅ `test_analysis_only.py` - Analysis-only tests
5. ✅ `test_collection.py` - Collection tests
6. ✅ `test_collection_only.py` - Collection-only tests
7. ✅ `test_collectors.py` - Collector tests
8. ✅ `test_duplicate_handling.py` - Duplicate detection
9. ✅ `test_fixes.py` - Fix tests
10. ✅ `test_last_post_tracking.py` - Last post tracking
11. ✅ `test_orchestrator.py` - Orchestrator tests
12. ✅ `test_post_analyzer.py` - Post analyzer tests
13. ✅ `test_reddit_collector.py` - Reddit tests
14. ✅ `test_simple_collection.py` - Simple collection
15. ✅ `test_stop_at_last_post.py` - Stop logic tests
16. ✅ `test_supabase_insert.py` - Supabase tests
17. ✅ `test_threads_collector.py` - Threads tests
18. ✅ `test_twitter_collector.py` - Twitter tests

**Test Status:** 21/23 passing (91%)

### Missing Tests (Need to Add)
1. ❌ `test_web_components.py` - Web UI tests
2. ❌ `test_telegram_bot.py` - Bot tests
3. ❌ `test_discoveries_ui.py` - Discoveries tab
4. ❌ `test_active_discovery.py` - Active discovery
5. ❌ `test_thread_summarizer.py` - Summarization
6. ❌ `test_media_analyzer.py` - Media analysis
7. ❌ `test_intelligent_curator.py` - Curation
8. ❌ `test_semantic_search.py` - Search
9. ❌ `test_research_agents.py` - AI agents
10. ❌ `test_rate_limiting.py` - Rate limits
11. ❌ `test_vector_indexing.py` - Embeddings
12. ❌ `test_api.py` - API endpoints

---

## 🚀 Quick Reference - How to Run Things

### Start Web UI
```bash
svelte run src/web/app.py
# Or
./start_web.sh
```

### Start Telegram Bot
```bash
./run_telegram_bot.sh
# Or
python src/services/telegram_bot.py
```

### Run Full Collection
```bash
python run_full_collection.py
```

### Run Tests
```bash
# All tests
pytest tests/ -v

# Specific feature
pytest tests/test_twitter_collector.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Run Main CLI
```bash
python main.py web          # Launch web UI
python main.py --version    # Show version
python main.py --help       # Show help
```

---

## 📊 Feature Status Matrix

| Feature | Files | Tests | Status | Priority |
|---------|-------|-------|--------|----------|
| Web Dashboard | ✅ | ❌ | ✅ Working | High |
| Twitter Collector | ✅ | ✅ | ✅ Working | High |
| Reddit Collector | ✅ | ✅ | ✅ Working | High |
| **Threads Collector** | ✅ | ✅ | ⚠️ **Needs Fix** | **High** |
| Telegram Bot | ✅ | ❌ | ✅ Working | High |
| RSS Discovery | ✅ | ✅ | ✅ Working | High |
| AI Analysis | ✅ | ✅ | ✅ Working | High |
| Value Scoring | ✅ | ✅ | ✅ Working | High |
| Database Sync | ✅ | ✅ | ✅ Working | High |
| Semantic Search | ✅ | ❌ | 🔄 Partial | Medium |
| Vector Indexing | ✅ | ❌ | 🔄 Partial | Medium |
| Research Agents | ✅ | ❌ | 🔄 Partial | Medium |
| Book Library | ✅ | ❌ | 🔄 Partial | Low |
| API | ✅ | ❌ | 🔄 Partial | Low |

---

## 🎯 Immediate Priorities

### 1. Fix Threads Collector (HIGH PRIORITY)
**Files to Check:**
- `src/core/extraction/threads_extractor.py` (923 lines)
- `cookies/threads_cookies.json`

**Issues:**
- Cookie authentication may be stale
- HTML structure changes need updating
- Selector updates required

**Test File:**
- `tests/test_threads_collector.py`

---

### 2. Add Missing Critical Tests
**Priority Tests:**
1. Web UI component tests
2. Telegram bot tests
3. Semantic search tests
4. Vector indexing tests

---

### 3. Complete Smart Discovery Features
**Per roadmap in SMART_DISCOVERY_ROADMAP.md:**
1. Concept extraction
2. Similarity search
3. LLM-guided discovery

---

## 📝 Notes

### Database Schema
**SQLite (beyondlines.db):**
- `posts` - All social media posts
- `discoveries` - RSS/Reddit/GitHub discoveries
- `telegram_messages` - Telegram messages
- `scrape_state` - Scraping progress
- `user_preferences` - User settings

**Supabase:**
- Mirrors SQLite tables
- Provides cloud backup
- Enables web access

### Dependencies
**Core:**
- svelte - Web UI
- playwright - Browser automation
- supabase - Cloud database
- praw - Reddit API
- python-telegram-bot - Telegram bot

**AI:**
- openai - GPT-4
- anthropic - Claude
- google-generativeai - Gemini

**See:** `requirements.txt` for full list

---

**Last Updated:** October 14, 2024
**Status:** Complete and verified ✅
