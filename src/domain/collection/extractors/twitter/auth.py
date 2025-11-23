import logging

logger = logging.getLogger(__name__)
"""Twitter authentication - simple and reliable (matches Threads approach)"""

import asyncio
import json
import random
import re
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..twitter_cookies import TwitterCookieStore
from .utils import jitter


class TwitterAuth:
    """Handles Twitter authentication with cookies or password"""

    def __init__(
        self,
        username: str,
        password: Optional[str],
        cookie_store: TwitterCookieStore,
        headless: bool = False,
    ):
        self.username = username
        self.password = password
        self.cookie_store = cookie_store
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_authenticated = False

    async def authenticate(self, max_retries: int = 3) -> bool:
        """Authenticate with Twitter - tries cookies first, then password"""
        for attempt in range(max_retries):
            try:
                logger.warning(
                    f"🔄 Authentication attempt {attempt + 1}/{max_retries}..."
                )

                # Try cookie authentication first (uses persistent context)
                if await self._try_cookie_auth():
                    logger.info("✅ Cookie authentication successful")
                    self.is_authenticated = True
                    return True

                # Cookie auth failed - try password
                if not self.password:
                    logger.error("❌ No password provided and cookies failed")
                    return False

                if await self._try_password_auth():
                    logger.info("✅ Password authentication successful")
                    self.is_authenticated = True
                    return True

                return False

            except Exception as e:
                logger.error(f"❌ Authentication attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    return False

        return False

    async def _try_cookie_auth(self) -> bool:
        """Try cookie authentication - EXACT same approach as Threads extractor"""
        if not self.cookie_store.exists():
            logger.warning("⚠️  No cookie file found")
            return False

        try:
            cookie_path = self.cookie_store.path

            # Validate format
            if not self.cookie_store.validate():
                logger.warning("⚠️  Cookie file format invalid")
                return False

            logger.warning(
                "🍪 Attempting cookie authentication - PLAIN browser, no stealth..."
            )

            # PLAIN browser - nothing fancy
            if not self.playwright:
                self.playwright = await async_playwright().start()

            # Launch browser - DEFAULT settings only
            self.browser = await self.playwright.chromium.launch(headless=self.headless)

            # Check if cookies are in storage_state format
            try:
                with open(cookie_path, "r") as f:
                    data = json.load(f)
                is_storage_state = isinstance(data, dict) and (
                    "cookies" in data or "origins" in data
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                is_storage_state = False

            # Create context - PLAIN, no extra properties
            if is_storage_state:
                self.context = await self.browser.new_context(storage_state=cookie_path)
                logger.info("📱 Browser context created with storage_state")
            else:
                # Load cookies manually
                self.context = await self.browser.new_context()
                try:
                    with open(cookie_path, "r") as f:
                        cookie_data = json.load(f)
                    cookies = (
                        cookie_data.get("cookies", [])
                        if isinstance(cookie_data, dict)
                        else cookie_data
                    )
                    await self.context.add_cookies(cookies)
                    logger.info("📱 Browser context created, loaded cookies manually")
                except Exception as e:
                    logger.error(f"⚠️ Failed to load cookies: {e}")
                    return False

            # Create page - PLAIN
            self.page = await self.context.new_page()

            # Navigate - PLAIN
            await self.page.goto(
                "https://x.com/home", wait_until="domcontentloaded", timeout=60000
            )
            await asyncio.sleep(2)

            # Check for "Something went wrong" error
            try:
                page_text = await self.page.evaluate("document.body.innerText")
                if "something went wrong" in page_text.lower():
                    logger.error(
                        "❌ Twitter detected automation - showing 'Something went wrong'"
                    )
                    logger.info("   This means Twitter blocked the request")
                    logger.info("   Cookies may be banned or account flagged")
                    return False
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            # Check if logged in (simple check like Threads)
            current_url = self.page.url
            if "login" in current_url.lower():
                logger.error("❌ Redirected to login - cookies expired")
                return False

            # Check for timeline (optional - URL check is more reliable)
            try:
                await self.page.wait_for_selector(
                    '[data-testid="primaryColumn"]', timeout=25000
                )
                logger.info("✅ Found timeline - logged in")

                # Save fresh cookies (like Threads)
                await self.context.storage_state(path=str(cookie_path))
                logger.info(f"✅ Refreshed cookies: {cookie_path}")
                return True
            except Exception as e:
                # Not an error - selector might not be present, but URL check will confirm
                logger.debug(f"Timeline selector not found (this is OK): {e}")
                pass

            # Check URL (more reliable than selector)
            if "/home" in current_url:
                await self.context.storage_state(path=str(cookie_path))
                logger.info(f"✅ On home page - logged in, refreshed cookies")
                return True

            logger.error("❌ Could not verify login")
            return False

        except Exception as e:
            logger.error(f"❌ Cookie auth error: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _try_password_auth(self) -> bool:
        """Try password authentication"""
        try:
            # Create context if needed
            if not self.context:
                self.context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                )
                await self.context.add_init_script(
                    """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                """
                )

            if not self.page:
                self.page = await self.context.new_page()

            logger.info("🔑 Starting password login...")
            await jitter()
            await self.page.goto(
                "https://x.com/login", wait_until="domcontentloaded", timeout=60000
            )
            await jitter(300)

            # Enter username
            username_selector = 'input[name="text"], input[autocomplete="username"]'
            await self.page.wait_for_selector(username_selector, timeout=30000)
            await self.page.fill(username_selector, self.username)
            await jitter(300)
            await self.page.click('button:has-text("Next")')

            # Handle verification if needed
            try:
                verification = await self.page.wait_for_selector(
                    'input[data-testid="ocfEnterTextTextInput"]', timeout=5000
                )
                await verification.fill(self.username)
                await self.page.click('button:has-text("Next")')
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            # Enter password
            password_selector = (
                'input[name="password"], input[autocomplete="current-password"]'
            )
            await self.page.wait_for_selector(password_selector, timeout=30000)
            await self.page.fill(password_selector, self.password)

            # Click login
            await self.page.click('button[data-testid="LoginForm_Login_Button"]')
            await asyncio.sleep(3)

            # Verify login
            try:
                await self.page.wait_for_selector(
                    '[data-testid="primaryColumn"]', timeout=30000
                )
                logger.info("✅ Login successful")

                # Save cookies
                cookie_path = self.cookie_store.path
                self.cookie_store.ensure_parent_dir()
                await self.context.storage_state(path=str(cookie_path))
                logger.info(f"✅ Saved cookies: {cookie_path}")
                return True
            except Exception as e:
                current_url = self.page.url
                if "login" in current_url.lower():
                    logger.error("❌ Still on login page - authentication failed")
                    return False
                # Might be logged in but selector failed
                return True

        except Exception as e:
            logger.error(f"❌ Password auth error: {e}")
            return False

    async def close(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
