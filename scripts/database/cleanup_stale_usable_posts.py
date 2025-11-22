#!/usr/bin/env python3
"""
Cleanup Stale Time-Sensitive Posts from usable_posts

Removes posts that are past their relevance window:
- same-day: > 24 hours old
- 24-72h: > 72 hours old
- this-week: > 168 hours (7 days) old
- evergreen: KEEP (always valid)

This ensures usable_posts only contains:
- Evergreen content (always valid)
- Currently time-sensitive content (still within relevance window)
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.database.manager import SupabaseManager

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def cleanup_stale_posts(dry_run: bool = True) -> dict:
    """
    Remove stale time-sensitive posts from usable_posts.

    Args:
        dry_run: If True, only report what would be deleted

    Returns:
        Dict with cleanup statistics
    """
    supabase = SupabaseManager().client

    # Get all time-sensitive posts
    response = (
        supabase.table("usable_posts")
        .select("id, post_id, relevance_window, time_sensitive, created_at")
        .eq("time_sensitive", True)
        .execute()
    )

    time_sensitive_posts = response.data
    logger.info(f"📊 Found {len(time_sensitive_posts)} time-sensitive posts")

    now = datetime.now(timezone.utc)
    stale_posts = []
    valid_posts = []

    for post in time_sensitive_posts:
        created_at_str = post.get("created_at")
        if not created_at_str:
            # No created_at - can't determine age, keep it
            valid_posts.append(post)
            continue

        try:
            if isinstance(created_at_str, str):
                created_at = datetime.fromisoformat(
                    created_at_str.replace("Z", "+00:00")
                )
            else:
                created_at = created_at_str

            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            age_hours = (now - created_at).total_seconds() / 3600.0
            relevance_window = post.get("relevance_window", "")

            # Check if stale based on relevance window
            is_stale = False
            if relevance_window == "same-day" and age_hours > 24:
                is_stale = True
            elif relevance_window == "24-72h" and age_hours > 72:
                is_stale = True
            elif relevance_window == "this-week" and age_hours > 168:  # 7 days
                is_stale = True

            if is_stale:
                stale_posts.append(
                    {
                        "id": post["id"],
                        "post_id": post.get("post_id"),
                        "relevance_window": relevance_window,
                        "age_hours": round(age_hours, 1),
                        "created_at": created_at_str,
                    }
                )
            else:
                valid_posts.append(post)

        except Exception as e:
            logger.warning(f"⚠️  Error processing post {post.get('post_id')}: {e}")
            # On error, keep the post (safer)
            valid_posts.append(post)

    logger.info(f"\n📊 Cleanup Analysis:")
    logger.info(f"   ✅ Valid time-sensitive: {len(valid_posts)}")
    logger.info(f"   🗑️  Stale (to remove): {len(stale_posts)}")

    if stale_posts:
        logger.info(f"\n🗑️  Stale Posts (oldest first):")
        for stale in sorted(stale_posts, key=lambda x: x["age_hours"], reverse=True)[
            :10
        ]:
            logger.info(
                f"   - {stale['post_id']}: {stale['relevance_window']} ({stale['age_hours']:.1f}h old)"
            )

    if not dry_run and stale_posts:
        # Delete stale posts
        deleted_count = 0
        for stale in stale_posts:
            try:
                supabase.table("usable_posts").delete().eq("id", stale["id"]).execute()
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to delete post {stale['post_id']}: {e}")

        logger.info(f"\n✅ Cleanup Complete: Removed {deleted_count} stale posts")
    elif dry_run:
        logger.info(f"\n🔍 DRY RUN: Would remove {len(stale_posts)} stale posts")
        logger.info(f"   Run with --execute to actually delete")

    return {
        "total_time_sensitive": len(time_sensitive_posts),
        "valid": len(valid_posts),
        "stale": len(stale_posts),
        "deleted": 0 if dry_run else len(stale_posts),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Cleanup stale time-sensitive posts from usable_posts"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete stale posts (default: dry run)",
    )
    args = parser.parse_args()

    result = cleanup_stale_posts(dry_run=not args.execute)

    if args.execute:
        print(f"\n✅ Cleanup complete: {result['deleted']} stale posts removed")
    else:
        print(f"\n🔍 Dry run: {result['stale']} stale posts would be removed")
        print(f"   Run with --execute to actually delete")
