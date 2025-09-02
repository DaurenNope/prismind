# PrisMind Project Overview

## 🎯 Project Purpose

**PrisMind** is an intelligent personal knowledge management system that transforms social media bookmarks into structured, searchable intelligence. It extracts saved content from Twitter, Reddit, and Threads, analyzes it with AI, and organizes it into actionable insights through a modern dashboard interface.

## 🏗️ Core Architecture

### Main Application Flow
1. **Data Collection** → **AI Analysis** → **Database Storage** → **Dashboard Display**
2. **Multi-platform extraction** (Twitter, Reddit, Threads)
3. **AI-powered analysis** (Mistral, Gemini, local models)
4. **Interactive dashboard** (Streamlit)
5. **Database management** (SQLite + Supabase)

## 📁 File Structure Analysis

### 🚀 **ENTRY POINTS & LAUNCHERS**

#### **KEEP - Core Application Files**
- **`start.sh`** ✅ - Main startup script that launches dashboard on available port
- **`scripts/dashboard.py`** ✅ - **PRIMARY DASHBOARD** - Streamlit interface for data exploration
- **`collect_multi_platform.py`** ✅ - **MAIN DATA COLLECTION** - Orchestrates extraction from all platforms
- **`analyze_and_categorize_bookmarks.py`** ✅ - **MAIN ANALYSIS PIPELINE** - Processes collected data with AI

#### **CONSIDER FOR CLEANUP**
- **`run_all_tests.py`** ⚠️ - Test runner, keep but verify it runs all tests properly
- **`example_usage.py`** ⚠️ - Example code, consider moving to docs or removing if outdated

### 🧠 **CORE INTELLIGENCE MODULES**

#### **KEEP - Essential Analysis Components**
- **`core/analysis/intelligent_content_analyzer.py`** ✅ - **BRAIN OF THE SYSTEM** - Main AI analysis orchestrator
- **`core/analysis/mistral_analyzer.py`** ✅ - Primary AI analysis using Mistral
- **`core/analysis/social_content_analyzer.py`** ✅ - Social media specific analysis
- **`core/analysis/value_scorer.py`** ✅ - Content value scoring algorithm
- **`core/analysis/thread_summarizer.py`** ✅ - Thread/conversation summarization
- **`core/analysis/comment_analyzer.py`** ✅ - Comment analysis for Reddit
- **`core/analysis/threads_analyzer.py`** ✅ - Threads platform specific analysis
- **`core/analysis/deep_research_analyzer.py`** ✅ - Deep research content analysis
- **`core/analysis/media_analyzer.py`** ✅ - Media content analysis
- **`core/analysis/local_media_analyzer.py`** ✅ - Local media analysis using OCR + Qwen3:8B
- **`core/analysis/shuttleai_analyzer.py`** ✅ - ShuttleAI fallback analyzer

#### **KEEP - Learning & Feedback Systems**
- **`core/learning/smart_organizer.py`** ✅ - Intelligent content organization
- **`core/learning/feedback_system.py`** ✅ - User feedback and learning system

### 🔗 **DATA EXTRACTION MODULES**

#### **KEEP - Platform Extractors**
- **`core/extraction/social_extractor_base.py`** ✅ - **BASE CLASS** - Defines standard post format
- **`core/extraction/twitter_extractor_playwright.py`** ✅ - **TWITTER EXTRACTOR** - Uses Playwright for Twitter
- **`core/extraction/reddit_extractor.py`** ✅ - **REDDIT EXTRACTOR** - Reddit API integration
- **`core/extraction/threads_extractor.py`** ✅ - **THREADS EXTRACTOR** - Threads platform extraction

### 🗄️ **DATABASE & DATA MANAGEMENT**

#### **KEEP - Database Management**
- **`scripts/database_manager.py`** ✅ - **UNIFIED DATABASE MANAGER** - Central database operations
- **`supabase_manager.py`** ✅ - Supabase cloud database integration
- **`multi_table_manager.py`** ✅ - Multi-table database operations

#### **CONSIDER FOR CLEANUP**
- **`create_all_tables.py`** ⚠️ - Table creation script, keep but verify it's still needed
- **`create_table.py`** ⚠️ - Generic table creator, might be redundant
- **`create_table_direct.py`** ⚠️ - Direct table creation, might be redundant
- **`create_table_supabase_client.py`** ⚠️ - Supabase table creation, might be redundant

### 🛠️ **UTILITY & CONFIGURATION**

