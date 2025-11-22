# Script Directory Cleanup Plan

## Analysis Directory (12 files)

**Keep (Core Analysis):**
- analyze_unanalyzed_posts.py
- reanalyze_posts.py
- reanalyze_missing_metadata.py
- recategorize_posts.py
- fast_recategorize.py
- process_backlog_now.py
- production_content_pipeline.py

**Move/Archive:**
- analyze_collected_posts.py → utilities/ (diagnostic)
- backlog_analysis.py → utilities/ (one-time analysis)
- check_backfill_progress.py → archive/ (one-time)
- clean_supabase_safe.py → database/ (database operation)
- comprehensive_validation.py → database/ (validation)

## Publishing Directory (31 files)

**Keep (Core Publishing):**
- batch_rewrite_usable_posts.py
- publish_scheduled.py
- production_rewrite_and_schedule.py
- rewrite_from_supabase.py
- regenerate_fresh_rewrites.py
- regenerate_qronoya_examples.py
- curate_usable_posts.py
- recache_usable_posts.py

**Move to Database:**
- validate_all_posts.py
- validate_evergreen_posts.py
- validate_usable_posts.py
- cleanup_bad_posts.py
- cleanup_stale_usable_posts.py
- delete_posts.py
- delete_recent_twitter_posts.py
- remove_stray_twitter_posts.py
- mark_truncated_posts.py

**Move to Testing:**
- live_posting_test.py
- test_post_now.py
- test_threads_posting.py
- test_threads_posting_debug.py
- test_twitter_post.py
- test_usable_posts_workflow.py

**Move to Utilities:**
- check_existing_posts.py
- check_specific_twitter_posts.py
- check_supabase_posts.py
- query_twitter_posts_supabase.py
- show_recent_twitter_posts.py
- show_where_posts_are.py

**Archive (One-time):**
- post_actual_reply.py → archive/specific_cases/
- post_actual_reply_now.py → archive/specific_cases/

## Testing Directory (17 files)

**Keep (Active Tests):**
- e2e_quick_check.py
- verify_deployment_ready.py
- verify_truncation.py
- verify_show_more.py
- test_collection_simple.py
- test_threads_collection_5.py
- test_twitter_collection.py
- test_twitter_collector.py
- focused_collector_test.py
- simple_collector_test.py

**Archive (One-time/Experimental):**
- ACTUAL_threads_reply.py → archive/old_tests/
- actual_threads_reply_guy.py → archive/old_tests/
- automated_live_test.py → archive/old_tests/
- creative_testing_offline.py → archive/old_tests/
- demo_full_workflow.py → archive/old_tests/
- real_threads_reply_guy.py → archive/old_tests/
- simple_categorizer.py → archive/old_tests/ (if obsolete)

## Utilities Directory (30 files)

**Keep (Active Utilities):**
- manage_cookies.py (referenced in code)
- manage_profiles.py
- capture_threads_cookies.py
- capture_twitter_cookies.py
- convert_twitter_cookies.py
- import_twitter_cookies_from_curl.py
- generate_ai_summaries.py
- update_engagement_metrics.py
- update_voice_model.py
- precompute_persona_embeddings.py
- run_autonomous.py
- run_pipeline.py
- web_ui.py
- dashboard.py
- disable_automation.py

**Archive (One-time/Specific):**
- diagnose_project.py → archive/specific_cases/
- diagnose_twitter_auth.py → archive/specific_cases/
- diagnose_twitter_supabase.py → archive/specific_cases/
- debug_url_extraction.py → archive/specific_cases/
- database_behavior_explanation.py → archive/specific_cases/
- find_used_files.py → archive/specific_cases/
- identify_truncated_posts.py → archive/specific_cases/
- show_truncated_details.py → archive/specific_cases/
- purge_rag_examples.py → archive/specific_cases/
- threads_com_reply_guy.py → archive/specific_cases/
- threads_real_working.py → archive/specific_cases/
- real_world_test.py → archive/specific_cases/
- query_by_collected_date.py → archive/specific_cases/ (example script)
- verify_collectors.py → archive/specific_cases/ (if one-time)
- fetch_full_content_from_url.py → archive/specific_cases/ (if one-time)
