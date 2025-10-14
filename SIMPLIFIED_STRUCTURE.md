# PrisMind Simplified Project Structure

This document outlines the proposed simplified structure for the PrisMind project after cleaning.

## Root Directory

```
prismind/
├── config/
│   ├── collection.json
│   └── content_sources.json
├── src/
│   ├── core/
│   │   ├── extraction/
│   │   │   ├── article_extractor.py
│   │   │   └── multi_topic_sources.py
│   │   ├── analysis/
│   │   │   ├── intelligent_content_analyzer.py
│   │   │   └── value_scorer.py
│   │   └── discovery/
│   │       └── discovery_engine.py
│   ├── services/
│   │   ├── autonomous_discovery.py
│   │   ├── new_database_manager.py
│   │   ├── collection_service.py
│   │   └── telegram_bot.py
│   ├── web/
│   │   ├── components/
│   │   │   ├── sidebar.py
│   │   │   └── tabs.py
│   │   └── app.py
│   └── supabase_manager.py
├── scripts/
│   ├── run_collector.py
│   └── dashboard.py
├── tests/
├── main.py
├── run_full_collection.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## Key Components

### 1. Content Collection (`src/core/extraction/`)
- `multi_topic_sources.py` - All content sources organized by category
- `article_extractor.py` - RSS feed processing and extraction

### 2. Content Analysis (`src/core/analysis/`)
- `intelligent_content_analyzer.py` - Main content analysis engine
- `value_scorer.py` - Content scoring and quality assessment

### 3. Discovery (`src/core/discovery/`)
- `discovery_engine.py` - Main discovery logic that finds relevant content

### 4. Services (`src/services/`)
- `autonomous_discovery.py` - Scheduled discovery and collection
- `new_database_manager.py` - Database operations abstraction
- `collection_service.py` - Content collection coordination
- `telegram_bot.py` - Telegram bot implementation

### 5. Web Interface (`src/web/`)
- `app.py` - Main Streamlit application
- `components/` - UI components for different tabs and features

### 6. Configuration and Environment
- `config/` - Configuration files
- `.env.example` - Example environment variables
- `requirements.txt` - Python dependencies

### 7. Documentation (Essential Only)
- `README.md` - Main project documentation
- `FUNCTIONALITY.md` - Core functionality documentation
- `CLEANING_PLAN.md` - This cleaning plan
- `SIMPLIFIED_STRUCTURE.md` - This document
- `RULES.md` - Development rules and guidelines

## Removed Components

### Eliminated Redundancy
- Multiple discovery engines consolidated into one
- Multiple analysis modules consolidated into one
- Multiple extraction modules consolidated into one
- Duplicate scripts removed

### Removed Unused Files
- Empty or stub files in services
- Archive directories
- Historical documentation files
- Cache and temporary files
- Redundant configuration files

## Benefits of Simplification

1. **Clear Structure**: Easy to understand project organization
2. **Single Responsibility**: Each module has a clear, specific purpose
3. **Reduced Maintenance**: Fewer files to maintain and update
4. **Improved Onboarding**: New developers can quickly understand the codebase
5. **Better Focus**: Concentration on working features rather than experimental ones