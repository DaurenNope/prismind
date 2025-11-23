#!/usr/bin/env python3
"""
REAL THREADS REPLY GUY
Uses existing auth/posting modules - no recreation
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


async def test_existing_threads_posting():
    """Test the existing Threads posting module"""
    print("🧵 Testing EXISTING Threads posting module...")

    try:
        from src.domain.publishing.platforms.threads_playwright import (
            post_to_threads_playwright,
        )

        # Test content
        test_content = "Testing Beyondlines Reply Guy functionality. AI automation for social media engagement works! 🚀 #AI #Automation"

        print(f"📝 Posting test content: {test_content}")
        print(f"📏 Length: {len(test_content)} characters")

        # Use the existing posting function
        result = await post_to_threads_playwright(test_content)

        if result.get("success"):
            print(f"✅ Successfully posted to Threads!")
            print(f"   Post ID: {result.get('post_id')}")
            print(f"   URL: {result.get('url')}")
            print(f"   Check Threads for the actual post!")
            return True
        else:
            print(f"❌ Failed to post to Threads: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ Threads posting test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def search_threads_for_mentions():
    """Search threads.com for beyondlines mentions using existing methods"""
    print("🔍 Searching Threads for beyondlines mentions...")

    try:
        from dotenv import load_dotenv
        from playwright.async_api import async_playwright

        load_dotenv()

        # Use existing cookie management
        cookie_file = os.getenv("THREADS_COOKIES_FILE") or "config/threads_cookies.json"

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"]
        )

        context = await browser.new_context()

        # Load existing cookies if available
        if os.path.exists(cookie_file):
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
            await context.add_cookies(cookies)
            print("✅ Loaded existing cookies")

        page = await context.new_page()

        # Search for beyondlines discussions
        search_url = "https://threads.com/search?q=beyondlines+automation+AI"
        await page.goto(search_url, wait_until="networkidle")
        await asyncio.sleep(3)

        # Look for discussions
        discussions = []
        discussion_links = await page.query_selector_all('a[href*="/t/"]')

        for link in discussion_links[:3]:
            try:
                href = await link.get_attribute("href")
                title = await link.inner_text()
                if href and len(title) > 20:
                    discussions.append(
                        {
                            "url": f"https://threads.com{href}",
                            "title": title[:100] + "..." if len(title) > 100 else title,
                        }
                    )
            except:
                continue

        print(f"✅ Found {len(discussions)} relevant discussions:")
        for i, d in enumerate(discussions, 1):
            print(f"   {i}. {d['title']}")
            print(f"      {d['url']}")

        await browser.close()
        return discussions

    except Exception as e:
        print(f"❌ Search failed: {e}")
        return []


async def generate_reply_with_real_profile():
    """Generate reply using existing profile system"""
    print("🤖 Generating reply with existing profile system...")

    try:
        from src.domain.analysis.analyzers.ai_service_manager import ai_service_manager
        from src.services.profile_content_selector import profile_content_selector

        # Load cryptoniard profile
        profile = await profile_content_selector.get_profile("cryptoniard")
        if not profile:
            print("❌ Could not load cryptoniard profile")
            return None

        print(f"✅ Loaded profile: {profile.get('display_name', 'Cryptoniard')}")

        # Create mention context
        mention_context = {
            "platform": "threads",
            "content_type": "forum_reply",
            "topic": "AI automation for social media",
            "voice_guidelines": profile.get("voice_guidelines", {}),
        }

        # Generate content using existing system
        reply_content = await profile_content_selector.generate_content(
            profile_key="cryptoniard",
            content_type="forum_reply",
            context=mention_context,
        )

        if reply_content:
            print(f"✅ Generated reply using existing profile system:")
            print(f"📝 {reply_content[:200]}...")
            print(f"📏 Length: {len(reply_content)} characters")
            return reply_content
        else:
            # Fallback to direct AI generation
            print("⚠️  Profile generation failed, using fallback...")

            fallback_prompt = """You are Cryptoniard, a DeFi realist focused on AI automation.
            Reply to this forum question about AI social media automation.
            Be constructive, realistic, and practical. 2-3 paragraphs max."""

            reply = await ai_service_manager.generate_text(
                prompt=fallback_prompt, max_tokens=200, temperature=0.7
            )
            print(f"✅ Generated fallback reply:")
            print(f"📝 {reply[:200]}...")
            return reply

    except Exception as e:
        print(f"❌ Reply generation failed: {e}")
        return None


async def create_and_post_real_reply():
    """Create and post actual reply to a Threads discussion"""
    print("🚀 Creating and posting REAL reply to Threads...")

    # Search for discussions
    discussions = await search_threads_for_mentions()

    if not discussions:
        print("⚠️  No discussions found, creating test post...")

        # Generate reply
        reply = await generate_reply_with_real_profile()
        if not reply:
            print("❌ Failed to generate reply")
            return False

        print(f"\n📝 Reply content:")
        print(f"{reply}")

        # Post as new thread since no discussion found
        from src.domain.publishing.platforms.threads_playwright import (
            post_to_threads_playwright,
        )

        result = await post_to_threads_playwright(reply)

        if result.get("success"):
            print(f"✅ Posted new thread to Threads!")
            print(f"   URL: {result.get('url')}")
            return True
        else:
            print(f"❌ Failed to post: {result.get('error')}")
            return False

    else:
        # Use first discussion
        discussion = discussions[0]
        print(f"\n🎯 Target discussion: {discussion['title']}")
        print(f"   URL: {discussion['url']}")

        # Generate reply
        reply = await generate_reply_with_real_profile()
        if not reply:
            return False

        print(f"\n📝 Reply to post:")
        print(f"{reply}")

        # TODO: Post as reply to existing discussion
        # This would require extending the existing posting module
        print(f"\n⚠️  Reply generated, need to extend posting module for replies")
        print(f"   Existing module posts new threads only")

        return True


async def main():
    """Main function using existing modules"""
    print("🎯 REAL THREADS REPLY GUY")
    print("Using existing authentication and posting modules")

    # Test existing posting first
    posting_works = await test_existing_threads_posting()

    # Create and post real reply
    reply_success = await create_and_post_real_reply()

    print("\n" + "=" * 60)
    print("THREADS REPLY GUY STATUS")
    print("=" * 60)
    print(f"Existing posting module: {'✅ Works' if posting_works else '❌ Failed'}")
    print(f"Reply generation: {'✅ Works' if reply_success else '❌ Failed'}")

    if posting_works:
        print(f"\n✅ THREADS REPLY GUY CAN POST!")
        print(f"   - Uses existing authentication")
        print(f"   - Uses existing posting module")
        print(f"   - Uses existing profile system")
        print(f"   - Actually posts to Threads (check the app!)")

    return 0 if posting_works else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