#### **KEEP - Configuration & Setup**
- **`requirements.txt`** ✅ - Python dependencies
- **`pytest.ini`** ✅ - Test configuration
- **`config/`** ✅ - Configuration files directory
  - **`config/threads_cookies_qronoya.json`** ✅ - Threads authentication
  - **`config/twitter_cookies_cryptoniard.json`** ✅ - Twitter authentication

#### **KEEP - Documentation**
- **`README.md`** ✅ - Main project documentation
- **`START_GUIDE.md`** ✅ - Getting started guide
- **`SUPABASE_SETUP.md`** ✅ - Supabase setup instructions
- **`REDDIT_SETUP_GUIDE.md`** ✅ - Reddit API setup guide
- **`CLEANUP_README.md`** ✅ - Cleanup documentation
- **`CLEANUP_SUMMARY.md`** ✅ - Cleanup summary

#### **KEEP - Templates**
- **`templates/social_post_template.md`** ✅ - Post template for exports

### 🧪 **TESTING FRAMEWORK**

#### **KEEP - Test Suite**
- **`tests/`** ✅ - Complete test directory
  - **`tests/test_supabase_manager.py`** ✅ - Supabase manager tests
  - **`tests/test_threads_extractor.py`** ✅ - Threads extractor tests
  - **`tests/test_twitter_extractor.py`** ✅ - Twitter extractor tests
  - **`tests/test_threads_url.py`** ✅ - Threads URL tests
  - **`tests/test_supabase_integration.py`** ✅ - Supabase integration tests
  - **`tests/test_database_manager.py`** ✅ - Database manager tests
  - **`tests/test_social_content_analyzer.py`** ✅ - Social content analyzer tests
  - **`tests/test_value_scorer.py`** ✅ - Value scorer tests
  - **`tests/test_feedback_system.py`** ✅ - Feedback system tests
  - **`tests/conftest.py`** ✅ - Test configuration

### 📊 **DATA PROCESSING & ANALYSIS**

#### **KEEP - Data Processing**
- **`analyze_media.py`** ✅ - Media content analysis
- **`enhance_all_simple.py`** ✅ - Simple enhancement pipeline
- **`extract_reddit_comments.py`** ✅ - Reddit comment extraction
- **`rescrape_single_post.py`** ✅ - Single post re-scraping utility

#### **CONSIDER FOR CLEANUP**
- **`collect_bookmarks.py`** ⚠️ - Legacy bookmark collection, might be replaced by `collect_multi_platform.py`

### 🔧 **SETUP & CONFIGURATION SCRIPTS**

#### **KEEP - Setup Scripts**
- **`setup_auto_collection.py`** ✅ - Auto collection setup
- **`setup_twitter_config.py`** ✅ - Twitter configuration setup
- **`start_auto_collection.sh`** ✅ - Auto collection startup script

### 🗄️ **DATABASE SCHEMAS**

#### **KEEP - SQL Schemas**
- **`sql/create_programming_table.sql`** ✅ - Programming category table
- **`sql/create_research_table.sql`** ✅ - Research category table
- **`sql/create_copywriting_table.sql`** ✅ - Copywriting category table
- **`scripts/supabase_setup.sql`** ✅ - Supabase setup schema

### 🐛 **DEBUGGING & DEVELOPMENT**

#### **CONSIDER FOR CLEANUP**
- **`debug_dashboard_db.py`** ⚠️ - Debug script, keep for development but consider moving to dev tools
- **`debug_db.py`** ⚠️ - Debug script, keep for development but consider moving to dev tools
- **`check_db_schema.py`** ⚠️ - Schema checker, keep but consider moving to dev tools
- **`test_ai_analysis.py`** ⚠️ - AI analysis test, keep but consider moving to tests
- **`test_mcp_functionality.py`** ⚠️ - MCP test, keep but consider moving to tests
- **`test_table.py`** ⚠️ - Table test, keep but consider moving to tests

### 📁 **DATA DIRECTORIES**

#### **KEEP - Data Storage**
- **`data/`** ✅ - Local database and data files
- **`output/`** ✅ - Generated reports and processed data
- **`scripts/data/`** ✅ - Script-specific data
- **`playwright_user_data/`** ✅ - Playwright browser data

### 📋 **MISCELLANEOUS**

#### **CONSIDER FOR CLEANUP**
- **`update_curation_table.py`** ⚠️ - Table update script, verify if still needed
- **`supabase-mcp-config.json`** ⚠️ - MCP configuration, verify if still needed
- **`deprecated_backup.tar.gz`** ❌ - **DELETE** - Deprecated backup, should be removed
- **`run_all_tests.py`** ⚠️ - Test runner, verify it runs all tests properly

