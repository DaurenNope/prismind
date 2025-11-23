import asyncio
import json
import logging
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import parse_qs, urlencode, urlparse

from playwright.async_api import Browser, Page, async_playwright

from ..rate_limiting.rate_limit_config import RateLimitConfig
from .social_extractor_base import SocialExtractorBase, SocialPost
from .twitter.api_client import TwitterAPIClient
from .twitter_cookies import TwitterCookieStore

logger = logging.getLogger(__name__)


def load_collection_config():
    """Load collection configuration from config file"""
    config_path = Path("config/collection.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {"twitter": {"extract_threads": False}}


class TwitterExtractorPlaywright(SocialExtractorBase):
    """Extract saved tweets and bookmarks from Twitter using Playwright"""

    def __init__(
        self,
        username: str,
        password: str = None,
        headless: bool = False,
        cookie_file: str = None,
    ):
        super().__init__()
        self.username = username
        self.password = password
        self.headless = headless
        self.cookie_file = cookie_file or f"config/cookies/twitter_cookies_{username}.json"
        self._cookie_store = TwitterCookieStore(self.cookie_file)
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.is_authenticated = False

        # Load configuration
        config = load_collection_config()
        self.extract_threads = config.get("twitter", {}).get("extract_threads", False)
        # Safety/jitter and scroll caps
        twitter_cfg = config.get("twitter", {})
        self.jitter_ms: List[int] = twitter_cfg.get("jitter_ms", [300, 1200])
        self.scroll_limit_cfg: Optional[int] = twitter_cfg.get("scroll_limit")

    async def _jitter(self, extra_ms: int = 0):
        """Sleep a random jitter to mimic human behavior."""
        try:
            low, high = (
                (self.jitter_ms[0], self.jitter_ms[1])
                if isinstance(self.jitter_ms, list) and len(self.jitter_ms) == 2
                else (300, 1200)
            )
            delay = (
                max(0, low)
                if low == high
                else __import__("random").randint(int(low), int(high))
            )
            await asyncio.sleep((delay + max(0, extra_ms)) / 1000)
        except Exception as e:
            logger.error(f"Error: {e}")
            # Best-effort; do not fail collection on jitter errors
            await asyncio.sleep(0.3)

    async def _refresh_and_save_cookies(self) -> bool:
        """
        Refresh and save cookies using storage_state (sophisticated approach like Threads)

        This saves the entire browser state (cookies, localStorage, etc.)
        Automatically called after successful operations to keep cookies fresh.
        """
        try:
            if self.context and self.is_authenticated:
                cookie_path = self._cookie_store.path
                self._cookie_store.ensure_parent_dir()

                # Use storage_state to save (saves cookies + browser state)
                # This is Playwright's native format - most reliable
                await self.context.storage_state(path=str(cookie_path))
                logger.info(f"✅ Refreshed and saved browser state to {cookie_path}")

                # Verify cookies were saved
                if cookie_path.exists():
                    cookies = self._cookie_store.load()
                    if cookies is not None:
                        logger.info(
                            f"✅ Verified: Saved {len(cookies)} cookies in storage_state format"
                        )
                        return True
                    logger.warning(
                        "⚠️ Cookies saved but could not verify storage_state contents"
                    )
                    return True  # Still return True as save likely succeeded
                else:
                    logger.warning(
                        f"⚠️ Cookie file not found after save: {cookie_path}"
                    )
                    return False
            else:
                logger.warning(
                    "⚠️ Cannot refresh cookies: context not available or not authenticated"
                )
                return False
        except Exception as e:
            logger.error(f"⚠️ Failed to refresh cookies: {e}")
            import traceback

            traceback.print_exc()
        return False

    async def _auto_refresh_cookies_if_needed(self) -> bool:
        """
        Automatically refresh cookies if needed (before they expire)

        Checks cookie freshness and refreshes proactively.
        This prevents authentication failures due to expired cookies.
        """
        try:
            if not self.context or not self.is_authenticated:
                return False

            age_seconds = self._cookie_store.get_age_seconds()
            if age_seconds is None:
                # No cookies to refresh
                return False

            # Refresh if cookies are older than 1 hour (proactive refresh)
            # Twitter cookies typically last much longer, but refreshing keeps them fresh
            if age_seconds > 3600:  # 1 hour
                logger.info(
                    f"🔄 Cookies are {int(age_seconds/60)} minutes old - refreshing proactively..."
                )
                return await self._refresh_and_save_cookies()

            return True
        except Exception as e:
            logger.error(f"⚠️ Auto-refresh check failed: {e}")
            return False

    def _check_cookie_freshness(self) -> bool:
        """
        Check if cookies are fresh enough to use without refresh.

        Returns True if cookies are fresh, False if they should be refreshed.
        """
        age_seconds = self._cookie_store.get_age_seconds()
        if age_seconds is None:
            return False

        is_fresh = age_seconds < 21600  # 6 hours

        if not is_fresh:
            try:
                logger.warning(
                    f"⚠️ Cookies are {int(age_seconds/3600)} hours old - may need refresh"
                )
            except Exception:
                logger.warning("⚠️ Cookies may be old - could not compute exact age")

        return is_fresh

    def _validate_cookie_format(self) -> bool:
        """
        Validate that cookies are in the correct storage_state format (like Threads)

        Returns True if cookies are in the correct format, False otherwise.
        """
        try:
            cookie_path = self._cookie_store.path
            if not cookie_path.exists():
                return False

            with cookie_path.open("r") as f:
                cookie_data = json.load(f)

            # Check if it's in storage_state format: {"cookies": [...], "origins": [...]}
            if not isinstance(cookie_data, dict):
                logger.warning(
                    f"⚠️ Cookie file is not in storage_state format (expected dict, got {type(cookie_data)})"
                )
                return False

            if "cookies" not in cookie_data:
                logger.warning(
                    f"⚠️ Cookie file missing 'cookies' key (not in storage_state format)"
                )
                return False

            cookies = cookie_data.get("cookies", [])
            if not isinstance(cookies, list):
                logger.warning(
                    f"⚠️ Cookie file 'cookies' is not a list (expected list, got {type(cookies)})"
                )
                return False

            # Validate cookie structure
            for cookie in cookies:
                if not isinstance(cookie, dict):
                    logger.warning(
                        f"⚠️ Invalid cookie format: expected dict, got {type(cookie)}"
                    )
                    return False
                if "name" not in cookie or "value" not in cookie:
                    logger.warning(f"⚠️ Invalid cookie: missing 'name' or 'value'")
                    return False

            logger.info(
                f"✅ Cookie file validated: {len(cookies)} cookies in storage_state format"
            )
            return True

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Cookie file is not valid JSON: {e}")
            return False
        except Exception as e:
            logger.warning(f"⚠️ Could not validate cookie format: {e}")
            return False

    async def _try_cookie_authentication(self) -> bool:
        """
        Try to authenticate using existing cookies - SOPHISTICATED approach like Threads

        Uses storage_state (Playwright's native cookie/state management) for reliable authentication.
        """
        cookie_path = self._cookie_store.path
        if not self._cookie_store.exists():
            logger.warning("⚠️  Cookie file not found - skipping cookie authentication")
            return False

        try:
            self._cookie_store.ensure_parent_dir()
            # Validate cookie format (sophisticated approach like Threads)
            if not self._validate_cookie_format():
                logger.warning(
                    "⚠️  Cookie file is not in storage_state format - will attempt to convert on next save"
                )
                # Don't fail - we'll try to use it anyway and fix it on save

            # Check cookie freshness
            is_fresh = self._check_cookie_freshness()
            if not is_fresh:
                logger.info(
                    "🔄 Cookies are old - will refresh after successful authentication"
                )

            logger.warning(
                "🍪 Attempting cookie-based authentication (using storage_state)..."
            )

            # Launch browser if not already launched (like Threads does)
            if not self.playwright:
                self.playwright = await async_playwright().start()

            if not self.browser or not self.browser.is_connected():
                logger.info("🔧 Launching browser for cookie authentication...")
                self.browser = await self.playwright.chromium.launch(
                    headless=self.headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )

            # IMPORTANT: Use storage_state directly - this is the sophisticated approach (like Threads)
            # This loads cookies AND browser state (localStorage, sessionStorage, etc.)
            # This creates a NEW context with the saved state - this is the key!
            # Enhanced anti-detection context with comprehensive evasion
            self.context = await self.browser.new_context(
                storage_state=str(cookie_path),
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="America/New_York",
                permissions=["geolocation", "notifications"],
                color_scheme="light",
                device_scale_factor=1,
                has_touch=False,
                is_mobile=False,
                java_script_enabled=True,
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "Sec-Ch-Ua-Mobile": "?0",
                    "Sec-Ch-Ua-Platform": '"macOS"',
                },
            )

            # Comprehensive anti-detection scripts BEFORE creating page
            await self.context.add_init_script(
                """
                // Remove webdriver property completely
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Add full Chrome runtime
                window.navigator.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };

                // Realistic plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        return [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                            { name: 'Native Client', filename: 'internal-nacl-plugin' }
                        ];
                    }
                });

                // Realistic languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                // Add permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Remove Chrome DevTools Protocol markers
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;

                // Remove automation indicators
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => false
                });

                // Override permissions
                const originalPermissions = navigator.permissions;
                navigator.permissions = {
                    ...originalPermissions,
                    query: async (parameters) => {
                        if (parameters.name === 'notifications') {
                            return { state: 'default', onchange: null };
                        }
                        return originalPermissions.query(parameters);
                    }
                };

                // Add realistic hardware concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 8
                });

                // Add device memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });

                // Override getBattery if it exists
                if (navigator.getBattery) {
                    navigator.getBattery = () => Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1
                    });
                }

                // Remove automation from window
                delete window.__playwright;
                delete window.__pw_manual;
                delete window.__PW_inspect;
                delete window.playwright;

                // Override toString to hide automation
                window.navigator.webdriver = undefined;
                Object.defineProperty(navigator, 'webdriver', {
                    configurable: true,
                    get: () => false
                });
            """
            )

            self.page = await self.context.new_page()

            # Apply playwright-stealth if available
            try:
                from playwright_stealth import stealth_async as stealth

                await stealth(self.page)
                logger.info("✅ Applied playwright-stealth anti-detection")
            except ImportError:
                logger.warning(
                    "⚠️ playwright-stealth not available - using basic anti-detection"
                )
            except Exception as e:
                logger.error(
                    f"⚠️ playwright-stealth failed: {e} - continuing with basic anti-detection"
                )

            # Navigate directly to home page (like Threads does)
            await self._jitter()
            await self.page.goto(
                "https://x.com/home", wait_until="domcontentloaded", timeout=60000
            )
            await asyncio.sleep(3)  # Wait for page to load

            # Check for rate limiting errors on page
            page_text = await self.page.evaluate("document.body.innerText")
            if re.search(r"g;\d+:-\d+:[a-zA-Z0-9]+:\d+", page_text):
                logger.error(
                    "⚠️  Rate limiting error detected in page - cookies may be expired or account is rate limited"
                )
                await self.page.screenshot(
                    path="logs/twitter_cookie_auth_rate_limit.png"
                )
                return False

            # Simple check: are we on login page? (like Threads does)
            current_url = self.page.url
            if "login" in current_url.lower() or "signin" in current_url.lower():
                logger.error(
                    "❌ Cookie authentication failed - redirected to login page (cookies expired)"
                )
                return False

            # Check for timeline (logged in indicator)
            try:
                timeline_element = await self.page.wait_for_selector(
                    '[data-testid="primaryColumn"]', timeout=5000
                )
                if timeline_element:
                    logger.info("✅ Cookie authentication successful! (found timeline)")
                    self.is_authenticated = True
                    # AUTO-REFRESH: Save fresh cookies using storage_state
                    await self.context.storage_state(path=str(cookie_path))
                    logger.info(f"✅ Refreshed and saved browser state to {cookie_path}")
                    return True
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            # Also check URL - if we're on /home, we're likely logged in
            if "/home" in current_url and "/login" not in current_url:
                logger.info("✅ Cookie authentication successful! (on home page)")
                self.is_authenticated = True
                # AUTO-REFRESH: Save fresh cookies using storage_state
                await self.context.storage_state(path=str(cookie_path))
                logger.info(f"✅ Refreshed and saved browser state to {cookie_path}")
                return True

            # If we got here, authentication likely failed
            logger.error(
                "❌ Cookie authentication failed - could not verify login status"
            )
            return False

        except Exception as e:
            logger.error(f"❌ Cookie authentication error: {e}")
            return False

    async def authenticate(self, max_retries: int = 3) -> bool:
        """Authenticate with Twitter using Playwright, with retries and more robust selectors.

        Uses sophisticated cookie management like Threads:
        - Checks cookie freshness before attempting auth
        - Uses storage_state for reliable cookie loading
        - Auto-refreshes cookies after successful authentication
        """
        for attempt in range(max_retries):
            try:
                logger.warning(
                    f"🔄 Authentication attempt {attempt + 1}/{max_retries}..."
                )

                # Check cookie freshness before attempting auth
                if self._cookie_store.exists():
                    is_fresh = self._check_cookie_freshness()
                    if not is_fresh:
                        logger.warning(
                            "🔄 Cookies are old but will attempt to use them (will refresh if auth succeeds)"
                        )

                if not self.playwright:
                    self.playwright = await async_playwright().start()

                # Initialize browser if needed (for cookie auth to work)
                if not self.browser or not self.browser.is_connected():
                    # Enhanced anti-detection browser launch with comprehensive flags
                    launch_args = [
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--lang=en-US",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=IsolateOrigins,site-per-process",
                        "--disable-site-isolation-trials",
                        "--disable-web-security",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-infobars",
                        "--disable-notifications",
                        "--disable-popup-blocking",
                        "--disable-translate",
                        "--disable-background-networking",
                        "--disable-background-timer-throttling",
                        "--disable-renderer-backgrounding",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-component-extensions-with-background-pages",
                        "--disable-default-apps",
                        "--disable-extensions",
                        "--disable-hang-monitor",
                        "--disable-ipc-flooding-protection",
                        "--disable-prompt-on-repost",
                        "--disable-sync",
                        "--force-color-profile=srgb",
                        "--metrics-recording-only",
                        "--no-first-run",
                        "--enable-automation=false",
                        "--password-store=basic",
                        "--use-mock-keychain",
                        "--disable-features=TranslateUI",
                        "--disable-ipc-flooding-protection",
                    ]

                    # Launch regular browser (not persistent context yet - cookie auth will create context)
                    logger.info("🔧 Launching browser for authentication...")
                    self.browser = await self.playwright.chromium.launch(
                        headless=self.headless,
                        args=launch_args,
                    )
                    logger.info("✅ Browser launched")

                # TRY COOKIE AUTHENTICATION FIRST (PRIORITY - avoids rate limiting)
                # Use sophisticated storage_state approach (like Threads)
                # This will create context with storage_state if cookies exist
                logger.warning(
                    "🍪 Attempting cookie-based authentication using storage_state (avoids rate limiting)..."
                )
                if await self._try_cookie_authentication():
                    # Cookies already refreshed in _try_cookie_authentication via storage_state
                    # Context and page are already created in _try_cookie_authentication
                    logger.info(
                        "✅ Cookie authentication successful - bypassing password login"
                    )
                    self.is_authenticated = True
                    return True
                else:
                    logger.error(
                        "⚠️  Cookie authentication failed - cookies may be expired or missing"
                    )
                    logger.info(
                        "   Will try password authentication to get fresh cookies"
                    )

                    # Cookie auth failed - create context for password login
                    if not self.context:
                        logger.info(
                            "🔑 Creating new browser context for password authentication (will get fresh cookies)..."
                        )
                        self.context = await self.browser.new_context(
                            viewport={"width": 1920, "height": 1080},
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                            locale="en-US",
                            timezone_id="America/New_York",
                            permissions=["geolocation", "notifications"],
                            color_scheme="light",
                            device_scale_factor=1,
                            has_touch=False,
                            is_mobile=False,
                            java_script_enabled=True,
                            extra_http_headers={
                                "Accept-Language": "en-US,en;q=0.9",
                                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                                "Accept-Encoding": "gzip, deflate, br, zstd",
                                "Connection": "keep-alive",
                                "Upgrade-Insecure-Requests": "1",
                                "Sec-Fetch-Dest": "document",
                                "Sec-Fetch-Mode": "navigate",
                                "Sec-Fetch-Site": "none",
                                "Sec-Fetch-User": "?1",
                                "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                                "Sec-Ch-Ua-Mobile": "?0",
                                "Sec-Ch-Ua-Platform": '"macOS"',
                            },
                        )

                        # Add comprehensive anti-detection scripts (same as cookie auth)
                        await self.context.add_init_script(
                            """
                            // Remove webdriver property completely
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined
                            });

                            // Add full Chrome runtime
                            window.navigator.chrome = {
                                runtime: {},
                                loadTimes: function() {},
                                csi: function() {},
                                app: {}
                            };

                            // Realistic plugins
                            Object.defineProperty(navigator, 'plugins', {
                                get: () => {
                                    return [
                                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                                    ];
                                }
                            });

                            // Realistic languages
                            Object.defineProperty(navigator, 'languages', {
                                get: () => ['en-US', 'en']
                            });

                            // Remove Chrome DevTools Protocol markers
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
                            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;

                            // Remove automation indicators
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => false
                            });

                            // Add realistic hardware
                            Object.defineProperty(navigator, 'hardwareConcurrency', {
                                get: () => 8
                            });

                            Object.defineProperty(navigator, 'deviceMemory', {
                                get: () => 8
                            });

                            // Remove automation from window
                            delete window.__playwright;
                            delete window.__pw_manual;
                            delete window.__PW_inspect;
                            delete window.playwright;

                            // Override toString to hide automation
                            window.navigator.webdriver = undefined;
                            Object.defineProperty(navigator, 'webdriver', {
                                configurable: true,
                                get: () => false
                            });
                        """
                        )

                    if not self.page or self.page.is_closed():
                        self.page = await self.context.new_page()

                        # Apply playwright-stealth if available
                        try:
                            from playwright_stealth import stealth_async as stealth

                            await stealth(self.page)
                            logger.info("✅ Applied playwright-stealth anti-detection")
                        except ImportError:
                            logger.warning(
                                "⚠️ playwright-stealth not available - using basic anti-detection"
                            )
                        except Exception as e:
                            logger.error(
                                f"⚠️ playwright-stealth failed: {e} - continuing with basic anti-detection"
                            )

                if not self.password:
                    logger.error("❌ No password provided for fresh login.")
                    logger.info(
                        "💡 Set TWITTER_PASSWORD environment variable to get fresh cookies"
                    )
                    return False

                # Password login to get fresh cookies (cookie auth failed)
                logger.info(
                    "🔑 Starting password authentication to get fresh cookies..."
                )
                logger.info("   This will get new, valid cookies from Twitter")
                await self._jitter()
                await self.page.goto(
                    "https://x.com/login", wait_until="domcontentloaded", timeout=60000
                )
                await self._jitter(300)

                # Step 1: Enter username (with human-like typing)
                username_selector = 'input[name="text"], input[autocomplete="username"]'
                logger.info("👤 Entering username...")
                await self.page.wait_for_selector(username_selector, timeout=30000)

                # Human-like typing (type character by character with random delays)
                username_input = await self.page.query_selector(username_selector)
                if username_input:
                    await username_input.click()
                    await self._jitter(200)  # Small delay before typing
                    for char in self.username:
                        await username_input.type(char, delay=random.randint(50, 150))
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                else:
                    # Fallback to fill if click fails
                    await self.page.fill(username_selector, self.username)

                await self._jitter(300)  # Human-like pause before clicking
                await self.page.click('button:has-text("Next")')

                # Step 2: Handle potential verification
                verification_selector = 'input[data-testid="ocfEnterTextTextInput"]'
                try:
                    verification_input = await self.page.wait_for_selector(
                        verification_selector, timeout=5000
                    )
                    logger.warning(
                        "⚠️ Twitter is asking for additional verification (e.g., phone number or username). This is an anti-bot measure."
                    )
                    # You might need to enter a phone number or username here if prompted
                    # For now, we will assume it's asking for the username again
                    await verification_input.fill(self.username)
                    await self.page.click('button:has-text("Next")')
                except Exception as e:
                    logger.info(f"✅ No special verification prompt detected: {e}")

                # Step 3: Enter password (with human-like typing)
                password_selector = (
                    'input[name="password"], input[autocomplete="current-password"]'
                )
                logger.info("🔑 Entering password...")
                await self.page.wait_for_selector(password_selector, timeout=30000)

                # Human-like typing for password (slower, more realistic)
                password_input = await self.page.query_selector(password_selector)
                if password_input:
                    await password_input.click()
                    await self._jitter(200)
                    for char in self.password:
                        await password_input.type(char, delay=random.randint(80, 200))
                        await asyncio.sleep(random.uniform(0.08, 0.2))
                else:
                    # Fallback to fill if click fails
                    await self.page.fill(password_selector, self.password)

                # Step 4: Click Login
                login_button_selector = 'button[data-testid="LoginForm_Login_Button"]'
                await self.page.wait_for_selector(login_button_selector, timeout=10000)
                await self.page.click(login_button_selector)

                # Wait longer for response (error messages may take time to appear)
                await asyncio.sleep(3)  # Wait 3 seconds for error to appear

                # Check for error messages (rate limiting, etc.) - comprehensive check
                try:
                    # Get full page text to check for errors
                    page_text = await self.page.evaluate("document.body.innerText")
                    page_html = await self.page.content()

                    # Check for specific error patterns
                    error_patterns = [
                        "could not log you in",
                        "try again later",
                        "rate limit",
                        "g;.*:.*:.*:.*:1",  # Twitter error identifier pattern
                        "something went wrong",
                        "temporarily restricted",
                        "suspended",
                        "blocked",
                    ]

                    # Check page text
                    page_text_lower = page_text.lower()
                    for pattern in error_patterns:
                        if pattern.startswith("g;"):
                            # Check for Twitter error identifier pattern
                            if re.search(r"g;\d+:-\d+:[a-zA-Z0-9]+:\d+", page_text):
                                error_msg = "Twitter authentication blocked - rate limiting detected"
                                logger.error(f"⚠️ {error_msg}")
                                await self.page.screenshot(
                                    path=f"logs/twitter_auth_error_{attempt + 1}.png"
                                )
                                raise Exception(error_msg)
                        elif pattern in page_text_lower:
                            # Extract full error message
                            error_msg = f"Twitter authentication blocked: {pattern}"
                            logger.error(f"⚠️ {error_msg}")
                            await self.page.screenshot(
                                path=f"logs/twitter_auth_error_{attempt + 1}.png"
                            )
                            raise Exception(error_msg)

                    # Also check for error elements (more specific selectors)
                    error_selectors = [
                        'div[role="alert"]',
                        '[data-testid="error"]',
                        '[data-testid="errorDetail"]',
                        'span:has-text("Could not log you in")',
                        'span:has-text("Try again later")',
                        'span:has-text("Something went wrong")',
                        '[class*="error"]',
                        '[class*="Error"]',
                    ]

                    for selector in error_selectors:
                        try:
                            error_elements = await self.page.query_selector_all(
                                selector
                            )
                            for error_element in error_elements:
                                error_text = await error_element.inner_text()
                                if error_text:
                                    error_text_lower = error_text.lower()
                                    if any(
                                        pattern in error_text_lower
                                        for pattern in error_patterns
                                        if not pattern.startswith("g;")
                                    ):
                                        logger.error(
                                            f"⚠️ Twitter rate limiting/error detected: {error_text}"
                                        )
                                        await self.page.screenshot(
                                            path=f"logs/twitter_auth_error_{attempt + 1}.png"
                                        )
                                        raise Exception(
                                            f"Twitter authentication blocked: {error_text}"
                                        )
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            if "Twitter authentication blocked" in str(e):
                                raise  # Re-raise our custom error
                            continue

                except Exception as check_error:
                    logger.error(f"Error: {e}")
                    if "Twitter authentication blocked" in str(check_error):
                        raise  # Re-raise our custom error
                    # Otherwise, continue to normal verification

                # Step 5: Verify login success
                home_timeline_selector = '[data-testid="primaryColumn"]'
                try:
                    await self.page.wait_for_selector(
                        home_timeline_selector, timeout=30000
                    )
                except Exception as e:
                    # Check if we're still on login page (authentication failed)
                    current_url = self.page.url
                    page_text = await self.page.evaluate("document.body.innerText")
                    page_text_lower = page_text.lower()

                    # Check for Twitter error identifier pattern
                    if re.search(r"g;\d+:-\d+:[a-zA-Z0-9]+:\d+", page_text):
                        error_msg = "Twitter authentication blocked - rate limiting detected (error identifier found)"
                        logger.error(f"❌ {error_msg}")
                        await self.page.screenshot(
                            path=f"logs/twitter_auth_failed_{attempt + 1}.png"
                        )
                        raise Exception(error_msg)

                    if (
                        "login" in current_url.lower()
                        or "signin" in current_url.lower()
                    ):
                        logger.error(f"❌ Still on login page. URL: {current_url}")
                        # Check for specific error messages in page
                        if any(
                            pattern in page_text_lower
                            for pattern in [
                                "could not log",
                                "try again later",
                                "rate limit",
                                "something went wrong",
                            ]
                        ):
                            await self.page.screenshot(
                                path=f"logs/twitter_auth_failed_{attempt + 1}.png"
                            )
                            raise Exception(
                                "Twitter authentication blocked - rate limiting or anti-bot detection. Please wait and try again later."
                            )
                        raise Exception(f"Authentication failed - still on login page")
                    raise

                self.is_authenticated = True
                logger.info(f"✅ Successfully logged in to Twitter as {self.username}")

                # AUTO-SAVE: Save browser state using storage_state (sophisticated approach like Threads)
                # This ensures cookies are always fresh after authentication
                cookie_path = self._cookie_store.path
                self._cookie_store.ensure_parent_dir()
                await self.context.storage_state(path=str(cookie_path))
                logger.info(
                    f"✅ Saved browser state to {cookie_path} (includes cookies + localStorage)"
                )

                # Verify cookies were saved properly
                await self._refresh_and_save_cookies()

                return True

            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Authentication attempt {attempt + 1} failed: {e}")

                # Take screenshot for debugging
                try:
                    if self.page and not self.page.is_closed():
                        await self.page.screenshot(
                            path=f"logs/auth_failure_attempt_{attempt + 1}.png"
                        )
                except Exception as e:
                    logger.error(f"⚠️ Screenshot failed: {e}")
                    pass

                # Check if it's a rate limiting error (including Twitter error identifier pattern)
                has_rate_limit_pattern = (
                    "rate limit" in error_msg.lower()
                    or "try again later" in error_msg.lower()
                    or "could not log" in error_msg.lower()
                    or "temporarily restricted" in error_msg.lower()
                    or "twitter authentication blocked" in error_msg.lower()
                    or re.search(r"g;\d+:-\d+:[a-zA-Z0-9]+:\d+", error_msg) is not None
                )

                if has_rate_limit_pattern:
                    logger.warning(
                        "⚠️  Twitter rate limiting/anti-bot detection detected!"
                    )
                    logger.error(f"   Error: {error_msg[:200]}")  # Show first 200 chars
                    logger.warning(
                        "💡 This means Twitter is blocking automated login attempts."
                    )
                    logger.info()
                    logger.info("🔧 Solutions:")
                    logger.info(
                        "   1. WAIT: Wait 1-2 hours (or longer) before trying again"
                    )
                    logger.info(
                        "   2. USE COOKIES: Ensure valid cookies exist - they bypass login"
                    )
                    logger.info("      Check: cookies/twitter_cookies_cryptoniard.json")
                    logger.info(
                        "   3. MANUAL LOGIN: Log in manually once in browser to refresh cookies"
                    )
                    logger.info(
                        "   4. SKIP FOR NOW: Focus on Threads collection (has valid cookies)"
                    )
                    logger.info(
                        "   5. CHECK COOKIES: Run: python scripts/manage_cookies.py"
                    )
                    logger.info()

                    if attempt == 0:
                        # On first attempt, suggest waiting longer
                        logger.info(
                            "⏭️  Skipping further retries (rate limit detected)"
                        )
                        logger.info(
                            "💡 Run collection again later (wait 1-2 hours), or use cookies to bypass"
                        )
                        return False

                    wait_time = 60 * (attempt + 1)  # Longer wait: 60s, 120s, 180s
                    logger.warning(f"⏳ Waiting {wait_time} seconds before retry...")
                    await asyncio.sleep(wait_time)

                    # Don't clean up browser on rate limit - keep it for retry
                    continue
                else:
                    # Regular retry with shorter wait
                    if self.page and not self.page.is_closed():
                        await self.page.close()
                    if self.context:
                        await self.context.close()
                        self.context = None
                    if attempt >= max_retries - 1:
                        logger.error("❌ All authentication attempts failed.")
                        if (
                            "rate limit" in error_msg.lower()
                            or "try again later" in error_msg.lower()
                        ):
                            logger.info(
                                "💡 Tip: Twitter may be rate limiting. Wait 15-30 minutes and try again."
                            )
                        return False
                    await asyncio.sleep(5)  # Wait before retrying
        return False

    def _extract_tweets_from_api_response(self, api_data: dict) -> List[SocialPost]:
        """
        Extract tweets from Twitter GraphQL API response.
        This is a fallback when DOM parsing fails due to automation detection.
        """
        tweets = []
        try:
            # Twitter GraphQL response structure:
            # { "data": { "bookmark_timeline": { "timeline": { "instructions": [...] } } } }
            # or similar variations

            def find_tweet_entries(obj, path=""):
                """Recursively find tweet entries in GraphQL response"""
                entries = []
                if isinstance(obj, dict):
                    # Look for entries array
                    if "entries" in obj:
                        entries.extend(obj["entries"])
                    # Look for timeline instructions
                    if "instructions" in obj:
                        for instruction in obj.get("instructions", []):
                            if (
                                isinstance(instruction, dict)
                                and "entries" in instruction
                            ):
                                entries.extend(instruction.get("entries", []))
                    # Recursively search
                    for key, value in obj.items():
                        entries.extend(find_tweet_entries(value, f"{path}.{key}"))
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        entries.extend(find_tweet_entries(item, f"{path}[{i}]"))
                return entries

            entries = find_tweet_entries(api_data)
            logger.info(f"   📊 Found {len(entries)} entries in API response")

            for entry in entries:
                try:
                    # Extract tweet data from entry
                    # Entry structure varies, but typically has content.entryId and content.itemContent
                    if not isinstance(entry, dict):
                        continue

                    entry_id = entry.get("entryId", "")
                    content = entry.get("content", {})

                    # Look for tweet content
                    item_content = content.get("itemContent", {})
                    if not item_content:
                        # Try alternative paths
                        item_content = content.get("tweet", {}) or content.get(
                            "tweetResult", {}
                        ).get("result", {})

                    if not item_content:
                        continue

                    # Extract tweet data
                    tweet_data = item_content.get("tweet", {}) or item_content.get(
                        "legacy", {}
                    )
                    if not tweet_data:
                        continue

                    # Get tweet ID
                    tweet_id = (
                        tweet_data.get("id_str")
                        or tweet_data.get("id")
                        or entry_id.replace("tweet-", "")
                    )
                    if not tweet_id:
                        continue

                    # Get content
                    full_text = tweet_data.get("full_text") or tweet_data.get(
                        "text", ""
                    )

                    # Get author
                    user = tweet_data.get("user", {})
                    author = user.get("name", "Unknown")
                    author_handle = user.get("screen_name", "")

                    # Get created_at
                    created_at_str = tweet_data.get("created_at", "")
                    created_at = None
                    if created_at_str:
                        try:
                            from dateutil import parser

                            created_at = parser.parse(created_at_str)
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            pass

                    # Get URL
                    tweet_url = (
                        f"https://x.com/{author_handle}/status/{tweet_id}"
                        if author_handle
                        else f"https://x.com/i/web/status/{tweet_id}"
                    )

                    # Create SocialPost
                    post = SocialPost(
                        platform="twitter",
                        author=author,
                        author_handle=author_handle,
                        content=full_text,
                        created_at=created_at,
                        url=tweet_url,
                        post_type="tweet",
                        is_saved=True,  # These are bookmarks
                        post_id=f"twitter_{tweet_id}",
                    )

                    tweets.append(post)
                    logger.info(
                        f"   ✅ Extracted tweet from API: {tweet_id} by @{author_handle}"
                    )

                except Exception as e:
                    logger.error(f"   ⚠️ Error extracting tweet from entry: {e}")
                    continue

            logger.info(
                f"   ✅ Successfully extracted {len(tweets)} tweets from API response"
            )
            return tweets

        except Exception as e:
            logger.error(f"   ❌ Error parsing API response: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def _scroll_page(self):
        """Scroll the page to load more content"""
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception as e:
            logger.error(f"⚠️ Scroll error: {e}")

    async def get_saved_posts_api_first(
        self,
        limit: int = 50,
        stop_at_post_id: Optional[str] = None,
    ) -> List[SocialPost]:
        """
        Fetch bookmarks purely via Twitter's GraphQL responses instead of DOM scraping.
        Returns newest-first posts and stops once the last collected ID is reached.
        """
        if limit <= 0:
            return []

        if not self.is_authenticated:
            if not await self.authenticate():
                return []

        if not self.page:
            logger.error("Twitter page is not initialized; cannot run API collector")
            return []

        direct_api_posts = await self._collect_saved_posts_via_direct_api(
            limit=limit, stop_at_post_id=stop_at_post_id
        )
        if direct_api_posts:
            logger.info(
                f"📥 Direct GraphQL client returned {len(direct_api_posts)} tweets (limit={limit})"
            )
            return direct_api_posts

        response_promises = []
        bookmarks_event = asyncio.Event()
        request_snapshot: Dict[str, Optional[dict]] = {
            "headers": None,
            "base_url": None,
            "query_params": None,
            "method": None,
            "body": None,
        }

        snapshot_file = Path("logs/twitter_graphql_request.json")
        cached_snapshot: Dict[str, Any] = {}
        if snapshot_file.exists():
            try:
                with snapshot_file.open("r", encoding="utf-8") as fh:
                    cached_snapshot = json.load(fh)
            except Exception as cached_err:
                logger.debug(f"⚠️ Could not load cached Twitter snapshot: {cached_err}")

        def handle_request(request):
            """Capture the outbound GraphQL request template."""
            try:
                url = request.url
            except Exception:
                return

            lower_url = url.lower()
            if "/graphql" not in lower_url:
                return
            if "bookmark" not in lower_url and "timeline" not in lower_url:
                return

            if not request_snapshot["headers"]:
                try:
                    request_snapshot["headers"] = request.headers
                except Exception:
                    pass

            if not request_snapshot["method"]:
                try:
                    request_snapshot["method"] = request.method
                except Exception:
                    pass

            if not request_snapshot["body"]:
                try:
                    body = request.post_data or request.post_data_json
                except Exception:
                    body = None
                if body:
                    request_snapshot["body"] = body

            if not request_snapshot["base_url"]:
                try:
                    parsed = urlparse(url)
                    request_snapshot["base_url"] = (
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    )
                    request_snapshot["query_params"] = parse_qs(parsed.query)
                except Exception:
                    pass

        async def handle_response(response):
            """Capture bookmark GraphQL responses without blocking."""
            try:
                url = response.url
            except Exception:
                return

            lower_url = url.lower()
            if "/graphql" not in lower_url:
                return
            if "bookmark" not in lower_url and "timeline" not in lower_url:
                return
            if response.status != 200:
                return

            response_promises.append((url, response))
            req = response.request
            if req and not request_snapshot["headers"]:
                try:
                    request_snapshot["headers"] = req.headers
                except Exception:
                    pass

            if not request_snapshot["base_url"]:
                try:
                    parsed = urlparse(url)
                    request_snapshot["base_url"] = (
                        f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                    )
                    request_snapshot["query_params"] = parse_qs(parsed.query)
                except Exception:
                    pass

            if not bookmarks_event.is_set():
                bookmarks_event.set()

        self.page.on("request", handle_request)
        self.page.on("response", handle_response)
        if self.context:
            self.context.on("request", handle_request)
            self.context.on("response", handle_response)

        try:
            logger.info("📡 Navigating to bookmarks page (API-first mode)...")
            await self.page.goto(
                "https://x.com/i/bookmarks",
                wait_until="domcontentloaded",
                timeout=30000,
            )
            try:
                await asyncio.wait_for(bookmarks_event.wait(), timeout=15)
            except asyncio.TimeoutError:
                logger.warning(
                    "⚠️ No bookmark GraphQL responses detected within timeout window"
                )
            await self._jitter(1000)
        finally:
            try:
                self.page.off("response", handle_response)
            except Exception:
                pass
            if self.context:
                try:
                    self.context.off("response", handle_response)
                except Exception:
                    pass
                try:
                    self.context.off("request", handle_request)
                except Exception:
                    pass
            try:
                self.page.off("request", handle_request)
            except Exception:
                pass

        def normalize_tweet_id(value: Optional[str]) -> str:
            return self._normalize_tweet_id(value)

        def decode_param(params: Optional[dict], key: str) -> Dict:
            if not params:
                return {}
            raw = params.get(key)
            if not raw:
                return {}
            try:
                return json.loads(raw[0])
            except Exception:
                return {}

        def extract_cursor(api_payload: dict, cursor_type: str = "Bottom") -> Optional[str]:
            def walk(obj):
                if isinstance(obj, dict):
                    entry_id = obj.get("entryId", "")
                    if entry_id and cursor_type.lower() in entry_id.lower():
                        content = obj.get("content", {})
                        if isinstance(content, dict):
                            val = (
                                content.get("value")
                                or content.get("cursorValue")
                                or content.get("text")
                            )
                            if val:
                                return val
                    content = obj.get("content")
                    if isinstance(content, dict):
                        if (
                            content.get("__typename") == "TimelineCursor"
                            and content.get("cursorType") == cursor_type
                        ):
                            val = (
                                content.get("value")
                                or content.get("cursorValue")
                                or content.get("text")
                            )
                            if val:
                                return val
                    for child in obj.values():
                        result = walk(child)
                        if result:
                            return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = walk(item)
                        if result:
                            return result
                return None

            return walk(api_payload)

        def parse_json_value(raw):
            if not raw:
                return {}
            data = raw
            if isinstance(raw, list):
                data = raw[0] if raw else None
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except Exception:
                    return {}
            if isinstance(data, dict):
                return data
            return {}

        def parse_request_body(raw_body):
            if not raw_body:
                return {}
            data = raw_body
            if isinstance(data, bytes):
                data = data.decode("utf-8", errors="ignore")
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except Exception:
                    return {}
            if isinstance(data, dict):
                return data
            return {}

        cached_body_source = (
            request_snapshot.get("body")
            or cached_snapshot.get("body")
            or cached_snapshot.get("body_template")
        )
        body_template = parse_request_body(cached_body_source)
        query_params = (
            request_snapshot.get("query_params")
            or cached_snapshot.get("query_params")
            or {}
        )

        base_request_payload = {
            "base_url": request_snapshot.get("base_url")
            or cached_snapshot.get("base_url"),
            "headers": request_snapshot.get("headers")
            or cached_snapshot.get("headers")
            or {},
            "method": (
                request_snapshot.get("method")
                or cached_snapshot.get("method")
                or "GET"
            ).upper(),
            "body_template": body_template,
            "variables": body_template.get("variables")
            or cached_snapshot.get("variables")
            or parse_json_value(query_params.get("variables")),
            "features": body_template.get("features")
            or body_template.get("extensions", {}).get("features")
            or cached_snapshot.get("features")
            or parse_json_value(query_params.get("features")),
            "field_toggles": body_template.get("fieldToggles")
            or cached_snapshot.get("field_toggles")
            or parse_json_value(query_params.get("fieldToggles")),
            "query_params": query_params,
        }

        # Persist snapshot for debugging (only when we actually captured the template)
        if base_request_payload["base_url"] and base_request_payload["headers"]:
            try:
                logs_dir = Path("logs")
                logs_dir.mkdir(exist_ok=True)
                payload_preview = {
                    "base_url": base_request_payload["base_url"],
                    "method": base_request_payload["method"],
                    "variables": base_request_payload["variables"],
                    "features": base_request_payload["features"],
                    "field_toggles": base_request_payload["field_toggles"],
                    "body_template": base_request_payload["body_template"],
                    "headers": base_request_payload["headers"],
                    "query_params": base_request_payload.get("query_params"),
                    "body": request_snapshot.get("body"),
                }
                with snapshot_file.open("w", encoding="utf-8") as fh:
                    json.dump(payload_preview, fh, indent=2)
                logger.info(
                    f"💾 Saved Twitter GraphQL request snapshot to {snapshot_file}"
                )
            except Exception as snapshot_err:
                logger.debug(f"Could not write Twitter request snapshot: {snapshot_err}")

        def build_graphql_url(base_url: str, variables: dict, features: dict, toggles: dict):
            params = {
                "variables": json.dumps(variables or {}, separators=(",", ":")),
                "features": json.dumps(features or {}, separators=(",", ":")),
            }
            if toggles:
                params["fieldToggles"] = json.dumps(toggles, separators=(",", ":"))
            return f"{base_url}?{urlencode(params)}"

        async def fetch_graphql_page(cursor_value: Optional[str]) -> Optional[dict]:
            if (
                not base_request_payload["base_url"]
                or not base_request_payload["headers"]
                or not getattr(self.context, "request", None)
            ):
                return None

            variables = dict(base_request_payload["variables"] or {})
            if cursor_value:
                variables["cursor"] = cursor_value
            else:
                variables.pop("cursor", None)
            if limit and variables is not None:
                variables["count"] = max(
                    min(limit, 100), int(variables.get("count", 20) or 20)
                )

            headers = {
                k: v
                for k, v in (base_request_payload["headers"] or {}).items()
                if not k.startswith(":")
            }
            headers.setdefault("accept", "application/json, text/plain, */*")
            headers.setdefault("content-type", "application/json")

            request_context = self.context.request
            method = base_request_payload.get("method", "GET")
            try:
                if method == "POST":
                    body = dict(base_request_payload["body_template"] or {})
                    body["variables"] = variables
                    if base_request_payload["features"]:
                        body.setdefault("features", base_request_payload["features"])
                    if base_request_payload["field_toggles"]:
                        body.setdefault(
                            "fieldToggles", base_request_payload["field_toggles"]
                        )
                    resp = await request_context.post(
                        base_request_payload["base_url"],
                        headers=headers,
                        data=json.dumps(body, separators=(",", ":")),
                        timeout=20000,
                    )
                else:
                    full_url = build_graphql_url(
                        base_request_payload["base_url"],
                        variables,
                        base_request_payload["features"],
                        base_request_payload["field_toggles"],
                    )
                    resp = await request_context.get(
                        full_url,
                        headers=headers,
                        timeout=20000,
                    )
                if resp.ok:
                    return await resp.json()
                logger.warning(
                    f"⚠️ GraphQL request failed with status {resp.status}"
                )
            except Exception as exc:
                logger.warning(f"⚠️ GraphQL request error: {exc}")
            return None

        posts: List[SocialPost] = []
        seen_ids: Set[str] = set()
        normalized_stop = normalize_tweet_id(stop_at_post_id)

        def process_payload(payload: dict) -> str:
            """Add tweets from payload; return 'stop', 'full', or 'continue'."""
            tweets = self._extract_tweets_from_api_response(payload) or []
            for tweet in tweets:
                tweet_id = normalize_tweet_id(getattr(tweet, "post_id", None))
                if not tweet_id:
                    continue
                if tweet_id in seen_ids:
                    continue
                if normalized_stop and tweet_id == normalized_stop:
                    logger.info(f"🛑 Reached last collected tweet via API: {tweet_id}")
                    return "stop"
                seen_ids.add(tweet_id)
                posts.append(tweet)
                if len(posts) >= limit:
                    return "full"
            return "continue"

        next_cursor = None
        for url, response in response_promises:
            try:
                text = await response.text()
                if not text or text.strip().startswith("<!DOCTYPE"):
                    continue
                payload = json.loads(text)
            except Exception as exc:
                logger.debug(f"⚠️ Could not parse bookmarks response {url}: {exc}")
                continue

            result = process_payload(payload)
            if result in ("stop", "full"):
                next_cursor = None
                break

            cursor_candidate = extract_cursor(payload, "Bottom")
            if cursor_candidate:
                next_cursor = cursor_candidate

            if len(posts) >= limit:
                break

        if not posts and base_request_payload["base_url"]:
            logger.info(
                "📡 No bookmark responses intercepted; attempting direct GraphQL fetch"
            )
            payload = await fetch_graphql_page(cursor_value=None)
            if payload:
                result = process_payload(payload)
                if result not in ("stop", "full"):
                    next_cursor = extract_cursor(payload, "Bottom")

        pagination_attempts = 0
        while (
            next_cursor
            and len(posts) < limit
            and pagination_attempts < 5
        ):
            pagination_attempts += 1
            payload = await fetch_graphql_page(next_cursor)
            if not payload:
                break
            result = process_payload(payload)
            if result in ("stop", "full"):
                break
            new_cursor = extract_cursor(payload, "Bottom")
            if not new_cursor or new_cursor == next_cursor:
                break
            next_cursor = new_cursor

        logger.info(
            f"📥 API-first collector captured {len(posts)} tweets (limit={limit}, stop_at={stop_at_post_id})"
        )
        if not posts:
            logger.warning("⚠️ API-first collector returned no posts")
        else:
            await self._refresh_and_save_cookies()

        return posts

    async def _collect_saved_posts_via_direct_api(
        self, limit: int, stop_at_post_id: Optional[str]
    ) -> List[SocialPost]:
        """Use cookie-authenticated GraphQL client to fetch bookmarks directly."""
        if not self.context:
            return []

        try:
            cookies_list = await self.context.cookies()
        except Exception as err:
            logger.debug(f"⚠️ Could not read cookies for direct API call: {err}")
            return []

        cookie_map = {}
        for cookie in cookies_list or []:
            name = cookie.get("name")
            value = cookie.get("value")
            if name and value:
                cookie_map[name] = value

        ct0 = cookie_map.get("ct0")
        auth_token = cookie_map.get("auth_token")

        if not ct0 or not auth_token:
            logger.debug(
                "⚠️ Missing ct0/auth_token cookies; skipping direct GraphQL bookmark fetch"
            )
            return []

        client = TwitterAPIClient(cookie_map, auth_token, ct0)
        collected: List[SocialPost] = []
        seen_ids: Set[str] = set()
        normalized_stop = self._normalize_tweet_id(stop_at_post_id)
        cursor: Optional[str] = None

        while len(collected) < limit:
            batch_size = max(1, min(50, limit - len(collected)))
            try:
                batch, next_cursor = await client.get_bookmarks(
                    limit=batch_size, cursor=cursor
                )
            except Exception as exc:
                logger.warning(f"⚠️ Direct Twitter API request failed: {exc}")
                break

            if not batch:
                break

            for tweet in batch:
                tweet_id = self._normalize_tweet_id(tweet.post_id)
                if not tweet_id or tweet_id in seen_ids:
                    continue
                if normalized_stop and tweet_id == normalized_stop:
                    logger.info("🛑 Reached stop tweet via direct API")
                    return collected

                seen_ids.add(tweet_id)
                collected.append(tweet)
                if len(collected) >= limit:
                    break

            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor

        if collected:
            await self._refresh_and_save_cookies()

        return collected

    @staticmethod
    def _normalize_tweet_id(value: Optional[str]) -> str:
        if not value:
            return ""
        text = str(value).strip()
        if text.lower().startswith("twitter_"):
            return text.split("_", 1)[1]
        return text

    async def get_saved_posts(
        self, limit: int = 50, skip_cached_ids: set = None, stop_at_post_id: str = None
    ) -> List[SocialPost]:
        """
        Legacy DOM-based bookmark scraping.
        This path is deprecated and disabled unless TWITTER_DOM_FALLBACK=true.
        Use get_saved_posts_api_first for production.
        """
        if os.getenv("TWITTER_DOM_FALLBACK", "false").lower() not in ("1", "true", "yes"):
            logger.warning(
                "⚠️ Twitter DOM fallback is disabled. Set TWITTER_DOM_FALLBACK=true to re-enable."
            )
            return []
        if not self.is_authenticated:
            if not await self.authenticate():
                return []

        posts = []
        processed_tweet_ids = (
            set(skip_cached_ids) if skip_cached_ids else set()
        )  # Create a copy to avoid modifying the input set
        logger.info(f"🚫 Will skip {len(processed_tweet_ids)} already cached tweets")

        # Track if we've encountered the stop post
        stop_post_encountered = False
        logger.info(
            f"🛑 Will stop collection when reaching post ID: {stop_at_post_id or 'N/A'}"
        )

        try:
            # Navigate to bookmarks using a more natural approach
            # Instead of direct URL navigation, try clicking through the UI
            await self._jitter()
            logger.info("🌐 Navigating to bookmarks page...")
            logger.info(f"   Current URL before navigation: {self.page.url}")

            # First, make sure we're on home page and wait for it to fully load
            if "/home" not in self.page.url and "/i/bookmarks" not in self.page.url:
                logger.info("   Not on home page, navigating to home first...")
                try:
                    await self.page.goto(
                        "https://x.com/home",
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                    # Wait longer for page to fully load and stabilize
                    await self._jitter(3000)
                    logger.info(f"   ✅ On home page: {self.page.url}")
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not navigate to home: {e}")

            # Add human-like behavior: move mouse, scroll a bit
            try:
                logger.info(
                    "   Adding human-like interactions (mouse movement, scroll)..."
                )
                # Small random scroll to simulate human behavior
                await self.page.evaluate("window.scrollBy(0, Math.random() * 200)")
                await self._jitter(1000)

                # Move mouse to simulate human presence
                await self.page.mouse.move(100, 100)
                await self._jitter(500)
                await self.page.mouse.move(200, 150)
                await self._jitter(500)
            except Exception as e:
                logger.warning(f"   ⚠️ Could not add mouse movements: {e}")

            # Wait longer for page to be fully interactive
            logger.info("   Waiting for page to be fully interactive...")
            await self._jitter(2000)

            # Try clicking the bookmarks link in sidebar instead of direct navigation
            # This is more natural and less likely to trigger automation detection
            logger.warning("   Attempting to click bookmarks link in sidebar...")
            bookmarks_clicked = False
            try:
                # Wait for sidebar to load
                await self.page.wait_for_timeout(3000)

                # Try multiple selectors for bookmarks link
                bookmarks_selectors = [
                    'a[href="/i/bookmarks"]',
                    'a[href*="bookmarks"]',
                    '[data-testid="AppTabBar_Bookmarks_Link"]',
                    'nav a[href*="bookmarks"]',
                    'a[aria-label*="Bookmarks"]',
                    'a[aria-label*="bookmarks"]',
                    '[role="link"][href*="bookmarks"]',
                ]

                for selector in bookmarks_selectors:
                    try:
                        bookmarks_link = await self.page.wait_for_selector(
                            selector, timeout=5000, state="visible"
                        )
                        if bookmarks_link:
                            # Hover first (human-like)
                            await bookmarks_link.hover()
                            await self._jitter(800)  # Human pause before clicking

                            # Scroll into view
                            await bookmarks_link.scroll_into_view_if_needed()
                            await self._jitter(500)

                            # Click with human-like delay
                            await bookmarks_link.click(
                                delay=random.randint(50, 150)
                            )  # Random delay like human
                            logger.info(
                                f"   ✅ Clicked bookmarks link using selector: {selector}"
                            )
                            bookmarks_clicked = True

                            # Wait for navigation with longer delay
                            await self._jitter(3000)  # Wait for navigation
                            break
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue

                if not bookmarks_clicked:
                    logger.warning(
                        "   ⚠️ Could not find bookmarks link in sidebar, will try direct navigation"
                    )
            except Exception as e:
                logger.error(f"   ⚠️ Error trying to click bookmarks link: {e}")

            # Set up network request tracking BEFORE navigation (if we're doing direct nav)
            bookmarks_api_called = False
            api_responses = []  # Track all relevant API responses
            api_response_data = None  # Store the actual response data

            # Store response promises to read them later
            response_promises = []

            # Intercept fetch/XHR at JavaScript level to catch GraphQL calls before they're blocked
            await self.page.add_init_script(
                """
                // Intercept fetch to capture GraphQL responses
                const originalFetch = window.fetch;
                window.__twitter_api_responses = [];

                window.fetch = async function(...args) {
                    const url = args[0];
                    if (typeof url === 'string' && (url.includes('graphql') || url.includes('bookmark') || url.includes('/i/api/'))) {
                        console.log('🔍 Intercepting fetch:', url);
                        try {
                            const response = await originalFetch.apply(this, args);
                            const clonedResponse = response.clone();
                            const text = await clonedResponse.text();
                            if (text && text.length > 1000 && !text.trim().startsWith('<!DOCTYPE')) {
                                try {
                                    const json = JSON.parse(text);
                                    window.__twitter_api_responses.push({
                                        url: url,
                                        data: json,
                                        timestamp: Date.now()
                                    });
                                    console.log('✅ Captured API response:', url, Object.keys(json));
                                } catch (e) {
                                    // Not JSON, skip
                                }
                            }
                            return response;
                        } catch (e) {
                            return originalFetch.apply(this, args);
                        }
                    }
                    return originalFetch.apply(this, args);
                };

                // Also intercept XMLHttpRequest
                const originalXHROpen = XMLHttpRequest.prototype.open;
                const originalXHRSend = XMLHttpRequest.prototype.send;
                XMLHttpRequest.prototype.open = function(method, url, ...args) {
                    this._url = url;
                    return originalXHROpen.apply(this, [method, url, ...args]);
                };
                XMLHttpRequest.prototype.send = function(...args) {
                    if (this._url && (this._url.includes('graphql') || this._url.includes('bookmark') || this._url.includes('/i/api/'))) {
                        this.addEventListener('load', function() {
                            if (this.status === 200 && this.responseText && this.responseText.length > 1000) {
                                try {
                                    const json = JSON.parse(this.responseText);
                                    window.__twitter_api_responses.push({
                                        url: this._url,
                                        data: json,
                                        timestamp: Date.now()
                                    });
                                    console.log('✅ Captured XHR response:', this._url);
                                } catch (e) {}
                            }
                        });
                    }
                    return originalXHRSend.apply(this, args);
                };
            """
            )

            async def handle_response(response):
                """Track when bookmarks API responses come in"""
                nonlocal bookmarks_api_called
                url = response.url

                # Twitter uses GraphQL endpoints for bookmarks timeline
                # Check for various patterns that indicate bookmarks data
                is_relevant = any(
                    keyword in url.lower()
                    for keyword in [
                        "/graphql",
                        "bookmarks",
                        "bookmark",
                        "timeline",
                        "/2/timeline",
                        "bookmarktimeline",
                    ]
                )

                if is_relevant and response.status == 200:
                    bookmarks_api_called = True
                    # Store the response to read later (don't await here to avoid blocking)
                    response_promises.append((url, response))
                    logger.info(
                        f"📡 Detected bookmarks API call: {url[:100]}... (will parse after navigation)"
                    )

            # Listen for network responses (set up before navigation)
            self.page.on("response", handle_response)

            # Only do direct navigation if clicking didn't work
            navigation_success = bookmarks_clicked
            nav_errors = []

            # Check if page is still open
            if self.page.is_closed():
                logger.error("   ❌ Page was closed - cannot navigate")
                raise Exception("Page was closed before navigation")

            if not bookmarks_clicked:
                logger.warning("   Attempting direct URL navigation as fallback...")
                # Try multiple navigation strategies

                # Strategy 1: Try domcontentloaded (fastest, most reliable)
                try:
                    if self.page.is_closed():
                        raise Exception("Page closed before navigation")
                    logger.warning("   Attempting navigation with domcontentloaded...")
                    await self.page.goto(
                        "https://x.com/i/bookmarks",
                        wait_until="domcontentloaded",
                        timeout=30000,
                    )
                    logger.info(f"   ✅ Navigation complete (domcontentloaded)")
                    logger.info(f"   URL after navigation: {self.page.url}")
                    navigation_success = True
                except Exception as e:
                    nav_errors.append(f"domcontentloaded: {e}")
                    logger.error(f"   ⚠️ domcontentloaded failed: {e}")
                    # Check if page is still open
                    if self.page.is_closed():
                        logger.error("   ❌ Page was closed during navigation")
                        raise Exception("Page closed during navigation")

                # Strategy 2: Try load if domcontentloaded failed
                if not navigation_success and not self.page.is_closed():
                    try:
                        logger.warning("   Attempting navigation with load...")
                        await self.page.goto(
                            "https://x.com/i/bookmarks",
                            wait_until="load",
                            timeout=60000,
                        )
                        logger.info(f"   ✅ Navigation complete (load)")
                        logger.info(f"   URL after navigation: {self.page.url}")
                        navigation_success = True
                    except Exception as e:
                        nav_errors.append(f"load: {e}")
                        logger.error(f"   ⚠️ load failed: {e}")
                        if self.page.is_closed():
                            logger.error("   ❌ Page was closed during navigation")
                            raise Exception("Page closed during navigation")

                # Strategy 3: Try commit (minimal wait)
                if not navigation_success and not self.page.is_closed():
                    try:
                        logger.warning(
                            "   Attempting navigation with commit (minimal wait)..."
                        )
                        await self.page.goto(
                            "https://x.com/i/bookmarks",
                            wait_until="commit",
                            timeout=30000,
                        )
                        logger.info(f"   ✅ Navigation complete (commit)")
                        logger.info(f"   URL after navigation: {self.page.url}")
                        navigation_success = True
                        # Wait a bit for page to load
                        await self.page.wait_for_timeout(3000)
                    except Exception as e:
                        nav_errors.append(f"commit: {e}")
                        logger.error(f"   ⚠️ commit failed: {e}")

            # Verify we're on bookmarks page (if page is still open)
            if not self.page.is_closed():
                current_url_after_nav = self.page.url
                if "bookmarks" not in current_url_after_nav.lower():
                    logger.warning(
                        f"   ⚠️ Not on bookmarks page after navigation/click. URL: {current_url_after_nav}"
                    )
                    navigation_success = False
            else:
                logger.warning("   ⚠️ Page was closed - cannot verify URL")
                navigation_success = False

            if not navigation_success:
                logger.error(f"   ❌ All navigation strategies failed!")
                for error in nav_errors:
                    logger.error(f"      - {error}")

                # Even if navigation failed, try to extract from API if we have it
                if api_response_data:
                    logger.error(
                        "   💡 Navigation failed but we have API response data - will try to extract from API"
                    )
                else:
                    # Take screenshot to see what happened (only if page is still open)
                    try:
                        if not self.page.is_closed():
                            await self.page.screenshot(
                                path="logs/twitter_navigation_failed.png",
                                full_page=True,
                            )
                            logger.error(
                                f"   📸 Screenshot saved: logs/twitter_navigation_failed.png"
                            )

                            # Also check what URL we're actually on
                            current_url = self.page.url
                            logger.info(f"   📍 Current URL: {current_url}")

                            # Check for error messages
                            try:
                                page_text = await self.page.inner_text("body")
                                if "something went wrong" in page_text.lower():
                                    logger.error(
                                        f"   ⚠️ Page shows 'Something went wrong' error"
                                    )
                                    logger.info(
                                        f"   💡 Twitter detected automation - will try API response extraction"
                                    )
                                if len(page_text) < 200:
                                    logger.warning(
                                        f"   ⚠️ Page has very little content ({len(page_text)} chars)"
                                    )
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                pass
                    except Exception as screenshot_error:
                        logger.error(
                            f"   ⚠️ Could not take screenshot: {screenshot_error}"
                        )

                # Don't raise exception if we have API data to work with
                if not api_response_data:
                    raise Exception(
                        f"Failed to navigate to bookmarks page. Errors: {nav_errors}"
                    )

            # Wait for React app to hydrate and API calls to complete
            logger.info("⏳ Waiting for React app to hydrate and API calls...")
            await self._jitter(2000)  # Initial wait for React hydration

            # Wait for bookmarks API to be called (up to 15 seconds)
            logger.info("⏳ Waiting for bookmarks API response...")
            for i in range(15):
                if bookmarks_api_called:
                    logger.info(f"✅ Bookmarks API response detected after {i+1}s")
                    break
                await self.page.wait_for_timeout(1000)

            if not bookmarks_api_called:
                logger.warning(
                    "⚠️ No bookmarks API call detected, but continuing anyway..."
                )

            # AGGRESSIVE DATA EXTRACTION - Try multiple sources even when page shows error
            logger.warning(
                "🔍 Attempting aggressive data extraction from multiple sources..."
            )

            # Initialize tweets_appeared flag
            tweets_appeared = False

            # Strategy 1: Check JavaScript context for intercepted API responses
            logger.info(
                "   📡 Strategy 1: Checking JavaScript-intercepted API responses..."
            )
            for wait_cycle in range(3):
                try:
                    js_responses = await self.page.evaluate(
                        """
                        () => {
                            return window.__twitter_api_responses || [];
                        }
                    """
                    )

                    if js_responses:
                        logger.info(
                            f"   ✅ Found {len(js_responses)} JS-captured responses!"
                        )
                        for js_resp in js_responses:
                            if js_resp.get("data"):
                                try:
                                    api_tweets = self._extract_tweets_from_api_response(
                                        js_resp["data"]
                                    )
                                    if api_tweets:
                                        logger.info(
                                            f"   🎉 Extracted {len(api_tweets)} tweets from JS data!"
                                        )
                                        for tweet in api_tweets:
                                            if tweet.post_id not in processed_tweet_ids:
                                                posts.append(tweet)
                                                processed_tweet_ids.add(tweet.post_id)
                                        tweets_appeared = True
                                        break
                                except Exception as e:
                                    logger.error(f"Error: {e}")
                                    pass
                        if tweets_appeared:
                            break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                if wait_cycle < 2:
                    await self.page.wait_for_timeout(2000)

            # Strategy 2: Extract from page's JavaScript variables/state
            if not tweets_appeared:
                logger.info(
                    "   📄 Strategy 2: Checking page JavaScript variables for embedded data..."
                )
                try:
                    page_data = await self.page.evaluate(
                        """
                        () => {
                            const data = {};
                            // Check common Twitter data locations
                            if (window.__INITIAL_STATE__) data.initialState = window.__INITIAL_STATE__;
                            if (window.__NEXT_DATA__) data.nextData = window.__NEXT_DATA__;
                            if (window.__APOLLO_STATE__) data.apolloState = window.__APOLLO_STATE__;
                            if (window.__REACT_QUERY_STATE__) data.reactQueryState = window.__REACT_QUERY_STATE__;
                            // Check for any data in script tags
                            const scripts = Array.from(document.querySelectorAll('script'));
                            for (const script of scripts) {
                                const text = script.textContent || script.innerHTML;
                                if (text && text.length > 1000 && (text.includes('bookmark') || text.includes('tweet') || text.includes('entry'))) {
                                    try {
                                        const jsonMatch = text.match(/\{.*"entries".*\}/s);
                                        if (jsonMatch) {
                                            data.scriptData = JSON.parse(jsonMatch[0]);
                                            break;
                                        }
                                    } catch (e) {}
                                }
                            }
                            return data;
                        }
                    """
                    )

                    # Try to extract from any found data
                    for key, value in page_data.items():
                        if value:
                            try:
                                api_tweets = self._extract_tweets_from_api_response(
                                    value
                                )
                                if api_tweets:
                                    logger.info(
                                        f"   🎉 Extracted {len(api_tweets)} tweets from {key}!"
                                    )
                                    for tweet in api_tweets:
                                        if tweet.post_id not in processed_tweet_ids:
                                            posts.append(tweet)
                                            processed_tweet_ids.add(tweet.post_id)
                                    tweets_appeared = True
                                    break
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                pass
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not extract from page variables: {e}")

            # Strategy 3: Check localStorage/sessionStorage
            if not tweets_appeared:
                logger.info(
                    "   💾 Strategy 3: Checking browser storage for cached data..."
                )
                try:
                    storage_data = await self.page.evaluate(
                        """
                        () => {
                            const data = {};
                            try {
                                for (let i = 0; i < localStorage.length; i++) {
                                    const key = localStorage.key(i);
                                    if (key && (key.includes('bookmark') || key.includes('tweet') || key.includes('timeline'))) {
                                        try {
                                            data[key] = JSON.parse(localStorage.getItem(key));
                                        } catch (e) {
                                            data[key] = localStorage.getItem(key);
                                        }
                                    }
                                }
                            } catch (e) {}
                            return data;
                        }
                    """
                    )

                    for key, value in storage_data.items():
                        if value:
                            try:
                                api_tweets = self._extract_tweets_from_api_response(
                                    value
                                )
                                if api_tweets:
                                    logger.info(
                                        f"   🎉 Extracted {len(api_tweets)} tweets from storage!"
                                    )
                                    for tweet in api_tweets:
                                        if tweet.post_id not in processed_tweet_ids:
                                            posts.append(tweet)
                                            processed_tweet_ids.add(tweet.post_id)
                                    tweets_appeared = True
                                    break
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                pass
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            # Strategy 4: Parse HTML for embedded JSON data
            if not tweets_appeared:
                logger.debug("   🔍 Strategy 4: Parsing HTML for embedded JSON data...")
                try:
                    html_content = await self.page.content()
                    # Look for JSON in script tags
                    import re

                    json_patterns = [
                        r'<script[^>]*>.*?(\{.*?"entries".*?\}).*?</script>',
                        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
                        r"window\.__NEXT_DATA__\s*=\s*(\{.*?\});",
                    ]

                    for pattern in json_patterns:
                        matches = re.findall(pattern, html_content, re.DOTALL)
                        for match in matches:
                            try:
                                data = json.loads(match)
                                api_tweets = self._extract_tweets_from_api_response(
                                    data
                                )
                                if api_tweets:
                                    logger.info(
                                        f"   🎉 Extracted {len(api_tweets)} tweets from HTML JSON!"
                                    )
                                    for tweet in api_tweets:
                                        if tweet.post_id not in processed_tweet_ids:
                                            posts.append(tweet)
                                            processed_tweet_ids.add(tweet.post_id)
                                    tweets_appeared = True
                                    break
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                pass
                        if tweets_appeared:
                            break
                except Exception as e:
                    logger.warning(f"   ⚠️ Could not parse HTML: {e}")

            # Now read the actual response data (fallback)
            logger.info("📥 Reading API response data from network layer...")
            if not response_promises:
                logger.warning(
                    "   ⚠️ No API response promises stored - responses may have been missed"
                )
            else:
                logger.info(
                    f"   📊 Found {len(response_promises)} API response(s) to read"
                )

            for url, response in response_promises:
                try:
                    logger.info(f"   📖 Reading response from: {url[:80]}...")
                    response_text = await response.text()
                    if (
                        response_text and len(response_text) > 1000
                    ):  # Substantial response
                        api_responses.append(
                            {
                                "url": url[:150],
                                "status": response.status,
                                "has_content": len(response_text) > 100,
                                "size": len(response_text),
                            }
                        )
                        logger.info(
                            f"📡 Reading API response: {url[:100]}... ({len(response_text)} chars)"
                        )

                        # Save full response for debugging
                        try:
                            debug_path = f"logs/twitter_api_response_full_{len(response_text)}.json"
                            with open(debug_path, "w", encoding="utf-8") as f:
                                f.write(response_text)
                            logger.info(f"   💾 Saved full API response to {debug_path}")
                        except Exception as save_error:
                            logger.error(
                                f"   ⚠️ Could not save full response: {save_error}"
                            )

                        # Check if response is actually JSON (not HTML error page)
                        if response_text.strip().startswith(
                            "<!DOCTYPE"
                        ) or response_text.strip().startswith("<html"):
                            logger.error(
                                f"   ⚠️ Response is HTML (error page), not JSON - skipping"
                            )
                            continue

                        # Try to parse JSON and extract tweet data
                        try:
                            data = json.loads(response_text)
                            api_response_data = data
                            logger.info(f"✅ Successfully parsed API response JSON")

                            # Print structure for debugging
                            if isinstance(data, dict):
                                logger.info(
                                    f"   Response top-level keys: {list(data.keys())[:20]}"
                                )

                                # Try multiple paths to find tweet data
                                def find_any_tweet_data(obj, path="", depth=0):
                                    """Recursively find any tweet-like data structures"""
                                    if depth > 10:  # Prevent infinite recursion
                                        return None

                                    if isinstance(obj, dict):
                                        # Check for common tweet indicators
                                        if "full_text" in obj or "text" in obj:
                                            return obj
                                        if "tweet" in obj:
                                            return obj.get("tweet")
                                        if "legacy" in obj:
                                            return obj.get("legacy")
                                        if "entries" in obj:
                                            entries = obj.get("entries", [])
                                            if entries and isinstance(entries[0], dict):
                                                return entries[0]
                                        if "instructions" in obj:
                                            instructions = obj.get("instructions", [])
                                            for inst in instructions:
                                                if (
                                                    isinstance(inst, dict)
                                                    and "entries" in inst
                                                ):
                                                    entries = inst.get("entries", [])
                                                    if entries:
                                                        return (
                                                            entries[0]
                                                            if isinstance(
                                                                entries[0], dict
                                                            )
                                                            else entries
                                                        )

                                        # Recursively search
                                        for key, value in obj.items():
                                            result = find_any_tweet_data(
                                                value, f"{path}.{key}", depth + 1
                                            )
                                            if result:
                                                return result

                                    elif isinstance(obj, list) and len(obj) > 0:
                                        # Check first item
                                        result = find_any_tweet_data(
                                            obj[0], f"{path}[0]", depth + 1
                                        )
                                        if result:
                                            return result

                                    return None

                                # Try to find tweet data
                                sample_tweet = find_any_tweet_data(data)
                                if sample_tweet:
                                    logger.info(
                                        f"   ✅ Found tweet-like data structure!"
                                    )
                                    logger.info(
                                        f"   Sample keys: {list(sample_tweet.keys())[:15] if isinstance(sample_tweet, dict) else 'Not a dict'}"
                                    )

                                # Look for timeline instructions which contain tweet entries
                                def find_timeline_instructions(obj, path=""):
                                    """Recursively find timeline instructions in GraphQL response"""
                                    if isinstance(obj, dict):
                                        if "instructions" in obj:
                                            return obj.get("instructions", [])
                                        if "timeline" in obj:
                                            return find_timeline_instructions(
                                                obj["timeline"], path + ".timeline"
                                            )
                                        if "entries" in obj:
                                            return obj.get("entries", [])
                                        for key, value in obj.items():
                                            result = find_timeline_instructions(
                                                value, f"{path}.{key}"
                                            )
                                            if result:
                                                return result
                                    elif isinstance(obj, list):
                                        for i, item in enumerate(obj):
                                            result = find_timeline_instructions(
                                                item, f"{path}[{i}]"
                                            )
                                            if result:
                                                return result
                                    return None

                                instructions = find_timeline_instructions(data)
                                if instructions:
                                    logger.info(
                                        f"   ✅ Found timeline instructions in API response!"
                                    )
                                    # Count tweet entries
                                    entry_count = 0
                                    for instruction in instructions:
                                        if (
                                            isinstance(instruction, dict)
                                            and "entries" in instruction
                                        ):
                                            entry_count += len(
                                                instruction.get("entries", [])
                                            )
                                    logger.info(
                                        f"   📊 Found {entry_count} entries in timeline instructions"
                                    )
                                else:
                                    logger.warning(
                                        f"   ⚠️ No timeline instructions found - checking alternative structures..."
                                    )

                                    # Try to find entries directly
                                    def count_entries(obj, count=0):
                                        if isinstance(obj, dict):
                                            if "entries" in obj:
                                                count += len(obj.get("entries", []))
                                            for value in obj.values():
                                                count = count_entries(value, count)
                                        elif isinstance(obj, list):
                                            for item in obj:
                                                count = count_entries(item, count)
                                        return count

                                    total_entries = count_entries(data)
                                    if total_entries > 0:
                                        logger.info(
                                            f"   📊 Found {total_entries} total entries in response"
                                        )
                        except json.JSONDecodeError as json_error:
                            logger.error(
                                f"⚠️ API response is not valid JSON: {json_error}"
                            )
                            # Try to save a sample for debugging
                            try:
                                sample_path = "logs/twitter_api_response_sample.txt"
                                with open(sample_path, "w", encoding="utf-8") as f:
                                    f.write(response_text[:10000])  # First 10000 chars
                                logger.info(
                                    f"   💾 Saved API response sample to {sample_path}"
                                )
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                pass
                except Exception as e:
                    logger.warning(f"⚠️ Could not read API response: {e}")
                    import traceback

                    traceback.print_exc()

            # CRITICAL: Wait for actual tweet elements to appear in DOM (React has rendered)
            logger.info("⏳ Waiting for tweets to render in DOM...")
            tweets_appeared = False
            working_selector = None
            tweet_count = 0

            # More comprehensive selectors to try (updated for current Twitter/X structure)
            test_selectors = [
                'article[data-testid="tweet"]',  # Most specific
                '[data-testid="tweet"]',  # More flexible
                'article[role="article"]',  # Generic article
                '[role="article"]',  # Most generic
                'div[data-testid="cellInnerDiv"]',  # Container
                '[data-testid="cellInnerDiv"]',  # Container without tag
                'section[data-testid="cellInnerDiv"]',  # Section variant
                'div[role="article"]',  # Div with article role
                '[data-testid="tweetText"]',  # Tweet text element (parent might be tweet)
                'div[data-testid="tweet"]',  # Div variant
                '[data-testid="primaryColumn"] article',  # Articles in main column
                '[data-testid="primaryColumn"] [role="article"]',  # Articles in main column
            ]

            for attempt in range(
                60
            ):  # Wait up to 60 seconds for tweets to appear (increased for slow loading)
                try:
                    # Try each selector
                    for selector in test_selectors:
                        try:
                            # Use wait_for_selector with timeout to check if element exists
                            # This is more reliable than query_selector_all for waiting
                            try:
                                await self.page.wait_for_selector(
                                    selector, timeout=1000, state="attached"
                                )
                                # If we get here, element exists - now count them
                                elements = await self.page.query_selector_all(selector)
                                if len(elements) > 0:
                                    tweet_count = len(elements)
                                    working_selector = selector
                                    tweets_appeared = True
                                    logger.warning(
                                        f"✅ Found {tweet_count} tweet elements after {attempt+1}s (selector: {selector})"
                                    )
                                    break
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                # Selector didn't find element, try next
                                continue
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            continue

                    if tweets_appeared:
                        break

                    # Also try a more aggressive approach: check if page has any content at all
                    if attempt % 5 == 0:  # Every 5 seconds
                        page_text = await self.page.inner_text("body")
                        if len(page_text) > 1000:  # Page has substantial content
                            logger.info(
                                f"📄 Page has content ({len(page_text)} chars), but no tweets found yet..."
                            )

                except Exception as e:
                    logger.error(
                        f"⚠️ Error checking for tweets (attempt {attempt+1}): {e}"
                    )

                await self.page.wait_for_timeout(1000)

            # Check for "Something went wrong" error early and try API extraction
            try:
                if not self.page.is_closed():
                    page_text = await self.page.inner_text("body")
                    if "something went wrong" in page_text.lower():
                        logger.warning(
                            "   ⚠️ Page shows 'Something went wrong' - Twitter detected automation"
                        )
                        logger.error(
                            "   💡 Attempting to extract from API response even though page shows error..."
                        )

                        # Try to get API data from JavaScript context again
                        try:
                            js_responses = await self.page.evaluate(
                                """
                                () => {
                                    return window.__twitter_api_responses || [];
                                }
                            """
                            )
                            if js_responses:
                                logger.debug(
                                    f"   🔍 Found {len(js_responses)} JS-captured responses despite error page"
                                )
                                for js_resp in js_responses:
                                    if js_resp.get("data"):
                                        api_response_data = js_resp["data"]
                                        break
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            pass

                        # Don't wait for DOM - try API extraction immediately
                        if api_response_data:
                            api_tweets = self._extract_tweets_from_api_response(
                                api_response_data
                            )
                            if api_tweets:
                                logger.info(
                                    f"   ✅ Successfully extracted {len(api_tweets)} tweets from API!"
                                )
                                for tweet in api_tweets:
                                    if tweet.post_id not in processed_tweet_ids:
                                        posts.append(tweet)
                                        processed_tweet_ids.add(tweet.post_id)
                                tweets_appeared = True
                                logger.info(
                                    f"   🎉 Bypassed automation detection by using API data!"
                                )
                        else:
                            logger.warning(
                                "   ⚠️ No API response data available to extract from"
                            )
            except Exception as e:
                logger.error(f"   ⚠️ Error checking page: {e}")

            if not tweets_appeared:
                logger.warning("⚠️ No tweets found in DOM after waiting 60s")
                logger.info(f"   API responses detected: {len(api_responses)}")
                if api_responses:
                    logger.debug("   API response details:")
                    for resp in api_responses[:3]:  # Show first 3
                        logger.info(
                            f"     - {resp['url']} (status: {resp['status']}, content: {resp['has_content']})"
                        )

                # If we have API response data, try to extract tweets from it
                # This works even when Twitter shows "Something went wrong" error page
                if api_response_data:
                    logger.warning(
                        "   🔄 Attempting to extract tweets from API response data..."
                    )
                    logger.error(
                        "   💡 This works even if page shows error - API response has the data!"
                    )
                    try:
                        api_tweets = self._extract_tweets_from_api_response(
                            api_response_data
                        )
                        if api_tweets:
                            logger.info(
                                f"   ✅ Successfully extracted {len(api_tweets)} tweets from API response!"
                            )
                            # Add these to posts list
                            for tweet in api_tweets:
                                if tweet.post_id not in processed_tweet_ids:
                                    posts.append(tweet)
                                    processed_tweet_ids.add(tweet.post_id)
                                    logger.info(
                                        f"   ✅ Added tweet from API: {tweet.post_id}"
                                    )
                            tweets_appeared = (
                                True  # Mark as found so we don't continue DOM scraping
                            )
                            logger.info(
                                f"   🎉 Using API response data instead of DOM (automation detected but data extracted!)"
                            )
                    except Exception as api_extract_error:
                        logger.error(
                            f"   ⚠️ Failed to extract tweets from API response: {api_extract_error}"
                        )
                        import traceback

                        traceback.print_exc()
                elif api_responses and any(r.get("has_content") for r in api_responses):
                    logger.warning(
                        "   ⚠️ API responses detected but data not parsed yet"
                    )
                    logger.info("   💡 Will try to read API responses now...")
                    # Try to read responses now
                    for url, response_info in response_promises:
                        try:
                            if isinstance(response_info, tuple):
                                url, response = response_info
                                response_text = await response.text()
                                if response_text and len(response_text) > 1000:
                                    try:
                                        data = json.loads(response_text)
                                        api_tweets = (
                                            self._extract_tweets_from_api_response(data)
                                        )
                                        if api_tweets:
                                            logger.info(
                                                f"   ✅ Extracted {len(api_tweets)} tweets from delayed API read!"
                                            )
                                            for tweet in api_tweets:
                                                if (
                                                    tweet.post_id
                                                    not in processed_tweet_ids
                                                ):
                                                    posts.append(tweet)
                                                    processed_tweet_ids.add(
                                                        tweet.post_id
                                                    )
                                            tweets_appeared = True
                                            break
                                    except Exception as e:
                                        logger.error(f"Error: {e}")
                                        pass
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            pass

                # Debug: Check what's actually on the page
                if not self.page.is_closed():
                    try:
                        page_text = await self.page.inner_text("body")
                        logger.info(f"   📄 Page text length: {len(page_text)} chars")
                        # Check for common indicators
                        if "bookmark" in page_text.lower():
                            logger.info("   ✅ Page contains 'bookmark' text")
                        if "tweet" in page_text.lower():
                            logger.info("   ✅ Page contains 'tweet' text")
                        if "something went wrong" in page_text.lower():
                            logger.warning(
                                "   ⚠️ Page shows 'Something went wrong' - Twitter detected automation"
                            )
                            logger.info(
                                "   💡 Will try to use API response data instead of DOM"
                            )

                        # Try to find ANY article or div elements
                        all_articles = await self.page.query_selector_all("article")
                        all_divs = await self.page.query_selector_all("div[role]")
                        logger.info(
                            f"   📊 Found {len(all_articles)} <article> elements"
                        )
                        logger.info(
                            f"   📊 Found {len(all_divs)} <div> elements with role attribute"
                        )

                        # Check for primary column
                        primary_col = await self.page.query_selector(
                            '[data-testid="primaryColumn"]'
                        )
                        if primary_col:
                            logger.info("   ✅ Found primaryColumn element")
                            col_text = await primary_col.inner_text()
                            logger.info(
                                f"   📄 Primary column text length: {len(col_text)} chars"
                            )
                    except Exception as e:
                        logger.warning(f"   ⚠️ Could not analyze page structure: {e}")

                if not tweets_appeared:
                    logger.warning(
                        "   ⚠️ Will try scrolling to trigger lazy loading..."
                    )
            else:
                logger.info(f"✅ Tweets appeared! Using selector: {working_selector}")

            # Final wait for any remaining rendering
            await self.page.wait_for_timeout(2000)
            logger.info("✅ Finished waiting for content to load")

            # Take early screenshot for debugging (before scrolling)
            try:
                screenshot_path = "logs/twitter_bookmarks_initial.png"
                Path("logs").mkdir(parents=True, exist_ok=True)
                await self.page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"📸 Initial page screenshot saved: {screenshot_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not take initial screenshot: {e}")

            # Check if bookmarks page loaded - try multiple selectors
            logger.info("⏳ Waiting for page structure to load...")
            page_loaded = False

            # Try multiple selectors that indicate the page has loaded
            selectors_to_try = [
                '[data-testid="primaryColumn"]',  # Main column
                'main[role="main"]',  # Main content area
                'article[data-testid="tweet"]',  # Tweet articles
                '[data-testid="cellInnerDiv"]',  # Tweet container
                "body",  # Fallback - body always exists
            ]

            for selector in selectors_to_try:
                try:
                    await self.page.wait_for_selector(
                        selector, timeout=5000, state="attached"
                    )
                    logger.info(f"✅ Page structure loaded (found: {selector})")
                    page_loaded = True
                    break
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue

            if not page_loaded:
                # Last resort: check if URL is correct and page has loaded
                current_url = self.page.url
                if "bookmarks" in current_url:
                    logger.warning(
                        "⚠️ Could not find expected selectors, but URL is correct"
                    )
                    logger.info("   Continuing with URL verification only...")
                    # Wait a bit more for dynamic content
                    await self._jitter(3000)
                else:
                    logger.error(
                        f"❌ Could not access bookmarks page - URL is {current_url}, expected bookmarks"
                    )
                    # Take screenshot for debugging
                    try:
                        screenshot_path = "logs/twitter_bookmarks_error.png"
                        Path("logs").mkdir(parents=True, exist_ok=True)
                        await self.page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"📸 Screenshot saved: {screenshot_path}")
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass
                    return []

            # CRITICAL: Verify we're on bookmarks page before collecting
            current_url = self.page.url
            logger.info(f"📍 Current URL after navigation: {current_url}")

            # Wait a moment for any redirects
            await self.page.wait_for_timeout(2000)
            final_url = self.page.url
            if final_url != current_url:
                logger.warning(f"   ⚠️ URL changed after wait: {final_url}")
                current_url = final_url

            # Check page title
            try:
                page_title = await self.page.title()
                logger.info(f"   📄 Page title: {page_title}")
            except Exception as e:
                logger.warning(f"   ⚠️ Could not get page title: {e}")

            # Check for any error messages on the page
            try:
                page_text = await self.page.inner_text("body")
                if "something went wrong" in page_text.lower():
                    logger.warning(
                        f"   ⚠️ Page contains 'something went wrong' message"
                    )
                if "automation" in page_text.lower() or "bot" in page_text.lower():
                    logger.warning(
                        f"   ⚠️ Page may contain automation detection message"
                    )
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            if "bookmarks" not in current_url.lower():
                logger.error(
                    f"❌ CRITICAL: Not on bookmarks page! Current URL: {current_url}"
                )
                logger.error(
                    f"   Aborting to avoid collecting non-bookmarked feed posts"
                )
                # Take screenshot for debugging
                try:
                    screenshot_path = "logs/twitter_wrong_page.png"
                    Path("logs").mkdir(parents=True, exist_ok=True)
                    await self.page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"📸 Screenshot saved: {screenshot_path}")
                    logger.info(
                        f"   Please check the screenshot to see what page we're on"
                    )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                return []

            logger.info(f"✅ Verified on bookmarks page: {current_url}")

            # Additional verification: Check for bookmarks page indicator
            try:
                # Look for bookmarks page header or indicator
                bookmarks_indicator = await self.page.query_selector(
                    'h1:has-text("Bookmarks"), [data-testid="primaryColumn"] h1, [aria-label*="Bookmarks"]'
                )
                if not bookmarks_indicator:
                    # Try checking page title
                    page_title = await self.page.title()
                    if "bookmark" not in page_title.lower():
                        logger.warning(
                            f"⚠️ Warning: Page title doesn't indicate bookmarks: {page_title}"
                        )
                        logger.info(
                            f"   Continuing anyway, but will verify each tweet is bookmarked"
                        )
            except Exception as e:
                logger.warning(f"⚠️ Could not verify bookmarks page indicator: {e}")
                # Continue anyway - we'll verify each tweet individually

            # Wait for tweets to start loading (they load dynamically)
            logger.info("⏳ Waiting for tweets to load...")
            await self._jitter(
                5000
            )  # Give extra time for tweets to load (increased from 3000)

            # Try to trigger React rendering by interacting with the page
            try:
                # Scroll a tiny bit to trigger any lazy loading
                await self.page.evaluate("window.scrollBy(0, 100)")
                await self.page.wait_for_timeout(1000)
                # Scroll back
                await self.page.evaluate("window.scrollBy(0, -100)")
                await self.page.wait_for_timeout(1000)
                logger.info("✅ Triggered initial scroll interaction")
            except Exception as e:
                logger.warning(f"⚠️ Could not trigger scroll interaction: {e}")

            # IMPORTANT: Scroll to trigger lazy loading (Twitter loads content on scroll)
            # If we already found tweets, we might not need to scroll yet
            if not tweets_appeared or tweet_count == 0:
                logger.info("📜 Scrolling to trigger content loading...")
                # Scroll multiple times to trigger lazy loading (increased attempts)
                for scroll_i in range(5):  # Increased from 3 to 5
                    await self._scroll_page()
                    await self.page.wait_for_timeout(
                        2000
                    )  # Wait between scrolls (increased from 1500)

                    # Check if tweets appeared after scroll using all selectors
                    for selector in test_selectors:
                        try:
                            elements = await self.page.query_selector_all(selector)
                            if len(elements) > tweet_count:
                                logger.info(
                                    f"✅ Scroll {scroll_i+1}: Found {len(elements)} tweets (was {tweet_count}) with selector: {selector}"
                                )
                                tweet_count = len(elements)
                                tweets_appeared = True
                                if not working_selector:
                                    working_selector = selector
                                break
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            continue

                    if tweets_appeared:
                        break

                await self._jitter(
                    3000
                )  # Wait after scrolls for content to load (increased from 2000)
                await self.page.wait_for_timeout(
                    3000
                )  # Extra wait for dynamic content (increased from 2000)
            else:
                logger.info(
                    f"✅ Tweets already found ({tweet_count}), skipping initial scroll"
                )

            # Check for empty state (but be more specific - don't match header text)
            try:
                # Look for specific empty state indicators (not just any mention of bookmarks)
                empty_state_selectors = [
                    '[data-testid="emptyState"]',
                    'div:has-text("You haven\'t added any Tweets to your Bookmarks yet")',
                    'div:has-text("Save Tweets for later")',
                ]
                is_empty = False
                for selector in empty_state_selectors:
                    try:
                        empty_element = await self.page.query_selector(selector)
                        if empty_element:
                            is_empty = True
                            logger.info(
                                "ℹ️ Bookmarks page appears to be empty (found empty state indicator)"
                            )
                            break
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue

                # Also check page text for very specific empty messages
                if not is_empty:
                    page_text = await self.page.inner_text("body")
                    # Only match very specific empty state messages (not generic "bookmarks" text)
                    specific_empty_messages = [
                        "you haven't added any tweets to your bookmarks yet",
                        "save tweets for later",
                    ]
                    if any(msg in page_text.lower() for msg in specific_empty_messages):
                        # But only return empty if we also don't find any tweet elements
                        # (sometimes the message appears but tweets are loading)
                        tweet_check = await self.page.query_selector_all(
                            'article[data-testid="tweet"]'
                        )
                        if len(tweet_check) == 0:
                            logger.info("ℹ️ Bookmarks page appears to be empty")
                            logger.info(
                                "   This account may not have any bookmarked tweets"
                            )
                            return []
            except Exception as e:
                logger.warning(f"⚠️ Could not check empty state: {e}")
                # Continue anyway - better to try than to give up

            # Try multiple selectors to find tweets (after scrolling) - updated for current Twitter/X
            tweet_selectors = [
                'article[data-testid="tweet"]',  # Standard tweet article
                '[data-testid="tweet"]',  # Just the data-testid (more flexible)
                'article[role="article"]',  # Alternative article selector
                'div[data-testid="tweet"]',  # Div variant
                '[role="article"]',  # Generic article role
                '[data-testid="cellInnerDiv"]',  # Tweet container cell
                'section[data-testid="cellInnerDiv"]',  # Section variant
                'div[role="article"]',  # Div with article role
                '[data-testid="primaryColumn"] article',  # Articles in main column
                '[data-testid="primaryColumn"] [role="article"]',  # Articles in main column
                '[data-testid="primaryColumn"] [data-testid="tweet"]',  # Tweets in main column
            ]

            tweets_found = False
            working_selector = None

            # Try all selectors and report what we find
            for selector in tweet_selectors:
                try:
                    logger.debug(f"🔍 Trying selector: {selector}")
                    elements = await self.page.query_selector_all(selector)
                    logger.info(f"   Found {len(elements)} elements")
                    if len(elements) > 0:
                        logger.info(
                            f"✅ Found {len(elements)} elements with selector: {selector}"
                        )
                        tweets_found = True
                        working_selector = selector
                        break
                except Exception as e:
                    logger.error(f"   Selector failed: {e}")
                    continue

            if not tweets_found:
                logger.warning(
                    "⚠️ No tweets found with any selector after initial scroll"
                )
                logger.info("   Will try more scrolling - Twitter loads content lazily")
                # Scroll a few more times to trigger loading
                for i in range(3):
                    logger.warning(f"📜 Additional scroll attempt {i+1}/3...")
                    await self._scroll_page()
                    await self.page.wait_for_timeout(2000)
                    # Check again after each scroll
                    for selector in tweet_selectors[:3]:  # Try top 3 selectors
                        try:
                            elements = await self.page.query_selector_all(selector)
                            if len(elements) > 0:
                                logger.info(
                                    f"✅ Found {len(elements)} tweets after scroll {i+1} with: {selector}"
                                )
                                tweets_found = True
                                working_selector = selector
                                break
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            continue
                    if tweets_found:
                        break

                if not tweets_found:
                    # Take screenshot for debugging
                    try:
                        screenshot_path = "logs/twitter_bookmarks_no_tweets.png"
                        Path("logs").mkdir(parents=True, exist_ok=True)
                        await self.page.screenshot(path=screenshot_path, full_page=True)
                        logger.info(f"📸 Screenshot saved: {screenshot_path}")

                        # Also save page HTML for debugging
                        try:
                            html_path = "logs/twitter_bookmarks_page.html"
                            html_content = await self.page.content()
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(html_content)
                            logger.info(f"📄 Page HTML saved: {html_path}")
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            pass
                    except Exception as screenshot_error:
                        logger.error(
                            f"⚠️ Could not take screenshot: {screenshot_error}"
                        )

                # Still continue - use first selector as fallback and let scrolling logic handle it
                working_selector = tweet_selectors[0]  # Use first as fallback

            logger.info(f"📥 Starting to extract Twitter bookmarks (target: {limit})...")

            # Improved scrolling mechanism
            scroll_attempts = 0
            max_scroll_attempts = 50  # default upper bound
            if self.scroll_limit_cfg:
                try:
                    max_scroll_attempts = max(
                        1, min(max_scroll_attempts, int(self.scroll_limit_cfg))
                    )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
            no_new_content_count = 0
            last_tweet_count = 0

            while (
                len(posts) < limit
                and scroll_attempts < max_scroll_attempts
                and not stop_post_encountered
            ):
                try:
                    # Get all tweet articles on the page with fresh query
                    # Use the working selector we found, or try all selectors again
                    tweet_elements = []
                    if working_selector:
                        tweet_elements = await self.page.query_selector_all(
                            working_selector
                        )
                    else:
                        # Try all selectors and use the one that finds elements
                        for selector in tweet_selectors:
                            elements = await self.page.query_selector_all(selector)
                            if len(elements) > 0:
                                tweet_elements = elements
                                working_selector = selector
                                logger.info(
                                    f"✅ Found working selector during scroll: {selector}"
                                )
                                break

                    current_tweet_count = len(tweet_elements)

                    logger.debug(
                        f"📊 Scroll attempt {scroll_attempts + 1}: Found {current_tweet_count} tweet elements on page"
                    )

                    # Process all tweets but check for duplicates properly
                    new_tweets_found = 0
                    processed_this_scroll = set()  # Track what we process this scroll

                    for i, tweet_element in enumerate(tweet_elements):
                        if len(posts) >= limit:
                            break

                        try:
                            # Validate element is still attached to DOM
                            try:
                                await tweet_element.bounding_box()
                            except Exception as e:
                                logger.warning(
                                    f"⚠️ Tweet element {i} no longer valid, skipping: {e}"
                                )
                                continue

                            # CRITICAL: Verify this tweet is actually bookmarked
                            # Check for bookmark button with aria-pressed="true" or "Remove bookmark" label
                            is_bookmarked = False
                            try:
                                # Method 1: Check for aria-pressed="true" on bookmark button
                                bookmark_button = await tweet_element.query_selector(
                                    '[data-testid="bookmark"]'
                                )
                                if bookmark_button:
                                    aria_pressed = await bookmark_button.get_attribute(
                                        "aria-pressed"
                                    )
                                    if aria_pressed == "true":
                                        is_bookmarked = True
                                        logger.info(
                                            f"✅ Tweet {i}: Verified bookmark (aria-pressed=true)"
                                        )

                                    # Method 2: Check button text/label for "Remove" or "Saved"
                                    if not is_bookmarked:
                                        button_text = await bookmark_button.inner_text()
                                        aria_label = (
                                            await bookmark_button.get_attribute(
                                                "aria-label"
                                            )
                                            or ""
                                        )

                                        if any(
                                            keyword in button_text.lower()
                                            or keyword in aria_label.lower()
                                            for keyword in [
                                                "remove",
                                                "saved",
                                                "bookmarked",
                                            ]
                                        ):
                                            is_bookmarked = True
                                            logger.info(
                                                f"✅ Tweet {i}: Verified bookmark (label check)"
                                            )

                                # Method 3: Check for "Remove bookmark" text anywhere in tweet
                                if not is_bookmarked:
                                    tweet_text = await tweet_element.inner_text()
                                    if (
                                        "remove bookmark" in tweet_text.lower()
                                        or "saved" in tweet_text.lower()
                                    ):
                                        # This is less reliable, but as fallback
                                        is_bookmarked = True
                                        logger.info(
                                            f"✅ Tweet {i}: Verified bookmark (text fallback)"
                                        )

                            except Exception as bookmark_check_error:
                                logger.error(
                                    f"⚠️ Error checking bookmark status for tweet {i}: {bookmark_check_error}"
                                )
                                # If we can't verify, skip to be safe
                                logger.warning(
                                    f"⏭️ Skipping tweet {i}: Cannot verify bookmark status"
                                )
                                continue

                            if not is_bookmarked:
                                logger.info(
                                    f"⏭️ Skipping tweet {i}: Not bookmarked (bookmark button not pressed)"
                                )
                                continue

                            # Extract tweet data with thread handling
                            tweet_data = await self._extract_tweet_data_with_threads(
                                tweet_element, is_saved=True
                            )
                            if tweet_data:
                                # Helper function to normalize Twitter post IDs for comparison
                                def normalize_twitter_id(post_id: str) -> str:
                                    """Normalize Twitter post ID by removing 'twitter_' prefix if present"""
                                    if not post_id:
                                        return ""
                                    post_id = str(post_id).strip()
                                    # Remove 'twitter_' prefix if present (case-insensitive)
                                    if post_id.lower().startswith("twitter_"):
                                        return post_id[8:]  # len('twitter_') = 8
                                    return post_id

                                # Check if we've reached the stop post (normalize for comparison)
                                if stop_at_post_id:
                                    normalized_tweet_id = normalize_twitter_id(
                                        tweet_data.post_id
                                    )
                                    normalized_stop_id = normalize_twitter_id(
                                        str(stop_at_post_id)
                                    )

                                    if (
                                        normalized_tweet_id
                                        and normalized_stop_id
                                        and normalized_tweet_id == normalized_stop_id
                                    ):
                                        logger.info(
                                            f"🛑 Reached stop post ID: {stop_at_post_id} (matched: {tweet_data.post_id})"
                                        )
                                        stop_post_encountered = True
                                        break

                                # Check if we already processed this tweet
                                if tweet_data.post_id in processed_tweet_ids:
                                    # CRITICAL: Check if this duplicate is the stop post
                                    # If so, we should stop collection (even though it's a duplicate)
                                    if stop_at_post_id:
                                        normalized_tweet_id = normalize_twitter_id(
                                            tweet_data.post_id
                                        )
                                        normalized_stop_id = normalize_twitter_id(
                                            str(stop_at_post_id)
                                        )

                                        if (
                                            normalized_tweet_id
                                            and normalized_stop_id
                                            and normalized_tweet_id
                                            == normalized_stop_id
                                        ):
                                            logger.info(
                                                f"🛑 Reached stop post ID (duplicate): {stop_at_post_id} (matched: {tweet_data.post_id})"
                                            )
                                            stop_post_encountered = True
                                            break

                                    logger.debug(
                                        f"⏭️ Skipped already processed tweet: {tweet_data.post_id}"
                                    )
                                    continue

                                # Check if we processed this tweet in this scroll
                                if tweet_data.post_id in processed_this_scroll:
                                    logger.debug(
                                        f"⏭️ Skipped duplicate in this scroll: {tweet_data.post_id}"
                                    )
                                    continue

                                # Double-check for duplicates by content/URL (more robust)
                                is_duplicate = False
                                for existing_post in posts:
                                    if (
                                        existing_post.post_id == tweet_data.post_id
                                        or existing_post.url == tweet_data.url
                                        or (
                                            existing_post.content == tweet_data.content
                                            and len(tweet_data.content) > 10
                                        )
                                    ):
                                        is_duplicate = True
                                        break

                                if not is_duplicate:
                                    posts.append(tweet_data)
                                    processed_tweet_ids.add(tweet_data.post_id)
                                    processed_this_scroll.add(tweet_data.post_id)
                                    new_tweets_found += 1
                                    logger.info(
                                        f"✅ Extracted NEW tweet {len(posts)}: @{tweet_data.author_handle}"
                                    )

                                    # Periodic cookie refresh during collection (sophisticated approach like Threads)
                                    # Refresh cookies every 10 tweets to keep them fresh
                                    if len(posts) % 10 == 0:
                                        logger.info(
                                            f"🔄 Refreshing cookies periodically (every 10 tweets)..."
                                        )
                                        await self._auto_refresh_cookies_if_needed()
                                else:
                                    logger.debug(
                                        f"⏭️ Skipped duplicate tweet: {tweet_data.post_id}"
                                    )
                            else:
                                logger.warning(
                                    f"⚠️ Could not extract tweet data from element {i}"
                                )

                        except Exception as e:
                            logger.error(f"⚠️ Error processing tweet element {i}: {e}")
                            continue

                    # Update progress and scroll if needed
                    if new_tweets_found > 0:
                        logger.debug(
                            f"🔍 Found {new_tweets_found} new tweets in this scroll"
                        )
                        no_new_content_count = 0  # Reset counter
                    else:
                        no_new_content_count += 1
                        logger.debug(f"🔍 No new tweets found in this scroll")

                    # Check if we should scroll for more content
                    if len(posts) < limit and not stop_post_encountered:
                        if no_new_content_count >= 5:  # Increased from 3 to 5
                            logger.warning(
                                "🛑 No new content loaded after 5 attempts, stopping..."
                            )
                            break

                        # Periodic cookie refresh during scrolling (sophisticated approach like Threads)
                        # Refresh cookies every 5 scroll attempts to keep them fresh
                        if scroll_attempts > 0 and scroll_attempts % 5 == 0:
                            logger.info(
                                f"🔄 Refreshing cookies periodically (every 5 scrolls)..."
                            )
                            await self._auto_refresh_cookies_if_needed()

                        # If no tweets found at all yet, try scrolling anyway (might trigger loading)
                        if current_tweet_count == 0 and scroll_attempts < 3:
                            logger.warning(
                                f"📜 No tweets found yet, scrolling to trigger loading (attempt {scroll_attempts + 1})..."
                            )
                            scroll_attempts += 1
                            await self._scroll_page()
                            await self._jitter(1000)  # Wait longer after scroll
                            await self.page.wait_for_timeout(
                                2000
                            )  # Extra wait for content
                            continue  # Go back to check for tweets

                        if current_tweet_count > last_tweet_count:
                            last_tweet_count = current_tweet_count
                            scroll_attempts += 1
                            logger.info("📜 Scrolling to load more content...")
                            await self._scroll_page()
                            await self._jitter(500)  # Increased wait time
                            await self.page.wait_for_timeout(
                                1000
                            )  # Extra wait for dynamic content
                            logger.info(
                                f"📈 Progress: {len(posts)}/{limit} tweets extracted"
                            )
                        elif (
                            current_tweet_count == last_tweet_count
                            and current_tweet_count > 0
                        ):
                            # Same count but we have tweets - might need more scrolling
                            scroll_attempts += 1
                            logger.info("📜 Scrolling to load more tweets...")
                            await self._scroll_page()
                            await self._jitter(500)
                            await self.page.wait_for_timeout(1500)
                            logger.info(
                                f"📈 Progress: {len(posts)}/{limit} tweets extracted"
                            )
                        else:
                            logger.info("🛑 No more tweets loading, stopping...")
                            break
                    else:
                        # We've either reached our limit or encountered the stop post
                        if stop_post_encountered:
                            logger.info("🛑 Stopped collection at last collected post")
                        break

                except Exception as e:
                    logger.error(
                        f"⚠️ Error during scroll attempt {scroll_attempts + 1}: {e}"
                    )
                    scroll_attempts += 1
                    if scroll_attempts >= max_scroll_attempts:
                        logger.warning("🛑 Max scroll attempts reached")
                        break
                    await self.page.wait_for_timeout(3000)

            logger.info(f"✅ Retrieved {len(posts)} bookmarked tweets from Twitter")

            # AUTO-REFRESH: Refresh cookies after successful collection (sophisticated approach like Threads)
            # This keeps cookies fresh and prevents expiration issues
            refresh_success = await self._refresh_and_save_cookies()
            if refresh_success:
                logger.info("✅ Cookies refreshed and saved after collection")
            else:
                logger.error("⚠️ Cookie refresh failed (but collection succeeded)")

            return posts

        except Exception as e:
            logger.error(f"❌ Error getting saved tweets: {e}")
            import traceback

            traceback.print_exc()
            return []

    async def get_liked_posts(self, limit: int = 50) -> List[SocialPost]:
        """Get liked tweets from Twitter"""
        if not self.is_authenticated:
            if not await self.authenticate():
                return []

        posts = []

        try:
            # Navigate to likes page
            await self._jitter()
            await self.page.goto(
                f"https://x.com/{self.username}/likes",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await self._jitter(300)

            # Similar scrolling logic as bookmarks
            tweets_collected = 0
            scroll_attempts = 0
            max_scroll_attempts = 20

            while tweets_collected < limit and scroll_attempts < max_scroll_attempts:
                tweet_elements = await self.page.query_selector_all(
                    'article[data-testid="tweet"]'
                )

                for tweet_element in tweet_elements[tweets_collected:]:
                    if tweets_collected >= limit:
                        break

                    try:
                        tweet_data = await self._extract_tweet_data_with_threads(
                            tweet_element, is_saved=False
                        )
                        if tweet_data:
                            posts.append(tweet_data)
                            tweets_collected += 1
                    except Exception as e:
                        logger.error(f"⚠️ Error processing liked tweet: {e}")
                        continue

                await self.page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await self._jitter(200)
                scroll_attempts += 1

                new_tweet_count = len(
                    await self.page.query_selector_all('article[data-testid="tweet"]')
                )
                if new_tweet_count == len(tweet_elements):
                    break

            logger.info(f"✅ Retrieved {len(posts)} liked tweets from Twitter")

        except Exception as e:
            logger.error(f"❌ Error getting Twitter likes: {e}")

        return posts

    async def _extract_tweet_data_with_threads(
        self, tweet_element, is_saved: bool = True
    ) -> Optional[SocialPost]:
        """Extract tweet data with improved thread handling - avoids navigation to prevent DOM issues"""
        try:
            # First extract the main tweet
            main_tweet = await self._extract_tweet_data(tweet_element, is_saved)
            if not main_tweet:
                return None

            # Check for thread indicators without navigation
            has_thread_indicator = False
            try:
                # Look for "Show this thread" link or thread indicators
                thread_elements = await tweet_element.query_selector_all(
                    'a[role="link"]'
                )
                for element in thread_elements:
                    try:
                        text = await element.inner_text()
                        if any(
                            indicator in text.lower()
                            for indicator in ["show this thread", "thread", "show more"]
                        ):
                            has_thread_indicator = True
                            break
                    except Exception as e:
                        logger.error(f"⚠️ Error reading thread element: {e}")
                        continue

                # Also check for reply indicators (tweets that look like they continue)
                if not has_thread_indicator:
                    content = main_tweet.content.strip()
                    if (
                        content.endswith("...")
                        or content.endswith("/1")
                        or content.endswith("1/")
                        or "thread" in content.lower()
                        or content.count("\n") > 3
                    ):  # Long tweets often indicate threads
                        has_thread_indicator = True

            except Exception as e:
                logger.error(f"⚠️ Error checking thread indicators: {e}")

            # Mark thread if detected (extraction will happen in second pass)
            if has_thread_indicator:
                main_tweet.post_type = "thread"
                if self.extract_threads:
                    logger.info(
                        "🧵 Thread detected (will extract full content in second pass)"
                    )
                else:
                    logger.info(
                        "🧵 Thread detected but extraction disabled (config: extract_threads=false)"
                    )

            return main_tweet

        except Exception as e:
            logger.error(f"❌ Error extracting tweet with threads: {e}")
            return await self._extract_tweet_data(tweet_element, is_saved)

    async def _extract_full_thread(
        self, tweet_url: str, author_handle: str
    ) -> Optional[str]:
        """Navigate to tweet URL and extract the full thread content with enhanced scrolling"""
        try:
            # Save current page URL to return to it later
            current_url = self.page.url

            # Extract tweet ID from URL
            tweet_id = (
                tweet_url.split("/status/")[-1].split("?")[0]
                if "/status/" in tweet_url
                else None
            )
            if not tweet_id:
                logger.error("❌ Could not extract tweet ID from URL")
                return None

            logger.info(f"🔗 Navigating to tweet: {tweet_url}")
            logger.info(f"🆔 Tweet ID: {tweet_id}")

            # Try multiple navigation strategies
            navigation_successful = False

            # Strategy 1: Direct navigation
            try:
                await self.page.goto(tweet_url, wait_until="load", timeout=15000)
                await self.page.wait_for_timeout(3000)

                # Check if we're on the right page
                current_page_url = self.page.url
                if "/status/" in current_page_url and tweet_id in current_page_url:
                    navigation_successful = True
                    logger.info("✅ Direct navigation successful")
                else:
                    logger.warning(
                        f"⚠️ Direct navigation failed. Current URL: {current_page_url}"
                    )
            except Exception as e:
                logger.error(f"⚠️ Direct navigation error: {e}")

            # Strategy 2: Try twitter.com instead of x.com
            if not navigation_successful:
                try:
                    twitter_url = tweet_url.replace("x.com", "twitter.com")
                    logger.info(f"🔄 Trying twitter.com: {twitter_url}")
                    await self.page.goto(twitter_url, wait_until="load", timeout=15000)
                    await self.page.wait_for_timeout(3000)

                    current_page_url = self.page.url
                    if "/status/" in current_page_url and tweet_id in current_page_url:
                        navigation_successful = True
                        logger.info("✅ Twitter.com navigation successful")
                    else:
                        logger.warning(
                            f"⚠️ Twitter.com navigation failed. Current URL: {current_page_url}"
                        )
                except Exception as e:
                    logger.error(f"⚠️ Twitter.com navigation error: {e}")

            # Strategy 3: Search for the tweet from user's profile
            if not navigation_successful:
                try:
                    logger.debug(
                        f"🔍 Trying to find tweet via user profile: @{author_handle}"
                    )
                    profile_url = f"https://x.com/{author_handle.replace('@', '')}"
                    await self.page.goto(profile_url, wait_until="load", timeout=15000)
                    await self.page.wait_for_timeout(3000)

                    # Look for the specific tweet on the profile
                    tweet_links = await self.page.query_selector_all(
                        f'a[href*="/status/{tweet_id}"]'
                    )
                    if tweet_links:
                        logger.info("🎯 Found tweet link on profile, clicking...")
                        await tweet_links[0].click()
                        await self.page.wait_for_timeout(3000)

                        current_page_url = self.page.url
                        if (
                            "/status/" in current_page_url
                            and tweet_id in current_page_url
                        ):
                            navigation_successful = True
                            logger.info("✅ Profile navigation successful")
                        else:
                            logger.warning(
                                f"⚠️ Profile navigation failed. Current URL: {current_page_url}"
                            )
                    else:
                        logger.warning("⚠️ Could not find tweet on user profile")
                except Exception as e:
                    logger.error(f"⚠️ Profile navigation error: {e}")

            if not navigation_successful:
                logger.error("❌ All navigation strategies failed")
                return None

            # Try to click "Show this thread" or similar buttons with stable selectors
            try:
                # Multiple strategies to find and click thread expansion
                thread_selectors = [
                    'a[href*="/status/"]:has-text("Show this thread")',
                    'a:has-text("Show this thread")',
                    'a[role="link"]:has-text("Show this thread")',
                    'button:has-text("Show this thread")',
                    'a:has-text("Show more")',
                ]
                
                expansion_clicked = False
                for selector in thread_selectors:
                    try:
                        buttons = await self.page.query_selector_all(selector)
                        for button in buttons[:1]:  # Only try first match
                            if await button.is_visible():
                                await button.scroll_into_view_if_needed()
                                await self._jitter(500)
                                await button.click()
                                await self.page.wait_for_timeout(2000)
                                logger.debug(f"✅ Clicked thread expansion with selector: {selector}")
                                expansion_clicked = True
                                break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                    if expansion_clicked:
                        break
                
                # Fallback: try finding by text content
                if not expansion_clicked:
                    try:
                        all_links = await self.page.query_selector_all('a[role="link"]')
                        for link in all_links[:10]:  # Limit search to first 10
                            try:
                                text = await link.inner_text()
                                if text and any(
                                    phrase in text.lower()
                                    for phrase in ["show this thread", "show more", "thread"]
                                ):
                                    if await link.is_visible():
                                        await link.scroll_into_view_if_needed()
                                        await self._jitter(500)
                                        await link.click()
                                        await self.page.wait_for_timeout(2000)
                                        logger.debug(f"✅ Clicked thread expansion by text: {text}")
                                        break
                            except Exception:
                                continue
                    except Exception as e:
                        logger.debug(f"Fallback expansion click failed: {e}")
            except Exception as e:
                logger.warning(f"⚠️ Could not click thread expansion: {e}")

            # Scroll down to load more tweets in the thread
            logger.info("📜 Scrolling to load more thread content...")
            for scroll_attempt in range(3):
                await self.page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await self.page.wait_for_timeout(2000)

                # Check if new content loaded
                new_tweet_count = len(
                    await self.page.query_selector_all('article[data-testid="tweet"]')
                )
                logger.warning(
                    f"   Scroll {scroll_attempt + 1}: Found {new_tweet_count} tweets"
                )

            # Find all tweets in the thread from the same author AND valuable replies
            thread_parts = []
            valuable_replies = []

            # Get all tweet articles on the page after scrolling
            tweet_elements = await self.page.query_selector_all(
                'article[data-testid="tweet"]'
            )
            logger.debug(
                f"📊 Found {len(tweet_elements)} tweets on thread page after scrolling"
            )

            # Verify we found the target author's tweets
            target_author_found = False
            found_authors = []
            for element in tweet_elements:
                try:
                    author_element = await element.query_selector(
                        '[data-testid="User-Name"] a'
                    )
                    if author_element:
                        href = await author_element.get_attribute("href")
                        if href:
                            handle = href.split("/")[-1]
                            found_authors.append(handle)
                            # More flexible matching - remove @ and compare case-insensitively
                            clean_target = author_handle.replace("@", "").lower()
                            clean_found = handle.lower()
                            if clean_target == clean_found:
                                target_author_found = True
                                break
                except Exception as e:
                    logger.error(f"⚠️ Error checking author: {e}")
                    continue

            if not target_author_found:
                logger.warning(f"⚠️ Target author @{author_handle} not found on page.")
                logger.debug(f"🔍 Found authors: {list(set(found_authors))}")
                # Don't return None immediately - let's try to extract anyway if we have tweets
                if not tweet_elements:
                    return None

            for tweet_element in tweet_elements:
                try:
                    # Check if this tweet is from the same author
                    author_element = await tweet_element.query_selector(
                        '[data-testid="User-Name"] a'
                    )
                    if not author_element:
                        continue

                    tweet_author_handle = await author_element.get_attribute("href")
                    if tweet_author_handle:
                        tweet_author_handle = tweet_author_handle.split("/")[-1]

                        # Only include tweets from the same author (flexible matching)
                        clean_target = author_handle.replace("@", "").lower()
                        clean_found = tweet_author_handle.lower()
                        if clean_target == clean_found:
                            # Extract the tweet content
                            text_element = await tweet_element.query_selector(
                                '[data-testid="tweetText"]'
                            )
                            if text_element:
                                content = await text_element.inner_text()
                                if content and content.strip():
                                    # Get tweet timestamp to maintain order
                                    time_element = await tweet_element.query_selector(
                                        "time"
                                    )
                                    timestamp = ""
                                    tweet_id = ""
                                    if time_element:
                                        timestamp = await time_element.get_attribute(
                                            "datetime"
                                        )
                                        # Try to get tweet ID from the link
                                        parent_link = await time_element.query_selector(
                                            "xpath=.."
                                        )
                                        if parent_link:
                                            href = await parent_link.get_attribute(
                                                "href"
                                            )
                                            if href and "/status/" in href:
                                                tweet_id = href.split("/status/")[
                                                    -1
                                                ].split("?")[0]

                                    # Avoid duplicates by checking tweet ID
                                    if not any(
                                        part.get("tweet_id") == tweet_id
                                        for part in thread_parts
                                        if tweet_id
                                    ):
                                        thread_parts.append(
                                            {
                                                "content": content.strip(),
                                                "timestamp": timestamp,
                                                "tweet_id": tweet_id,
                                            }
                                        )
                                        logger.debug(
                                            f"   📝 Found thread part {len(thread_parts)}: {content[:50]}..."
                                        )

                except Exception as e:
                    logger.error(f"⚠️ Error processing thread tweet: {e}")
                    continue

            # Sort by timestamp to maintain thread order
            if thread_parts:
                thread_parts.sort(key=lambda x: x.get("timestamp", ""))

                # Combine all thread parts
                full_content = "\n\n".join([part["content"] for part in thread_parts])
                logger.info(
                    f"✅ Extracted thread with {len(thread_parts)} parts, {len(full_content)} characters"
                )

                # Return to original page (bookmarks)
                try:
                    await self.page.goto(current_url, wait_until="load", timeout=30000)
                    await self.page.wait_for_timeout(2000)
                    logger.info("✅ Returned to bookmarks page")
                except Exception as e:
                    logger.warning(f"⚠️ Could not return to original page: {e}")
                    # Force return to bookmarks if current_url doesn't work
                    try:
                        await self.page.goto(
                            "https://x.com/i/bookmarks",
                            wait_until="load",
                            timeout=30000,
                        )
                        await self.page.wait_for_timeout(2000)
                        logger.info("✅ Force navigated back to bookmarks")
                    except Exception as e:
                        logger.error(f"❌ Failed to return to bookmarks: {e}")

                return full_content
            else:
                logger.error("❌ No thread parts found")

        except Exception as e:
            logger.error(f"❌ Error extracting full thread: {e}")

        # Try to return to original page even if extraction failed
        try:
            await self.page.goto(current_url, wait_until="load", timeout=30000)
            await self.page.wait_for_timeout(2000)
            logger.error("✅ Returned to bookmarks page after failed extraction")
        except Exception as e:
            logger.error(f"⚠️ Failed to return to original page: {e}")
            # Force return to bookmarks
            try:
                await self.page.goto(
                    "https://x.com/i/bookmarks", wait_until="load", timeout=30000
                )
                await self.page.wait_for_timeout(2000)
                logger.error("✅ Force navigated back to bookmarks after failure")
            except Exception as e2:
                logger.error(
                    f"❌ Failed to return to bookmarks after thread extraction failure: {e2}"
                )

        return None

    async def _extract_tweet_data(
        self, tweet_element, is_saved: bool = True
    ) -> Optional[SocialPost]:
        """Extract data from a single tweet element, handling various content types."""
        try:
            # Check if element is still valid and attached to DOM
            try:
                await tweet_element.bounding_box()
            except Exception as e:
                logger.warning(f"⚠️ Tweet element no longer valid, skipping: {e}")
                return None

            # Skip promotional tweets
            if await tweet_element.query_selector('[data-testid="promotedIndicator"]'):
                logger.info("⏭️ Skipping promotional tweet.")
                return None

            # Main tweet content - extract BEFORE and AFTER "Show more" click
            content = ""
            initial_content = ""
            truncation_flag = False
            thread_part = None
            thread_total = None

            def _tweet_looks_truncated(initial_text: str, final_text: str) -> bool:
                initial_text = (initial_text or "").strip()
                final_text = (final_text or "").strip()
                if not final_text:
                    return bool(initial_text)
                ellipsis = final_text.endswith(("…", "..."))
                very_short = len(final_text) < 50 and len(initial_text) > len(
                    final_text
                )
                no_growth = (
                    initial_text
                    and len(final_text) <= len(initial_text)
                    and initial_text.endswith(("…", "..."))
                )
                ratio_gap = (
                    len(initial_text) > 0
                    and len(final_text) < len(initial_text) * 0.6
                    and (len(initial_text) - len(final_text)) > 80
                )
                return (ellipsis and very_short) or no_growth or ratio_gap

            # ALWAYS try to expand tweets - more aggressive approach
            expanded = False
            try:
                # IMPORTANT: Scroll tweet into view first
                await tweet_element.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(1000)

                logger.debug("🔍 Aggressively checking for truncated content...")

                # First, get initial content to check if it's truncated
                initial_text_element = await tweet_element.query_selector(
                    '[data-testid="tweetText"]'
                )
                initial_content = ""
                if initial_text_element:
                    initial_content = await initial_text_element.inner_text()
                    logger.info(
                        f"📄 Initial content length: {len(initial_content)} chars"
                    )

                # Try multiple comprehensive selectors for "Show more" button
                show_more_selectors = [
                    '[data-testid="tweet-text-show-more-button"]',
                    'div[role="button"]:has-text("Show more")',
                    'span:has-text("Show more")',
                    '[dir="ltr"]:has-text("Show more")',
                    '[aria-label*="Show more"]',
                    'button:has-text("Show more")',
                    'a:has-text("Show more")',
                    # More generic selectors
                    'div[tabindex="0"]:has-text("Show more")',
                    'span[role="button"]:has-text("Show more")',
                    '[data-testid*="show-more"]',
                ]

                # Also try looking for ellipsis or truncated indicators
                truncation_indicators = [
                    'span:has-text("…")',
                    'div:has-text("…")',
                    '[data-testid*="truncate"]',
                ]

                logger.debug(
                    f"🔍 Found {len(show_more_selectors)} show more selectors to try"
                )

                for i, selector in enumerate(show_more_selectors):
                    try:
                        # Look for show more buttons within this tweet element
                        show_more_buttons = await tweet_element.query_selector_all(
                            selector
                        )
                        logger.info(
                            f"   Selector {i+1} ({selector}): Found {len(show_more_buttons)} elements"
                        )

                        for j, button in enumerate(show_more_buttons):
                            try:
                                # Multiple checks to ensure we have the right button
                                is_visible = await button.is_visible()
                                if not is_visible:
                                    logger.info(
                                        f"     Button {j+1}: Not visible, skipping"
                                    )
                                    continue

                                # Get button text and attributes
                                button_text = await button.inner_text()
                                aria_label = (
                                    await button.get_attribute("aria-label") or ""
                                )

                                logger.info(
                                    f"     Button {j+1}: text='{button_text}', aria_label='{aria_label}'"
                                )

                                # Check if this looks like a show more button
                                text_lower = button_text.lower()
                                if (
                                    ("show" in text_lower and "more" in text_lower)
                                    or "show more" in aria_label.lower()
                                    or "expand" in text_lower
                                ):
                                    logger.info(
                                        f"🔽 Clicking 'Show more' button {j+1}: '{button_text}'..."
                                    )

                                    # Scroll button into view again
                                    await button.scroll_into_view_if_needed()
                                    await self.page.wait_for_timeout(500)

                                    # Try multiple click methods
                                    try:
                                        await button.click(force=True)
                                        logger.info("     ✅ Direct click successful")
                                    except Exception as click_error:
                                        logger.error(
                                            f"     ⚠️ Direct click failed: {click_error}"
                                        )
                                        try:
                                            await button.evaluate("el => el.click()")
                                            logger.info(
                                                "     ✅ JavaScript click successful"
                                            )
                                        except Exception as js_error:
                                            logger.error(
                                                f"     ❌ JavaScript click failed: {js_error}"
                                            )
                                            continue

                                    # Wait for expansion
                                    await self.page.wait_for_timeout(3000)

                                    # Verify expansion worked by checking content length
                                    new_text_element = (
                                        await tweet_element.query_selector(
                                            '[data-testid="tweetText"]'
                                        )
                                    )
                                    if new_text_element:
                                        new_content = (
                                            await new_text_element.inner_text()
                                        )
                                        if len(new_content) > len(initial_content):
                                            expanded = True
                                            logger.info(
                                                f"✅ Tweet expanded! Content grew from {len(initial_content)} to {len(new_content)} chars"
                                            )
                                            break
                                        else:
                                            logger.warning(
                                                f"⚠️ Content didn't expand: {len(new_content)} chars (was {len(initial_content)})"
                                            )

                                    expanded = True  # Assume success if no error
                                    break

                            except Exception as btn_e:
                                logger.error(f"     Button {j+1} failed: {btn_e}")
                                continue

                        if expanded:
                            break

                    except Exception as e:
                        logger.error(f"   Selector {i+1} failed: {e}")
                        continue

                # If no show more buttons found, still try to extract anyway
                if not expanded:
                    logger.info(
                        "ℹ️ No 'Show more' buttons found - proceeding with current content"
                    )

            except Exception as e:
                logger.error(f"⚠️ Show more detection error: {e}")

            # Extract tweet content (AFTER expansion if button was clicked)
            try:
                # If we expanded, wait a bit longer and re-query the element
                if expanded:
                    await self.page.wait_for_timeout(1500)  # Extra wait for DOM update
                    logger.info("⏳ Waiting for DOM to update after expansion...")

                # Query for text element (fresh query after expansion)
                text_element = await tweet_element.query_selector(
                    '[data-testid="tweetText"]'
                )

                if text_element:
                    logger.info("📄 Found tweet text element, extracting content...")
                    # Try to get ALL text content, including nested spans
                    content = await text_element.inner_text()
                    logger.info(f"📝 Initial extraction: {len(content)} chars")

                    # Always try to get comprehensive content even if not truncated
                    try:
                        # Get all spans and build comprehensive text
                        all_spans = await text_element.query_selector_all("span")
                        if all_spans:
                            logger.debug(
                                f"🔍 Found {len(all_spans)} spans, building comprehensive text..."
                            )
                            texts = []
                            for i, span in enumerate(
                                all_spans[:50]
                            ):  # Limit to avoid too many
                                try:
                                    span_text = await span.inner_text()
                                    if (
                                        span_text
                                        and span_text.strip()
                                        and span_text not in texts
                                    ):
                                        texts.append(span_text.strip())
                                except Exception as e:
                                    logger.error(f"Error: {e}")
                                    continue

                            if texts:
                                # Join and clean up the text
                                alt_content = " ".join(texts)
                                # Remove common duplicates and clean up
                                alt_content = " ".join(alt_content.split())

                                original_length = len(content)
                                if len(alt_content) > len(content):
                                    content = alt_content
                                    improvement = len(content) - original_length
                                    logger.info(
                                        f"✅ Comprehensive extraction: {len(content)} chars (improved by {improvement})"
                                    )
                                else:
                                    logger.info(
                                        f"ℹ️ Comprehensive extraction same length: {len(alt_content)} chars"
                                    )
                    except Exception as span_error:
                        logger.error(f"⚠️ Span extraction error: {span_error}")

                    # Check if content still looks truncated
                    if content and (content.endswith("…") or content.endswith("...")):
                        logger.warning(
                            "⚠️ Content still appears truncated, trying alternative selectors..."
                        )
                        # Try alternative selectors
                        alt_selectors = [
                            '[data-testid="tweetText"] div',
                            '[data-testid="tweetText"] p',
                            "div[lang] span",
                            '[dir="auto"] span',
                        ]

                        for alt_selector in alt_selectors:
                            try:
                                alt_elements = await tweet_element.query_selector_all(
                                    alt_selector
                                )
                                if alt_elements:
                                    alt_texts = []
                                    for el in alt_elements:
                                        try:
                                            el_text = await el.inner_text()
                                            if el_text and el_text not in alt_texts:
                                                alt_texts.append(el_text)
                                        except Exception as e:
                                            logger.error(f"Error: {e}")
                                            continue
                                    if alt_texts:
                                        alt_content = " ".join(alt_texts)
                                        if len(alt_content) > len(content):
                                            content = alt_content
                                            logger.info(
                                                f"✅ Alternative extraction improved length to {len(content)} chars"
                                            )
                                            break
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                continue
                else:
                    logger.error("❌ No tweet text element found")
                    content = ""

                # Final logging
                if content:
                    logger.info(f"🎯 Final content extracted: {len(content)} chars")
                    if len(content) < 50:
                        logger.warning(
                            "⚠️ WARNING: Very short content - may be truncated"
                        )
                else:
                    logger.error("❌ No content extracted")

            except Exception as e:
                logger.error(f"⚠️ Error extracting tweet text: {e}")
                content = ""

            # Handle quoted tweets
            try:
                quoted_tweet_element = await tweet_element.query_selector(
                    'div[role="link"] > div.css-1dbjc4n > div > div'
                )
                if quoted_tweet_element:
                    quoted_author_element = await quoted_tweet_element.query_selector(
                        'div[data-testid="User-Name"] span'
                    )
                    quoted_author = (
                        await quoted_author_element.inner_text()
                        if quoted_author_element
                        else "Unknown"
                    )

                    quoted_text_element = await quoted_tweet_element.query_selector(
                        '[data-testid="tweetText"]'
                    )
                    quoted_text = (
                        await quoted_text_element.inner_text()
                        if quoted_text_element
                        else ""
                    )

                    content += (
                        f"\n\n--- Quoted Tweet by @{quoted_author} ---\n{quoted_text}"
                    )
            except Exception as e:
                logger.error(f"⚠️ Error extracting quoted tweet: {e}")
                pass

            try:
                author_element = await tweet_element.query_selector(
                    '[data-testid="User-Name"] span'
                )
                author = (
                    await author_element.inner_text() if author_element else "Unknown"
                )

                handle_element = await tweet_element.query_selector(
                    'a[role="link"][data-testid*="User-Name"]'
                )
                author_handle = ""
                if handle_element:
                    href = await handle_element.get_attribute("href")
                    if href:
                        # Extract username from href like "/username" or "/username/status/123"
                        parts = href.split("/")
                        username = parts[1] if len(parts) > 1 else ""
                        if username and username not in [
                            "i",
                            "home",
                            "explore",
                            "notifications",
                        ]:
                            author_handle = f"@{username}"

                # Fallback: try to extract from author name or other elements
                if not author_handle:
                    # Try alternate selectors
                    try:
                        handle_text = await tweet_element.query_selector(
                            '[data-testid="User-Name"] span:has-text("@")'
                        )
                        if handle_text:
                            text = await handle_text.inner_text()
                            if text.startswith("@"):
                                author_handle = text.split()[0]  # Get first @mention
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass

                # Last resort: try to get from link element's href
                if not author_handle:
                    try:
                        # Look for any link in the tweet that might have username
                        time_elem = await tweet_element.query_selector("time")
                        if time_elem:
                            parent_link = await time_elem.query_selector("xpath=..")
                            if parent_link:
                                href = await parent_link.get_attribute("href")
                                if href and "/status/" in href:
                                    # Extract from URL format: /username/status/123
                                    parts = href.split("/")
                                    if len(parts) > 1:
                                        username = parts[1]
                                        if username and username not in ["i", "home"]:
                                            author_handle = f"@{username}"
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        pass

            except Exception as e:
                logger.error(f"⚠️ Error extracting author info: {e}")
                author = "Unknown"
                author_handle = ""

            time_element = await tweet_element.query_selector("time")
            tweet_url = ""
            tweet_id = ""
            if time_element:
                # First try to get the tweet URL from the time element's parent link
                parent_link = await time_element.query_selector("xpath=..")
                if parent_link:
                    href = await parent_link.get_attribute("href")
                    if href:
                        tweet_url = (
                            f"https://x.com{href}" if href.startswith("/") else href
                        )
                        # Extract tweet ID from URL
                        match = re.search(r"/status/(\d+)", tweet_url)
                        if match:
                            tweet_id = match.group(1)

                # If we still don't have an ID, try to get it from the tweet element's data attributes
                if not tweet_id:
                    try:
                        # Try to get the tweet ID from the article element's data attributes
                        article_element = await tweet_element.query_selector(
                            "xpath=ancestor-or-self::article"
                        )
                        if article_element:
                            tweet_id = await article_element.get_attribute(
                                "data-tweet-id"
                            )
                            if not tweet_id and tweet_url:
                                # Fallback to extracting from URL if available
                                match = re.search(r"/status/(\d+)", tweet_url)
                                if match:
                                    tweet_id = match.group(1)
                    except Exception as e:
                        logger.error(
                            f"⚠️ Error extracting tweet ID from data attributes: {e}"
                        )

            # If we still don't have an ID, generate a fallback ID using content hash
            if not tweet_id and content:
                import hashlib

                content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:10]
                tweet_id = f"fallback_{content_hash}"
                logger.warning(f"⚠️ Generated fallback tweet ID: {tweet_id}")

            # Set the post_id in the tweet data
            post_id = (
                f"twitter_{tweet_id}"
                if tweet_id
                else f"twitter_{int(datetime.now().timestamp())}"
            )

            # Get the timestamp from the time element
            created_at_str = (
                await time_element.get_attribute("datetime") if time_element else None
            )
            if created_at_str:
                try:
                    # Convert to datetime object and ensure it's timezone-aware
                    if created_at_str.endswith("Z"):
                        created_at = datetime.fromisoformat(
                            created_at_str[:-1] + "+00:00"
                        )
                    else:
                        created_at = datetime.fromisoformat(created_at_str)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    logger.info(f"🕒 Parsed tweet timestamp: {created_at.isoformat()}")
                except Exception as e:
                    logger.error(f"⚠️ Error parsing timestamp '{created_at_str}': {e}")
                    created_at = datetime.now(timezone.utc)
            else:
                logger.warning("⚠️ No timestamp found, using current time")
                created_at = datetime.now(timezone.utc)

            engagement = {}
            engagement_selectors = {
                "replies": '[data-testid="reply"]',
                "retweets": '[data-testid="retweet"]',
                "likes": '[data-testid="like"]',
            }
            for key, selector in engagement_selectors.items():
                try:
                    element = await tweet_element.query_selector(selector)
                    engagement[key] = (
                        self._parse_count(await element.inner_text()) if element else 0
                    )
                except Exception as e:
                    logger.error(f"⚠️ Error extracting {key} engagement: {e}")
                    engagement[key] = 0

            media_urls = []
            video_urls = []

            # Extract images
            try:
                for img in await tweet_element.query_selector_all(
                    '[data-testid="tweetPhoto"] img'
                ):
                    try:
                        src = await img.get_attribute("src")
                        if src and "pbs.twimg.com" in src:
                            media_urls.append(
                                f"{src.split('?')[0]}?format=jpg&name=orig"
                            )
                    except Exception as e:
                        logger.error(f"⚠️ Error extracting image: {e}")
                        continue
            except Exception as e:
                logger.error(f"⚠️ Error extracting media: {e}")

            # Enhanced video detection
            video_players = await tweet_element.query_selector_all(
                '[data-testid="videoPlayer"]'
            )
            if video_players:
                logger.debug(f"🎬 Found {len(video_players)} video players in tweet {tweet_id}")

                for video_player in video_players:
                    # Get video element
                    video = await video_player.query_selector("video")
                    if video:
                        poster = await video.get_attribute("poster")
                        src = await video.get_attribute("src")

                        if poster:
                            media_urls.append(poster)
                            # Try to derive video URL from poster
                            if "ext_tw_video_thumb" in poster:
                                video_url = poster.replace(
                                    "ext_tw_video_thumb", "ext_tw_video"
                                ).replace(".jpg", ".mp4")
                                video_urls.append(video_url)
                                logger.info(f"🎥 Derived video URL: {video_url}")

                        if src:
                            video_urls.append(src)
                            logger.info(f"🎥 Found direct video URL: {src}")

                    # Look for video links within the player
                    video_links = await video_player.query_selector_all(
                        'a[href*="/i/videos/"]'
                    )
                    for link in video_links:
                        href = await link.get_attribute("href")
                        if href:
                            video_urls.append(
                                f"https://twitter.com{href}"
                                if href.startswith("/")
                                else href
                            )
                            logger.info(f"🎥 Found video link: {href}")

            # Look for external video links (YouTube, Vimeo, etc.)
            external_video_links = await tweet_element.query_selector_all(
                'a[href*="youtube.com"], a[href*="youtu.be"], a[href*="vimeo.com"]'
            )
            for link in external_video_links:
                href = await link.get_attribute("href")
                if href:
                    video_urls.append(href)
                    logger.info(f"🎥 Found external video: {href}")

            # Combine all media URLs
            all_media_urls = media_urls + video_urls

            if initial_content and content:
                truncation_flag = _tweet_looks_truncated(initial_content, content)
                if truncation_flag:
                    logger.warning(
                        f"⚠️ Possible truncated tweet detected (initial_len={len(initial_content)}, final_len={len(content)})"
                    )

            # Detect trailing thread markers like "1/7"
            if content:
                thread_marker = re.compile(
                    r"(.*?)(?:\s+|\n|\r)(\d+)\s*/\s*(\d+)\s*$", re.DOTALL
                )
                match_marker = thread_marker.match(content.strip())
                if match_marker:
                    base = match_marker.group(1).rstrip()
                    part = int(match_marker.group(2))
                    total = int(match_marker.group(3))
                    if 0 < part <= total <= 50:
                        thread_part = part
                        thread_total = total
                        content = base
                        logger.info(
                            f"🔗 Detected tweet thread marker {part}/{total}, trimming indicator."
                        )

            hashtags = re.findall(r"#(\w+)", content)
            mentions = re.findall(r"@(\w+)", content)

            # Normalize handle to username form (no @)
            normalized_handle = (author_handle or "").lstrip("@").strip()

            # Create the SocialPost with the generated post_id
            analysis_payload = {
                "tweet_id": tweet_id,
                "tweet_url": tweet_url or f"https://x.com/i/web/status/{tweet_id}"
                if tweet_id
                else "",
            }
            if truncation_flag:
                analysis_payload.update(
                    {
                        "truncation_flag": True,
                        "initial_length": len(initial_content.strip())
                        if initial_content
                        else 0,
                        "final_length": len(content.strip()) if content else 0,
                        "expanded": expanded,
                    }
                )
            if thread_part and thread_total:
                analysis_payload["thread_part"] = {
                    "part": thread_part,
                    "total": thread_total,
                }

            return SocialPost(
                platform="twitter",
                author=author or "Unknown",
                author_handle=normalized_handle,
                content=content,
                created_at=created_at,
                url=tweet_url or f"https://x.com/i/web/status/{tweet_id}"
                if tweet_id
                else "",
                post_type="tweet",
                media_urls=media_urls,
                engagement=engagement,
                is_saved=is_saved,
                post_id=post_id,
                hashtags=hashtags,
                mentions=mentions,
                analysis=analysis_payload,
            )

        except Exception as e:
            logger.error(f"❌ Error extracting tweet data: {e}")
            return None

    async def get_tweet_replies(self, tweet_url: str, limit: int = 10) -> List[Dict]:
        """Extract top replies from a Twitter thread"""
        try:
            if not self.page:
                await self.authenticate()

            logger.debug(f"🔍 Extracting replies from: {tweet_url}")
            await self.page.goto(
                tweet_url, wait_until="load", timeout=10000
            )  # Reduced timeout
            await self.page.wait_for_timeout(2000)  # Wait for replies to load

            # Look for reply tweets
            reply_selectors = [
                'article[data-testid="tweet"]',
                '[data-testid="tweet"]',
                'div[data-testid="cellInnerDiv"]',
            ]

            replies = []
            for selector in reply_selectors:
                reply_elements = await self.page.query_selector_all(selector)

                # Skip the first element (original tweet)
                for reply_element in reply_elements[1 : limit + 1]:
                    try:
                        # Extract reply data
                        text_element = await reply_element.query_selector(
                            '[data-testid="tweetText"]'
                        )
                        if not text_element:
                            continue

                        content = await text_element.inner_text()
                        if not content or len(content.strip()) < 10:
                            continue

                        # Get author info
                        author_element = await reply_element.query_selector(
                            '[data-testid="User-Name"] span'
                        )
                        author = (
                            await author_element.inner_text()
                            if author_element
                            else "Unknown"
                        )

                        handle_element = await reply_element.query_selector(
                            'a[role="link"][data-testid*="User-Name"]'
                        )
                        author_handle = ""
                        if handle_element:
                            href = await handle_element.get_attribute("href")
                            if href:
                                author_handle = f"@{href.split('/')[-1]}"

                        # Get engagement metrics
                        like_element = await reply_element.query_selector(
                            '[data-testid="like"] span'
                        )
                        likes = 0
                        if like_element:
                            like_text = await like_element.inner_text()
                            likes = self._parse_engagement_number(like_text)

                        retweet_element = await reply_element.query_selector(
                            '[data-testid="retweet"] span'
                        )
                        retweets = 0
                        if retweet_element:
                            retweet_text = await retweet_element.inner_text()
                            retweets = self._parse_engagement_number(retweet_text)

                        # Get timestamp and URL
                        time_element = await reply_element.query_selector("time")
                        created_at = ""
                        reply_url = ""
                        if time_element:
                            created_at = await time_element.get_attribute("datetime")
                            parent_link = await time_element.query_selector("xpath=..")
                            if parent_link:
                                href = await parent_link.get_attribute("href")
                                if href:
                                    reply_url = (
                                        f"https://x.com{href}"
                                        if href.startswith("/")
                                        else href
                                    )

                        # Calculate engagement score
                        engagement_score = likes + (
                            retweets * 2
                        )  # Retweets weighted more

                        # Only include replies with some engagement or meaningful content
                        if engagement_score > 0 or len(content) > 50:
                            replies.append(
                                {
                                    "author": author,
                                    "author_handle": author_handle,
                                    "content": content,
                                    "likes": likes,
                                    "retweets": retweets,
                                    "score": engagement_score,
                                    "created_at": created_at,
                                    "url": reply_url,
                                    "platform": "twitter",
                                }
                            )

                        if len(replies) >= limit:
                            break

                    except Exception as e:
                        logger.error(f"⚠️ Error extracting reply: {e}")
                        continue

                if replies:
                    break  # Found replies with this selector

            # Sort by engagement score
            replies.sort(key=lambda x: x["score"], reverse=True)
            logger.info(f"✅ Extracted {len(replies)} replies")
            return replies[:limit]

        except Exception as e:
            logger.error(f"❌ Error extracting Twitter replies: {e}")
            return []

    def _parse_engagement_number(self, text: str) -> int:
        """Parse engagement numbers like '1.2K', '5M', etc."""
        if not text or text.isspace():
            return 0

        text = text.strip().upper()
        if text == "":
            return 0

        try:
            if "K" in text:
                return int(float(text.replace("K", "")) * 1000)
            elif "M" in text:
                return int(float(text.replace("M", "")) * 1000000)
            else:
                return int(text.replace(",", ""))
        except (ValueError, TypeError) as e:
            return 0

    def _parse_count(self, count_str: str) -> int:
        """Parse engagement count strings like '1.2K' to integers"""
        if not count_str or count_str == "0":
            return 0

        count_str = count_str.strip()
        if count_str.endswith("K"):
            return int(float(count_str[:-1]) * 1000)
        elif count_str.endswith("M"):
            return int(float(count_str[:-1]) * 1000000)
        else:
            try:
                return int(count_str)
            except (ValueError, TypeError):
                return 0

    async def extract_single_tweet(self, tweet_url: str) -> Optional[SocialPost]:
        """Extract a single tweet from its URL"""
        try:
            # Navigate to the tweet URL
            await self.page.goto(
                tweet_url, wait_until="domcontentloaded", timeout=15000
            )
            await self.page.wait_for_timeout(3000)

            # Find the tweet element
            tweet_element = await self.page.query_selector(
                'article[data-testid="tweet"]'
            )
            if not tweet_element:
                logger.error(f"❌ Could not find tweet element for: {tweet_url}")
                return None

            # Extract tweet data
            tweet_data = await self._extract_tweet_data(tweet_element, is_saved=True)
            return tweet_data

        except Exception as e:
            logger.error(f"❌ Error extracting single tweet: {e}")
            return None

    async def extract_threads_second_pass(
        self, posts: List[SocialPost], max_retries: int = 2
    ) -> List[SocialPost]:
        """
        Extract full thread content for posts marked as threads.
        This is called after initial collection to avoid DOM conflicts.
        
        Args:
            posts: List of SocialPost objects that may contain threads
            max_retries: Maximum number of retries per thread extraction
            
        Returns:
            List of SocialPost objects with full thread content where applicable
        """
        if not self.extract_threads:
            logger.info("🧵 Thread extraction disabled in config, skipping second pass")
            return posts
            
        if not self.page or self.page.is_closed():
            logger.warning("⚠️ Page not available for thread extraction, skipping")
            return posts
            
        thread_posts = [p for p in posts if p and getattr(p, "post_type", None) == "thread"]
        
        if not thread_posts:
            logger.info("✅ No threads detected in collected posts")
            return posts
            
        logger.info(f"🧵 Starting second pass thread extraction for {len(thread_posts)} threads")
        
        # Save current page URL to return to it after extraction
        original_url = self.page.url
        
        updated_posts = []
        extracted_count = 0
        failed_count = 0
        
        for idx, post in enumerate(posts, 1):
            # Only process posts marked as threads
            if not post or getattr(p, "post_type", None) != "thread":
                updated_posts.append(post)
                continue
                
            # Extract full thread content
            thread_url = getattr(post, "url", None)
            author_handle = getattr(post, "author_handle", None) or getattr(post, "author", None)
            
            if not thread_url or not author_handle:
                logger.warning(f"⚠️ Thread post {idx} missing URL or author, skipping")
                updated_posts.append(post)
                failed_count += 1
                continue
                
            logger.info(f"🧵 [{idx}/{len(thread_posts)}] Extracting thread: {thread_url}")
            
            # Extract thread with retry logic
            full_thread_content = None
            for attempt in range(max_retries):
                try:
                    full_thread_content = await self._extract_full_thread(
                        thread_url, author_handle
                    )
                    if full_thread_content:
                        break
                except Exception as e:
                    logger.warning(
                        f"⚠️ Thread extraction attempt {attempt + 1}/{max_retries} failed: {e}"
                    )
                    if attempt < max_retries - 1:
                        await self._jitter(2000)  # Wait before retry
                    else:
                        logger.error(f"❌ All retry attempts failed for thread: {thread_url}")
            
            # Update post with full thread content if extracted
            if full_thread_content and len(full_thread_content.strip()) > 0:
                original_content = getattr(post, "content", "") or ""
                
                # Only update if thread content is longer than original
                if len(full_thread_content.strip()) > len(original_content.strip()):
                    post.content = full_thread_content
                    logger.info(
                        f"✅ Thread extracted: {len(full_thread_content)} chars "
                        f"(was {len(original_content)} chars)"
                    )
                    extracted_count += 1
                else:
                    logger.warning(
                        f"⚠️ Thread content not longer than original, keeping original content"
                    )
            else:
                logger.warning(f"⚠️ Could not extract full thread content, keeping original")
                failed_count += 1
                
            updated_posts.append(post)
            
            # Add jitter between extractions to avoid rate limiting
            if idx < len(thread_posts):
                await self._jitter(1500)
        
        # Try to return to original page
        try:
            if original_url and "/i/bookmarks" not in self.page.url:
                logger.info("🔄 Returning to original page after thread extraction...")
                await self.page.goto(original_url, wait_until="load", timeout=30000)
                await self._jitter(1000)
        except Exception as e:
            logger.warning(f"⚠️ Could not return to original page: {e}")
        
        logger.info(
            f"✅ Thread extraction complete: {extracted_count} extracted, "
            f"{failed_count} failed, {len(thread_posts) - extracted_count - failed_count} skipped"
        )
        
        return updated_posts

    async def close(self):
        """Clean up browser resources"""
        if hasattr(self, "context") and self.context:
            await self.context.close()
        if hasattr(self, "browser") and self.browser:
            await self.browser.close()
        if hasattr(self, "playwright") and self.playwright:
            await self.playwright.stop()

    def __del__(self):
        """Ensure browser is closed when object is destroyed"""
        # Note: Cannot run async cleanup in destructor
        # Cleanup should be called explicitly via close() method
        pass
