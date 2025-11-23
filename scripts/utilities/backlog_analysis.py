#!/usr/bin/env python3
"""
Backlog Analysis Script

Re-analyzes the latest 50-100 posts with the improved analyzer logic,
focusing on getting posts into usable_posts table.
"""

import asyncio
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.database.manager import SupabaseManager
from src.domain.analysis.services.post_analyzer import analyze_and_store_post
from src.services.new_database_manager import get_database_manager
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


async def get_posts_for_reanalysis(
    supabase_manager: SupabaseManager, limit: int = 100, focus_usable: bool = True
) -> List[Dict[str, Any]]:
    """
    Get posts that need re-analysis, prioritizing ones not in usable_posts.

    Args:
        supabase_manager: Supabase manager instance
        limit: Maximum number of posts to fetch
        focus_usable: If True, prioritize posts not in usable_posts

    Returns:
        List of post dictionaries
    """
    if not supabase_manager or not supabase_manager.client:
        logger.error("❌ Supabase manager not available")
        return []

    try:
        client = supabase_manager.client

        if focus_usable:
            # Get posts that are NOT in usable_posts
            # Query: Get posts from 'posts' table that don't have a matching entry in 'usable_posts'

            # First, get all post_ids that ARE in usable_posts
            existing_usable = (
                client.table("usable_posts").select("post_id,platform").execute()
            )
            existing_ids = {
                (row["post_id"], row["platform"]) for row in existing_usable.data
            }

            # Get latest posts from posts table
            all_posts = (
                client.table("posts")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit * 2)  # Get more to filter
                .execute()
            )

            # Filter to posts NOT in usable_posts
            posts_not_in_usable = [
                post
                for post in all_posts.data
                if (post.get("post_id"), post.get("platform")) not in existing_ids
            ]

            # Take up to limit
            posts = posts_not_in_usable[:limit]

            logger.info(
                f"📊 Found {len(posts)} posts not in usable_posts (from {len(all_posts.data)} total)"
            )
        else:
            # Just get latest posts (may include ones already in usable_posts)
            response = (
                client.table("posts")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            posts = response.data
            logger.info(f"📊 Found {len(posts)} latest posts")

        return posts

    except Exception as e:
        logger.error(f"❌ Error fetching posts: {e}", exc_info=True)
        return []


async def reanalyze_post(
    post: Dict[str, Any], db_manager, supabase_manager: Optional[SupabaseManager]
) -> Dict[str, Any]:
    """
    Re-analyze a single post with improved analyzer logic.

    Returns:
        Dict with 'success', 'post_id', 'error' keys
    """
    post_id = post.get("post_id", "unknown")
    platform = post.get("platform", "unknown")

    try:
        # Analyze with improved logic (will auto-curate to usable_posts if criteria met)
        await analyze_and_store_post(
            db_manager, post, supabase_manager=supabase_manager
        )

        logger.info(f"✅ Re-analyzed: {platform}/{post_id}")
        return {"success": True, "post_id": post_id, "platform": platform}

    except Exception as e:
        logger.error(f"❌ Failed to re-analyze {platform}/{post_id}: {e}", exc_info=True)
        return {
            "success": False,
            "post_id": post_id,
            "platform": platform,
            "error": str(e),
        }


async def main(limit: int = 100, focus_usable: bool = True):
    """Main function to re-analyze backlog posts"""

    logger.info("\n" + "=" * 70)
    logger.info("🔄 BACKLOG ANALYSIS - Re-analyzing with improved logic")
    logger.info("=" * 70)
    logger.info(f"   Limit: {limit} posts")
    logger.info(f"   Focus on usable_posts: {focus_usable}")
    logger.info("=" * 70 + "\n")

    # Initialize managers
    try:
        db_manager = get_database_manager()
        logger.info("✅ Database manager initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database manager: {e}")
        return

    try:
        supabase_manager = SupabaseManager()
        logger.info("✅ Supabase manager initialized")
    except Exception as e:
        logger.warning(f"⚠️ Supabase manager not available: {e}")
        supabase_manager = None

    # Get posts for re-analysis
    posts = await get_posts_for_reanalysis(
        supabase_manager, limit=limit, focus_usable=focus_usable
    )

    if not posts:
        logger.warning("⚠️ No posts found for re-analysis")
        return

    logger.info(f"\n📋 Processing {len(posts)} posts...\n")

    # Process posts
    results = {"total": len(posts), "success": 0, "failed": 0, "errors": []}

    for i, post in enumerate(posts, 1):
        post_id = post.get("post_id", "unknown")
        platform = post.get("platform", "unknown")

        logger.info(f"[{i}/{len(posts)}] Processing {platform}/{post_id}...")

        result = await reanalyze_post(post, db_manager, supabase_manager)

        if result["success"]:
            results["success"] += 1
        else:
            results["failed"] += 1
            results["errors"].append(
                {
                    "post_id": post_id,
                    "platform": platform,
                    "error": result.get("error", "Unknown error"),
                }
            )

        # Small delay to avoid rate limiting
        if i < len(posts):
            await asyncio.sleep(0.5)

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 BACKLOG ANALYSIS SUMMARY")
    logger.info("=" * 70)
    logger.info(f"   Total processed: {results['total']}")
    logger.info(f"   ✅ Successful: {results['success']}")
    logger.info(f"   ❌ Failed: {results['failed']}")

    if results["errors"]:
        logger.info("\n   Errors encountered:")
        for err in results["errors"][:10]:  # Show first 10 errors
            logger.info(
                f"      - {err['platform']}/{err['post_id']}: {err['error'][:100]}"
            )
        if len(results["errors"]) > 10:
            logger.info(f"      ... and {len(results['errors']) - 10} more errors")

    logger.info("=" * 70 + "\n")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Re-analyze backlog posts with improved logic"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of posts to analyze (default: 100)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all posts (not just ones not in usable_posts)",
    )

    args = parser.parse_args()

    # Run async main
    asyncio.run(main(limit=args.limit, focus_usable=not args.all))




