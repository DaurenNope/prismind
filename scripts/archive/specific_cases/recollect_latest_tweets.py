#!/usr/bin/env python3
"""
Re-collect latest Twitter posts to ensure they have full content (with "read more" expanded).

This script:
1. Finds the latest N Twitter posts from database
2. Re-collects them from Twitter bookmarks (with "read more" expansion)
3. Updates the database with full content
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.domain.collection.extractors.twitter import TwitterExtractorPlaywright
from src.infrastructure.database.manager import SupabaseManager


async def recollect_latest_tweets(limit: int = 50, dry_run: bool = False):
    """
    Re-collect latest Twitter posts to get full content.

    Args:
        limit: Number of latest posts to re-collect
        dry_run: If True, only show what would be updated (don't actually update)
    """
    print("=" * 60)
    print(f"🔄 Re-collecting Latest {limit} Twitter Posts")
    print("=" * 60)

    # Get Supabase client
    try:
        supabase_manager = SupabaseManager()
        supabase = supabase_manager.client
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return

    # Find latest Twitter posts
    print(f"\n📊 Finding latest {limit} Twitter posts...")
    try:
        response = (
            supabase.table("posts")
            .select("post_id, content, url, platform, collected_at")
            .eq("platform", "twitter")
            .order("collected_at", desc=True)
            .limit(limit)
            .execute()
        )

        latest_posts = response.data or []

        if not latest_posts:
            print("✅ No Twitter posts found")
            return

        print(f"✅ Found {len(latest_posts)} latest posts")

        # Show what we found
        print("\n📋 Latest posts to re-collect:")
        for i, post in enumerate(latest_posts[:10], 1):
            content = post.get("content", "")[:60]
            print(f"  {i}. {post.get('post_id')}: {content}...")
        if len(latest_posts) > 10:
            print(f"  ... and {len(latest_posts) - 10} more")

    except Exception as e:
        print(f"❌ Failed to query Supabase: {e}")
        return

    if dry_run:
        print("\n🔍 DRY RUN - Would re-collect these posts")
        print("   Run without --dry-run to actually update")
        return

    # Authenticate with Twitter
    print("\n🔐 Authenticating with Twitter...")
    twitter_username = os.getenv("TWITTER_USERNAME")
    twitter_password = os.getenv("TWITTER_PASSWORD")
    cookie_path_env = (
        os.getenv("TWITTER_COOKIE_FILE")
        or os.getenv("TWITTER_COOKIES_FILE")
        or os.getenv("TWITTER_COOKIES_PATH")
    )

    if not twitter_username:
        print("❌ TWITTER_USERNAME not set")
        return

    default_cookie_path = Path("cookies") / f"twitter_cookies_{twitter_username}.json"
    cookie_path = (
        Path(cookie_path_env).expanduser() if cookie_path_env else default_cookie_path
    )

    headless_mode = os.getenv("HEADLESS_MODE", "true").lower() in ("true", "1", "yes")

    extractor = TwitterExtractorPlaywright(
        username=twitter_username,
        password=twitter_password,
        headless=headless_mode,
        cookie_file=str(cookie_path) if cookie_path.exists() else None,
    )

    try:
        auth_success = await extractor.authenticate()
        if not auth_success:
            print("❌ Twitter authentication failed")
            return

        print("✅ Authenticated with Twitter")

        # Get fresh bookmarks (with "read more" expansion)
        print(
            f"\n📥 Fetching fresh bookmarks (with full content, limit: {limit * 2})..."
        )
        bookmarks = await extractor.get_saved_posts(
            limit=limit * 2
        )  # Get more to match

        if not bookmarks:
            print("⚠️ No bookmarks found")
            return

        print(f"✅ Found {len(bookmarks)} bookmarks")

        # Match latest posts with fresh bookmarks
        print("\n🔄 Updating posts...")
        updated_count = 0
        skipped_count = 0

        # Create lookup by numeric tweet ID (extract just the number)
        def extract_numeric_id(post_id_str: str) -> str:
            """Extract numeric ID from post_id (handles twitter_123456 format)"""
            if not post_id_str:
                return ""
            # Remove twitter_ prefix and any other non-numeric prefixes
            numeric = (
                post_id_str.replace("twitter_", "").replace("Twitter_", "").strip()
            )
            # Extract just the numeric part
            import re

            match = re.search(r"\d+", numeric)
            return match.group(0) if match else numeric

        bookmark_lookup = {}
        for bookmark in bookmarks:
            bookmark_id = str(bookmark.post_id or "")
            numeric_id = extract_numeric_id(bookmark_id)
            if numeric_id:
                bookmark_lookup[numeric_id] = bookmark
                # Also store with original format
                bookmark_lookup[bookmark_id] = bookmark

        print(f"   Created lookup for {len(bookmark_lookup)} bookmarks")

        for post in latest_posts:
            post_id = str(post.get("post_id", ""))
            numeric_id = extract_numeric_id(post_id)

            # Find matching bookmark by numeric ID
            bookmark = None
            if numeric_id and numeric_id in bookmark_lookup:
                bookmark = bookmark_lookup[numeric_id]
            elif post_id in bookmark_lookup:
                bookmark = bookmark_lookup[post_id]

            if not bookmark:
                skipped_count += 1
                print(f"  ⏭️  No match found for {post_id}")
                continue

            old_content = post.get("content", "")
            new_content = bookmark.content or ""

            # Update if new content is different (even if same length - might have better formatting)
            if new_content and new_content != old_content:
                try:
                    # Update in Supabase
                    update_result = (
                        supabase.table("posts")
                        .update({"content": new_content, "updated_at": "now()"})
                        .eq("post_id", post_id)
                        .eq("platform", "twitter")
                        .execute()
                    )

                    if update_result.data:
                        updated_count += 1
                        old_len = len(old_content)
                        new_len = len(new_content)
                        print(f"  ✅ Updated {post_id}: {old_len} → {new_len} chars")
                    else:
                        print(f"  ⚠️  Update failed for {post_id}")
                except Exception as e:
                    print(f"  ❌ Error updating {post_id}: {e}")
            else:
                skipped_count += 1
                print(f"  ⏭️  {post_id}: content unchanged ({len(old_content)} chars)")

        print(f"\n✅ Updated {updated_count}/{len(latest_posts)} posts")
        print(f"   Skipped: {skipped_count} (not in bookmarks or unchanged)")

    except Exception as e:
        print(f"❌ Error during re-collection: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await extractor.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Re-collect latest Twitter posts")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Number of latest posts to re-collect (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without actually updating",
    )

    args = parser.parse_args()

    asyncio.run(recollect_latest_tweets(limit=args.limit, dry_run=args.dry_run))
