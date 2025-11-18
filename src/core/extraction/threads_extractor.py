from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import jmespath
from parsel import Selector
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from .social_extractor_base import SocialExtractorBase, SocialPost

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ThreadsExtractor(SocialExtractorBase):
    """
    Extractor for Threads.net. This extractor uses Playwright to load a thread's
    page and parse a hidden JSON data object to retrieve thread information.
    NOTE: This extractor ONLY supports scraping public posts by URL. It does not
    support fetching saved/bookmarked posts due to authentication complexities.
    """

    def __init__(self):
        super().__init__()
        self.platform_name = "threads"
        self.allowed_authors = self._load_allowed_handles()

    def _load_allowed_handles(self) -> set[str]:
        """
        Load allowed handles from environment variable.

        NOTE: THREADS_USERNAME is NOT automatically added to allowlist.
        It's only used for authentication. To filter by specific authors,
        explicitly set THREADS_ALLOWED_HANDLES (comma-separated).

        If THREADS_ALLOWED_HANDLES is not set, ALL posts are collected.
        """
        allowed = set()
        env_handles = os.getenv("THREADS_ALLOWED_HANDLES")
        if env_handles:
            for handle in env_handles.split(","):
                norm = self._normalize_handle(handle)
                if norm:
                    allowed.add(norm)
        # REMOVED: Don't auto-add THREADS_USERNAME to allowlist
        # THREADS_USERNAME is only for authentication, not filtering
        # If user wants to filter, they should set THREADS_ALLOWED_HANDLES explicitly
        return allowed

    def _register_allowed_handle(self, handle: Optional[str]) -> None:
        norm = self._normalize_handle(handle)
        if norm:
            self.allowed_authors.add(norm)

    @staticmethod
    def _normalize_handle(handle: Optional[str]) -> Optional[str]:
        if not handle:
            return None
        return handle.strip().lstrip("@").lower() or None

    def _extract_handle_from_url(self, url: str) -> Optional[str]:
        if "/@" not in url:
            return None
        try:
            return self._normalize_handle(url.split("/@")[1].split("/")[0])
        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def _is_allowed_handle(self, handle: Optional[str]) -> bool:
        if not self.allowed_authors:
            return True
        if not handle:
            return False
        return handle in self.allowed_authors

    def _warn_if_cookie_stale(self, cookies_path: str, max_hours: int = 36) -> None:
        try:
            file_age_hours = (time.time() - Path(cookies_path).stat().st_mtime) / 3600
            if file_age_hours > max_hours:
                logging.warning(
                    f"⚠️ Cookies are {file_age_hours:.0f} hours old - may need refresh"
                )
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

    def _ensure_storage_state_format(self, cookies_path: str) -> str:
        try:
            with open(cookies_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Error: {e}")
            return cookies_path

        if isinstance(data, dict) and ("cookies" in data or "origins" in data):
            return cookies_path

        if isinstance(data, list):
            converted: Dict[str, List[Dict[str, Any]]] = {"cookies": []}
            for cookie in data:
                if not isinstance(cookie, dict):
                    continue
                name = cookie.get("name")
                value = cookie.get("value")
                domain = cookie.get("domain")
                path_value = cookie.get("path", "/")
                if not all([name, value, domain]):
                    continue
                converted_cookie = {
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": path_value or "/",
                    "secure": cookie.get("secure", True),
                    "httpOnly": cookie.get("httpOnly", False),
                }
                expires = (
                    cookie.get("expires")
                    or cookie.get("expirationDate")
                    or cookie.get("expiry")
                )
                if expires:
                    try:
                        converted_cookie["expires"] = int(expires)
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass
                converted["cookies"].append(converted_cookie)
            try:
                with open(cookies_path, "w") as f:
                    json.dump(converted, f, indent=2)
                logging.info(
                    f"🪄 Converted {cookies_path} to storage_state format for reliability"
                )
            except Exception as convert_err:
                logging.warning(
                    f"⚠️ Failed to rewrite cookies file in storage_state format: {convert_err}"
                )

        return cookies_path

    async def authenticate(
        self,
        username: str,
        password: str,
        cookies_path: str = "cookies/threads_cookies.json",
    ) -> bool:
        """Authenticates the user by trying cookies first, then falling back to login."""
        try:
            logging.info(f"🔐 Starting Threads authentication process")
            logging.info(f"📁 Cookie file path: {cookies_path}")
            logging.info(f"👤 Username: {username}")
            logging.info(f"🔑 Password provided: {'Yes' if password else 'No'}")
            self._register_allowed_handle(username)

            if Path(cookies_path).exists():
                logging.info(f"🍪 Cookie file exists, attempting cookie authentication")
                file_size = Path(cookies_path).stat().st_size
                logging.info(f"📊 Cookie file size: {file_size} bytes")
                self._warn_if_cookie_stale(cookies_path)
                cookies_path = self._ensure_storage_state_format(cookies_path)

                if await self._authenticate_with_cookies(cookies_path):
                    logging.info("✅ Cookie authentication successful")
                    return True
                else:
                    logging.warning("❌ Cookie authentication failed")
            else:
                logging.warning(f"🍪 Cookie file not found at {cookies_path}")

            logging.info("🔄 Falling back to username/password login")
            return await self._authenticate_with_login(username, password, cookies_path)
        except Exception as e:
            logging.error(f"❌ Authentication process failed with exception: {e}")
            logging.error(f"❌ Exception type: {type(e).__name__}")
            import traceback

            logging.error(f"❌ Full traceback: {traceback.format_exc()}")
            return False

    async def _authenticate_with_cookies(self, cookies_path: str) -> bool:
        """Authenticates using cookies - SIMPLIFIED to match working test."""
        try:
            logging.info("🍪 Starting cookie-based authentication")

            self.pw = await async_playwright().start()
            self.browser = await self.pw.chromium.launch(headless=True)
            logging.info("🌐 Browser launched successfully")

            # Prefer detecting storage_state format; otherwise manually add cookies
            try:
                with open(cookies_path, "r") as _f:
                    _data = json.load(_f)
                is_storage_state = isinstance(_data, dict) and (
                    "cookies" in _data or "origins" in _data
                )
                logging.info(
                    f"📋 Cookie format detected: {'storage_state' if is_storage_state else 'raw/json'}"
                )
                if is_storage_state:
                    cookie_count = len(_data.get("cookies", []))
                    logging.info(
                        f"🍪 Found {cookie_count} cookies in storage_state format"
                    )
            except Exception as e:
                logging.warning(f"⚠️ Failed to read cookie file: {e}")
                is_storage_state = False

            if is_storage_state:
                # Load as storage_state
                self.context = await self.browser.new_context(
                    storage_state=cookies_path,
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                )
                logging.info("📱 Browser context created with storage_state")
            else:
                # Create context and load cookies manually (JSON jar or raw string)
                self.context = await self.browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                logging.info("📱 Browser context created, loading cookies manually")
                try:
                    self._load_json_cookies(self.context, cookies_path)
                    logging.info("✅ JSON cookies loaded successfully")
                except Exception as e:
                    logging.warning(f"⚠️ JSON cookie loading failed: {e}")
                    # Fall back to raw cookies format
                    self._load_raw_cookies(self.context, cookies_path)
                    logging.info("✅ Raw cookies loaded successfully")

            self.page = await self.context.new_page()
            logging.info("📄 New page created")

            # Go directly to saved posts – try threads.net first, then fallback to threads.com
            logging.info("🔍 Navigating to saved posts with cookies...")
            saved_urls = [
                "https://www.threads.net/saved",
                "https://www.threads.com/saved",
            ]
            auth_ok = False
            for saved_url in saved_urls:
                try:
                    logging.info(f"🌐 Trying URL: {saved_url}")
                    await self.page.goto(
                        saved_url, wait_until="domcontentloaded", timeout=20000
                    )
                    await asyncio.sleep(3)
                    current_url = self.page.url
                    logging.info(f"📍 Current URL after navigation: {current_url}")

                    if "login" not in current_url:
                        logging.info(
                            f"✅ Cookie authentication successful! URL: {current_url}"
                        )
                        auth_ok = True
                        break
                    else:
                        logging.warning(f"⚠️ Redirected to login page from {saved_url}")
                except Exception as nav_err:
                    logging.error(f"❌ Navigation failed for {saved_url}: {nav_err}")

            if not auth_ok:
                logging.warning(
                    "❌ Cookie auth failed to land on saved page; will require login."
                )
                return False

            return True

        except Exception as e:
            logging.error(f"❌ Cookie authentication failed: {e}")
            logging.error(f"❌ Exception type: {type(e).__name__}")
            import traceback

            logging.error(f"❌ Full traceback: {traceback.format_exc()}")
            if hasattr(self, "browser") and self.browser:
                await self.browser.close()
            if hasattr(self, "pw") and self.pw:
                await self.pw.stop()
            return False

    def _load_json_cookies(self, context, cookies_path: str):
        """Load cookies from JSON file"""
        try:
            with open(cookies_path, "r") as f:
                cookies_data = json.load(f)

            # Convert to Playwright cookie format
            playwright_cookies = []
            for cookie in cookies_data:
                playwright_cookie = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": cookie["domain"],
                    "path": cookie["path"],
                    "secure": cookie.get("secure", False),
                    "httpOnly": cookie.get("httpOnly", False),
                }

                # Add expiration if present
                if "expirationDate" in cookie and not cookie.get("session", False):
                    playwright_cookie["expires"] = cookie["expirationDate"]

                # Add sameSite if present and valid
                if cookie.get("sameSite") and cookie["sameSite"] in [
                    "Strict",
                    "Lax",
                    "None",
                ]:
                    playwright_cookie["sameSite"] = cookie["sameSite"]
                elif cookie.get("sameSite") == "no_restriction":
                    playwright_cookie["sameSite"] = "None"
                elif cookie.get("sameSite") == "lax":
                    playwright_cookie["sameSite"] = "Lax"

                playwright_cookies.append(playwright_cookie)

            # Add cookies to context
            context.add_cookies(playwright_cookies)
            logging.info(f"Loaded {len(playwright_cookies)} cookies from JSON")

        except Exception as e:
            logging.error(f"Failed to load JSON cookies: {e}")

    def _load_raw_cookies(self, context, cookies_path: str):
        """Load raw cookies from file"""
        try:
            with open(cookies_path, "r") as f:
                cookie_content = f.read().strip()

            # Parse cookies string
            cookies = []
            for cookie_pair in cookie_content.split("; "):
                if "=" in cookie_pair:
                    name, value = cookie_pair.split("=", 1)

                    # Add cookies for multiple domains since Threads uses Instagram infrastructure
                    for domain in [".threads.net", ".instagram.com", ".facebook.com"]:
                        cookies.append(
                            {
                                "name": name,
                                "value": value,
                                "domain": domain,
                                "path": "/",
                            }
                        )

            # Add cookies to context
            context.add_cookies(cookies)
            logging.info(f"Loaded {len(cookies)} cookies across multiple domains")

        except Exception as e:
            logging.error(f"Failed to load raw cookies: {e}")

    def _check_login_status(self, page) -> bool:
        """Check if user is logged in to Threads"""
        try:
            # Look for login indicators
            login_indicators = [
                'a[href="/login"]',
                'button:has-text("Log in")',
                'div:has-text("Log in")',
            ]

            for indicator in login_indicators:
                if page.query_selector(indicator):
                    return False

            # Look for logged-in indicators
            logged_in_indicators = [
                'nav[role="navigation"]',
                'svg[aria-label="Home"]',
                'a[href*="/profile"]',
                '[data-testid="primaryColumn"]',
            ]

            for indicator in logged_in_indicators:
                if page.query_selector(indicator):
                    return True

            return False

        except Exception as e:
            logging.error(f"Error checking login status: {e}")
            return False

    async def _authenticate_with_login(
        self, username: str, password: str, cookies_path: str
    ) -> bool:
        """Authenticates by logging directly into Threads.net."""
        try:
            logging.info("🔑 Starting username/password authentication")

            self.pw = await async_playwright().start()
            self.browser = await self.pw.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            logging.info("🌐 Navigating to Threads login page...")
            await self.page.goto(
                "https://www.threads.net/login", wait_until="domcontentloaded"
            )
            current_url = self.page.url
            logging.info(f"📍 Current URL after navigation: {current_url}")

            # Wait a bit for page to fully load
            await asyncio.sleep(3)

            # Try multiple selectors for username field on Threads
            username_selectors = [
                'input[name="username"]',
                'input[aria-label="Username"]',
                'input[placeholder*="username"]',
                'input[placeholder*="Username"]',
                'input[type="text"]',
                'input[aria-label="Phone number, username, or email"]',
            ]

            username_field = None
            for selector in username_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    username_field = selector
                    logging.info(f"Found username field with selector: {selector}")
                    break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not username_field:
                logging.error("Could not find username field")
                return False

            logging.info(f"Entering username: {username}")
            await self.page.fill(username_field, username)

            # Find password field
            password_selectors = [
                'input[name="password"]',
                'input[type="password"]',
                'input[aria-label="Password"]',
            ]

            password_field = None
            for selector in password_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=3000)
                    password_field = selector
                    logging.info(f"Found password field with selector: {selector}")
                    break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not password_field:
                logging.error("Could not find password field")
                return False

            await self.page.fill(password_field, password)

            logging.info("Clicking login button...")
            # Try multiple login button selectors for Threads
            login_button_selectors = [
                'button[type="submit"]',
                'div[role="button"]:has-text("Log in")',
                'button:has-text("Log in")',
                'div[role="button"]:has-text("Login")',
                'button:has-text("Login")',
                '[data-testid="loginButton"]',
                "button.x1i10hfl",  # Common Threads button class
                'div[role="button"].x1i10hfl',
            ]

            login_clicked = False
            for selector in login_button_selectors:
                try:
                    if await self.page.is_visible(selector, timeout=3000):
                        logging.info(f"Found login button with selector: {selector}")
                        await self.page.click(selector)
                        login_clicked = True
                        break
                except Exception as e:
                    logging.debug(f"Login button selector {selector} failed: {e}")
                    continue

            if not login_clicked:
                logging.error("Could not find or click login button")
                return False

            # Handle potential redirects and authentication flows
            try:
                # Wait for either successful login or onetap redirect
                await self.page.wait_for_load_state("networkidle", timeout=15000)

                # Check if we're on the onetap page or any challenge page
                current_url = self.page.url
                logging.info(f"Current URL after login: {current_url}")

                if (
                    "onetap" in current_url
                    or "challenge" in current_url
                    or "two_factor" in current_url
                ):
                    logging.info(
                        "Detected onetap/challenge/2FA page, handling redirect..."
                    )

                    # Try to find and click "Not Now" or skip buttons
                    skip_selectors = [
                        'button:has-text("Not Now")',
                        'button:has-text("Skip")',
                        'button:has-text("Maybe Later")',
                        '[role="button"]:has-text("Not Now")',
                        'a:has-text("Not Now")',
                        'button:has-text("Skip For Now")',
                        'button[type="button"]:has-text("Not now")',
                        '//button[contains(text(), "Not now")]',
                        '//button[contains(text(), "Skip")]',
                    ]

                    for selector in skip_selectors:
                        try:
                            if await self.page.is_visible(selector, timeout=3000):
                                logging.info(f"Clicking skip button: {selector}")
                                await self.page.click(selector)
                                await self.page.wait_for_load_state(
                                    "networkidle", timeout=8000
                                )
                                break
                        except Exception as skip_error:
                            logging.debug(
                                f"Skip selector {selector} failed: {skip_error}"
                            )
                            continue

                # Additional wait for page to stabilize
                await asyncio.sleep(2)

                # Wait for successful login indicators with extended timeout
                success_selectors = [
                    'a[href*="/profile"]',
                    'button[aria-label="Home"]',
                    'svg[aria-label="Home"]',
                    'a[href="/"]',  # Threads home link
                    '[aria-label="Home"]',
                    'nav[role="navigation"]',
                    'div[role="main"]',
                    'button[aria-label="Create"]',
                    'a[href*="@"]',  # Profile links
                ]

                login_success = False
                for selector in success_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        logging.info(f"Login successful - found element: {selector}")
                        login_success = True
                        break
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue

                if not login_success:
                    # Check if we're on Threads home page by URL
                    current_url = self.page.url
                    if "threads.net" in current_url and ("login" not in current_url):
                        logging.info("Login successful - on Threads home page")
                        login_success = True

                if not login_success:
                    raise Exception("Could not verify successful login")

            except Exception as e:
                logging.error(f"Login verification failed: {e}")
                # Take screenshot for debugging
                await self.page.screenshot(path="logs/threads_login_failure.png")
                return False

            logging.info("Successfully logged into Threads.")

            # Save the authentication state to the cookies file
            await self.context.storage_state(path=cookies_path)
            logging.info(f"Authentication state saved to {cookies_path}")
            # Also mirror to legacy path for compatibility
            legacy_path = "config/threads_cookies.json"
            try:
                await self.context.storage_state(path=legacy_path)
                logging.info(f"Authentication state mirrored to {legacy_path}")
            except Exception as legacy_err:
                logging.debug(
                    f"Could not mirror Threads cookies to legacy path: {legacy_err}"
                )

            return True
        except Exception as e:
            logging.error(f"Login authentication failed: {e}")
            try:
                await self.page.screenshot(path="logs/threads_login_failure.png")
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
            # Clean up browser on error
            if hasattr(self, "browser") and self.browser:
                await self.browser.close()
            if hasattr(self, "pw") and self.pw:
                await self.pw.stop()
            return False

    async def get_saved_posts(
        self,
        username: str = None,
        password: str = None,
        limit: int = 50,
        cookies_path: str = "cookies/threads_cookies.json",
        stop_at_post_id: Optional[str] = None,
        existing_ids: Optional[set] = None,
    ) -> List[SocialPost]:
        """
        Fetch saved/bookmarked Threads posts.
        If already authenticated (has self.page), uses existing session.
        Otherwise, authenticates with provided credentials.

        Direct link: https://www.threads.com/saved
        """
        logging.info("Fetching saved posts from Threads...")

        # Check if already authenticated
        if not (hasattr(self, "page") and self.page):
            logging.info("Not authenticated yet, authenticating now...")
            if not username or not password:
                logging.error("No credentials provided and not already authenticated")
                return []

            auth_success = await self.authenticate(username, password, cookies_path)
            if not auth_success:
                logging.error("Authentication failed, cannot fetch saved posts.")
                return []
        else:
            logging.info("Using existing authenticated session")

        posts = []
        try:
            page = self.page

            # Navigate to saved posts page - NEW STRATEGY: Go to home first, then navigate via UI
            logging.info("🏠 Navigating to home page first to ensure we're logged in...")
            await page.goto(
                "https://www.threads.com/", wait_until="domcontentloaded", timeout=20000
            )
            await page.wait_for_timeout(5000)

            # Wait for home page to load
            home_loaded = False
            for attempt in range(10):
                await page.wait_for_timeout(1000)
                has_content = await page.evaluate(
                    """
                    () => {
                        const body = document.body;
                        return body && body.children.length > 0;
                    }
                """
                )
                if has_content:
                    home_loaded = True
                    logging.info(f"✅ Home page loaded after {attempt + 1} seconds")
                    break

            if not home_loaded:
                logging.warning("⚠️ Home page did not load properly")

            # Now try to navigate to saved posts via UI or direct URL
            bookmarks_url = "https://www.threads.com/saved"
            logging.info(f"🔖 Navigating to saved posts: {bookmarks_url}")

            # Try clicking saved link first (if available)
            try:
                # Look for saved/bookmarks link in various places
                saved_selectors = [
                    'a[href*="/saved"]',
                    'a[href="/saved"]',
                    '[aria-label*="Saved"]',
                    '[aria-label*="saved"]',
                    'a:has-text("Saved")',
                    'a:has-text("saved")',
                    '[data-testid*="saved"]',
                    '[data-testid*="bookmark"]',
                ]
                saved_link = None
                for selector in saved_selectors:
                    try:
                        saved_link = await page.wait_for_selector(
                            selector, timeout=2000
                        )
                        if saved_link:
                            logging.info(
                                f"✅ Found saved link with selector: {selector}"
                            )
                            break
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue

                if saved_link:
                    await saved_link.click()
                    await page.wait_for_timeout(5000)
                    current_url = page.url
                    logging.info(f"✅ Clicked saved link, now at: {current_url}")
                else:
                    # Fallback: direct navigation
                    logging.info("🔗 Saved link not found, trying direct navigation...")
                    await page.goto(
                        bookmarks_url, wait_until="domcontentloaded", timeout=20000
                    )
                    await page.wait_for_timeout(3000)
            except Exception as nav_err:
                logging.debug(f"UI navigation failed, trying direct URL: {nav_err}")
                await page.goto(
                    bookmarks_url, wait_until="domcontentloaded", timeout=20000
                )
                await page.wait_for_timeout(3000)

            # Check final URL
            current_url = page.url
            logging.info(f"📍 After navigation, current URL: {current_url}")

            if (
                "login" in current_url.lower()
                or "accounts/login" in current_url.lower()
            ):
                logging.warning("⚠️ Redirected to login page - cookies may be expired")
                raise Exception("Not logged in - redirected to login page")

            # CRITICAL: Wait for /saved page to actually load content
            # Threads /saved page loads content very slowly and may need scrolling to trigger
            logging.info("⏳ Waiting for /saved page content to load...")

            # First, wait for basic page structure
            await page.wait_for_timeout(5000)

            # Try scrolling to trigger lazy loading (saved posts might be lazy-loaded)
            logging.info("📜 Scrolling to trigger content loading...")
            for scroll_attempt in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                await page.evaluate("window.scrollTo(0, 0)")  # Scroll back up
                await page.wait_for_timeout(1000)

            # Wait for network to be idle (content loaded)
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass  # Continue even if networkidle times out

            # Check if content has loaded
            max_wait_attempts = 15
            content_loaded = False
            for attempt in range(max_wait_attempts):
                await page.wait_for_timeout(1000)
                has_content = await page.evaluate(
                    """
                    () => {
                        const body = document.body;
                        // Check for various indicators of content
                        const hasDivs = body.querySelectorAll('div').length > 50;
                        const hasText = body.innerText.length > 200;
                        const hasLinks = body.querySelectorAll('a').length > 5;
                        const hasArticles = body.querySelectorAll('article').length > 0;
                        // Check for Threads-specific post containers
                        const hasPostContainers = body.querySelectorAll('[data-testid*="post"], [data-testid*="thread"], article').length > 0;
                        return hasDivs || (hasText && hasLinks) || hasArticles || hasPostContainers;
                    }
                """
                )
                if has_content:
                    content_loaded = True
                    logging.info(
                        f"✅ /saved page content loaded after {attempt + 1} seconds"
                    )
                    break
                # Try scrolling again every 3 seconds to trigger loading
                if attempt > 0 and attempt % 3 == 0:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(1000)
                    await page.evaluate("window.scrollTo(0, 0)")

            if not content_loaded:
                logging.warning(
                    "⚠️ /saved page content did not load after maximum wait time"
                )
                # Take a screenshot for debugging
                try:
                    await page.screenshot(
                        path="logs/threads_saved_empty.png", full_page=True
                    )
                    logging.info("📸 Screenshot saved: logs/threads_saved_empty.png")
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            await page.wait_for_timeout(2000)  # Extra wait for dynamic content

            # Final URL check - ensure we're on /saved page
            final_url = page.url
            logging.info(f"📍 Final URL before extraction: {final_url}")
            if "/saved" not in final_url and "login" not in final_url.lower():
                logging.warning(f"⚠️ Got redirected from /saved to: {final_url}")
                logging.info("🔄 Attempting to navigate back to /saved...")
                await page.goto(
                    bookmarks_url, wait_until="domcontentloaded", timeout=20000
                )
                await page.wait_for_timeout(5000)
                # Try scrolling again to trigger content
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(3000)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(2000)
                final_url = page.url
                logging.info(f"📍 After re-navigation, URL: {final_url}")

            # Extract post links by scrolling with improved incremental collection
            post_links = set()
            reached_stop_id = False
            consecutive_seen = 0
            scroll_attempts = 5

            logging.info(
                f"Scrolling to load saved posts (max {scroll_attempts} scrolls, stop_at: {stop_at_post_id or 'none'})..."
            )
            for i in range(scroll_attempts):
                # Wait a bit for content to load after scroll
                await page.wait_for_timeout(2000)

                # Use JavaScript evaluation to get links (handles React/JS-rendered content)
                links = []
                try:
                    # Primary method: JavaScript evaluation (most reliable for JS-rendered pages)
                    page_links = await page.evaluate(
                        """
                        () => {
                            const links = Array.from(document.querySelectorAll('a[href]'));
                            return links.map(a => a.href).filter(href => href && (href.includes('/post/') || href.includes('@') && href.includes('/post/')));
                        }
                    """
                    )
                    links.extend(page_links)
                except Exception as js_err:
                    logging.debug(f"JavaScript link extraction failed: {js_err}")

                # Fallback: HTML parsing (in case JS method fails)
                if not links:
                    try:
                        content = await page.content()
                        selector = Selector(content)
                        # Primary selector
                        links.extend(
                            selector.css('a[href*="/post/"]::attr(href)').getall()
                        )
                        # Alternative: links with @username/post pattern
                        links.extend(
                            href
                            for href in selector.css(
                                'a[href*="@"]::attr(href)'
                            ).getall()
                            if "/post/" in href
                        )
                        # Alternative: any link containing /post/
                        all_links = selector.css("a::attr(href)").getall()
                        links.extend([l for l in all_links if "/post/" in l])
                    except Exception as html_err:
                        logging.debug(f"HTML parsing failed: {html_err}")

                # Deduplicate and normalize
                links = list({link for link in links if "/post/" in link})
                before_count = len(post_links)

                # Debug: log what we found
                if i == 0:
                    logging.info(
                        f"🔍 First scroll: Found {len(links)} links with /post/ pattern"
                    )

                    # Always check page state on first scroll for debugging
                    try:
                        page_state = await page.evaluate(
                            """
                            () => {
                                return {
                                    url: window.location.href,
                                    title: document.title,
                                    bodyTextLength: document.body.innerText.length,
                                    allLinks: document.querySelectorAll('a').length,
                                    articles: document.querySelectorAll('article').length,
                                    divs: document.querySelectorAll('div').length,
                                    hasReactRoot: !!document.querySelector('[data-reactroot], #root, #__next'),
                                    bodyHTML: document.body.innerHTML.substring(0, 500)
                                };
                            }
                        """
                        )
                        logging.info(f"   📊 Page state: {page_state}")
                    except Exception as state_err:
                        logging.debug(f"   Page state check failed: {state_err}")

                    if len(links) == 0:
                        # Try to see what's actually on the page using Playwright (more reliable than HTML parsing)
                        try:
                            # Get all links using Playwright (handles JS-rendered content)
                            page_links = await page.evaluate(
                                """
                                () => {
                                    const links = Array.from(document.querySelectorAll('a[href]'));
                                    return links.map(a => a.href).filter(href => href && href.includes('/post/'));
                                }
                            """
                            )
                            if page_links:
                                logging.info(
                                    f"   ✅ Found {len(page_links)} post links via JavaScript evaluation"
                                )
                                links = page_links
                            else:
                                # Try to find any clickable elements that might be posts
                                all_clickable = await page.evaluate(
                                    """
                                    () => {
                                        const elements = Array.from(document.querySelectorAll('a, [role="link"], [data-testid*="post"], [data-testid*="thread"]'));
                                        return elements.map(el => ({
                                            tag: el.tagName,
                                            href: el.href || el.getAttribute('href') || '',
                                            text: el.innerText?.substring(0, 50) || '',
                                            testid: el.getAttribute('data-testid') || ''
                                        })).slice(0, 10);
                                    }
                                """
                                )
                                logging.info(
                                    f"   🔍 Page analysis: Found {len(all_clickable)} potentially relevant elements"
                                )
                                if all_clickable:
                                    logging.info(
                                        f"   Sample elements: {all_clickable[:3]}"
                                    )

                                # Also try to get page text to see if content is there
                                page_text = await page.evaluate(
                                    "document.body.innerText"
                                )
                                if page_text:
                                    text_length = len(page_text.strip())
                                    logging.info(
                                        f"   Page has {text_length} characters of text content"
                                    )
                                    if text_length < 100:
                                        logging.warning(
                                            "   ⚠️ Page appears mostly empty - may not be loaded or not logged in"
                                        )

                                # Try to find Threads-specific post containers
                                post_containers = await page.evaluate(
                                    """
                                    () => {
                                        // Look for common Threads post container patterns
                                        const containers = [];
                                        // Try data-testid attributes
                                        const testid_elements = document.querySelectorAll('[data-testid]');
                                        testid_elements.forEach(el => {
                                            const testid = el.getAttribute('data-testid');
                                            if (testid && (testid.includes('post') || testid.includes('thread') || testid.includes('item'))) {
                                                containers.push({
                                                    testid: testid,
                                                    tag: el.tagName,
                                                    hasLinks: el.querySelectorAll('a').length,
                                                    text: el.innerText?.substring(0, 100) || ''
                                                });
                                            }
                                        });
                                        // Also try article tags (common for social posts)
                                        const articles = document.querySelectorAll('article');
                                        articles.forEach(el => {
                                            containers.push({
                                                testid: 'article',
                                                tag: 'ARTICLE',
                                                hasLinks: el.querySelectorAll('a').length,
                                                text: el.innerText?.substring(0, 100) || ''
                                            });
                                        });
                                        return containers.slice(0, 5);
                                    }
                                """
                                )
                                if post_containers:
                                    logging.info(
                                        f"   📦 Found {len(post_containers)} potential post containers"
                                    )
                                    logging.info(
                                        f"   Sample containers: {post_containers[:2]}"
                                    )

                                # Check if page says "No saved posts" or similar
                                page_html_snippet = await page.evaluate(
                                    "document.body.innerHTML.substring(0, 2000)"
                                )
                                if (
                                    "no saved" in page_html_snippet.lower()
                                    or "no bookmarks" in page_html_snippet.lower()
                                ):
                                    logging.info("   ℹ️ Page indicates no saved posts")
                                elif "saved" in page_html_snippet.lower():
                                    logging.info(
                                        "   ℹ️ Page mentions 'saved' - content may be loading"
                                    )
                        except Exception as debug_err:
                            logging.debug(f"   Debug evaluation failed: {debug_err}")

                        # Fallback: try HTML parsing
                        all_a_tags = selector.css("a::attr(href)").getall()
                        logging.info(
                            f"   HTML parsing: Total <a> tags on page: {len(all_a_tags)}"
                        )
                        if all_a_tags:
                            sample = all_a_tags[:5]
                            logging.info(f"   Sample links: {sample}")

                # Process links in the order they appear (newest should appear first in DOM)
                for link in links:
                    if not link.startswith("http"):
                        link = f"https://www.threads.net{link}"

                    # Extract post code from URL
                    try:
                        code = link.strip("/").split("/")[-1]
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        code = None

                    # Skip if we can't extract a valid code
                    if not code:
                        continue

                    # Allowlist filtering removed - collect all posts
                    # (If filtering is needed, it can be done at the database level)

                    # Early-stop: if this link corresponds to the last collected id, break
                    if stop_at_post_id and code and code == stop_at_post_id:
                        reached_stop_id = True
                        logging.info(f"🛑 Reached stop_at_post_id: {stop_at_post_id}")
                        post_links.add(link)
                        break

                    # Duplicate detection vs existing IDs - improved logic
                    # NOTE: Don't stop on first duplicate - saved posts may not be in strict chronological order
                    # Continue collecting to find all new posts, even if some duplicates are mixed in
                    if existing_ids and code and (code in existing_ids):
                        consecutive_seen += 1
                        logging.debug(
                            f"   Found existing post ID: {code} (duplicate {consecutive_seen})"
                        )
                        # Only stop if we see many consecutive duplicates (5+) indicating we've reached the end
                        # This allows for some duplicates mixed in with new posts
                        if consecutive_seen >= 5:
                            reached_stop_id = True
                            logging.info(
                                f"🛑 Found {consecutive_seen} consecutive duplicates - likely reached end of new posts"
                            )
                            break
                        # Skip adding duplicate to post_links but continue processing
                        continue
                    else:
                        # Found a new post - reset consecutive duplicate counter
                        if consecutive_seen > 0:
                            logging.info(
                                f"   ✅ Found new post after {consecutive_seen} duplicates: {code}"
                            )
                        consecutive_seen = 0
                    post_links.add(link)

                new_found = len(post_links) - before_count
                logging.info(
                    f"  Scroll {i+1}/{scroll_attempts}: Found {new_found} new posts (total: {len(post_links)})"
                )
                if reached_stop_id:
                    logging.info("🛑 Detected stop condition - stopping early")
                    break

                # Keep consecutive check as a fallback
                if consecutive_seen >= 1 and len(post_links) >= 1:
                    logging.info("🛑 Consecutive duplicates detected - stopping early")
                    break

                # Scroll down
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)

                # Stop if we found enough
                if len(post_links) >= limit:
                    logging.info(f"Reached limit of {limit} posts")
                    break

            if not post_links:
                logging.warning(
                    "No saved post links found. Either no saved posts exist or page structure changed."
                )
                return []

            # Filter out already-seen before scraping - improved duplicate detection
            filtered = []
            duplicate_count = 0
            seen_codes = set()  # Track codes to avoid duplicates within this batch

            for u in post_links:
                try:
                    c = u.strip("/").split("/")[-1]
                except Exception as e:
                    logger.error(f"Error: {e}")
                    c = None

                # Skip if already seen in this batch (deduplicate within batch)
                if c and c in seen_codes:
                    duplicate_count += 1
                    logging.debug(f"Skipping duplicate within batch: {c}")
                    continue

                # Skip if already exists in DB
                if existing_ids and c and (c in existing_ids):
                    duplicate_count += 1
                    logging.debug(f"Skipping duplicate post ID: {c}")
                    continue

                # Add to filtered list and track as seen
                if c:
                    seen_codes.add(c)
                    filtered.append(u)

            # Limit to requested number
            urls_to_scrape = filtered[:limit]
            logging.info(
                f"Found {len(post_links)} total, {len(filtered)} new, {duplicate_count} duplicates; will scrape {len(urls_to_scrape)}"
            )

            # Refresh and save cookies/state for future sessions
            try:
                if hasattr(self, "context") and self.context:
                    await self.context.storage_state(path=cookies_path)
                    logging.info(
                        f"✅ Refreshed and saved browser state to {cookies_path}"
                    )
                    # Mirror to legacy config path
                    legacy_path = "config/threads_cookies.json"
                    try:
                        await self.context.storage_state(path=legacy_path)
                        logging.info(f"✅ Also mirrored browser state to {legacy_path}")
                    except Exception as legacy_err:
                        logging.debug(
                            f"Could not mirror Threads cookies to legacy path: {legacy_err}"
                        )
            except Exception as _save_err:
                logging.debug(f"Could not save Threads cookies: {_save_err}")

            # Scrape the posts using a fresh lightweight context; keep auth session open
            return await self.scrape_posts_from_urls_async(urls_to_scrape)

        except Exception as e:
            logging.error(f"Failed to get saved posts: {e}")
            # Clean up browser on error
            if hasattr(self, "browser") and self.browser:
                await self.browser.close()
            if hasattr(self, "pw") and self.pw:
                await self.pw.stop()
            return []

    async def scrape_posts_from_urls_async(
        self, urls: List[str], max_retries: int = 3
    ) -> List[SocialPost]:
        """
        Async version of scrape_posts_from_urls for use within async context.
        Improved with isolated page instances, better error handling, and connection pooling.
        """
        posts = []
        seen_post_ids = set()  # Track post IDs to avoid duplicates

        # Process URLs in smaller batches to avoid overwhelming the server
        batch_size = 5  # Process 5 URLs at a time
        url_batches = [
            urls[i : i + batch_size] for i in range(0, len(urls), batch_size)
        ]

        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            # Reuse storage state if available for more consistent rendering
            context_kwargs = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "locale": "en-US",
            }
            try:
                if hasattr(self, "context") and self.context:
                    state = await self.context.storage_state()
                    context = await browser.new_context(
                        storage_state=state, **context_kwargs
                    )
                else:
                    context = await browser.new_context(**context_kwargs)
            except Exception as e:
                logging.warning(
                    f"Failed to use storage state, creating fresh context: {e}"
                )
                context = await browser.new_context(**context_kwargs)

            # Process each batch with connection pooling
            for batch_idx, batch in enumerate(url_batches):
                logging.info(
                    f"Processing batch {batch_idx + 1}/{len(url_batches)} with {len(batch)} URLs"
                )

                # Create a semaphore to limit concurrent connections
                semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests

                async def process_single_url(url):
                    post = None
                    for attempt in range(max_retries):
                        page = None
                        try:
                            logging.info(
                                f"Scraping thread: {url} (Attempt {attempt + 1}/{max_retries})"
                            )

                            # Create a fresh page for each attempt
                            page = await context.new_page()

                            # Set reasonable timeouts with longer values for reliability
                            page.set_default_timeout(45000)  # 45 seconds
                            page.set_default_navigation_timeout(60000)  # 60 seconds

                            post = await self._scrape_thread_data_async(url, page)
                            if post:
                                return post  # Success, return immediately
                        except Exception as e:
                            error_msg = str(e)
                            logging.error(
                                f"Failed to scrape {url} on attempt {attempt + 1}: {error_msg}"
                            )

                            # Check for specific context/browser errors
                            is_context_error = any(
                                phrase in error_msg.lower()
                                for phrase in [
                                    "target page, context or browser has been closed",
                                    "connection closed while reading from driver",
                                    "context has been closed",
                                    "browser has been closed",
                                    "connection closed",
                                    "page.goto: target closed",
                                    "page.goto: net::err_aborted",
                                    "page.goto: timeout",
                                ]
                            )

                            if attempt >= max_retries - 1:
                                logging.error(
                                    f"All retries failed for {url}. Final error: {error_msg}"
                                )
                                try:
                                    if page:
                                        await page.screenshot(
                                            path=f"debug_scrape_failed_{url.split('/')[-1]}.png"
                                        )
                                except Exception as screenshot_error:
                                    logging.error(
                                        f"Failed to save screenshot: {screenshot_error}"
                                    )
                                return None  # Return None on final failure
                            else:
                                # For context errors, wait longer before retry
                                if is_context_error:
                                    wait_time = 5 * (
                                        attempt + 1
                                    )  # Longer backoff for context issues
                                    logging.info(
                                        f"Context error detected, waiting {wait_time}s before retry..."
                                    )
                                    await asyncio.sleep(wait_time)
                                else:
                                    await asyncio.sleep(
                                        3 * (attempt + 1)
                                    )  # Standard exponential backoff
                        finally:
                            # Always close the page to prevent resource leaks
                            if page:
                                try:
                                    await page.close()
                                except Exception as close_error:
                                    logging.debug(f"Error closing page: {close_error}")
                    return None  # Return None if all retries failed

                # Process URLs in the batch concurrently with semaphore limiting
                async def process_with_semaphore(url):
                    async with semaphore:
                        return await process_single_url(url)

                tasks = [process_with_semaphore(url) for url in batch]
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                # Collect successful results from this batch
                for result in batch_results:
                    if isinstance(result, Exception):
                        logging.error(f"Batch processing error: {result}")
                    elif result is not None:  # Only add non-None results
                        # Check for duplicates by post_id
                        post_id = getattr(result, "post_id", None)
                        if post_id and post_id not in seen_post_ids:
                            seen_post_ids.add(post_id)
                            posts.append(result)
                            logging.debug(f"Added new post: {post_id}")
                        elif post_id:
                            logging.debug(f"Skipping duplicate post: {post_id}")

                # Add delay between batches to avoid rate limiting
                if batch_idx < len(url_batches) - 1:
                    await asyncio.sleep(2)  # 2 second delay between batches

            await browser.close()
        return posts

    def scrape_posts_from_urls(
        self, urls: List[str], max_retries: int = 3
    ) -> List[SocialPost]:
        """
        Scrapes multiple Threads posts from a given list of URLs with retries.
        Updated with isolated page instances, better error handling, and batching.
        """
        posts = []
        seen_post_ids = set()  # Track post IDs to avoid duplicates

        # Process URLs in smaller batches to avoid overwhelming the server
        batch_size = 5  # Process 5 URLs at a time
        url_batches = [
            urls[i : i + batch_size] for i in range(0, len(urls), batch_size)
        ]

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width": 1920, "height": 1080})

            # Process each batch with connection pooling
            for batch_idx, batch in enumerate(url_batches):
                logging.info(
                    f"Processing batch {batch_idx + 1}/{len(url_batches)} with {len(batch)} URLs"
                )

                # Process URLs in the batch sequentially (sync version)
                for url in batch:
                    post = None
                    for attempt in range(max_retries):
                        page = None
                        try:
                            logging.info(
                                f"Scraping thread: {url} (Attempt {attempt + 1}/{max_retries})"
                            )

                            # Create a fresh page for each attempt
                            page = context.new_page()

                            # Set reasonable timeouts with longer values for reliability
                            page.set_default_timeout(45000)  # 45 seconds
                            page.set_default_navigation_timeout(60000)  # 60 seconds

                            try:
                                post = self._scrape_thread_data(url, page)
                                if post:
                                    # Check for duplicates by post_id
                                    post_id = getattr(post, "post_id", None)
                                    if post_id and post_id not in seen_post_ids:
                                        seen_post_ids.add(post_id)
                                        posts.append(post)
                                        logging.debug(f"Added new post: {post_id}")
                                    elif post_id:
                                        logging.debug(
                                            f"Skipping duplicate post: {post_id}"
                                        )
                                    break  # Success, move to next URL
                            except Exception as scrape_error:
                                error_msg = str(scrape_error)
                                logging.error(
                                    f"Failed to scrape {url} on attempt {attempt + 1}: {error_msg}"
                                )

                                # Check for specific context/browser errors
                                is_context_error = any(
                                    phrase in error_msg.lower()
                                    for phrase in [
                                        "target page, context or browser has been closed",
                                        "connection closed while reading from driver",
                                        "context has been closed",
                                        "browser has been closed",
                                        "connection closed",
                                        "page.goto: target closed",
                                        "page.goto: timeout",
                                    ]
                                )

                                if attempt >= max_retries - 1:
                                    logging.error(
                                        f"All retries failed for {url}. Final error: {error_msg}"
                                    )
                                    try:
                                        if page:
                                            page.screenshot(
                                                path=f"debug_scrape_failed_{url.split('/')[-1]}.png"
                                            )
                                    except Exception as screenshot_error:
                                        logging.error(
                                            f"Failed to save screenshot: {screenshot_error}"
                                        )
                                else:
                                    # For context errors, wait longer before retry
                                    if is_context_error:
                                        wait_time = 5 * (
                                            attempt + 1
                                        )  # Longer backoff for context issues
                                        logging.info(
                                            f"Context error detected, waiting {wait_time}s before retry..."
                                        )
                                        time.sleep(wait_time)
                                    else:
                                        time.sleep(
                                            3 * (attempt + 1)
                                        )  # Standard exponential backoff
                        finally:
                            # Always close the page to prevent resource leaks
                            if page:
                                try:
                                    page.close()
                                except Exception as close_error:
                                    logging.debug(f"Error closing page: {close_error}")

                # Add delay between batches to avoid rate limiting
                if batch_idx < len(url_batches) - 1:
                    time.sleep(2)  # 2 second delay between batches

            browser.close()
        return posts

    async def get_liked_posts(self, limit: int = 100) -> List[SocialPost]:
        """
        Get liked posts from Threads. Currently not supported.
        """
        raise NotImplementedError("Threads API does not support retrieving liked posts")

    def _parse_thread_data(self, data: Dict) -> Optional[SocialPost]:
        """
        Parses the JSON data for a single thread post and maps it to the SocialPost dataclass.
        """
        result = jmespath.search(
            """{
            text: post.caption.text,
            published_on: post.taken_at,
            id: post.id,
            pk: post.pk,
            code: post.code,
            username: post.user.username,
            author_handle: post.user.username,
            images: post.carousel_media[].image_versions2.candidates[1].url,
            videos: post.video_versions[].url
        }""",
            data,
        )
        if not result or not result.get("id"):
            return None

        post_url = (
            f"https://www.threads.net/@{result['username']}/post/{result['code']}"
        )
        created_at_dt = datetime.fromtimestamp(result["published_on"], tz=timezone.utc)

        # Engagement data can be nested differently, so we search for it
        like_count = jmespath.search("post.like_count", data) or 0
        reply_count_str = jmespath.search("view_replies_cta_string", data)
        reply_count = 0
        if reply_count_str and isinstance(reply_count_str, str):
            try:
                reply_count = int(reply_count_str.split(" ")[0])
            except (ValueError, IndexError):
                reply_count = 0

        media_urls = list(set(result.get("videos") or []))
        if result.get("images"):
            media_urls.extend(result["images"])

        return SocialPost(
            platform=self.platform_name,
            post_id=result["id"],
            author=result["username"],
            author_handle=result["author_handle"],
            content=result.get("text", ""),
            created_at=created_at_dt,
            url=post_url,
            post_type="post",
            media_urls=media_urls,
            engagement={
                "likes": like_count,
                "replies": reply_count,
            },
        )

    async def _scrape_thread_data_async(
        self, url: str, page, force_dom: bool = False
    ) -> Optional[SocialPost]:
        """
        Async version of _scrape_thread_data for use within async context.
        Updated to work with isolated page instances.
        """
        try:

            def _sanitize_threads_content(raw: str):
                """Reduce Threads content to the original post text.
                - Remove 'Translate' duplicates
                - Drop likely comments/replies and noisy lines (usernames-only, short interjections)
                - Remove UI artifacts (pagination like 1/3, username/time blocks like 'yeraly.ndr', 'AI Threads', '1d')
                - De-duplicate repeated sentences
                - Collapse whitespace and limit to first 800 chars
                """
                if not raw:
                    return raw, None, None
                import re

                def _strip_thread_marker(text: str):
                    pattern = re.compile(
                        r"(.*?)(?:\s+|\n|\r)(\d+)\s*/\s*(\d+)\s*$", re.DOTALL
                    )
                    match = pattern.match(text)
                    if match:
                        base = match.group(1).rstrip()
                        part = int(match.group(2))
                        total = int(match.group(3))
                        if 0 < part <= total <= 50:
                            return base, part, total
                    return text, None, None

                thread_part = None
                thread_total = None
                text = raw
                # Detect thread marker before cleaning (e.g., "1/7")
                try:
                    marker_match = re.search(r"(\d+)\s*/\s*(\d+)", text)
                    if marker_match:
                        part = int(marker_match.group(1))
                        total = int(marker_match.group(2))
                        if 0 < part <= total <= 50:
                            thread_part = part
                            thread_total = total
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                # Preserve Translate markers and pagination for thread segmentation
                # Remove short time markers like "1d", "2h"
                text = re.sub(r"\b\d+\s*[dhm]\b", " ", text, flags=re.I)
                # Split into lines/segments, filter
                segs = re.split(r"[\n\r]+|\s{2,}", text)
                cleaned = []
                seen = set()
                footer_phrases = (
                    "log in to see more replies",
                    "log in or sign up for threads",
                    "see what people are talking about",
                    "join the conversation",
                    "continue with instagram",
                    "log in with username instead",
                    "threads terms",
                    "privacy policy",
                    "cookies policy",
                    "report a problem",
                )
                for s in segs:
                    t = s.strip()
                    if not t:
                        continue
                    # Drop short noise, pure usernames, or domain-only embeds
                    if len(t) < 6:
                        continue
                    lowered = t.lower()
                    if any(phrase in lowered for phrase in footer_phrases):
                        continue
                    if lowered in ("log in", "learn more", "terms"):
                        continue
                    if re.fullmatch(r"@\w+", t):
                        continue
                    # Drop likely username/display-name blocks without @ and with dots/underscores
                    if re.fullmatch(r"[A-Za-z0-9._-]{3,32}", t):
                        continue
                    # Drop section labels
                    if t.lower() in ("ai threads", "threads", "original", "more"):
                        continue
                    if re.fullmatch(r"[\w.-]+\.(com|net|org|io|ai)(/.*)?", t, re.I):
                        continue
                    # Drop obvious comment markers
                    if t.startswith("=== ") or t.lower().startswith(
                        "top valuable comments"
                    ):
                        break
                    # De-duplicate segments
                    if t in seen:
                        continue
                    seen.add(t)
                    cleaned.append(t)
                # Heuristic: keep only the first 2-3 sentences of the main post
                main = " ".join(cleaned)
                # Sentence-level de-duplication
                sentences = re.split(r"(?<=[\.!?…])\s+", main)
                uniq_sent = []
                seen_sent = set()
                for sent in sentences:
                    s = sent.strip()
                    if not s:
                        continue
                    key = re.sub(r"\s+", " ", s.lower())
                    if key in seen_sent:
                        continue
                    seen_sent.add(key)
                    uniq_sent.append(s)
                main = " ".join(uniq_sent)
                # Aggressive comment detection: stop at ANY comment/reply indicator
                comment_patterns = [
                    r"(?i)(comments?:|replies?:|top valuable)",
                    r"💬",
                    r"^\s*@\w+\s*:",
                    r"(?i)^(reply|comment)\s*:",
                    r"^\d+\s*(comment|reply|replies)",
                    r"Show all comments",
                    r"View \d+ replies",
                    r"Reply to",
                    r"Replying to",
                ]
                import re

                earliest_comment = len(main)
                for pattern in comment_patterns:
                    match = re.search(pattern, main, re.IGNORECASE | re.MULTILINE)
                    if match:
                        earliest_comment = min(earliest_comment, match.start())

                # Cut off at comment markers (keep at least 30 chars before comment to avoid over-truncation)
                if earliest_comment < len(main) and earliest_comment > 30:
                    main = main[:earliest_comment].strip()

                # Also check for simple text markers
                cut_markers = [
                    "💬",
                    "Comments:",
                    "TOP VALUABLE COMMENTS",
                    "Score:",
                    "Reply:",
                    "Replies:",
                    "Show all",
                    "View replies",
                    "Replying to",
                ]
                for m in cut_markers:
                    idx = main.find(m)
                    if idx > 100:  # Keep at least 100 chars before marker
                        main = main[:idx]
                        break
                # Strip leading username prefix like "handle " or "handle:"
                main = re.sub(r"^([A-Za-z0-9._-]{2,32})\s*[:•\-–—]\s+", "", main)
                # If it still starts with a lone username token, drop it
                main = re.sub(r"^[A-Za-z0-9._-]{2,32}\s+", "", main)

                # Extract sequential thread segments based on Translate markers (e.g., "Translate 2/7")
                thread_pattern = re.compile(
                    r"(?i)(.*?)(?:Translate\s+(\d+)\s*/\s*(\d+))", re.DOTALL
                )
                thread_segments = []
                current_total = None
                expected_part = 1

                for match in thread_pattern.finditer(main):
                    segment = match.group(1).strip()
                    part = int(match.group(2))
                    total = int(match.group(3))

                    if current_total is None:
                        current_total = total
                    elif total != current_total:
                        break

                    if part < expected_part:
                        continue

                    if segment:
                        first_token = segment.split()[0] if segment.split() else ""
                        if not first_token.startswith("@") and not re.match(
                            r"^[\w\.-]+__", first_token
                        ):
                            thread_segments.append(segment)

                    expected_part = part + 1
                    if part >= total:
                        break

                if thread_segments:
                    main = " ".join(thread_segments).strip()
                else:
                    translate_marker = re.search(
                        r"Translate\s+\d+\s*/\s*\d+", main, re.IGNORECASE
                    )
                    if translate_marker:
                        main = main[: translate_marker.start()].rstrip()

                # Normalize spaces
                main = re.sub(r"\s+", " ", main).strip()
                # Remove leftover Translate keywords
                main = re.sub(r"\bTranslate\b", "", main, flags=re.IGNORECASE).strip()
                main, tail_part, tail_total = _strip_thread_marker(main)
                if (
                    tail_part
                    and tail_total
                    and (thread_part is None or thread_total is None)
                ):
                    thread_part, thread_total = tail_part, tail_total
                return (
                    main[:4000],
                    thread_part,
                    thread_total,
                )  # Increased from 800 to 4000

            def _looks_truncated(original: str, cleaned: str) -> bool:
                """Heuristic to detect if sanitized content may be truncated."""
                original = (original or "").strip()
                cleaned = (cleaned or "").strip()
                original_len = len(original)
                cleaned_len = len(cleaned)
                if cleaned_len == 0:
                    return original_len > 0
                if original_len == 0:
                    return False
                ellipsis_flag = cleaned.endswith(("...", "…"))
                large_gap = original_len > cleaned_len + 200 and cleaned_len < 600
                ratio_gap = (cleaned_len / original_len) < 0.45
                return (ellipsis_flag and large_gap) or (large_gap and ratio_gap)

            # Extract post code from URL for ID and normalize /media suffix
            parts = url.strip("/").split("/")
            post_code = parts[-1]
            if post_code == "media" and len(parts) >= 2:
                post_code = parts[-2]
                # Canonicalize URL without /media
                url = "/".join(parts[:-1])

            logging.info(f"Scraping Threads post: {post_code}")

            # Validate page is still active before navigation
            if not page or page.is_closed():
                raise Exception("Page is closed or invalid before navigation")

            # Navigate to the post with better error handling
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=40000)
            except Exception as nav_error:
                logging.warning(
                    f"Initial navigation failed: {nav_error}, trying with networkidle"
                )
                try:
                    await page.goto(url, wait_until="networkidle", timeout=40000)
                except Exception as nav_error2:
                    logger.error(f"Error: {e}")
                    raise Exception(f"Navigation failed completely: {nav_error2}")

            try:
                # Wait for article/main to appear (robust wait)
                await page.wait_for_selector(
                    'article, [role="article"], div[role="main"]', timeout=8000
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                await page.wait_for_timeout(2000)

            # Note: Threads doesn't use "See more" buttons like Twitter/X - posts are fully displayed by default

            # BEST METHOD: Extract from JSON-LD (most reliable and complete!)
            content = ""
            author = "Unknown Author"
            author_handle = "unknown"

            # CRITICAL: Extract author from URL FIRST as baseline (before any extraction)
            # This ensures we always have a fallback even if DOM selectors fail
            try:
                # URL format: https://www.threads.net/@username/post/code
                url_parts = url.split("/@")
                if len(url_parts) > 1:
                    user_and_rest = url_parts[1]
                    username = user_and_rest.split("/")[0]
                    if username:
                        author_handle = username  # Set as baseline
                        author = username  # Set as baseline
                        logging.debug(f"Set author baseline from URL: @{author_handle}")
            except Exception as e:
                logging.debug(f"URL-based author extraction (baseline) failed: {e}")

            # Priority 1: Try JSON-LD structured data
            try:
                json_ld_scripts = await page.query_selector_all(
                    'script[type="application/ld+json"]'
                )
                for script in json_ld_scripts:
                    try:
                        script_content = await script.inner_text()
                        if script_content:
                            import json

                            data = json.loads(script_content)
                            # Look for articleBody or text
                            if isinstance(data, dict):
                                article_body = (
                                    data.get("articleBody") or data.get("text") or ""
                                )
                                if article_body and len(article_body) > 20:
                                    content = article_body.strip()
                                    # Also try to get author from JSON-LD (only if better than baseline)
                                    author_data = data.get("author", {})
                                    if isinstance(author_data, dict):
                                        author_name = (
                                            author_data.get("name")
                                            or author_data.get("alternateName")
                                            or ""
                                        )
                                        # Only update if we found a valid author name (not generic)
                                        if author_name and author_name not in (
                                            "Thread",
                                            "Unknown Author",
                                            "Unknown",
                                        ):
                                            author = author_name
                                    # Try to extract handle from URL in JSON-LD
                                    json_url = data.get("url", "")
                                    if json_url and "/@" in json_url:
                                        url_parts = json_url.split("/@")
                                        if len(url_parts) > 1:
                                            handle_from_json = url_parts[1].split("/")[
                                                0
                                            ]
                                            # Only update if we got a valid handle (not generic)
                                            if (
                                                handle_from_json
                                                and handle_from_json
                                                not in ("Thread", "unknown")
                                            ):
                                                author_handle = handle_from_json
                                    if content:
                                        logging.info(
                                            f"✅ Extracted content from JSON-LD: {content[:50]}..."
                                        )
                                        break
                            elif isinstance(data, list):
                                # Sometimes JSON-LD is an array
                                for item in data:
                                    if isinstance(item, dict):
                                        article_body = (
                                            item.get("articleBody")
                                            or item.get("text")
                                            or ""
                                        )
                                        if article_body and len(article_body) > 20:
                                            content = article_body.strip()
                                            author_data = item.get("author", {})
                                            if isinstance(author_data, dict):
                                                author_name = (
                                                    author_data.get("name")
                                                    or author_data.get("alternateName")
                                                    or ""
                                                )
                                                if author_name:
                                                    author = author_name
                                            if content:
                                                logging.info(
                                                    f"✅ Extracted content from JSON-LD (array): {content[:50]}..."
                                                )
                                                break
                                if content:
                                    break
                    except Exception as e:
                        logging.debug(f"JSON-LD parsing failed: {e}")
                        continue
            except Exception as e:
                logging.debug(f"JSON-LD extraction failed: {e}")

            # Priority 2: Try meta description (fallback) — skip entirely if force_dom
            if not force_dom:
                if not content or len(content) < 20:
                    try:
                        meta_desc = await page.query_selector(
                            'meta[name="description"]'
                        )
                        if meta_desc:
                            meta_content = await meta_desc.get_attribute("content")
                            if meta_content:
                                content = meta_content.strip()
                                logging.info(
                                    f"✅ Extracted content from meta tag: {content[:50]}..."
                                )
                    except Exception as e:
                        logging.debug(f"Meta description extraction failed: {e}")
                if not content or len(content) < 20:
                    try:
                        og_desc = await page.query_selector(
                            'meta[property="og:description"]'
                        )
                        if og_desc:
                            og_content = await og_desc.get_attribute("content")
                            if og_content:
                                content = og_content.strip()
                                logging.info(
                                    f"✅ Extracted content from og:description: {content[:50]}..."
                                )
                    except Exception as e:
                        logging.debug(f"OG description extraction failed: {e}")
            created_at = datetime.now(timezone.utc)
            engagement = {}
            media_urls = []
            hashtags = []
            mentions = []

            # Guarded DOM fallback: only when JSON-LD/meta is missing/too short/truncated, or forced
            enable_dom_fallback = bool(force_dom)
            try:
                # If content is missing or very short, enable DOM fallback
                content_short = (not content) or (len(content) < 200)
                # Aggressive truncation detection: check for ellipsis anywhere
                content_truncated = False
                if content:
                    # Check for truncation markers: ellipsis at end, in middle, or common patterns
                    content_truncated = (
                        content.rstrip().endswith(
                            ("...", "…", "... and", "...и", "...и т.д.")
                        )
                        or ("..." in content)
                        or ("…" in content)
                        or (
                            content.endswith("...") and len(content) < 300
                        )  # Short content ending with ...
                    )
                else:
                    content_truncated = True
                # Enable if content is missing, too short, or clearly truncated
                if force_dom or content_short or content_truncated:
                    enable_dom_fallback = True
                    logging.info(
                        f"DOM fallback enabled: short={content_short}, truncated={content_truncated}, content_len={len(content) if content else 0}"
                    )
            except Exception as e:
                logger.error(f"Error: {e}")
                enable_dom_fallback = True
            if enable_dom_fallback:
                # Use meta tag content length as reference - if DOM gives more, prefer it
                meta_content_length = len(content) if content else 0
                # CRITICAL: Only extract from the FIRST article/post container, not replies
                article_selectors = [
                    "article:first-of-type",
                    '[role="article"]:first-of-type',
                    'div[data-pressable-container="true"]:first-of-type',
                    "article",
                    '[role="article"]',
                ]

                main_article = None
                for selector in article_selectors:
                    try:
                        # Get ONLY the first article element
                        article = await page.query_selector(selector)
                        if article:
                            # Check if this is likely the main post (not a reply)
                            # Replies usually have nested structure or different attributes
                            article_text = await article.inner_text()
                            if article_text and len(article_text.strip()) > 50:
                                main_article = article
                                logging.info(
                                    f"✅ Found main article with selector: {selector}"
                                )
                                break
                    except Exception as e:
                        logging.debug(f"Article selector {selector} failed: {e}")
                        continue

                if main_article:
                    try:
                        # First, extract the main post author handle for thread detection
                        main_author_handle = author_handle or "unknown"

                        # Extract text from main article and collect thread parts
                        text_selectors = [
                            '[dir="auto"]',
                            'span[dir="auto"]',
                            'div[dir="auto"]',
                        ]

                        thread_parts = []  # Collect all parts of the thread
                        seen_texts = set()
                        import re

                        # Extract main article content
                        for text_selector in text_selectors:
                            try:
                                elements = await main_article.query_selector_all(
                                    text_selector
                                )
                                if not elements:
                                    continue

                                main_texts = []
                                for elem in elements:
                                    text = await elem.inner_text()
                                    text = text.strip()
                                    if (
                                        text
                                        and len(text) > 20
                                        and text not in seen_texts
                                        and not text.startswith("@")
                                        and "Translate" not in text
                                        and not text.lower().startswith(
                                            (
                                                "comments:",
                                                "top valuable",
                                                "replies:",
                                                "reply:",
                                            )
                                        )
                                    ):
                                        main_texts.append(text)
                                        seen_texts.add(text)

                                if main_texts:
                                    thread_parts.append(" ".join(main_texts))
                                break
                            except Exception as e:
                                logging.debug(
                                    f"Text selector {text_selector} failed: {e}"
                                )
                                continue
                        # Now look for thread continuation: articles from same author with pagination
                        # Look for subsequent articles that might be thread parts
                        all_articles = await page.query_selector_all(
                            'article, [role="article"]'
                        )

                        for article in all_articles[
                            1:
                        ]:  # Skip first (already processed)
                            try:
                                # Check if this article is from the same author
                                article_author_elem = await article.query_selector(
                                    'a[href*="@"] span, a[role="link"] span'
                                )
                                if article_author_elem:
                                    article_author_text = (
                                        await article_author_elem.inner_text()
                                    )
                                    article_author_text = article_author_text.strip()

                                    # Extract handle from href or text
                                    article_author_handle = None
                                    try:
                                        author_link = await article.query_selector(
                                            'a[href*="@"]'
                                        )
                                        if author_link:
                                            href = await author_link.get_attribute(
                                                "href"
                                            )
                                            if href and "/@" in href:
                                                article_author_handle = href.split(
                                                    "/@"
                                                )[1].split("/")[0]
                                    except Exception as e:
                                        logger.error(f"Error: {e}")
                                        pass

                                    # If we can't get handle from href, try to extract from text
                                    if (
                                        not article_author_handle
                                        and article_author_text
                                    ):
                                        if article_author_text.startswith("@"):
                                            article_author_handle = article_author_text[
                                                1:
                                            ]
                                        elif article_author_text == main_author_handle:
                                            article_author_handle = main_author_handle

                                    # Check if this is from the same author
                                    if (
                                        article_author_handle
                                        and article_author_handle == main_author_handle
                                    ):
                                        # Extract text from this article
                                        article_texts = []
                                        for text_selector in text_selectors:
                                            try:
                                                elements = (
                                                    await article.query_selector_all(
                                                        text_selector
                                                    )
                                                )
                                                if not elements:
                                                    continue
                                                for elem in elements:
                                                    text = await elem.inner_text()
                                                    text = text.strip()
                                                    if (
                                                        text
                                                        and len(text) > 20
                                                        and text not in seen_texts
                                                        and not text.startswith("@")
                                                        and "Translate" not in text
                                                    ):
                                                        article_texts.append(text)
                                                        seen_texts.add(text)
                                                if article_texts:
                                                    break
                                            except Exception as e:
                                                logger.error(f"Error: {e}")
                                                continue

                                        if article_texts:
                                            logging.debug(
                                                f"Thread article candidate content snippet: {article_texts[0][:80]}"
                                            )
                                            article_content = " ".join(article_texts)
                                            # Check for pagination markers (1/5, 1/4, 1/3, etc.)
                                            pagination_pattern = r"\b\d+\s*/\s*\d+\b"
                                            has_pagination = bool(
                                                re.search(
                                                    pagination_pattern, article_content
                                                )
                                            )

                                            # If it has pagination, it's likely a thread part
                                            if has_pagination:
                                                thread_parts.append(article_content)
                                                logging.info(
                                                    f"✅ Found thread part {len(thread_parts)} from same author with pagination"
                                                )
                                            else:
                                                # Not a numbered part; keep scanning for others
                                                continue
                                    else:
                                        # Different author - skip (likely a reply)
                                        continue
                                else:
                                    # No author found - skip
                                    continue
                            except Exception as e:
                                logging.debug(f"Thread part extraction failed: {e}")
                                break

                        if thread_parts:
                            combined_text = " ".join(thread_parts)

                            # Remove pagination markers from final content (they're just UI indicators)
                            combined_text = re.sub(
                                r"\b\d+\s*/\s*\d+\b", "", combined_text
                            )

                            # Aggressive comment detection: stop at ANY comment/reply from different author
                            comment_patterns = [
                                r"(?i)(comments?:|replies?:|top valuable)",
                                r"💬",
                                r"(?i)^(reply|comment)\s*:",
                                r"^\d+\s*(comment|reply|replies)",
                            ]

                            # Find the earliest comment marker
                            earliest_comment = len(combined_text)
                            for pattern in comment_patterns:
                                match = re.search(pattern, combined_text)
                                if match:
                                    earliest_comment = min(
                                        earliest_comment, match.start()
                                    )

                            # Cut off at comment markers (keep at least 100 chars before comment)
                            if (
                                earliest_comment < len(combined_text)
                                and earliest_comment > 100
                            ):
                                combined_text = combined_text[:earliest_comment].strip()

                            # Final sanitization: remove leading username prefixes
                            combined_text = re.sub(
                                r"^([A-Za-z0-9._-]{2,32})\s*[:•\-–—]\s+",
                                "",
                                combined_text,
                            )
                            combined_text = re.sub(
                                r"^[A-Za-z0-9._-]{2,32}\s+", "", combined_text
                            )

                            # Use if longer than meta content
                            if len(combined_text) > meta_content_length:
                                content = combined_text
                                logging.info(
                                    f"✅ Extracted full thread content ({len(thread_parts)} parts, {len(combined_text)} chars)"
                                )
                    except Exception as e:
                        logging.debug(f"Main article extraction failed: {e}")
                # If still no content, do a broad body innerText fallback
                if not content or len(content) < max(60, meta_content_length):
                    try:
                        page_text = await page.evaluate(
                            '(sel) => document.body && document.body.innerText || ""',
                            "body",
                        )
                        if page_text and len(page_text.strip()) > meta_content_length:
                            content = page_text.strip()
                            logging.info(
                                "✅ Fallback: extracted content from document.body.innerText"
                            )
                    except Exception as e:
                        logging.debug(f"Body innerText fallback failed: {e}")
                # Retry once with a short re-navigation if content is still empty
                if (
                    not content
                    or len(content) < 60
                    or content.rstrip().endswith(("...", "…"))
                ):
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=40000)
                        await page.wait_for_selector(
                            'article, [role="article"], div[role="main"]', timeout=6000
                        )
                        # Try body text again
                        page_text = await page.evaluate(
                            '(sel) => document.body && document.body.innerText || ""',
                            "body",
                        )
                        if page_text and len(page_text.strip()) > 0:
                            content = page_text.strip()
                            logging.info(
                                "✅ Retry fallback: extracted content after networkidle reload"
                            )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass

            # Try to extract author information (only if better than URL baseline)
            author_selectors = [
                'a[role="link"] span',
                "h2 span",
                'div[dir="ltr"] span',
                "strong",
            ]

            for selector in author_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        author_text = await elem.inner_text()
                        author_text = author_text.strip()
                        # Only update if we found a valid author (not generic) and better than baseline
                        if (
                            author_text
                            and not author_text.startswith("@")
                            and len(author_text) < 50
                            and author_text
                            not in ("Thread", "Unknown Author", "Unknown")
                        ):
                            author = author_text
                            break
                except Exception as e:
                    logging.debug(f"Author selector {selector} failed: {e}")
                    continue

            # Try to extract author handle (only if better than URL baseline)
            handle_selectors = [
                'a[href*="@"] span',
                'span:has-text("@")',
                'div:has-text("@") span',
            ]

            for selector in handle_selectors:
                try:
                    elem = await page.query_selector(selector)
                    if elem:
                        handle_text = await elem.inner_text()
                        handle_text = handle_text.strip()
                        if handle_text.startswith("@"):
                            handle_value = handle_text[1:]  # Remove @
                            # Only update if we got a valid handle (not generic)
                            if handle_value and handle_value not in (
                                "Thread",
                                "unknown",
                                "Unknown",
                            ):
                                author_handle = handle_value
                            break
                except Exception as e:
                    logging.debug(f"Handle selector {selector} failed: {e}")
                    continue

            # Final fallback: ALWAYS extract author/handle from URL if DOM selectors failed or returned generic values
            # This ensures we never end up with "Thread" or "unknown" as the author
            try:
                # URL format: https://www.threads.net/@username/post/code
                url_parts = url.split("/@")
                if len(url_parts) > 1:
                    user_and_rest = url_parts[1]
                    username = user_and_rest.split("/")[0]
                    if username:
                        # Always override if we have generic values or if current values are generic
                        # Also override if author_handle is empty or just whitespace
                        if (
                            not author_handle
                            or not author_handle.strip()
                            or author_handle.lower()
                            in ("unknown", "thread", "unknown author")
                            or author_handle == "Thread"
                        ):
                            author_handle = username
                            logging.info(
                                f"✅ Extracted author_handle from URL: @{author_handle}"
                            )

                        if (
                            not author
                            or not author.strip()
                            or author.lower() in ("unknown author", "thread", "unknown")
                            or author == "Thread"
                        ):
                            author = username
                            logging.info(f"✅ Extracted author from URL: {author}")
            except Exception as e:
                logging.debug(f"Final URL-based author extraction failed: {e}")

            # REMOVED: Auto-refresh logic to prevent double-scraping
            # The get_saved_posts() already does full scraping, no need for refresh here

            # Try to extract engagement metrics
            try:
                # Look for like/heart buttons
                like_elements = await page.query_selector_all(
                    'svg[aria-label*="like"], svg[aria-label*="Like"], button[aria-label*="like"]'
                )
                if like_elements:
                    engagement["likes"] = len(like_elements)

                # Look for reply/comment indicators
                reply_elements = await page.query_selector_all(
                    'svg[aria-label*="reply"], svg[aria-label*="Reply"], button[aria-label*="reply"]'
                )
                if reply_elements:
                    engagement["replies"] = len(reply_elements)

                # Look for share/repost indicators
                share_elements = await page.query_selector_all(
                    'svg[aria-label*="share"], svg[aria-label*="Share"], svg[aria-label*="repost"]'
                )
                if share_elements:
                    engagement["shares"] = len(share_elements)

            except Exception as e:
                logging.debug(f"Failed to extract engagement: {e}")

            # Extract hashtags and mentions from content
            if content:
                import re

                hashtags = re.findall(r"#(\w+)", content)
                mentions = re.findall(r"@(\w+)", content)

            # If we couldn't extract meaningful content, create a basic placeholder
            if not content or len(content) < 5:
                content = f"Threads post {post_code} - Content extraction in progress"
                logging.warning(f"Could not extract meaningful content from {url}")

            # Final content sanitization to avoid replies/translations/noise
            raw_content_before_sanitize = content or ""
            content, thread_part, thread_total = _sanitize_threads_content(content)

            truncation_flag = False
            try:
                truncation_flag = _looks_truncated(raw_content_before_sanitize, content)
                if truncation_flag:
                    logging.warning(
                        "⚠️ Possible truncated Threads content detected: raw_len=%s cleaned_len=%s url=%s",
                        len(raw_content_before_sanitize.strip()),
                        len((content or "").strip()),
                        url,
                    )
            except Exception as trunc_err:
                logging.debug(f"Truncation detection failed: {trunc_err}")

            # Skip unnecessary re-scraping if content looks complete
            # This prevents the double-scraping issue in platform_collectors.py
            if (
                len(content) >= 100
                and not content.endswith("...")
                and not content.endswith("…")
            ):
                logging.info(
                    f"Content looks complete ({len(content)} chars), skipping auto-refresh"
                )
                force_dom = False

            normalized_handle = self._normalize_handle(author_handle)
            if normalized_handle and normalized_handle != author_handle:
                author_handle = normalized_handle
            # Allowlist filtering removed - collect all posts

            # Create the SocialPost object
            post_analysis = {}
            if truncation_flag:
                post_analysis.update(
                    {
                        "truncation_flag": True,
                        "raw_length": len(raw_content_before_sanitize.strip()),
                        "cleaned_length": len((content or "").strip()),
                    }
                )
            if thread_part and thread_total:
                logging.info(
                    f"🔗 Detected thread marker {thread_part}/{thread_total} in content."
                )
                post_analysis["thread_part"] = {
                    "part": thread_part,
                    "total": thread_total,
                }

            post = SocialPost(
                platform=self.platform_name,
                post_id=post_code,
                author=author,
                author_handle=author_handle,
                content=content,
                created_at=created_at,
                url=url,
                post_type="post",
                media_urls=media_urls,
                hashtags=hashtags,
                mentions=mentions,
                engagement=engagement,
                analysis=post_analysis or None,
            )

            logging.info(f"Successfully scraped Threads post: {post_code}")
            return post

        except Exception as e:
            logging.error(f"Failed to scrape thread {url}: {e}")
            # Return a basic placeholder if scraping fails
            try:
                post_code = url.strip("/").split("/")[-1]
                return SocialPost(
                    platform=self.platform_name,
                    post_id=post_code,
                    author="Threads User",
                    author_handle="threads_user",
                    content=f"Threads post from {url} - Scraping failed",
                    created_at=datetime.now(timezone.utc),
                    url=url,
                    post_type="post",
                    media_urls=[],
                    engagement={},
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                return None

    def _scrape_thread_data(self, url: str, page) -> Optional[SocialPost]:
        """
        Scrapes a single Threads post by URL using real content extraction.
        Updated to work with isolated page instances.
        """
        try:
            # Extract post code from URL for ID
            post_code = url.strip("/").split("/")[-1]

            logging.info(f"Scraping Threads post: {post_code}")

            # Validate page is still active before navigation
            if page.is_closed():
                raise Exception("Page is closed or invalid before navigation")

            # Navigate to the post with better error handling
            try:
                page.goto(url, timeout=30000)
            except Exception as nav_error:
                logging.warning(
                    f"Initial navigation failed: {nav_error}, trying with longer timeout"
                )
                try:
                    page.goto(url, timeout=45000)
                except Exception as nav_error2:
                    logger.error(f"Error: {e}")
                    raise Exception(f"Navigation failed completely: {nav_error2}")

            page.wait_for_timeout(3000)  # Wait for content to load

            # Try to extract real content using various selectors
            content = ""
            author = "Unknown Author"
            author_handle = "unknown"
            created_at = datetime.now(timezone.utc)
            engagement = {}
            media_urls = []
            hashtags = []
            mentions = []

            # Try different selectors for post content (sync version)
            content_selectors = [
                '[data-pressable-container="true"] span',
                "article span",
                '[role="article"] span',
                'div[dir="auto"] span',
                'span[dir="auto"]',
                'div[style*="text"] span',
            ]

            # Collect ALL text elements, not just first 3 (sync version)
            for selector in content_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    if elements:
                        # Get text from all matching elements
                        texts = []
                        seen_texts = set()  # Avoid duplicates
                        for elem in elements:
                            text = elem.inner_text().strip()
                            # Only meaningful text (length > 10) and not already seen
                            if text and len(text) > 10 and text not in seen_texts:
                                texts.append(text)
                                seen_texts.add(text)

                        if texts:
                            # Use ALL texts, not just first 3
                            combined_text = " ".join(texts)
                            # Filter out spam patterns (repeated usernames, etc.)
                            import re

                            # Remove very short segments that might be UI elements
                            segments = re.split(r"\s{2,}|\n", combined_text)
                            filtered_segments = [
                                s.strip()
                                for s in segments
                                if len(s.strip()) > 20
                                and not re.match(r"^@\w+\s*$", s.strip())
                            ]
                            filtered_content = " ".join(filtered_segments)

                            if filtered_content:
                                content = filtered_content
                                logging.info(
                                    f"✅ Extracted full content from DOM ({len(filtered_content)} chars)"
                                )
                                break
                except Exception as e:
                    logging.debug(f"Selector {selector} failed: {e}")
                    continue

            # Try to extract author information
            author_selectors = [
                'a[role="link"] span',
                "h2 span",
                'div[dir="ltr"] span',
                "strong",
            ]

            for selector in author_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem:
                        author_text = elem.inner_text().strip()
                        if (
                            author_text
                            and not author_text.startswith("@")
                            and len(author_text) < 50
                        ):
                            author = author_text
                            break
                except Exception as e:
                    logging.debug(f"Author selector {selector} failed: {e}")
                    continue

            # Try to extract author handle
            handle_selectors = [
                'a[href*="@"] span',
                'span:has-text("@")',
                'div:has-text("@") span',
            ]

            for selector in handle_selectors:
                try:
                    elem = page.query_selector(selector)
                    if elem:
                        handle_text = elem.inner_text().strip()
                        if handle_text.startswith("@"):
                            author_handle = handle_text[1:]  # Remove @
                            break
                except Exception as e:
                    logging.debug(f"Handle selector {selector} failed: {e}")
                    continue

            # Try to extract engagement metrics
            try:
                # Look for like/heart buttons
                like_elements = page.query_selector_all(
                    'svg[aria-label*="like"], svg[aria-label*="Like"], button[aria-label*="like"]'
                )
                if like_elements:
                    engagement["likes"] = len(like_elements)

                # Look for reply/comment indicators
                reply_elements = page.query_selector_all(
                    'svg[aria-label*="reply"], svg[aria-label*="Reply"], button[aria-label*="reply"]'
                )
                if reply_elements:
                    engagement["replies"] = len(reply_elements)

                # Look for share/repost indicators
                share_elements = page.query_selector_all(
                    'svg[aria-label*="share"], svg[aria-label*="Share"], svg[aria-label*="repost"]'
                )
                if share_elements:
                    engagement["shares"] = len(share_elements)

            except Exception as e:
                logging.debug(f"Failed to extract engagement: {e}")

            # Extract hashtags and mentions from content
            if content:
                import re

                hashtags = re.findall(r"#(\w+)", content)
                mentions = re.findall(r"@(\w+)", content)

            # If we couldn't extract meaningful content, create a basic placeholder
            if not content or len(content) < 10:
                content = f"Threads post {post_code} - Content extraction in progress"
                logging.warning(f"Could not extract meaningful content from {url}")

            # Create the SocialPost object
            post = SocialPost(
                platform=self.platform_name,
                post_id=post_code,
                author=author,
                author_handle=author_handle,
                content=content,
                created_at=created_at,
                url=url,
                post_type="post",
                media_urls=media_urls,
                hashtags=hashtags,
                mentions=mentions,
                engagement=engagement,
            )

            logging.info(f"Successfully scraped Threads post: {post_code}")
            return post

        except Exception as e:
            logging.error(f"Failed to scrape thread {url}: {e}")
            # Return a basic placeholder if scraping fails
            try:
                post_code = url.strip("/").split("/")[-1]
                return SocialPost(
                    platform=self.platform_name,
                    post_id=post_code,
                    author="Threads User",
                    author_handle="threads_user",
                    content=f"Threads post from {url} - Scraping failed",
                    created_at=datetime.now(timezone.utc),
                    url=url,
                    post_type="post",
                    media_urls=[],
                    engagement={},
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                return None

    def get_posts_by_urls(self, urls: list[str]) -> list[SocialPost]:
        # This will be updated later if needed
        raise NotImplementedError("URL-based scraping not supported in this version.")

    def _parse_thread_from_ld_json(self, data: dict) -> Optional[SocialPost]:
        """
        Parses the JSON-LD data from a script tag to extract post details.
        """
        try:
            post_id = data.get("identifier") or data.get("url", "").split("/")[-2]
            url = data.get("url")
            text = data.get("articleBody", "")
            author = data.get("author", {}).get("name", "unknown")

            date_str = data.get("datePublished")
            timestamp = (
                datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                if date_str
                else datetime.now(timezone.utc)
            )

            likes = 0
            for interaction in data.get("interactionStatistic", []):
                if (
                    interaction.get("interactionType")
                    == "https://schema.org/LikeAction"
                ):
                    likes = interaction.get("userInteractionCount", 0)
                    break

            return SocialPost(
                post_id=str(post_id),
                url=url,
                text=text,
                author=author,
                timestamp=timestamp,
                platform=self.platform_name,
                likes=likes,
            )
        except (KeyError, TypeError, IndexError) as e:
            logging.error(f"Failed to parse thread data from JSON: {e} - Data: {data}")
            return None

    async def close(self) -> None:
        """Clean up browser resources"""
        try:
            if hasattr(self, "page") and self.page:
                await self.page.close()
            if hasattr(self, "context") and self.context:
                await self.context.close()
            if hasattr(self, "browser") and self.browser:
                await self.browser.close()
            if hasattr(self, "pw") and self.pw:
                await self.pw.stop()
        except Exception as e:
            logging.debug(f"Error during ThreadsExtractor cleanup: {e}")
            pass
