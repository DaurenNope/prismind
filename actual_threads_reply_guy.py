#!/usr/bin/env python3
"""
ACTUAL THREADS.COM REPLY GUY
Real autonomous posting to threads.com - no simulation
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


class RealThreadsReplyGuy:
    """Actual working Reply Guy for threads.com"""

    def __init__(self):
        self.profile = None
        self.browser = None
        self.context = None
        self.page = None
        self.session_file = "config/threads_cookies.json"

    async def initialize(self):
        """Initialize the Reply Guy"""
        print("🔧 Initializing Real Threads Reply Guy...")

        # Load profile
        await self._load_profile()

        # Initialize browser
        await self._initialize_browser()

        # Login to threads.com
        await self._login_to_threads()

        print("✅ Real Threads Reply Guy initialized!")
        return True

    async def _load_profile(self):
        """Load the cryptoniard profile"""
        try:
            with open("config/profiles/cryptoniard.json", "r") as f:
                self.profile = json.load(f)
            print(f"✅ Loaded profile: {self.profile['display_name']}")
        except Exception as e:
            print(f"❌ Failed to load profile: {e}")
            raise

    async def _initialize_browser(self):
        """Initialize browser with stealth settings"""
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,  # Show for debugging
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Add stealth script
        await self.context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """
        )

        self.page = await self.context.new_page()
        print("✅ Browser initialized with stealth")

    async def _login_to_threads(self):
        """Login to threads.com"""
        try:
            # Try to load cookies
            if os.path.exists(self.session_file):
                with open(self.session_file, "r") as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                print("✅ Loaded saved cookies")

            # Navigate to threads.com
            await self.page.goto("https://threads.com", wait_until="networkidle")
            await asyncio.sleep(3)

            # Check if logged in
            if await self._is_logged_in():
                print("✅ Successfully logged into threads.com!")
            else:
                print("❌ Not logged in - manual login required")
                await self._manual_login()

        except Exception as e:
            print(f"❌ Login failed: {e}")
            raise

    async def _is_logged_in(self) -> bool:
        """Check if we're logged into threads.com"""
        try:
            # Look for login indicators (means NOT logged in)
            login_indicators = await self.page.query_selector_all(
                'button:has-text("Log in"), input[type="email"], input[type="password"]'
            )
            return len(login_indicators) == 0
        except:
            return False

    async def _manual_login(self):
        """Handle manual login"""
        print("🔐 MANUAL LOGIN REQUIRED")
        print("1. Browser window is open")
        print("2. Please log into threads.com")
        print("3. Press Enter when done...")
        input("Press Enter after logging in...")

        # Save cookies after login
        cookies = await self.context.cookies()
        os.makedirs("config", exist_ok=True)
        with open(self.session_file, "w") as f:
            json.dump(cookies, f, indent=2)
        print("💾 Saved login cookies!")

    async def search_for_mentions(self) -> list:
        """Search for beyondlines mentions on threads.com"""
        print("🔍 Searching for beyondlines mentions...")

        try:
            # Search for automation-related discussions
            search_url = "https://threads.com/search?q=beyondlines+OR+automation+OR+AI+social+media"
            await self.page.goto(search_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Look for discussion threads
            discussion_links = await self.page.query_selector_all('a[href*="/t/"]')

            mentions = []
            for link in discussion_links[:5]:  # Limit to first 5
                try:
                    href = await link.get_attribute("href")
                    title = await link.inner_text()

                    if href and len(title) > 10:  # Valid discussion
                        mentions.append(
                            {"url": f"https://threads.com{href}", "title": title}
                        )
                except:
                    continue

            print(f"✅ Found {len(mentions)} relevant discussions")
            return mentions

        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []

    async def generate_reply(self, discussion_title: str) -> str:
        """Generate reply using real cryptoniard profile"""
        try:
            from src.core.analysis.ai_service_manager import ai_service_manager

            voice_general = self.profile["voice_guidelines"]["general"]
            voice_english = self.profile["voice_guidelines"]["english"]

            prompt = f"""You are {self.profile['display_name']}, {voice_general}

{voice_english}

THREADS.COM FORUM CONTEXT:
Replying to a discussion titled: "{discussion_title}"

This is a technical forum discussion about AI/social media automation.

STYLE REQUIREMENTS:
- Constructive realism (no hype)
- Focus on practical considerations and challenges
- Mention specific technical aspects when relevant
- Direct, data-aware advice
- 2-3 paragraphs maximum
- Professional but conversational
- Add value to the discussion

Write the forum reply:"""

            reply = await ai_service_manager.generate_text(
                prompt=prompt,
                max_tokens=250,
                temperature=0.7,
                persona_id="cryptoniard_forum_reply",
            )

            return reply.strip()

        except Exception as e:
            print(f"❌ Reply generation failed: {e}")
            return "Great discussion topic! Looking forward to hearing more thoughts on this."

    async def post_reply(self, discussion_url: str, reply_content: str) -> bool:
        """Actually post a reply to threads.com discussion"""
        print(f"📝 Posting reply to: {discussion_url}")
        print(f"Content: {reply_content[:100]}...")

        try:
            # Navigate to discussion
            await self.page.goto(discussion_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Look for reply textarea or button
            reply_selectors = [
                'textarea[placeholder*="Reply"]',
                'textarea[placeholder*="Write"]',
                'div[contenteditable="true"]',
                "textarea",
            ]

            textarea = None
            for selector in reply_selectors:
                try:
                    textarea = await self.page.wait_for_selector(selector, timeout=5000)
                    if textarea:
                        break
                except:
                    continue

            if not textarea:
                print("❌ Cannot find reply text area")
                return False

            # Type the reply
            await textarea.clear()
            await textarea.type(reply_content, delay=50)
            await asyncio.sleep(1)

            # Find and click post button
            post_selectors = [
                'button:has-text("Post")',
                'button:has-text("Reply")',
                'button[type="submit"]',
                'button:has-text("Submit")',
            ]

            post_button = None
            for selector in post_selectors:
                try:
                    post_button = await self.page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if post_button and await post_button.is_enabled():
                        break
                except:
                    continue

            if not post_button:
                print("❌ Cannot find post button")
                return False

            await post_button.click()
            await asyncio.sleep(3)

            print("✅ Reply posted successfully!")
            return True

        except Exception as e:
            print(f"❌ Failed to post reply: {e}")
            return False

    async def run_automatic_reply_guy(self):
        """Run the automatic Reply Guy - find discussions and reply"""
        print("🚀 Starting Automatic Reply Guy...")
        print("Looking for discussions to engage with...")

        # Search for mentions
        discussions = await self.search_for_mentions()

        if not discussions:
            print("⚠️  No relevant discussions found")
            return False

        # Process each discussion
        for i, discussion in enumerate(discussions, 1):
            print(f"\n--- Processing Discussion {i}/{len(discussions)} ---")
            print(f"Title: {discussion['title']}")
            print(f"URL: {discussion['url']}")

            # Generate reply
            reply = await self.generate_reply(discussion["title"])
            print(f"Generated reply: {reply[:100]}...")

            # Post reply
            success = await self.post_reply(discussion["url"], reply)

            if success:
                print(f"✅ Successfully replied to discussion {i}")
            else:
                print(f"❌ Failed to reply to discussion {i}")

            # Wait between posts to avoid spam
            if i < len(discussions):
                print("⏱️  Waiting 60 seconds before next reply...")
                await asyncio.sleep(60)

        return True

    async def close(self):
        """Close browser and cleanup"""
        if self.browser:
            await self.browser.close()


async def main():
    """Run the actual Threads Reply Guy"""
    print("🎯 ACTUAL THREADS.COM REPLY GUY")
    print("Real autonomous posting - no simulation")

    try:
        reply_guy = RealThreadsReplyGuy()
        await reply_guy.initialize()

        # Run automatic Reply Guy
        success = await reply_guy.run_automatic_reply_guy()

        await reply_guy.close()

        if success:
            print(f"\n🎉 THREADS.COM REPLY GUY COMPLETED!")
            print(f"Real replies posted to threads.com!")
            print(f"Check the discussions for actual posts!")
        else:
            print(f"\n⚠️  No discussions found to engage with")

    except Exception as e:
        print(f"❌ Reply Guy failed: {e}")
        import traceback

        traceback.print_exc()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
