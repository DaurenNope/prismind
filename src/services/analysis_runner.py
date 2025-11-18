"""Utility functions for running AI analysis workflows from the UI or CLI."""

import asyncio
from typing import Any, Dict, List, Optional

from src.services.analysis.post_analyzer import analyze_and_store_post, log
from src.services.analysis_lock import analysis_lock_guard
from src.services.new_database_manager import get_database_manager


async def _analyze_posts_async(
    posts: List[Dict[str, Any]], limit: int
) -> Dict[str, Any]:
    """Internal helper to analyze posts asynchronously."""
    db_manager = get_database_manager()

    # Get Supabase manager for cloud sync
    try:
        from src.database.manager import SupabaseManager

        supabase_manager = SupabaseManager()
    except Exception as e:
        logger.error(f"Error: {e}")
        log(f"Supabase manager not available: {e}", "warning")
        supabase_manager = None

    processed = 0
    errors: List[str] = []

    for post in posts[:limit]:
        try:
            await analyze_and_store_post(
                db_manager, post, supabase_manager=supabase_manager
            )
            processed += 1
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Error: {e}")
            log(f"Analysis failed for post {post.get('post_id')}: {exc}", "error")
            errors.append(str(exc))

    attempted = min(limit, len(posts))
    return {
        "processed": processed,
        "attempted": attempted,
        "errors": errors,
    }


def analyze_recent_posts(
    limit: int = 10, unanalyzed_only: bool = True, platform: Optional[str] = None
) -> Dict[str, Any]:
    """Run AI analysis on recent posts.

    Args:
        limit: Maximum number of posts to analyze.
        unanalyzed_only: If True, restrict to posts without prior analysis.

    Returns:
        Dictionary with counts of processed posts and any errors encountered.
    """

    db_manager = get_database_manager()
    platforms = [platform] if platform else None

    posts: List[Dict[str, Any]] = []
    if unanalyzed_only:
        try:
            posts = db_manager.get_unanalyzed_posts(limit=limit, platforms=platforms)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error(f"Error: {e}")
            log(f"Unable to fetch unanalyzed posts: {exc}", "warning")

    if not posts:
        posts = db_manager.get_posts(limit=limit, platforms=platforms)

    if not posts:
        return {
            "processed": 0,
            "attempted": 0,
            "errors": ["No posts available for analysis."],
        }

    with analysis_lock_guard() as locked:
        if not locked:
            return {
                "processed": 0,
                "attempted": 0,
                "errors": ["Analysis already in progress; skipping duplicate run."],
            }

        return asyncio.run(_analyze_posts_async(posts, limit))
