#!/usr/bin/env python3
"""
Fix truncated tweets from the last month
"""
import asyncio
import time
from datetime import datetime, timedelta

from playwright.async_api import async_playwright

from src.supabase_manager import SupabaseManager


async def get_full_content(url: str) -> tuple[str, bool]:
    """Get full tweet content with Show more expansion"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            await page.goto(url, timeout=30000)
            await page.wait_for_timeout(3000)

            # Try clicking Show more
            expanded = False
            show_more_selectors = [
                '[data-testid="tweet-text-show-more-button"]',
                'div[role="button"]:has-text("Show more")',
                'span:has-text("Show more")',
                '[dir="ltr"]:has-text("Show more")',
            ]

            for selector in show_more_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        is_visible = await button.is_visible()
                        if is_visible:
                            await button.click(force=True)
                            await page.wait_for_timeout(2000)
                            expanded = True
                            break
                except:
                    continue

            # Get content
            tweet_text = await page.query_selector('[data-testid="tweetText"]')
            if tweet_text:
                content = await tweet_text.inner_text()
                return content, expanded

            return "", False

        except Exception as e:
            print(f"      Error: {e}")
            return "", False
        finally:
            await browser.close()


async def main():
    sm = SupabaseManager()

    # Get tweets from last month
    one_month_ago = (datetime.now() - timedelta(days=30)).isoformat()

    print(f"🔍 Finding truncated tweets from last month (since {one_month_ago[:10]})...")
    print("=" * 70)

    result = (
        sm.client.table("posts")
        .select("post_id, author, content, url, created_at")
        .eq("platform", "twitter")
        .gte("created_at", one_month_ago)
        .execute()
    )

    print(f"📊 Total tweets from last month: {len(result.data)}")

    # Find truncated ones
    truncated = []
    for post in result.data:
        content = post.get("content", "").strip()
        length = len(content)

        # Truncation indicators:
        # 1. Ends mid-sentence (200-500 chars, no proper punctuation)
        # 2. Ends with ellipsis but seems incomplete
        if 200 < length < 600:
            last_char = content[-1] if content else ""
            # Check for abrupt endings
            if last_char not in '.!?")' and not content.endswith("..."):
                truncated.append(post)
            # Or ends with ellipsis mid-word
            elif content.endswith("…") and length < 280:
                truncated.append(post)

    print(f"❌ Truncated tweets found: {len(truncated)}")
    print()

    if not truncated:
        print("✅ No truncated tweets found!")
        return

    # Show samples
    print("📋 Sample truncated tweets:")
    print("-" * 70)
    for post in truncated[:5]:
        author = post.get("author", "Unknown")[:20]
        content = post.get("content", "")
        print(f"{author:20} | {len(content):3} chars | ...{content[-60:]}")

    if len(truncated) > 5:
        print(f"   ... and {len(truncated) - 5} more")

    print()
    print(f"⚠️  This will open a browser and visit {len(truncated)} tweet URLs")
    print(f"   Estimated time: {len(truncated) * 5 // 60} minutes")
    print()
    print("🚀 Auto-starting in 3 seconds... (Ctrl+C to cancel)")
    await asyncio.sleep(3)

    print()
    print("🔧 Starting repair...")
    print("=" * 70)

    fixed = 0
    failed = 0
    no_change = 0

    for i, post in enumerate(truncated, 1):
        url = post.get("url")
        author = post.get("author", "Unknown")
        old_content = post.get("content", "")
        post_id = post.get("post_id")

        print(f"\\n[{i}/{len(truncated)}] {author[:30]}")
        print(f"   Old: {len(old_content)} chars")

        try:
            new_content, was_expanded = await get_full_content(url)

            if new_content and len(new_content) > len(old_content):
                improvement = len(new_content) - len(old_content)
                print(f"   ✅ New: {len(new_content)} chars (+{improvement})")
                print(f"      Expanded: {was_expanded}")

                # Update in both Supabase AND SQLite
                sm.client.table("posts").update({"content": new_content}).eq(
                    "post_id", post_id
                ).execute()

                # Update SQLite too
                import sqlite3

                conn = sqlite3.connect("beyondlines.db")
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE posts SET content = ? WHERE post_id = ?",
                    (new_content, post_id),
                )
                conn.commit()
                conn.close()

                fixed += 1
            elif new_content and len(new_content) == len(old_content):
                print(f"   ℹ️  No change ({len(new_content)} chars)")
                no_change += 1
            else:
                print(f"   ⚠️  Could not get better content")
                failed += 1

            # Rate limiting - don't hammer Twitter
            await asyncio.sleep(3)

        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed += 1
            await asyncio.sleep(2)

    print()
    print("=" * 70)
    print(f"📊 Final Results:")
    print(f"   ✅ Fixed:      {fixed}")
    print(f"   ℹ️  Unchanged:  {no_change}")
    print(f"   ❌ Failed:     {failed}")
    print(f"   📝 Total:      {len(truncated)}")
    print()
    print(
        f"🎉 Success rate: {fixed}/{len(truncated)} ({fixed*100//len(truncated) if truncated else 0}%)"
    )


if __name__ == "__main__":
    asyncio.run(main())
