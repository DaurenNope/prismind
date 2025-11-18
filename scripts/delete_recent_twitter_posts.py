#!/usr/bin/env python3
"""
Delete recently collected Twitter posts (last 10 minutes)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import datetime, timezone

from dateutil.parser import parse

from src.storage.db import get_storage


def delete_recent_posts():
    storage = get_storage()
    all_posts = storage.get_posts(limit=2000)
    twitter_posts = [p for p in all_posts if p.get("platform") == "twitter"]

    # Get posts from the last 10 minutes
    now = datetime.now(timezone.utc)
    recent_posts = []
    for post in twitter_posts:
        collected_at = post.get("collected_at")
        if collected_at:
            try:
                if isinstance(collected_at, str):
                    collected_dt = parse(collected_at)
                else:
                    collected_dt = collected_at
                if (
                    now - collected_dt.replace(tzinfo=timezone.utc)
                ).total_seconds() < 600:
                    recent_posts.append(post)
            except:
                pass

    print(f"Found {len(recent_posts)} posts collected in last 10 minutes")

    if not recent_posts:
        print("No posts to delete")
        return

    # Delete from Supabase
    if storage._supabase:
        deleted_count = 0
        for post in recent_posts:
            post_id = post.get("post_id")
            if post_id:
                try:
                    result = (
                        storage._supabase.client.table("posts")
                        .delete()
                        .eq("post_id", post_id)
                        .eq("platform", "twitter")
                        .execute()
                    )
                    if result.data:
                        deleted_count += 1
                        print(f"✅ Deleted: {post_id}")
                except Exception as e:
                    print(f"❌ Failed to delete {post_id}: {e}")

        print(f"\n✅ Deleted {deleted_count} posts from Supabase")

    # Delete from SQLite
    if storage._sqlite:
        deleted_count = 0
        for post in recent_posts:
            post_id = post.get("post_id")
            if post_id:
                try:
                    if storage._sqlite.delete_post(post_id):
                        deleted_count += 1
                except Exception as e:
                    print(f"❌ Failed to delete {post_id} from SQLite: {e}")

        print(f"✅ Deleted {deleted_count} posts from SQLite")


if __name__ == "__main__":
    delete_recent_posts()
