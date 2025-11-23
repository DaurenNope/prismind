#!/usr/bin/env python3
"""
Re-collect truncated Twitter posts to get full content.

This script:
1. Finds Twitter posts with truncated content (likely missing "read more" expansion)
2. Re-collects them from Twitter bookmarks
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
from src.infrastructure.database.storage.db import get_storage


def detect_truncated_content(content: str) -> bool:
    """
    Detect if content is truncated - using the same logic as the analyzer.
    """
    if not content or len(content.strip()) < 10:
        return False

    content = content.strip()

    # Obvious truncation: ends with ellipsis
    if content.endswith("...") or content.endswith("…"):
        return True

    # Contains "Show more" or "Read more" (shouldn't be in saved content)
    if "show more" in content.lower() or "read more" in content.lower():
        return True

    # Check for incomplete sentence (more careful detection)
    if len(content) > 50:
        last_char = content[-1]
        last_words = content.rstrip().split()[-3:] if content.rstrip().split() else []
        last_phrase = " ".join(last_words).lower() if last_words else ""

        # Definitely truncated: ends with comma
        if content.rstrip().endswith(","):
            return True

        # Definitely truncated: ends with mid-sentence connectors
        mid_sentence_endings = [
            " and",
            " but",
            " for",
            " was",
            " were",
            " that",
            " this",
            " the",
            " will be",
            " would be",
            " could be",
            " should be",
            " text and",
            " silent and",
            " the bitcoin",
            " but for",
        ]
        if any(
            content.rstrip().lower().endswith(ending) for ending in mid_sentence_endings
        ):
            return True

        # Ends with lowercase letter AND it's a connecting word (more conservative)
        if last_char.islower() and last_char.isalpha():
            # Only flag if it ends with common connecting words
            connecting_words = [
                "and",
                "but",
                "for",
                "was",
                "that",
                "the",
                "this",
                "with",
                "from",
            ]
            if last_phrase and any(
                last_phrase.endswith(word) for word in connecting_words
            ):
                return True

    return False


async def recollect_truncated_tweets(limit: int = 50, dry_run: bool = False):
    """
    Re-collect truncated Twitter posts.

    Args:
        limit: Maximum number of posts to re-collect
        dry_run: If True, only show what would be updated (don't actually update)
    """
    print("=" * 60)
    print("🔄 Re-collecting Truncated Twitter Posts")
    print("=" * 60)

    # Get Supabase client
    try:
        supabase_manager = SupabaseManager()
        supabase = supabase_manager.client
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return

    # Find truncated Twitter posts
    print("\n📊 Finding truncated Twitter posts...")
    try:
        response = (
            supabase.table("posts")
            .select("post_id, content, url, platform")
            .eq("platform", "twitter")
            .order("collected_at", desc=True)
            .limit(limit * 5)  # Get more to filter (check more posts)
            .execute()
        )

        all_posts = response.data or []
        truncated_posts = []

        for post in all_posts:
            content = post.get("content", "") or ""
            if detect_truncated_content(content):
                truncated_posts.append(post)
                if len(truncated_posts) >= limit:
                    break

        print(
            f"✅ Found {len(truncated_posts)} truncated posts (out of {len(all_posts)} total)"
        )

        if not truncated_posts:
            print("✅ No truncated posts found - all good!")
            return

        # Show what we found
        print("\n📋 Truncated posts to re-collect:")
        for i, post in enumerate(truncated_posts[:10], 1):  # Show first 10
            content = post.get("content", "")[:80]
            print(f"  {i}. {post.get('post_id')}: {content}...")
        if len(truncated_posts) > 10:
            print(f"  ... and {len(truncated_posts) - 10} more")

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
        print("\n📥 Fetching fresh bookmarks (with full content)...")
        print(
            f"   Looking for posts: {[p.get('post_id') for p in truncated_posts[:5]]}"
        )
        bookmarks = await extractor.get_saved_posts(
            limit=limit * 3
        )  # Get more to match older posts

        if not bookmarks:
            print("⚠️ No bookmarks found")
            return

        print(f"✅ Found {len(bookmarks)} bookmarks")

        # Match truncated posts with fresh bookmarks
        print("\n🔄 Updating truncated posts...")
        updated_count = 0

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
        found_ids = []
        for bookmark in bookmarks:
            bookmark_id = str(bookmark.post_id or "")
            numeric_id = extract_numeric_id(bookmark_id)
            if numeric_id:
                bookmark_lookup[numeric_id] = bookmark
                # Also store with original format
                bookmark_lookup[bookmark_id] = bookmark
                found_ids.append(numeric_id)

        print(f"   Found {len(found_ids)} bookmarks with IDs: {found_ids[:10]}...")

        for truncated_post in truncated_posts:
            post_id = str(truncated_post.get("post_id", ""))
            numeric_id = extract_numeric_id(post_id)

            # Find matching bookmark by numeric ID
            bookmark = None
            if numeric_id and numeric_id in bookmark_lookup:
                bookmark = bookmark_lookup[numeric_id]
            elif post_id in bookmark_lookup:
                bookmark = bookmark_lookup[post_id]

            if not bookmark:
                print(f"  ⏭️  No match found for {post_id}")
                continue

            old_content = truncated_post.get("content", "")
            new_content = bookmark.content or ""

            # Only update if new content is longer
            if len(new_content) > len(old_content):
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
                        print(
                            f"  ✅ Updated {post_id}: {len(old_content)} → {len(new_content)} chars"
                        )
                    else:
                        print(f"  ⚠️  Update failed for {post_id}")
                except Exception as e:
                    print(f"  ❌ Error updating {post_id}: {e}")
            else:
                print(
                    f"  ⏭️  {post_id}: new content not longer ({len(old_content)} → {len(new_content)})"
                )

        print(f"\n✅ Updated {updated_count}/{len(truncated_posts)} truncated posts")

    except Exception as e:
        print(f"❌ Error during re-collection: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await extractor.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Re-collect truncated Twitter posts")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of posts to re-collect (default: 50)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without actually updating",
    )

    args = parser.parse_args()

    asyncio.run(recollect_truncated_tweets(limit=args.limit, dry_run=args.dry_run))
