# PrisMind Cleaning Plan

This document outlines files and directories that should be removed to simplify the PrisMind project and make it more maintainable.

## Files/Directories to Remove

### 1. Archive Directories
These directories contain outdated files that are no longer relevant to the current project:

- `scripts/archive/` - Old scripts that are likely outdated
- `docs/archive/` - Old documentation files

### 2. Redundant Scripts
Scripts that duplicate functionality or are no longer needed:

- `scripts/automated_collector.py` - Redundant with other collection scripts
- `scripts/github_trending_scraper.py` - Duplicated functionality
- `scripts/scheduled_github_trending_job.py` - Very small file, likely not functional
- `scripts/rules_enforcement/` - Rules enforcement scripts that may not be needed

### 3. Historical Documentation
Documentation files that are no longer relevant:

- `CIRCULAR_IMPORT_FIX.md` - Historical fix documentation
- `FIXES_APPLIED.md` - Historical documentation
- `FIX_SUMMARY.md` - Historical documentation
- `README_FIXES.md` - Historical documentation
- `SIMPLE_FIX.md` - Historical documentation
- `START_HERE.md` - Redundant with other docs
- `START_INSTRUCTIONS.md` - Redundant with other docs
- `STATUS_REPORT.txt` - Outdated status report

### 4. Configuration/Cache Files
Temporary or cache files that can be regenerated:

- `.pytest_cache/` - Test cache files
- `.ruff_cache/` - Linting cache files
- `.env.temp` - Temporary environment file
- `requirements-api.txt` - Empty requirements file
- `start_bot.sh` - Empty shell script

### 5. Stub/Empty Service Components
Nearly empty files in the services directory that don't provide functionality:

- `src/services/analyzer.py` - Nearly empty
- `src/services/notifier.py` - Nearly empty
- `src/services/preferences.py` - Nearly empty
- `src/services/scheduler.py` - Nearly empty

### 6. Redundant Core Components
Multiple similar components that create confusion:

In `src/core/discovery/`:
- Multiple discovery engines that likely duplicate functionality

In `src/core/analysis/`:
- Multiple analysis modules that may overlap

In `src/core/extraction/`:
- Multiple extraction modules that may overlap

## Files to Keep (Essential Components)

### Core Functionality
1. Content collection from RSS feeds and social media
2. Content analysis and categorization
3. Database storage and retrieval
4. Web interface (Streamlit)
5. Telegram bot interface

### Essential Files
- `main.py` - Main entry point
- `run_full_collection.py` - Main collection pipeline
- `src/web/` - Web interface components
- `src/services/telegram_bot.py` - Telegram bot implementation
- `src/services/new_database_manager.py` - Database operations
- `src/core/extraction/multi_topic_sources.py` - Content sources
- `src/core/extraction/article_extractor.py` - RSS processing
- Documentation files:
  - `README.md` - Main documentation
  - `FUNCTIONALITY.md` - Core functionality documentation
  - `RULES.md` - Development rules
  - `QUICK_START.md` - Quick start guide
  - `TELEGRAM_PLAN.md` - Telegram bot plan

## Implementation Steps

1. First, backup the entire project
2. Remove archive directories
3. Remove redundant scripts
4. Remove historical documentation
5. Remove configuration/cache files
6. Remove stub/empty service components
7. Review and consolidate core components
8. Test that core functionality still works
9. Update documentation to reflect changes

## Benefits of Cleaning

1. **Reduced Complexity**: Fewer files to navigate and maintain
2. **Improved Maintainability**: Clearer structure with less redundancy
3. **Easier Onboarding**: New developers can understand the project more quickly
4. **Faster Builds**: Fewer files to process during builds and deployments
5. **Clearer Focus**: Concentration on core functionality that actually works