#!/usr/bin/env python3
"""
Collection orchestrator for coordinating multi-platform collection
"""

import asyncio
from typing import Set
from datetime import datetime

# Core imports
from src.supabase_manager import SupabaseManager
from src.services.new_database_manager import get_database_manager
from src.scrape_state_manager import state_manager

# Platform collectors
from src.services.collection.platform_collectors import (
    collect_twitter_bookmarks,
    collect_reddit_bookmarks,
    collect_threads_bookmarks,
    log,
)


async def run_full_collection(progress_callback=None):
    """
    Main collection function that orchestrates collection from all platforms

    Args:
        progress_callback: Optional async function(platform, message, counts) to report progress

    Returns:
        dict: Collection results summary
    """
    log("Starting MULTI-PLATFORM bookmark collection...")
    print("=" * 60)

    async def report(platform: str, message: str):
        """Report progress if callback provided"""
        if progress_callback:
            try:
                await progress_callback(platform, message, collection_results)
            except Exception as e:
                print(f"Progress callback error: {e}")

    # Initialize database manager
    db_manager = get_database_manager()

    # Initialize Supabase manager if credentials are available
    supabase_manager = None
    try:
        supabase_manager = SupabaseManager()
        log("Supabase manager initialized successfully", "success")
    except Exception as e:
        log(f"Could not initialize Supabase manager: {e}", "warning")
        log("Continuing with local storage only", "info")

    # Get existing post IDs to avoid duplicates
    existing_posts = db_manager.get_all_posts(include_deleted=False)
    existing_ids = set()
    existing_urls = set()
    
    for post in existing_posts:
        if 'post_id' in post and post['post_id']:
            existing_ids.add(str(post['post_id']))
        if 'url' in post and post['url']:
            existing_urls.add(str(post['url']))

    log(f"Database contains {len(existing_ids)} existing posts")
    log(f"Found {len(existing_urls)} unique URLs")

    collection_results = {
        "twitter": 0,
        "reddit": 0,
        "threads": 0,
        "total": 0,
        "errors": [],
    }

    # Collect from all platforms
    try:
        # Twitter
        log("Running Twitter collection...")
        await report("twitter", "Authenticating with Twitter...")
        try:
            twitter_count = await collect_twitter_bookmarks(
                db_manager=db_manager, 
                existing_ids=existing_ids, 
                existing_urls=existing_urls,
                supabase_manager=supabase_manager
            )
            collection_results["twitter"] = twitter_count
            collection_results["total"] += twitter_count
            await report("twitter", f"Collected {twitter_count} tweets")
        except Exception as e:
            error_msg = f"Twitter collection error: {e}"
            log(error_msg, "error")
            collection_results["errors"].append(error_msg)
            await report("twitter", f"Error: {str(e)[:40]}")

        # Reddit
        log("Running Reddit collection...")
        await report("reddit", "Fetching Reddit saved posts...")
        try:
            reddit_count = await collect_reddit_bookmarks(
                db_manager=db_manager, 
                existing_ids=existing_ids, 
                existing_urls=existing_urls,
                supabase_manager=supabase_manager
            )
            reddit_count = reddit_count or 0  # Handle None return value
            collection_results["reddit"] = reddit_count
            collection_results["total"] += reddit_count
            await report("reddit", f"Collected {reddit_count} posts")
        except Exception as e:
            error_msg = f"Reddit collection error: {e}"
            log(error_msg, "error")
            collection_results["errors"].append(error_msg)
            await report("reddit", f"Error: {str(e)[:40]}")

        # Threads
        log("Running Threads collection...")
        await report("threads", "Connecting to Threads...")
        try:
            threads_count = await collect_threads_bookmarks(
                db_manager=db_manager, 
                existing_ids=existing_ids, 
                existing_urls=existing_urls,
                supabase_manager=supabase_manager
            )
            threads_count = threads_count or 0  # Handle None return value
            collection_results["threads"] = threads_count
            collection_results["total"] += threads_count
            await report("threads", f"Collected {threads_count} posts")
        except Exception as e:
            error_msg = f"Threads collection error: {e}"
            log(error_msg, "error")
            collection_results["errors"].append(error_msg)
            await report("threads", f"Error: {str(e)[:40]}")

    except KeyboardInterrupt:
        log("Collection interrupted by user", "warning")
        return collection_results

    # Summary
    print("\n" + "=" * 60)
    log("MULTI-PLATFORM collection completed!", "success")
    log(f"Total new bookmarks collected: {collection_results['total']}")

    # Show scraping stats
    stats = state_manager.get_scraping_stats()
    print("\n📈 SCRAPING STATISTICS:")
    log(f"Total posts tracked: {stats['total_posts']}")
    for platform_stat in stats["platform_stats"]:
        log(
            f"  {platform_stat['platform']}: {platform_stat['total_posts_scraped']} posts"
        )

    if collection_results["total"] > 0:
        log("Tip: Use the dashboard's AI enhancement to analyze new content", "info")

        # Run intelligence automation after collection
        try:
            log("🧠 Running intelligence automation pipeline...", "info")
            from src.services.intelligence_automation import get_intelligence_automation

            automation = get_intelligence_automation()
            intelligence_results = await automation.process_after_collection(
                collection_results
            )

            if not intelligence_results.get("skipped"):
                analyzed = intelligence_results.get("analysis", {}).get("analyzed", 0)
                researched = intelligence_results.get("research", {}).get(
                    "researched", 0
                )
                log(
                    f"✅ Intelligence: Analyzed {analyzed}, Researched {researched} topics",
                    "success",
                )
                collection_results["intelligence"] = intelligence_results
        except Exception as e:
            log(f"⚠️ Intelligence automation failed: {e}", "warning")
            collection_results["intelligence_error"] = str(e)
    else:
        log("No new bookmarks found - you're up to date!", "info")

    return collection_results
