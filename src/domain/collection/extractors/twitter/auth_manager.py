import logging

logger = logging.getLogger(__name__)
"""Twitter Authentication Management"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from playwright.async_api import Browser, Page, async_playwright

from .twitter_cookies import TwitterCookieStore


class TwitterAuthManager:
    """Handles Twitter authentication and cookie management"""

    def __init__(
        self,
        username: str,
        password: str = None,
        cookie_file: str = None,
    ):
        self.username = username
        self.password = password
        self.cookie_file = cookie_file or f"config/cookies/twitter_cookies_{username}.json"
        self._cookie_store = TwitterCookieStore(self.cookie_file)
        self.is_authenticated = False

    async def authenticate(
        self, browser: Browser, max_retries: int = 3
    ) -> Optional[Page]:
        """Authenticate with Twitter and return authenticated page"""
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )

        page = await context.new_page()

        # Try cookie authentication first
        if await self._try_cookie_authentication(page):
            self.is_authenticated = True
            return page

        # Fall back to manual login if cookies don't work
        if self.password:
            for attempt in range(max_retries):
                try:
                    await self._manual_login(page)
                    self.is_authenticated = True
                    await self._refresh_and_save_cookies(page)
                    return page
                except Exception as e:
                    logger.error(f"❌ Login attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2)

        return None

    async def _try_cookie_authentication(self, page: Page) -> bool:
        """Try to authenticate using saved cookies"""
        try:
            # Check if we have valid cookies
            if not self._check_cookie_freshness():
                logger.warning(
                    "⚠️ Cookies are stale or missing, attempting to refresh..."
                )
                if not await self._auto_refresh_cookies_if_needed():
                    logger.error("❌ Could not refresh cookies, will need to log in")
                    return False

            # Load cookies
            cookies = self._cookie_store.load_cookies()
            if not cookies:
                return False

            # Validate cookie format
            if not self._validate_cookie_format():
                logger.error("❌ Cookie format validation failed")
                return False

            # Add cookies to browser context
            await page.context.add_cookies(cookies)

            # Test authentication by visiting Twitter
            await page.goto("https://twitter.com/home", wait_until="networkidle")

            # Check if we're authenticated
            await asyncio.sleep(3)

            # Look for signs of being logged in
            try:
                # Check for home timeline or logged-in elements
                authenticated_indicators = [
                    'div[data-testid="primaryColumn"]',
                    'a[aria-label="Home"]',
                    'div[data-testid="SideNav_AccountSwitcher_Button"]',
                    '[aria-label="Profile"]',
                ]

                for indicator in authenticated_indicators:
                    try:
                        element = await page.wait_for_selector(indicator, timeout=5000)
                        if element:
                            logger.info("✅ Successfully authenticated with cookies")
                            return True
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue

                # Check if redirected to login page
                if "login" in page.url.lower() or "i/flow/login" in page.url:
                    logger.error("❌ Cookies expired, need to re-authenticate")
                    return False

                # Check if we can access protected content
                try:
                    await page.goto(
                        "https://twitter.com/settings/account", wait_until="networkidle"
                    )
                    if "login" not in page.url.lower():
                        logger.info(
                            "✅ Successfully authenticated with cookies (verified via settings page)"
                        )
                        return True
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

                logger.warning(
                    "⚠️ Could not verify authentication status, but no login redirect detected"
                )
                return True

            except Exception as e:
                logger.error(f"❌ Error during cookie authentication check: {e}")
                return False

        except Exception as e:
            logger.error(f"❌ Cookie authentication failed: {e}")
            return False

    async def _manual_login(self, page: Page):
        """Perform manual login with username and password"""
        logger.info(f"🔐 Logging in as {self.username}...")

        # Go to Twitter login page
        await page.goto("https://twitter.com/i/flow/login", wait_until="networkidle")
        await asyncio.sleep(2)

        # Enter username
        username_input = await page.wait_for_selector(
            'input[name="text"]', timeout=10000
        )
        await username_input.fill(self.username)
        await asyncio.sleep(1)

        # Click Next button
        next_button = await page.wait_for_selector(
            'div[role="button"]:has-text("Next")', timeout=10000
        )
        await next_button.click()
        await asyncio.sleep(3)

        # Enter password
        try:
            password_input = await page.wait_for_selector(
                'input[name="password"]', timeout=10000
            )
            await password_input.fill(self.password)
            await asyncio.sleep(1)

            # Click Log in button
            login_button = await page.wait_for_selector(
                'div[role="button"]:has-text("Log in")', timeout=10000
            )
            await login_button.click()
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"⚠️ Password input failed: {e}")
            # Try alternative selectors
            try:
                password_input = await page.wait_for_selector(
                    'input[type="password"]', timeout=5000
                )
                await password_input.fill(self.password)
                await asyncio.sleep(1)

                login_button = await page.wait_for_selector(
                    '[data-testid="LoginForm_Login_Button"]', timeout=5000
                )
                await login_button.click()
                await asyncio.sleep(5)

            except Exception as e2:
                logger.error(f"❌ Alternative login also failed: {e2}")
                raise e2

        # Handle potential verification/challenges
        try:
            # Check for verification challenges
            if "challenge" in page.url.lower() or "verify" in page.url.lower():
                logger.warning(
                    "⚠️ Verification challenge detected - manual intervention may be required"
                )
                await asyncio.sleep(10)  # Give time for manual intervention
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Verify successful login
        await page.goto("https://twitter.com/home", wait_until="networkidle")
        await asyncio.sleep(3)

        # Check if login was successful
        if "login" not in page.url.lower():
            logger.info("✅ Login successful!")
        else:
            raise Exception("Login failed - still on login page")

    async def _refresh_and_save_cookies(self, page: Page) -> bool:
        """Refresh and save current cookies"""
        try:
            # Wait a bit for cookies to be set
            await asyncio.sleep(5)

            # Get all cookies from the current context
            cookies = await page.context.cookies()
            if not cookies:
                logger.warning("⚠️ No cookies found after login")
                return False

            # Filter for Twitter-related cookies only
            twitter_cookies = [
                cookie
                for cookie in cookies
                if "twitter.com" in cookie.get("domain", "")
            ]

            if not twitter_cookies:
                logger.warning("⚠️ No Twitter cookies found")
                return False

            # Save cookies
            self._cookie_store.save_cookies(twitter_cookies)
            logger.info(f"✅ Saved {len(twitter_cookies)} Twitter cookies")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save cookies: {e}")
            return False

    async def _auto_refresh_cookies_if_needed(self) -> bool:
        """Attempt to auto-refresh cookies using existing session"""
        try:
            # This is a placeholder for cookie refresh logic
            # In practice, this would involve using a headless browser
            # to refresh the session or using Twitter's API endpoints

            logger.warning(
                "⚠️ Auto cookie refresh not implemented - manual login required"
            )
            return False

        except Exception as e:
            logger.error(f"❌ Auto cookie refresh failed: {e}")
            return False

    def _check_cookie_freshness(self) -> bool:
        """Check if cookies are fresh enough"""
        try:
            cookies = self._cookie_store.load_cookies()
            if not cookies:
                return False

            # Look for auth_token and check its expiry
            auth_token = next(
                (c for c in cookies if c.get("name") == "auth_token"), None
            )
            if auth_token:
                # Cookies should be used within 24 hours for best results
                # This is a simplified check - in practice you'd want more sophisticated logic
                return True

            return False

        except Exception as e:
            logger.error(f"❌ Error checking cookie freshness: {e}")
            return False

    def _validate_cookie_format(self) -> bool:
        """Validate that cookies have the correct format"""
        try:
            cookies = self._cookie_store.load_cookies()
            if not cookies:
                return False

            required_fields = ["name", "value", "domain"]
            for cookie in cookies:
                for field in required_fields:
                    if field not in cookie:
                        logger.error(f"❌ Cookie missing required field: {field}")
                        return False

            # Check for essential Twitter cookies
            essential_cookies = ["auth_token", "ct0", "twid"]
            cookie_names = [c.get("name") for c in cookies]

            has_essential = any(
                essential in cookie_names for essential in essential_cookies
            )
            if not has_essential:
                logger.warning("⚠️ Missing essential Twitter cookies")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ Cookie format validation failed: {e}")
            return False
