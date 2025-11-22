# Script Usage Audit Report

## Investigation Results

### Scripts Referenced in Codebase
- `manage_cookies.py` - Referenced in twitter_extractor_playwright.py

### Scripts Mentioned in Documentation
- Various scripts mentioned but may not be actively used

### Analysis by Category

#### ONE-TIME/SPECIFIC CASE SCRIPTS (Archive These)

**Diagnostic Scripts (for specific issues):**
- `collection/check_collected_at_issue.py` - Debug specific collected_at filtering issue
- `database/check_twitter_limits.py` - Check Twitter API limits (diagnostic)
- `database/check_twitter_v2_limits.py` - Check Twitter v2 limits (diagnostic)
- `database/check_latest_threads_reddit.py` - Check latest posts (diagnostic)
- `database/check_recent_twitter_bookmarks.py` - Check bookmarks (diagnostic)

**One-Time Fix Scripts:**
- `collection/recollect_truncated_tweets.py` - One-time fix for truncated tweets
- `publishing/review_and_publish_from_database.py` - One-time review workflow
- `analysis/normalize_supabase_data.py` - One-time data normalization
- `database/apply_missing_migrations.py` - One-time migration (already identified)

**Total: 9 additional scripts to archive**

#### REPEATABLE/REUSABLE SCRIPTS (Keep Active)

**Collection (Core):**
- `run_full_collection.py` - Main collection
- `collect_then_analyze.py` - Collection workflow
- `collect_threads_only.py` - Threads collection
- `wait_and_collect.py` - Scheduled collection
- `verify_collectors.py` - Verify setup

**Analysis (Core):**
- `reanalyze_posts.py` - Re-analyze posts
- `process_backlog_now.py` - Process backlog
- `production_content_pipeline.py` - Production pipeline

**Publishing (Core):**
- `batch_rewrite_usable_posts.py` - Batch rewriting
- `publish_scheduled.py` - Publish scheduled
- `validate_usable_posts.py` - Validate posts

**Database (Core):**
- `sync_sqlite_to_supabase.py` - Regular sync
- `retry_failed_syncs.py` - Retry operations
- `check_sync_status.py` - Check sync

## Recommendations

1. **Archive 9 additional one-time scripts** → `archive/specific_cases/`
2. **Consolidate diagnostic scripts** - Create one diagnostic tool instead of many check_*.py
3. **Review remaining scripts** - Some may still be one-time use

## Impact

- Current: 112 active scripts
- After archiving: ~103 active scripts
- Reduction: ~8% more scripts archived
