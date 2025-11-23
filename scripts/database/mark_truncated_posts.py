#!/usr/bin/env python3
"""
Mark truncated posts in the database for later re-collection.

This script:
1. Finds all potentially truncated Twitter posts
2. Marks them in the database (adds a flag or updates a field)
3. Creates a list for re-collection
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.manager import SupabaseManager
from src.domain.analysis.services.post_analyzer import detect_content_truncation


def mark_truncated_posts(limit: int = 100):
    """Mark truncated posts in the database"""
    print("=" * 60)
    print("🔍 Marking Truncated Posts")
    print("=" * 60)

    sb = SupabaseManager()
    client = sb.client

    # Get Twitter posts
    print(f"\n📊 Checking latest {limit} Twitter posts...")
    response = (
        client.table("posts")
        .select("post_id, content, platform, url")
        .eq("platform", "twitter")
        .order("collected_at", desc=True)
        .limit(limit)
        .execute()
    )

    posts = response.data or []
    print(f"✅ Found {len(posts)} posts to check")

    truncated_posts = []
    for post in posts:
        content = post.get("content", "") or ""
        if detect_content_truncation(content):
            truncated_posts.append(post)

    print(f"\n⚠️ Found {len(truncated_posts)} truncated posts")

    if not truncated_posts:
        print("✅ No truncated posts found!")
        return

    # Show what we found
    print("\n📋 Truncated posts:")
    for i, post in enumerate(truncated_posts[:10], 1):
        content = post.get("content", "")[:60]
        print(f"  {i}. {post.get('post_id')}: {content}...")
    if len(truncated_posts) > 10:
        print(f"  ... and {len(truncated_posts) - 10} more")

    # Try to mark them in database (if we have a field for it)
    # For now, just print the list - we'll use this for re-collection
    print(f"\n✅ Found {len(truncated_posts)} posts to re-collect")
    print("\nTo re-collect these posts, run:")
    print(
        f"  python3 scripts/recollect_truncated_tweets.py --limit {len(truncated_posts)}"
    )

    return truncated_posts


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Mark truncated posts")
    parser.add_argument(
        "--limit", type=int, default=100, help="Number of posts to check (default: 100)"
    )

    args = parser.parse_args()
    mark_truncated_posts(limit=args.limit)
