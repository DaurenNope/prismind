#!/usr/bin/env python3
"""
Sync posts from SQLite to Supabase.
Bypasses the proxy initialization issue by using direct SQLite reads.
"""

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

# Unset proxy env vars before importing Supabase
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("THREADS_PROXY", None)

from dotenv import load_dotenv

load_dotenv()


def get_sqlite_posts(db_path: str = "beyondlines.db") -> List[Dict[str, Any]]:
    """Get all posts from SQLite"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM posts ORDER BY created_at DESC")
        rows = cursor.fetchall()
        posts = [dict(row) for row in rows]
        print(f"📥 Found {len(posts)} posts in SQLite")
        return posts
    finally:
        conn.close()


def sync_to_supabase(posts: List[Dict[str, Any]]):
    """Sync posts to Supabase"""
    try:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            print("❌ Missing Supabase credentials")
            return

        print("🔌 Connecting to Supabase...")
        client = create_client(url, key)

        print(f"📤 Syncing {len(posts)} posts to Supabase...")
        synced = 0
        failed = 0

        for post in posts:
            try:
                # Convert to Supabase format
                supabase_post = {
                    "post_id": post.get("post_id"),
                    "title": post.get("title"),
                    "content": post.get("content"),
                    "url": post.get("url"),
                    "platform": post.get("platform"),
                    "author": post.get("author"),
                    "author_handle": post.get("author_handle"),
                    "created_at": post.get("created_at"),
                    "ai_summary": post.get("ai_summary"),
                    "topic": post.get("topic"),
                    "content_type": post.get("content_type"),
                    "post_type": post.get("post_type"),
                    "media_urls": json.loads(post.get("media_urls"))
                    if post.get("media_urls")
                    else None,
                    "hashtags": json.loads(post.get("hashtags"))
                    if post.get("hashtags")
                    else None,
                    "mentions": json.loads(post.get("mentions"))
                    if post.get("mentions")
                    else None,
                    "is_saved": post.get("is_saved"),
                    "analyzed_at": post.get("analyzed_at"),
                    "sentiment": post.get("sentiment"),
                    "key_concepts": post.get("key_concepts"),
                    "analysis_model": post.get("analysis_model"),
                    "value_score": post.get("value_score"),
                    "quality_score": post.get("quality_score"),
                    "language": post.get("language"),
                }

                # Remove None values
                supabase_post = {
                    k: v for k, v in supabase_post.items() if v is not None
                }

                # Upsert to Supabase
                result = (
                    client.table("posts")
                    .upsert(supabase_post, on_conflict="url")
                    .execute()
                )

                if result.data:
                    synced += 1
                    if synced % 10 == 0:
                        print(f"   ✅ Synced {synced}/{len(posts)} posts...")
                else:
                    failed += 1

            except Exception as e:
                failed += 1
                print(f"   ⚠️ Failed to sync post {post.get('post_id')}: {e}")

        print(f"\n✅ Sync complete: {synced} synced, {failed} failed")

    except Exception as e:
        print(f"❌ Supabase sync failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("🔄 Syncing SQLite posts to Supabase...")
    posts = get_sqlite_posts()
    if posts:
        sync_to_supabase(posts)
    else:
        print("⚠️ No posts found in SQLite")
