"""
Twitter Posting Service using Playwright (Browser Automation)
Like mimesis autoposter - uses Playwright primarily
"""

import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)


async def post_to_twitter_playwright(content: str) -> Dict:
    """
    Post to Twitter using Playwright browser automation.
    
    Returns:
        Dict with 'success', 'tweet_id', 'url', 'error' keys
    """
    playwright = None
    browser = None
    page = None
    
    try:
        # Get credentials
        username = os.getenv("TWITTER_USERNAME")
        password = os.getenv("TWITTER_PASSWORD")
        cookie_file = os.getenv("TWITTER_COOKIE_FILE") or f"config/twitter_cookies_{username}.json" if username else None
        
        if not username:
            return {"success": False, "error": "TWITTER_USERNAME not set"}
        
        # Validate length
        if len(content) > 280:
            return {
                "success": False,
                "error": f"Tweet too long: {len(content)} chars (max 280)",
            }
        
        # Start Playwright
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=False,  # Keep visible for debugging
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        
        # Load cookies if available
        if cookie_file and Path(cookie_file).exists():
            with open(cookie_file, "r") as f:
                cookies_data = json.load(f)
                # Ensure cookies is a list (Playwright expects array)
                if isinstance(cookies_data, dict):
                    # If it's a dict, try to extract cookies array or convert
                    cookies = cookies_data.get("cookies", cookies_data.get("data", [cookies_data]))
                elif isinstance(cookies_data, list):
                    cookies = cookies_data
                else:
                    cookies = []
                if cookies:
                    await context.add_cookies(cookies)
        
        page = await context.new_page()
        
        # Navigate to Twitter compose
        await page.goto("https://twitter.com/compose/tweet", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        
        # Check if logged in - look for compose textarea
        try:
            # Twitter compose textarea selector (multiple possible)
            textarea = await page.wait_for_selector(
                '[data-testid="tweetTextarea_0"], [data-testid="tweetTextarea_1"], [contenteditable="true"][role="textbox"]',
                timeout=10000
            )
        except Exception as e:
            logger.debug(f"Compose textarea not found, attempting login: {e}")
            # Not logged in - try login
            if password:
                await page.goto("https://twitter.com/i/flow/login", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
                # Enter username
                try:
                    username_input = await page.wait_for_selector('input[autocomplete="username"]', timeout=10000)
                    await username_input.fill(username)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    return {"success": False, "error": f"Login failed (username): {str(e)}"}
                
                # Enter password
                try:
                    password_input = await page.wait_for_selector('input[type="password"]', timeout=10000)
                    await password_input.fill(password)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(5000)
                    
                    # Check for error messages (rate limiting, etc.)
                    try:
                        page_text = await page.evaluate("document.body.innerText")
                        current_url = page.url
                        
                        if "could not log" in page_text.lower() or "try again later" in page_text.lower():
                            # Take screenshot for debugging
                            await page.screenshot(path="logs/twitter_post_auth_error.png")
                            return {
                                "success": False,
                                "error": "Twitter authentication blocked - rate limiting detected. Please wait 15-30 minutes and try again."
                            }
                    except Exception as e:
                        logger.debug(f"Rate limit check failed: {e}", exc_info=True)
                        # Continue if check fails - non-critical
                        
                except Exception as e:
                    error_msg = str(e)
                    if "could not log" in error_msg.lower() or "try again later" in error_msg.lower():
                        return {
                            "success": False,
                            "error": f"Twitter rate limiting: {error_msg}. Please wait and try again later."
                        }
                    return {"success": False, "error": f"Login failed (password): {error_msg}"}
                
                # Navigate back to compose
                await page.goto("https://twitter.com/compose/tweet", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                
                try:
                    textarea = await page.wait_for_selector(
                        '[data-testid="tweetTextarea_0"], [data-testid="tweetTextarea_1"], [contenteditable="true"][role="textbox"]',
                        timeout=10000
                    )
                    # AUTO-SAVE: Save cookies after successful password login
                    if cookie_file:
                        try:
                            cookies = await context.cookies()
                            if cookies:
                                Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
                                with open(cookie_file, "w") as f:
                                    json.dump(cookies, f, indent=2)
                                print(f"✅ Saved {len(cookies)} cookies after password login to {cookie_file}")
                        except Exception as e:
                            logger.warning(f"⚠️ Failed to save cookies after login: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"❌ Could not find compose textarea after login: {e}", exc_info=True)
                    return {"success": False, "error": f"Could not find compose textarea after login: {e}"}
            else:
                return {"success": False, "error": "Not logged in and no password provided"}
        
        # Type content
        await textarea.click()
        await textarea.fill(content)
        await page.wait_for_timeout(1000)
        
        # Click tweet button
        tweet_button = await page.wait_for_selector(
            '[data-testid="tweetButton"], [data-testid="tweetButtonInline"]',
            timeout=10000
        )
        await tweet_button.click()
        
        # Wait for tweet to post
        await page.wait_for_timeout(3000)
        
        # Try to get tweet URL from current page or from navigation
        current_url = page.url
        tweet_id = None
        tweet_url = None
        
        # Try to extract tweet ID from URL or page
        if "/status/" in current_url:
            tweet_id = current_url.split("/status/")[-1].split("?")[0]
            username_from_page = current_url.split("twitter.com/")[1].split("/status/")[0]
            tweet_url = f"https://twitter.com/{username_from_page}/status/{tweet_id}"
        else:
            # Look for tweet in timeline or try to get from page
            try:
                # Check if we're on a status page
                status_elements = await page.query_selector_all('article[data-testid="tweet"]')
                if status_elements:
                    # Try to get link from the first tweet
                    link = await status_elements[0].query_selector('a[href*="/status/"]')
                    if link:
                        href = await link.get_attribute("href")
                        if href:
                            tweet_id = href.split("/status/")[-1].split("?")[0]
                            tweet_url = f"https://twitter.com{href}"
            except Exception as e:
                logger.debug(f"Failed to save cookies: {e}", exc_info=True)
                # Continue - cookie save is non-critical
        
        # If we couldn't get URL, use current URL or generate synthetic ID
        if not tweet_url:
            tweet_url = current_url if "twitter.com" in current_url else None
            if tweet_url and "/status/" in tweet_url:
                tweet_id = tweet_url.split("/status/")[-1].split("?")[0]
        
        # AUTO-SAVE: Save cookies for next time (as array)
        if cookie_file:
            try:
                cookies = await context.cookies()
                if cookies:
                    Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
                    with open(cookie_file, "w") as f:
                        # Save as array (Playwright format)
                        json.dump(cookies, f, indent=2)
                    print(f"✅ Refreshed {len(cookies)} cookies saved to {cookie_file}")
            except Exception as e:
                print(f"⚠️ Failed to save cookies: {e}")  # Don't fail on cookie save error
        
        return {
            "success": True,
            "tweet_id": tweet_id or f"playwright_{int(datetime.now().timestamp())}",
            "url": tweet_url or current_url,
            "error": None,
        }
        
    except Exception as e:
        # Try to save cookies even on error (in case auth succeeded)
        try:
            if cookie_file and context:
                cookies = await context.cookies()
                if cookies:
                    Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
                    with open(cookie_file, "w") as f:
                        json.dump(cookies, f, indent=2)
                    print(f"✅ Saved {len(cookies)} cookies even after error")
        except Exception as cookie_error:
            logger.warning(f"⚠️ Failed to save cookies on error: {cookie_error}", exc_info=True)
        
        return {
            "success": False,
            "error": f"Playwright posting failed: {str(e)}",
        }
    finally:
        # Cleanup
        if page:
            try:
                await page.close()
            except Exception as e:
                logger.debug(f"Page close failed: {e}", exc_info=True)
                # Continue - cleanup failures are non-critical
        if browser:
            try:
                await browser.close()
            except Exception as e:
                logger.debug(f"Browser close failed: {e}", exc_info=True)
                # Continue - cleanup failures are non-critical
        if playwright:
            try:
                await playwright.stop()
            except Exception as e:
                logger.debug(f"Playwright stop failed: {e}", exc_info=True)
                # Continue - cleanup failures are non-critical


def post_to_twitter_direct(content: str) -> Dict:
    """
    Post to Twitter using Playwright (wrapper for async function).
    
    Returns:
        Dict with 'success', 'tweet_id', 'url', 'error' keys
    """
    try:
        # Run async function
        return asyncio.run(post_to_twitter_playwright(content))
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to run Playwright: {str(e)}",
        }

