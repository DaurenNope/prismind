# Script Usage Audit Report

## Methodology
1. Checked codebase references
2. Checked documentation mentions
3. Analyzed script purposes from headers
4. Identified one-time vs reusable scripts

## Findings

### REPEATABLE/REUSABLE (Keep Active)
These scripts are used regularly or on-demand:

**Collection (17 files):**
- `run_full_collection.py` - Main collection script
- `collect_then_analyze.py` - Collection + analysis workflow
- `collect_threads_only.py` - Threads collection
- `wait_and_collect.py` - Scheduled collection
- `verify_collectors.py` - Verify collection setup
- Others: Various collection utilities

**Analysis (12 files):**
- `reanalyze_posts.py` - Re-analyze existing posts
- `process_backlog_now.py` - Process backlog
- `production_content_pipeline.py` - Production pipeline
- Others: Analysis utilities

**Publishing (32 files):**
- `batch_rewrite_usable_posts.py` - Batch rewriting
- `publish_scheduled.py` - Publish scheduled posts
- `validate_usable_posts.py` - Validate posts
- Others: Publishing utilities

**Database (12 files):**
- `sync_sqlite_to_supabase.py` - Regular sync
- `retry_failed_syncs.py` - Retry failed operations
- `check_sync_status.py` - Check sync status
- Others: Database utilities

### ONE-TIME/SPECIFIC CASE (Archive/Remove)
These were for specific issues or one-time operations:

**Already Archived:**
- 8 fix scripts (fix_*.py)
- 5 backfill scripts (backfill_*.py)
- 7 old test scripts

**Potentially One-Time:**
- `check_collected_at_issue.py` - Specific issue check
- `recollect_truncated_tweets.py` - One-time fix for truncated tweets
- `check_twitter_limits.py` - Diagnostic for specific issue
- `review_and_publish_from_database.py` - One-time review workflow
- `normalize_supabase_data.py` - One-time normalization
- `apply_missing_migrations.py` - One-time migration

### TESTING/EXPERIMENTAL (Review)
- Test scripts in `testing/` - Some may be obsolete
- Experimental scripts - Review if still needed

## Recommendations

1. **Archive more one-time scripts** (6-10 additional scripts)
2. **Consolidate diagnostic scripts** - Many `check_*.py` could be one tool
3. **Review test scripts** - Remove obsolete tests
4. **Document actively used scripts** - Create README for each category

## Next Steps
- Review each script's last usage
- Archive confirmed one-time scripts
- Consolidate similar diagnostic scripts
