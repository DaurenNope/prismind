#!/usr/bin/env python3
"""
Fetch full content from Twitter post URLs directly.

This bypasses the bookmarks page limitation by fetching content directly from the tweet URL.
"""

import asyncio
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.domain.collection.extractors.twitter import TwitterExtractorPlaywright
from src.domain.collection.extractors.twitter.url_fetcher import fetch_tweet_content_from_url
from src.infrastructure.database.manager import SupabaseManager
from src.domain.analysis.services.post_analyzer import detect_content_truncation


async def fetch_full_content_from_url(
    post_url: str, extractor: TwitterExtractorPlaywright
) -> str:
    """
    Fetch full content from a Twitter post URL - uses reusable module.

    Args:
        post_url: The Twitter post URL (e.g., https://x.com/user/status/123456)
        extractor: Authenticated Twitter extractor

    Returns:
        Full content string, or empty if failed
    """
    if not extractor.auth or not extractor.auth.page:
        return ""

    print(f"  🌐 Fetching from: {post_url}")
    content = await fetch_tweet_content_from_url(extractor.auth.page, post_url)

    if content:
        print(f"  ✅ Extracted {len(content)} chars")
    else:
        print(f"  ⚠️ Could not extract content")

    return content or ""


async def fix_truncated_posts_from_urls(limit: int = 50):
    """
    Fix truncated posts by fetching full content from their URLs.

    Args:
        limit: Maximum number of posts to fix
    """
    print("=" * 60)
    print("🔧 Fixing Truncated Posts (Fetch from URL)")
    print("=" * 60)

    # Get Supabase client
    try:
        supabase_manager = SupabaseManager()
        supabase = supabase_manager.client
    except Exception as e:
        print(f"❌ Failed to connect to Supabase: {e}")
        return

    # Find truncated posts
    print(f"\n📊 Finding truncated posts...")
    try:
        response = (
            supabase.table("posts")
            .select("post_id, content, url, platform")
            .eq("platform", "twitter")
            .order("collected_at", desc=True)
            .limit(limit * 2)  # Get more to filter
            .execute()
        )

        all_posts = response.data or []
        truncated_posts = []

        for post in all_posts:
            content = post.get("content", "") or ""
            if detect_content_truncation(content):
                truncated_posts.append(post)
                if len(truncated_posts) >= limit:
                    break

        print(f"✅ Found {len(truncated_posts)} truncated posts")

        if not truncated_posts:
            print("✅ No truncated posts found!")
            return

    except Exception as e:
        print(f"❌ Failed to query Supabase: {e}")
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

        # Fix each truncated post
        print(f"\n🔄 Fixing {len(truncated_posts)} posts...")
        updated_count = 0
        failed_count = 0
        skipped_count = 0

        for i, post in enumerate(truncated_posts, 1):
            post_id = post.get("post_id", "")
            post_url = post.get("url", "")
            old_content = post.get("content", "")

            if not post_url:
                print(f"  ⏭️  {i}/{len(truncated_posts)}: {post_id} - No URL, skipping")
                skipped_count += 1
                continue

            print(f"\n  {i}/{len(truncated_posts)}: {post_id}")
            print(f"    URL: {post_url}")
            print(f"    Old content: {len(old_content)} chars")
            if len(old_content) > 0:
                print(f"    Old ending: {old_content[-50:]}")

            # Fetch full content from URL
            try:
                new_content = await fetch_full_content_from_url(post_url, extractor)
            except Exception as e:
                print(f"    ❌ Exception during fetch: {e}")
                failed_count += 1
                await asyncio.sleep(2)
                continue

            if new_content and len(new_content.strip()) > 10:  # Just need some content
                # Check if content is actually longer/better
                old_len = len(old_content.strip())
                new_len = len(new_content.strip())

                # CRITICAL: NEVER update if new content is shorter or equal
                if new_len <= old_len:
                    skipped_count += 1
                    print(
                        f"    ⏭️  New content not longer ({old_len} → {new_len} chars) - SKIPPING"
                    )
                    await asyncio.sleep(3)
                    continue

                # Update if:
                # 1. New content is significantly longer (> 20% increase)
                # 2. OR old content was clearly truncated (ends with connector words)
                should_update = False

                if new_len > old_len * 1.2:  # 20% longer
                    should_update = True
                elif (
                    old_len < 300 and new_len > old_len + 50
                ):  # Small posts, significant increase
                    should_update = True
                elif old_content.rstrip().endswith(
                    (",", " and", " but", " for", " was", " that")
                ):
                    should_update = True  # Definitely truncated

                if should_update:
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
                            print(f"    ✅ Updated: {old_len} → {new_len} chars")
                            if new_len > old_len:
                                print(f"    📈 Gained {new_len - old_len} chars")
                        else:
                            print(f"    ⚠️  Update failed (no data returned)")
                            failed_count += 1
                    except Exception as e:
                        print(f"    ❌ Error updating: {e}")
                        failed_count += 1
                else:
                    skipped_count += 1
                    print(
                        f"    ⏭️  Content not significantly better ({old_len} → {new_len} chars)"
                    )
            elif new_content:
                skipped_count += 1
                print(f"    ⏭️  New content too short ({len(new_content)} chars)")
            else:
                failed_count += 1
                print(f"    ⚠️  Failed to fetch content")

            # Delay between requests to avoid rate limiting
            await asyncio.sleep(3)  # Increased delay

        print(f"\n{'='*60}")
        print(f"📊 Summary:")
        print(f"  ✅ Updated: {updated_count}/{len(truncated_posts)}")
        print(f"  ⏭️  Skipped: {skipped_count}/{len(truncated_posts)}")
        print(f"  ❌ Failed: {failed_count}/{len(truncated_posts)}")
        print(f"{'='*60}")

        print(f"\n✅ Updated {updated_count}/{len(truncated_posts)} posts")

    except Exception as e:
        print(f"❌ Error during fix: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await extractor.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix truncated posts by fetching from URLs"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of posts to fix (default: 50)",
    )

    args = parser.parse_args()

    asyncio.run(fix_truncated_posts_from_urls(limit=args.limit))
