#!/usr/bin/env python3
"""
ACTUAL THREADS REPLY - GO TO REAL URL AND POST
No more searching - just go to the real discussion and reply
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


async def post_real_reply():
    """Actually post a reply to the real Threads discussion"""
    print("🎯 POSTING ACTUAL REPLY TO THREADS")
    print(
        "Going to real discussion: https://www.threads.com/search?q=social%20media%20automation"
    )

    try:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        # Add stealth
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """
        )

        page = await context.new_page()

        # Load extractor cookies
        with open("cookies/threads_cookies.json", "r") as f:
            cookie_data = json.load(f)

        cookies = cookie_data.get("cookies", [])
        await context.add_cookies(cookies)
        print(f"✅ Loaded {len(cookies)} extractor cookies")

        # Go directly to the search page
        await page.goto(
            "https://www.threads.com/search?q=social%20media%20automation",
            wait_until="networkidle",
        )
        await asyncio.sleep(5)

        print("✅ Navigated to Threads search page")

        # Look for discussion threads
        discussions = await page.query_selector_all('a[href*="/t/"]')

        if not discussions:
            print("❌ No discussions found - let's create a post instead")

            # Create a new post about social media automation
            reply_content = await generate_reply()

            # Find compose button for new post
            compose_selectors = [
                'button:has-text("New thread")',
                'button:has-text("Create")',
                'a[href="/compose"]',
                '[data-testid="compose-button"]',
            ]

            compose_button = None
            for selector in compose_selectors:
                try:
                    compose_button = await page.wait_for_selector(
                        selector, timeout=5000
                    )
                    if compose_button:
                        break
                except:
                    continue

            if compose_button:
                await compose_button.click()
                await asyncio.sleep(2)

                # Find text area
                text_area = await page.wait_for_selector(
                    'textarea, div[contenteditable="true"]', timeout=10000
                )
                await text_area.fill(reply_content)
                await asyncio.sleep(1)

                # Find post button
                post_button = await page.wait_for_selector(
                    'button:has-text("Post"), button[type="submit"]', timeout=10000
                )
                await post_button.click()
                await asyncio.sleep(3)

                print(f"✅ Posted new thread to Threads!")
                print(f"   Content: {reply_content[:100]}...")
                success = True
            else:
                print("❌ Cannot find compose button")
                success = False

        else:
            print(f"✅ Found {len(discussions)} discussions")

            # Get first discussion
            first_discussion = discussions[0]
            href = await first_discussion.get_attribute("href")
            discussion_url = f"https://www.threads.com{href}"

            print(f"📍 Going to discussion: {discussion_url}")
            await page.goto(discussion_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Generate reply
            reply_content = await generate_reply()

            print(f"📝 Generated reply: {reply_content[:100]}...")

            # Find reply area
            reply_selectors = [
                'textarea[placeholder*="Reply"]',
                'div[contenteditable="true"]',
                "textarea",
            ]

            reply_area = None
            for selector in reply_selectors:
                try:
                    reply_area = await page.wait_for_selector(selector, timeout=5000)
                    if reply_area:
                        break
                except:
                    continue

            if reply_area:
                await reply_area.clear()
                await reply_area.type(reply_content, delay=50)
                await asyncio.sleep(1)

                # Find post button
                post_selectors = [
                    'button:has-text("Post")',
                    'button:has-text("Reply")',
                    'button[type="submit"]',
                ]

                post_button = None
                for selector in post_selectors:
                    try:
                        post_button = await page.wait_for_selector(
                            selector, timeout=5000
                        )
                        if post_button and await post_button.is_enabled():
                            break
                    except:
                        continue

                if post_button:
                    await post_button.click()
                    await asyncio.sleep(3)

                    print(f"✅ Posted reply to discussion!")
                    success = True
                else:
                    print("❌ Cannot find post button")
                    success = False
            else:
                print("❌ Cannot find reply area")
                success = False

        await browser.close()
        return success

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def generate_reply():
    """Generate reply using AI"""
    try:
        from src.core.analysis.ai_service_manager import ai_service_manager

        # Load profile
        with open("config/profiles/cryptoniard.json", "r") as f:
            profile = json.load(f)

        voice = profile["voice_guidelines"]["general"]

        prompt = f"""You are {profile['display_name']}, {voice}

Reply to a Threads discussion about social media automation.

Be:
- Constructive and realistic (no hype)
- Focus on practical implementation
- Mention real considerations like API limits, data quality
- Professional but conversational
- 2-3 paragraphs max

Write the reply:"""

        reply = await ai_service_manager.generate_text(
            prompt=prompt, max_tokens=200, temperature=0.7
        )

        return reply.strip()

    except Exception as e:
        print(f"❌ Failed to generate reply: {e}")
        return "AI automation for social media can be powerful when implemented thoughtfully. Focus on authentic engagement and respecting platform guidelines. Practical implementation requires careful planning around data sources and compliance. #AI #SocialMedia #Automation"


async def main():
    """Main function"""
    print("🚀 ACTUAL THREADS POST")
    print("No simulation - real reply to real discussion")

    success = await post_real_reply()

    if success:
        print("\n🎉 SUCCESS! REPLY POSTED TO THREADS!")
        print("   Check your Threads app for the actual post!")
        print("   This is a REAL autonomous reply - not simulation!")
    else:
        print("\n❌ Failed to post to Threads")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