## 🔄 **APPLICATION WORKFLOW**

### 1. **Data Collection Phase**
```
collect_multi_platform.py
├── TwitterExtractorPlaywright (Twitter bookmarks)
├── RedditExtractor (Reddit saved posts)
└── ThreadsExtractor (Threads bookmarks)
```

### 2. **Analysis Phase**
```
analyze_and_categorize_bookmarks.py
├── IntelligentContentAnalyzer (Main AI analysis)
├── MistralAnalyzer (Primary AI)
├── SocialContentAnalyzer (Social-specific analysis)
├── ValueScorer (Content scoring)
└── LocalMediaAnalyzer (Media analysis)
```

### 3. **Storage Phase**
```
DatabaseManager
├── SQLite (Local storage)
└── SupabaseManager (Cloud storage)
```

### 4. **Display Phase**
```
scripts/dashboard.py
├── Feed view (Main dashboard)
├── Browse categories
├── Manual review
└── Advanced search
```

## 🎯 **CLEANUP RECOMMENDATIONS**

### **IMMEDIATE DELETIONS** ❌ ✅ **COMPLETED**
1. **`deprecated_backup.tar.gz`** ✅ - Removed deprecated backup
2. **`__pycache__/` directories** ✅ - Removed all Python cache directories
3. **`.pytest_cache/`** ✅ - Removed pytest cache

### **CONSIDER FOR REMOVAL** ⚠️ ✅ **COMPLETED**
1. **`collect_bookmarks.py`** ✅ - Removed (replaced by `collect_multi_platform.py`)
2. **`create_table*.py` files** ✅ - Removed redundant files (kept `create_all_tables.py`)
3. **Debug scripts** ✅ - Moved to `dev/` directory
4. **Test scripts in root** ✅ - Moved to `tests/` directory

### **KEEP BUT ORGANIZE** ✅ **COMPLETED**
1. **Move debug scripts** ✅ - Moved to `dev/` directory
2. **Move test scripts** ✅ - Moved to `tests/` directory
3. **Consolidate table creation** ✅ - Removed redundant files
4. **Update documentation** ✅ - Updated project overview
5. **Move example files** ✅ - Moved to `docs/` directory
6. **Move config files** ✅ - Moved to `config/` directory

## 🚀 **CORE FUNCTIONALITY SUMMARY**

### **Primary Features**
1. **Multi-platform bookmark extraction** (Twitter, Reddit, Threads)
2. **AI-powered content analysis** (Mistral, Gemini, local models)
3. **Intelligent categorization** and value scoring
4. **Interactive dashboard** for data exploration
5. **Media content analysis** (images, videos)
6. **Comment analysis** (Reddit threads)
7. **Export capabilities** (Obsidian, reports)

### **Key Components**
- **`collect_multi_platform.py`** - Data collection orchestrator
- **`analyze_and_categorize_bookmarks.py`** - Analysis pipeline
- **`scripts/dashboard.py`** - User interface
- **`core/analysis/intelligent_content_analyzer.py`** - AI analysis engine
- **`scripts/database_manager.py`** - Data persistence

### **Data Flow**
```
Social Media → Extractors → AI Analysis → Database → Dashboard
```

## 📊 **DEPENDENCIES & TECHNOLOGIES**

### **Core Technologies**
- **Python 3.10+** - Main programming language
- **Streamlit** - Dashboard interface
- **SQLite** - Local database
- **Supabase** - Cloud database
- **Playwright** - Web automation
- **Mistral AI** - Primary AI analysis
- **Google Gemini** - Secondary AI analysis
- **Ollama + Qwen3:8B** - Local media analysis

### **Key Libraries**
- **pandas** - Data manipulation
- **sqlite3** - Database operations
- **requests** - HTTP requests
- **python-dotenv** - Environment management
- **pytest** - Testing framework

## 🎯 **NEXT STEPS FOR CLEANUP**

1. **Remove deprecated files** (deprecated_backup.tar.gz, __pycache__)
2. **Consolidate table creation** scripts
3. **Move debug scripts** to dev directory
4. **Update documentation** to reflect current state
5. **Verify all tests** run properly
6. **Test complete workflow** from collection to dashboard
7. **Update README** with current file structure

This overview provides a comprehensive understanding of the PrisMind codebase and clear recommendations for cleanup and organization.
