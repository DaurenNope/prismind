import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import Browser, Page, async_playwright

from .social_extractor_base import SocialExtractorBase, SocialPost
from .twitter_cookies import TwitterCookieStore
from ..rate_limiting.rate_limit_config import RateLimitConfig


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
        self.cookie_file = cookie_file or f"config/twitter_cookies_{username}.json"
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
            low, high = (self.jitter_ms[0], self.jitter_ms[1]) if isinstance(self.jitter_ms, list) and len(self.jitter_ms) == 2 else (300, 1200)
            delay = max(0, low) if low == high else __import__("random").randint(int(low), int(high))
            await asyncio.sleep((delay + max(0, extra_ms)) / 1000)
        except Exception:
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
                print(f"✅ Refreshed and saved browser state to {cookie_path}")
                
                # Verify cookies were saved
                if cookie_path.exists():
                    cookies = self._cookie_store.load()
                    if cookies is not None:
                        print(f"✅ Verified: Saved {len(cookies)} cookies in storage_state format")
                        return True
                    print("⚠️ Cookies saved but could not verify storage_state contents")
                    return True  # Still return True as save likely succeeded
                else:
                    print(f"⚠️ Cookie file not found after save: {cookie_path}")
                    return False
            else:
                print("⚠️ Cannot refresh cookies: context not available or not authenticated")
                return False
        except Exception as e:
            print(f"⚠️ Failed to refresh cookies: {e}")
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
                print(f"🔄 Cookies are {int(age_seconds/60)} minutes old - refreshing proactively...")
                return await self._refresh_and_save_cookies()

            return True
        except Exception as e:
            print(f"⚠️ Auto-refresh check failed: {e}")
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
                print(f"⚠️ Cookies are {int(age_seconds/3600)} hours old - may need refresh")
            except Exception:
                print("⚠️ Cookies may be old - could not compute exact age")

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
            
            with cookie_path.open('r') as f:
                cookie_data = json.load(f)
            
            # Check if it's in storage_state format: {"cookies": [...], "origins": [...]}
            if not isinstance(cookie_data, dict):
                print(f"⚠️ Cookie file is not in storage_state format (expected dict, got {type(cookie_data)})")
                return False
            
            if 'cookies' not in cookie_data:
                print(f"⚠️ Cookie file missing 'cookies' key (not in storage_state format)")
                return False
            
            cookies = cookie_data.get('cookies', [])
            if not isinstance(cookies, list):
                print(f"⚠️ Cookie file 'cookies' is not a list (expected list, got {type(cookies)})")
                return False
            
            # Validate cookie structure
            for cookie in cookies:
                if not isinstance(cookie, dict):
                    print(f"⚠️ Invalid cookie format: expected dict, got {type(cookie)}")
                    return False
                if 'name' not in cookie or 'value' not in cookie:
                    print(f"⚠️ Invalid cookie: missing 'name' or 'value'")
                    return False
            
            print(f"✅ Cookie file validated: {len(cookies)} cookies in storage_state format")
            return True
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Cookie file is not valid JSON: {e}")
            return False
        except Exception as e:
            print(f"⚠️ Could not validate cookie format: {e}")
            return False

    async def _try_cookie_authentication(self) -> bool:
        """
        Try to authenticate using existing cookies - SOPHISTICATED approach like Threads
        
        Uses storage_state (Playwright's native cookie/state management) for reliable authentication.
        """
        cookie_path = self._cookie_store.path
        if not self._cookie_store.exists():
            print("⚠️  Cookie file not found - skipping cookie authentication")
            return False

        try:
            self._cookie_store.ensure_parent_dir()
            # Validate cookie format (sophisticated approach like Threads)
            if not self._validate_cookie_format():
                print("⚠️  Cookie file is not in storage_state format - will attempt to convert on next save")
                # Don't fail - we'll try to use it anyway and fix it on save
            
            # Check cookie freshness
            is_fresh = self._check_cookie_freshness()
            if not is_fresh:
                print("🔄 Cookies are old - will refresh after successful authentication")
            
            print("🍪 Attempting cookie-based authentication (using storage_state)...")
            
            # Ensure browser is initialized (should already be, but check)
            if not self.browser or not self.browser.is_connected():
                print("⚠️  Browser not initialized - cannot use storage_state")
                return False

            # IMPORTANT: Use storage_state directly - this is the sophisticated approach (like Threads)
            # This loads cookies AND browser state (localStorage, sessionStorage, etc.)
            # This creates a NEW context with the saved state - this is the key!
            self.context = await self.browser.new_context(
                storage_state=str(cookie_path),
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()

            # Navigate directly to home page (like Threads does)
            await self._jitter()
            await self.page.goto(
                "https://x.com/home", 
                wait_until='domcontentloaded', 
                timeout=60000
            )
            await asyncio.sleep(3)  # Wait for page to load

            # Check for rate limiting errors on page
            page_text = await self.page.evaluate("document.body.innerText")
            if re.search(r'g;\d+:-\d+:[a-zA-Z0-9]+:\d+', page_text):
                print("⚠️  Rate limiting error detected in page - cookies may be expired or account is rate limited")
                await self.page.screenshot(path="logs/twitter_cookie_auth_rate_limit.png")
                return False

            # Simple check: are we on login page? (like Threads does)
            current_url = self.page.url
            if 'login' in current_url.lower() or 'signin' in current_url.lower():
                print("❌ Cookie authentication failed - redirected to login page (cookies expired)")
                return False

            # Check for timeline (logged in indicator)
            try:
                timeline_element = await self.page.wait_for_selector(
                    '[data-testid="primaryColumn"]', 
                    timeout=5000
                )
                if timeline_element:
                    print("✅ Cookie authentication successful! (found timeline)")
                    self.is_authenticated = True
                    # AUTO-REFRESH: Save fresh cookies using storage_state
                    await self.context.storage_state(path=str(cookie_path))
                    print(f"✅ Refreshed and saved browser state to {cookie_path}")
                    return True
            except Exception:
                pass

            # Also check URL - if we're on /home, we're likely logged in
            if '/home' in current_url and '/login' not in current_url:
                print("✅ Cookie authentication successful! (on home page)")
                self.is_authenticated = True
                # AUTO-REFRESH: Save fresh cookies using storage_state
                await self.context.storage_state(path=str(cookie_path))
                print(f"✅ Refreshed and saved browser state to {cookie_path}")
                return True

            # If we got here, authentication likely failed
            print("❌ Cookie authentication failed - could not verify login status")
            return False

        except Exception as e:
            print(f"❌ Cookie authentication error: {e}")
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
                print(f"🔄 Authentication attempt {attempt + 1}/{max_retries}...")
                
                # Check cookie freshness before attempting auth
                if self._cookie_store.exists():
                    is_fresh = self._check_cookie_freshness()
                    if not is_fresh:
                        print("🔄 Cookies are old but will attempt to use them (will refresh if auth succeeds)")
                
                if not self.playwright:
                    self.playwright = await async_playwright().start()

                if not self.browser or not self.browser.is_connected():
                    self.browser = await self.playwright.chromium.launch(
                        headless=self.headless,
                        args=["--no-sandbox", "--disable-dev-shm-usage"],
                    )

                # Try cookie authentication first (PRIORITY - avoids rate limiting)
                # Use sophisticated storage_state approach (like Threads)
                # This will create context with storage_state if cookies exist
                print("🍪 Attempting cookie-based authentication using storage_state (avoids rate limiting)...")
                if await self._try_cookie_authentication():
                    # Cookies already refreshed in _try_cookie_authentication via storage_state
                    # Context and page are already created in _try_cookie_authentication
                    print("✅ Cookie authentication successful - bypassing password login")
                    return True
                else:
                    print("⚠️  Cookie authentication failed - cookies may be expired or missing")
                    
                    # Context wasn't created in _try_cookie_authentication (cookies failed)
                    # Create context for password login
                    if not self.context:
                        self.context = await self.browser.new_context(
                            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        )
                    
                    if not self.page or self.page.is_closed():
                        self.page = await self.context.new_page()

                if not self.password:
                    print("❌ Cookie authentication failed and no password provided.")
                    print("💡 Tip: Use valid cookies or wait for rate limit to expire")
                    print("💡 To get cookies: log in once manually or wait for automatic refresh")
                    return False

                # Check if cookies exist but are expired
                cookies_exist = self._cookie_store.exists()
                if cookies_exist:
                    print("⚠️  Cookies exist but authentication failed - they may be expired")
                    print("💡 Tip: Twitter is likely rate limiting. Wait 15-30 minutes or use fresh cookies")
                    print("   If rate limiting persists, consider waiting longer or using a different account")

                print("🔐 Falling back to password authentication...")
                print("⚠️  Note: Password login may fail due to rate limiting/anti-bot detection")
                await self._jitter()
                await self.page.goto(
                    "https://x.com/login", wait_until="domcontentloaded", timeout=60000
                )
                await self._jitter(300)

                # Step 1: Enter username
                username_selector = 'input[name="text"], input[autocomplete="username"]'
                print("👤 Entering username...")
                await self.page.wait_for_selector(username_selector, timeout=30000)
                await self.page.fill(username_selector, self.username)
                await self.page.click('button:has-text("Next")')

                # Step 2: Handle potential verification
                verification_selector = 'input[data-testid="ocfEnterTextTextInput"]'
                try:
                    verification_input = await self.page.wait_for_selector(
                        verification_selector, timeout=5000
                    )
                    print(
                        "⚠️ Twitter is asking for additional verification (e.g., phone number or username). This is an anti-bot measure."
                    )
                    # You might need to enter a phone number or username here if prompted
                    # For now, we will assume it's asking for the username again
                    await verification_input.fill(self.username)
                    await self.page.click('button:has-text("Next")')
                except Exception as e:
                    print(f"✅ No special verification prompt detected: {e}")

                # Step 3: Enter password
                password_selector = (
                    'input[name="password"], input[autocomplete="current-password"]'
                )
                print("🔑 Entering password...")
                await self.page.wait_for_selector(password_selector, timeout=30000)
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
                        "blocked"
                    ]
                    
                    # Check page text
                    page_text_lower = page_text.lower()
                    for pattern in error_patterns:
                        if pattern.startswith("g;"):
                            # Check for Twitter error identifier pattern
                            if re.search(r'g;\d+:-\d+:[a-zA-Z0-9]+:\d+', page_text):
                                error_msg = "Twitter authentication blocked - rate limiting detected"
                                print(f"⚠️ {error_msg}")
                                await self.page.screenshot(path=f"logs/twitter_auth_error_{attempt + 1}.png")
                                raise Exception(error_msg)
                        elif pattern in page_text_lower:
                            # Extract full error message
                            error_msg = f"Twitter authentication blocked: {pattern}"
                            print(f"⚠️ {error_msg}")
                            await self.page.screenshot(path=f"logs/twitter_auth_error_{attempt + 1}.png")
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
                            error_elements = await self.page.query_selector_all(selector)
                            for error_element in error_elements:
                                error_text = await error_element.inner_text()
                                if error_text:
                                    error_text_lower = error_text.lower()
                                    if any(pattern in error_text_lower for pattern in error_patterns if not pattern.startswith("g;")):
                                        print(f"⚠️ Twitter rate limiting/error detected: {error_text}")
                                        await self.page.screenshot(path=f"logs/twitter_auth_error_{attempt + 1}.png")
                                        raise Exception(f"Twitter authentication blocked: {error_text}")
                        except Exception as e:
                            if "Twitter authentication blocked" in str(e):
                                raise  # Re-raise our custom error
                            continue
                            
                except Exception as check_error:
                    if "Twitter authentication blocked" in str(check_error):
                        raise  # Re-raise our custom error
                    # Otherwise, continue to normal verification

                # Step 5: Verify login success
                home_timeline_selector = '[data-testid="primaryColumn"]'
                try:
                    await self.page.wait_for_selector(home_timeline_selector, timeout=30000)
                except Exception as e:
                    # Check if we're still on login page (authentication failed)
                    current_url = self.page.url
                    page_text = await self.page.evaluate("document.body.innerText")
                    page_text_lower = page_text.lower()
                    
                    # Check for Twitter error identifier pattern
                    if re.search(r'g;\d+:-\d+:[a-zA-Z0-9]+:\d+', page_text):
                        error_msg = "Twitter authentication blocked - rate limiting detected (error identifier found)"
                        print(f"❌ {error_msg}")
                        await self.page.screenshot(path=f"logs/twitter_auth_failed_{attempt + 1}.png")
                        raise Exception(error_msg)
                    
                    if 'login' in current_url.lower() or 'signin' in current_url.lower():
                        print(f"❌ Still on login page. URL: {current_url}")
                        # Check for specific error messages in page
                        if any(pattern in page_text_lower for pattern in ["could not log", "try again later", "rate limit", "something went wrong"]):
                            await self.page.screenshot(path=f"logs/twitter_auth_failed_{attempt + 1}.png")
                            raise Exception("Twitter authentication blocked - rate limiting or anti-bot detection. Please wait and try again later.")
                        raise Exception(f"Authentication failed - still on login page")
                    raise

                self.is_authenticated = True
                print(f"✅ Successfully logged in to Twitter as {self.username}")

                # AUTO-SAVE: Save browser state using storage_state (sophisticated approach like Threads)
                # This ensures cookies are always fresh after authentication
                cookie_path = self._cookie_store.path
                self._cookie_store.ensure_parent_dir()
                await self.context.storage_state(path=str(cookie_path))
                print(f"✅ Saved browser state to {cookie_path} (includes cookies + localStorage)")
                
                # Verify cookies were saved properly
                await self._refresh_and_save_cookies()

                return True

            except Exception as e:
                error_msg = str(e)
                print(f"❌ Authentication attempt {attempt + 1} failed: {e}")
                
                # Take screenshot for debugging
                try:
                    if self.page and not self.page.is_closed():
                        await self.page.screenshot(
                            path=f"logs/auth_failure_attempt_{attempt + 1}.png"
                        )
                except Exception as e:
                    print(f"⚠️ Screenshot failed: {e}")
                    pass
                
                # Check if it's a rate limiting error (including Twitter error identifier pattern)
                has_rate_limit_pattern = (
                    "rate limit" in error_msg.lower() or 
                    "try again later" in error_msg.lower() or 
                    "could not log" in error_msg.lower() or
                    "temporarily restricted" in error_msg.lower() or
                    "twitter authentication blocked" in error_msg.lower() or
                    re.search(r'g;\d+:-\d+:[a-zA-Z0-9]+:\d+', error_msg) is not None
                )
                
                if has_rate_limit_pattern:
                    print("⚠️  Twitter rate limiting/anti-bot detection detected!")
                    print(f"   Error: {error_msg[:200]}")  # Show first 200 chars
                    print("💡 This means Twitter is blocking automated login attempts.")
                    print()
                    print("🔧 Solutions:")
                    print("   1. WAIT: Wait 1-2 hours (or longer) before trying again")
                    print("   2. USE COOKIES: Ensure valid cookies exist - they bypass login")
                    print("      Check: cookies/twitter_cookies_cryptoniard.json")
                    print("   3. MANUAL LOGIN: Log in manually once in browser to refresh cookies")
                    print("   4. SKIP FOR NOW: Focus on Threads collection (has valid cookies)")
                    print("   5. CHECK COOKIES: Run: python scripts/manage_cookies.py")
                    print()
                    
                    if attempt == 0:
                        # On first attempt, suggest waiting longer
                        print("⏭️  Skipping further retries (rate limit detected)")
                        print("💡 Run collection again later (wait 1-2 hours), or use cookies to bypass")
                        return False
                    
                    wait_time = 60 * (attempt + 1)  # Longer wait: 60s, 120s, 180s
                    print(f"⏳ Waiting {wait_time} seconds before retry...")
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
                        print("❌ All authentication attempts failed.")
                        if "rate limit" in error_msg.lower() or "try again later" in error_msg.lower():
                            print("💡 Tip: Twitter may be rate limiting. Wait 15-30 minutes and try again.")
                        return False
                    await asyncio.sleep(5)  # Wait before retrying
        return False

    async def _scroll_page(self):
        """Scroll the page to load more content"""
        try:
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        except Exception as e:
            print(f"⚠️ Scroll error: {e}")
    
    async def get_saved_posts(
        self, limit: int = 50, skip_cached_ids: set = None, stop_at_post_id: str = None
    ) -> List[SocialPost]:
        """Get bookmarked tweets from Twitter with improved scrolling and thread handling"""
        if not self.is_authenticated:
            if not await self.authenticate():
                return []

        posts = []
        processed_tweet_ids = (
            set(skip_cached_ids) if skip_cached_ids else set()
        )  # Create a copy to avoid modifying the input set
        print(f"🚫 Will skip {len(processed_tweet_ids)} already cached tweets")
        
        # Track if we've encountered the stop post
        stop_post_encountered = False
        print(f"🛑 Will stop collection when reaching post ID: {stop_at_post_id or 'N/A'}")

        try:
            # Navigate to bookmarks
            await self._jitter()
            print("🌐 Navigating to bookmarks page...")
            try:
                # Try networkidle first (better if it works)
                await self.page.goto(
                    "https://x.com/i/bookmarks",
                    wait_until="networkidle",
                    timeout=30000,  # Shorter timeout for networkidle
                )
            except Exception as e:
                # Fallback to load if networkidle times out (Twitter keeps polling)
                print(f"⚠️ networkidle timed out (normal for dynamic pages), using load instead: {e}")
                await self.page.goto(
                    "https://x.com/i/bookmarks",
                    wait_until="load",
                    timeout=60000,
                )
            await self._jitter(2000)  # Wait longer for initial load and dynamic content

            # Check if bookmarks page loaded
            try:
                print("⏳ Waiting for page structure to load...")
                await self.page.wait_for_selector(
                    '[data-testid="primaryColumn"]', timeout=15000
                )
                print("✅ Page structure loaded")
            except Exception as e:
                print(
                    f"❌ Could not access bookmarks page - check if account has bookmarks enabled: {e}"
                )
                return []

            # Wait for tweets to start loading (they load dynamically)
            print("⏳ Waiting for tweets to load...")
            await self._jitter(2000)  # Give extra time for tweets to load
            
            # Try to wait for at least one tweet element to appear (with timeout)
            try:
                print("🔍 Looking for tweet elements...")
                await self.page.wait_for_selector(
                    'article[data-testid="tweet"]', 
                    timeout=10000,
                    state="attached"  # Don't require visible, just attached to DOM
                )
                print("✅ Tweets detected on page")
            except Exception as e:
                print(f"⚠️ No tweets found immediately: {e}")
                print("   This might be normal - will try scrolling to load more")
                # Take screenshot for debugging
                try:
                    screenshot_path = "logs/twitter_bookmarks_no_tweets.png"
                    Path("logs").mkdir(parents=True, exist_ok=True)
                    await self.page.screenshot(path=screenshot_path, full_page=True)
                    print(f"📸 Screenshot saved: {screenshot_path}")
                except Exception as screenshot_error:
                    print(f"⚠️ Could not take screenshot: {screenshot_error}")
                # Don't return - continue and try scrolling

            print(f"📥 Starting to extract Twitter bookmarks (target: {limit})...")

            # Improved scrolling mechanism
            scroll_attempts = 0
            max_scroll_attempts = 50  # default upper bound
            if self.scroll_limit_cfg:
                try:
                    max_scroll_attempts = max(1, min(max_scroll_attempts, int(self.scroll_limit_cfg)))
                except Exception:
                    pass
            no_new_content_count = 0
            last_tweet_count = 0

            while len(posts) < limit and scroll_attempts < max_scroll_attempts and not stop_post_encountered:
                try:
                    # Get all tweet articles on the page with fresh query
                    tweet_elements = await self.page.query_selector_all(
                        'article[data-testid="tweet"]'
                    )
                    current_tweet_count = len(tweet_elements)

                    print(
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
                                print(f"⚠️ Tweet element {i} no longer valid, skipping: {e}")
                                continue

                            # Extract tweet data with thread handling
                            tweet_data = await self._extract_tweet_data_with_threads(
                                tweet_element
                            )
                            if tweet_data:
                                # Check if we've reached the stop post (normalize for comparison)
                                if stop_at_post_id:
                                    # Normalize both IDs by removing twitter_ prefix
                                    normalized_tweet_id = tweet_data.post_id.replace('twitter_', '')
                                    normalized_stop_id = str(stop_at_post_id).replace('twitter_', '')
                                    
                                    if normalized_tweet_id == normalized_stop_id:
                                        print(f"🛑 Reached stop post ID: {stop_at_post_id} (matched: {tweet_data.post_id})")
                                        stop_post_encountered = True
                                        break

                                # Check if we already processed this tweet
                                if tweet_data.post_id in processed_tweet_ids:
                                    print(
                                        f"⏭️ Skipped already processed tweet: {tweet_data.post_id}"
                                    )
                                    continue

                                # Check if we processed this tweet in this scroll
                                if tweet_data.post_id in processed_this_scroll:
                                    print(
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
                                    print(
                                        f"✅ Extracted NEW tweet {len(posts)}: @{tweet_data.author_handle}"
                                    )
                                    
                                    # Periodic cookie refresh during collection (sophisticated approach like Threads)
                                    # Refresh cookies every 10 tweets to keep them fresh
                                    if len(posts) % 10 == 0:
                                        print(f"🔄 Refreshing cookies periodically (every 10 tweets)...")
                                        await self._auto_refresh_cookies_if_needed()
                                else:
                                    print(
                                        f"⏭️ Skipped duplicate tweet: {tweet_data.post_id}"
                                    )
                            else:
                                print(f"⚠️ Could not extract tweet data from element {i}")

                        except Exception as e:
                            print(f"⚠️ Error processing tweet element {i}: {e}")
                            continue

                    # Update progress and scroll if needed
                    if new_tweets_found > 0:
                        print(f"🔍 Found {new_tweets_found} new tweets in this scroll")
                        no_new_content_count = 0  # Reset counter
                    else:
                        no_new_content_count += 1
                        print(f"🔍 No new tweets found in this scroll")

                    # Check if we should scroll for more content
                    if len(posts) < limit and not stop_post_encountered:
                        if no_new_content_count >= 5:  # Increased from 3 to 5
                            print("🛑 No new content loaded after 5 attempts, stopping...")
                            break

                        # Periodic cookie refresh during scrolling (sophisticated approach like Threads)
                        # Refresh cookies every 5 scroll attempts to keep them fresh
                        if scroll_attempts > 0 and scroll_attempts % 5 == 0:
                            print(f"🔄 Refreshing cookies periodically (every 5 scrolls)...")
                            await self._auto_refresh_cookies_if_needed()

                        # If no tweets found at all yet, try scrolling anyway (might trigger loading)
                        if current_tweet_count == 0 and scroll_attempts < 3:
                            print(f"📜 No tweets found yet, scrolling to trigger loading (attempt {scroll_attempts + 1})...")
                            scroll_attempts += 1
                            await self._scroll_page()
                            await self._jitter(1000)  # Wait longer after scroll
                            await self.page.wait_for_timeout(2000)  # Extra wait for content
                            continue  # Go back to check for tweets

                        if current_tweet_count > last_tweet_count:
                            last_tweet_count = current_tweet_count
                            scroll_attempts += 1
                            print("📜 Scrolling to load more content...")
                            await self._scroll_page()
                            await self._jitter(500)  # Increased wait time
                            await self.page.wait_for_timeout(1000)  # Extra wait for dynamic content
                            print(f"📈 Progress: {len(posts)}/{limit} tweets extracted")
                        elif current_tweet_count == last_tweet_count and current_tweet_count > 0:
                            # Same count but we have tweets - might need more scrolling
                            scroll_attempts += 1
                            print("📜 Scrolling to load more tweets...")
                            await self._scroll_page()
                            await self._jitter(500)
                            await self.page.wait_for_timeout(1500)
                            print(f"📈 Progress: {len(posts)}/{limit} tweets extracted")
                        else:
                            print("🛑 No more tweets loading, stopping...")
                            break
                    else:
                        # We've either reached our limit or encountered the stop post
                        if stop_post_encountered:
                            print("🛑 Stopped collection at last collected post")
                        break

                except Exception as e:
                    print(f"⚠️ Error during scroll attempt {scroll_attempts + 1}: {e}")
                    scroll_attempts += 1
                    if scroll_attempts >= max_scroll_attempts:
                        print("🛑 Max scroll attempts reached")
                        break
                    await self.page.wait_for_timeout(3000)

            print(f"✅ Retrieved {len(posts)} bookmarked tweets from Twitter")
            
            # AUTO-REFRESH: Refresh cookies after successful collection (sophisticated approach like Threads)
            # This keeps cookies fresh and prevents expiration issues
            refresh_success = await self._refresh_and_save_cookies()
            if refresh_success:
                print("✅ Cookies refreshed and saved after collection")
            else:
                print("⚠️ Cookie refresh failed (but collection succeeded)")
            
            return posts

        except Exception as e:
            print(f"❌ Error getting saved tweets: {e}")
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
                        tweet_data = await self._extract_tweet_data(
                            tweet_element, is_saved=False
                        )
                        if tweet_data:
                            posts.append(tweet_data)
                            tweets_collected += 1
                    except Exception as e:
                        print(f"⚠️ Error processing liked tweet: {e}")
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

            print(f"✅ Retrieved {len(posts)} liked tweets from Twitter")

        except Exception as e:
            print(f"❌ Error getting Twitter likes: {e}")

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
                        print(f"⚠️ Error reading thread element: {e}")
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
                print(f"⚠️ Error checking thread indicators: {e}")

            # Extract full thread if enabled in configuration
            # NOTE: Thread extraction during bookmark scrolling causes DOM issues
            # Mark as thread but don't navigate away during collection
            if has_thread_indicator:
                if self.extract_threads:
                    print("🧵 Thread detected (will extract full content later to avoid DOM issues)")
                    main_tweet.post_type = "thread"
                    # TODO: Extract full thread in a second pass after all bookmarks are collected
                else:
                    print(
                        "🧵 Thread detected but extraction disabled (config: extract_threads=false)"
                    )
                    main_tweet.post_type = "thread"

            return main_tweet

        except Exception as e:
            print(f"❌ Error extracting tweet with threads: {e}")
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
                print("❌ Could not extract tweet ID from URL")
                return None

            print(f"🔗 Navigating to tweet: {tweet_url}")
            print(f"🆔 Tweet ID: {tweet_id}")

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
                    print("✅ Direct navigation successful")
                else:
                    print(
                        f"⚠️ Direct navigation failed. Current URL: {current_page_url}"
                    )
            except Exception as e:
                print(f"⚠️ Direct navigation error: {e}")

            # Strategy 2: Try twitter.com instead of x.com
            if not navigation_successful:
                try:
                    twitter_url = tweet_url.replace("x.com", "twitter.com")
                    print(f"🔄 Trying twitter.com: {twitter_url}")
                    await self.page.goto(twitter_url, wait_until="load", timeout=15000)
                    await self.page.wait_for_timeout(3000)

                    current_page_url = self.page.url
                    if "/status/" in current_page_url and tweet_id in current_page_url:
                        navigation_successful = True
                        print("✅ Twitter.com navigation successful")
                    else:
                        print(
                            f"⚠️ Twitter.com navigation failed. Current URL: {current_page_url}"
                        )
                except Exception as e:
                    print(f"⚠️ Twitter.com navigation error: {e}")

            # Strategy 3: Search for the tweet from user's profile
            if not navigation_successful:
                try:
                    print(f"🔍 Trying to find tweet via user profile: @{author_handle}")
                    profile_url = f"https://x.com/{author_handle.replace('@', '')}"
                    await self.page.goto(profile_url, wait_until="load", timeout=15000)
                    await self.page.wait_for_timeout(3000)

                    # Look for the specific tweet on the profile
                    tweet_links = await self.page.query_selector_all(
                        f'a[href*="/status/{tweet_id}"]'
                    )
                    if tweet_links:
                        print("🎯 Found tweet link on profile, clicking...")
                        await tweet_links[0].click()
                        await self.page.wait_for_timeout(3000)

                        current_page_url = self.page.url
                        if (
                            "/status/" in current_page_url
                            and tweet_id in current_page_url
                        ):
                            navigation_successful = True
                            print("✅ Profile navigation successful")
                        else:
                            print(
                                f"⚠️ Profile navigation failed. Current URL: {current_page_url}"
                            )
                    else:
                        print("⚠️ Could not find tweet on user profile")
                except Exception as e:
                    print(f"⚠️ Profile navigation error: {e}")

            if not navigation_successful:
                print("❌ All navigation strategies failed")
                return None

            # Try to click "Show this thread" or similar buttons
            try:
                show_thread_buttons = await self.page.query_selector_all(
                    'a[role="link"]'
                )
                for button in show_thread_buttons:
                    text = await button.inner_text()
                    if any(
                        phrase in text.lower()
                        for phrase in ["show this thread", "show more", "thread"]
                    ):
                        print(f"🔍 Found thread expansion button: {text}")
                        await button.click()
                        await self.page.wait_for_timeout(2000)
                        break
            except Exception as e:
                print(f"⚠️ Could not click thread expansion: {e}")

            # Scroll down to load more tweets in the thread
            print("📜 Scrolling to load more thread content...")
            for scroll_attempt in range(3):
                await self.page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await self.page.wait_for_timeout(2000)

                # Check if new content loaded
                new_tweet_count = len(
                    await self.page.query_selector_all('article[data-testid="tweet"]')
                )
                print(f"   Scroll {scroll_attempt + 1}: Found {new_tweet_count} tweets")

            # Find all tweets in the thread from the same author AND valuable replies
            thread_parts = []
            valuable_replies = []

            # Get all tweet articles on the page after scrolling
            tweet_elements = await self.page.query_selector_all(
                'article[data-testid="tweet"]'
            )
            print(
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
                    print(f"⚠️ Error checking author: {e}")
                    continue

            if not target_author_found:
                print(f"⚠️ Target author @{author_handle} not found on page.")
                print(f"🔍 Found authors: {list(set(found_authors))}")
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
                                        print(
                                            f"   📝 Found thread part {len(thread_parts)}: {content[:50]}..."
                                        )

                except Exception as e:
                    print(f"⚠️ Error processing thread tweet: {e}")
                    continue

            # Sort by timestamp to maintain thread order
            if thread_parts:
                thread_parts.sort(key=lambda x: x.get("timestamp", ""))

                # Combine all thread parts
                full_content = "\n\n".join([part["content"] for part in thread_parts])
                print(
                    f"✅ Extracted thread with {len(thread_parts)} parts, {len(full_content)} characters"
                )

                # Return to original page (bookmarks)
                try:
                    await self.page.goto(current_url, wait_until="load", timeout=30000)
                    await self.page.wait_for_timeout(2000)
                    print("✅ Returned to bookmarks page")
                except Exception as e:
                    print(f"⚠️ Could not return to original page: {e}")
                    # Force return to bookmarks if current_url doesn't work
                    try:
                        await self.page.goto("https://x.com/i/bookmarks", wait_until="load", timeout=30000)
                        await self.page.wait_for_timeout(2000)
                        print("✅ Force navigated back to bookmarks")
                    except Exception as e:
                        print(f"❌ Failed to return to bookmarks: {e}")

                return full_content
            else:
                print("❌ No thread parts found")

        except Exception as e:
            print(f"❌ Error extracting full thread: {e}")

        # Try to return to original page even if extraction failed
        try:
            await self.page.goto(current_url, wait_until="load", timeout=30000)
            await self.page.wait_for_timeout(2000)
            print("✅ Returned to bookmarks page after failed extraction")
        except Exception as e:
            print(f"⚠️ Failed to return to original page: {e}")
            # Force return to bookmarks
            try:
                await self.page.goto("https://x.com/i/bookmarks", wait_until="load", timeout=30000)
                await self.page.wait_for_timeout(2000)
                print("✅ Force navigated back to bookmarks after failure")
            except Exception as e2:
                print(f"❌ Failed to return to bookmarks after thread extraction failure: {e2}")

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
                print(f"⚠️ Tweet element no longer valid, skipping: {e}")
                return None

            # Skip promotional tweets
            if await tweet_element.query_selector('[data-testid="promotedIndicator"]'):
                print("⏭️ Skipping promotional tweet.")
                return None

            # Main tweet content - extract BEFORE and AFTER "Show more" click
            content = ""
            
            # ALWAYS try to expand tweets - more aggressive approach
            expanded = False
            try:
                # IMPORTANT: Scroll tweet into view first
                await tweet_element.scroll_into_view_if_needed()
                await self.page.wait_for_timeout(1000)
                
                print("🔍 Aggressively checking for truncated content...")
                
                # First, get initial content to check if it's truncated
                initial_text_element = await tweet_element.query_selector('[data-testid="tweetText"]')
                initial_content = ""
                if initial_text_element:
                    initial_content = await initial_text_element.inner_text()
                    print(f"📄 Initial content length: {len(initial_content)} chars")
                
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
                    '[data-testid*="show-more"]'
                ]
                
                # Also try looking for ellipsis or truncated indicators
                truncation_indicators = [
                    'span:has-text("…")',
                    'div:has-text("…")',
                    '[data-testid*="truncate"]'
                ]
                
                print(f"🔍 Found {len(show_more_selectors)} show more selectors to try")
                
                for i, selector in enumerate(show_more_selectors):
                    try:
                        # Look for show more buttons within this tweet element
                        show_more_buttons = await tweet_element.query_selector_all(selector)
                        print(f"   Selector {i+1} ({selector}): Found {len(show_more_buttons)} elements")
                        
                        for j, button in enumerate(show_more_buttons):
                            try:
                                # Multiple checks to ensure we have the right button
                                is_visible = await button.is_visible()
                                if not is_visible:
                                    print(f"     Button {j+1}: Not visible, skipping")
                                    continue
                                
                                # Get button text and attributes
                                button_text = await button.inner_text()
                                aria_label = await button.get_attribute('aria-label') or ""
                                
                                print(f"     Button {j+1}: text='{button_text}', aria_label='{aria_label}'")
                                
                                # Check if this looks like a show more button
                                text_lower = button_text.lower()
                                if (('show' in text_lower and 'more' in text_lower) or 
                                    'show more' in aria_label.lower() or
                                    'expand' in text_lower):
                                    
                                    print(f"🔽 Clicking 'Show more' button {j+1}: '{button_text}'...")
                                    
                                    # Scroll button into view again
                                    await button.scroll_into_view_if_needed()
                                    await self.page.wait_for_timeout(500)
                                    
                                    # Try multiple click methods
                                    try:
                                        await button.click(force=True)
                                        print("     ✅ Direct click successful")
                                    except Exception as click_error:
                                        print(f"     ⚠️ Direct click failed: {click_error}")
                                        try:
                                            await button.evaluate("el => el.click()")
                                            print("     ✅ JavaScript click successful")
                                        except Exception as js_error:
                                            print(f"     ❌ JavaScript click failed: {js_error}")
                                            continue
                                    
                                    # Wait for expansion
                                    await self.page.wait_for_timeout(3000)
                                    
                                    # Verify expansion worked by checking content length
                                    new_text_element = await tweet_element.query_selector('[data-testid="tweetText"]')
                                    if new_text_element:
                                        new_content = await new_text_element.inner_text()
                                        if len(new_content) > len(initial_content):
                                            expanded = True
                                            print(f"✅ Tweet expanded! Content grew from {len(initial_content)} to {len(new_content)} chars")
                                            break
                                        else:
                                            print(f"⚠️ Content didn't expand: {len(new_content)} chars (was {len(initial_content)})")
                                    
                                    expanded = True  # Assume success if no error
                                    break
                                    
                            except Exception as btn_e:
                                print(f"     Button {j+1} failed: {btn_e}")
                                continue
                        
                        if expanded:
                            break
                            
                    except Exception as e:
                        print(f"   Selector {i+1} failed: {e}")
                        continue
                        
                # If no show more buttons found, still try to extract anyway
                if not expanded:
                    print("ℹ️ No 'Show more' buttons found - proceeding with current content")
                    
            except Exception as e:
                print(f"⚠️ Show more detection error: {e}")

            # Extract tweet content (AFTER expansion if button was clicked)
            try:
                # If we expanded, wait a bit longer and re-query the element
                if expanded:
                    await self.page.wait_for_timeout(1500)  # Extra wait for DOM update
                    print("⏳ Waiting for DOM to update after expansion...")
                
                # Query for text element (fresh query after expansion)
                text_element = await tweet_element.query_selector('[data-testid="tweetText"]')
                
                if text_element:
                    print("📄 Found tweet text element, extracting content...")
                    # Try to get ALL text content, including nested spans
                    content = await text_element.inner_text()
                    print(f"📝 Initial extraction: {len(content)} chars")
                    
                    # Always try to get comprehensive content even if not truncated
                    try:
                        # Get all spans and build comprehensive text
                        all_spans = await text_element.query_selector_all('span')
                        if all_spans:
                            print(f"🔍 Found {len(all_spans)} spans, building comprehensive text...")
                            texts = []
                            for i, span in enumerate(all_spans[:50]):  # Limit to avoid too many
                                try:
                                    span_text = await span.inner_text()
                                    if span_text and span_text.strip() and span_text not in texts:
                                        texts.append(span_text.strip())
                                except Exception as e:
                                    continue
                            
                            if texts:
                                # Join and clean up the text
                                alt_content = ' '.join(texts)
                                # Remove common duplicates and clean up
                                alt_content = ' '.join(alt_content.split())
                                
                                original_length = len(content)
                                if len(alt_content) > len(content):
                                    content = alt_content
                                    improvement = len(content) - original_length
                                    print(f"✅ Comprehensive extraction: {len(content)} chars (improved by {improvement})")
                                else:
                                    print(f"ℹ️ Comprehensive extraction same length: {len(alt_content)} chars")
                    except Exception as span_error:
                        print(f"⚠️ Span extraction error: {span_error}")
                    
                    # Check if content still looks truncated
                    if content and (content.endswith('…') or content.endswith('...')):
                        print("⚠️ Content still appears truncated, trying alternative selectors...")
                        # Try alternative selectors
                        alt_selectors = [
                            '[data-testid="tweetText"] div',
                            '[data-testid="tweetText"] p',
                            'div[lang] span',
                            '[dir="auto"] span'
                        ]
                        
                        for alt_selector in alt_selectors:
                            try:
                                alt_elements = await tweet_element.query_selector_all(alt_selector)
                                if alt_elements:
                                    alt_texts = []
                                    for el in alt_elements:
                                        try:
                                            el_text = await el.inner_text()
                                            if el_text and el_text not in alt_texts:
                                                alt_texts.append(el_text)
                                        except Exception:
                                            continue
                                    if alt_texts:
                                        alt_content = ' '.join(alt_texts)
                                        if len(alt_content) > len(content):
                                            content = alt_content
                                            print(f"✅ Alternative extraction improved length to {len(content)} chars")
                                            break
                            except Exception:
                                continue
                else:
                    print("❌ No tweet text element found")
                    content = ""
                
                # Final logging
                if content:
                    print(f"🎯 Final content extracted: {len(content)} chars")
                    if len(content) < 50:
                        print("⚠️ WARNING: Very short content - may be truncated")
                else:
                    print("❌ No content extracted")
                    
            except Exception as e:
                print(f"⚠️ Error extracting tweet text: {e}")
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
                print(f"⚠️ Error extracting quoted tweet: {e}")
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
                        parts = href.split('/')
                        username = parts[1] if len(parts) > 1 else ""
                        if username and username not in ['i', 'home', 'explore', 'notifications']:
                            author_handle = f"@{username}"
                
                # Fallback: try to extract from author name or other elements
                if not author_handle:
                    # Try alternate selectors
                    try:
                        handle_text = await tweet_element.query_selector('[data-testid="User-Name"] span:has-text("@")')
                        if handle_text:
                            text = await handle_text.inner_text()
                            if text.startswith('@'):
                                author_handle = text.split()[0]  # Get first @mention
                    except Exception:
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
                                if href and '/status/' in href:
                                    # Extract from URL format: /username/status/123
                                    parts = href.split('/')
                                    if len(parts) > 1:
                                        username = parts[1]
                                        if username and username not in ['i', 'home']:
                                            author_handle = f"@{username}"
                    except Exception:
                        pass
                        
            except Exception as e:
                print(f"⚠️ Error extracting author info: {e}")
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
                        print(f"⚠️ Error extracting tweet ID from data attributes: {e}")

            # If we still don't have an ID, generate a fallback ID using content hash
            if not tweet_id and content:
                import hashlib

                content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:10]
                tweet_id = f"fallback_{content_hash}"
                print(f"⚠️ Generated fallback tweet ID: {tweet_id}")

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
                    print(f"🕒 Parsed tweet timestamp: {created_at.isoformat()}")
                except Exception as e:
                    print(f"⚠️ Error parsing timestamp '{created_at_str}': {e}")
                    created_at = datetime.now(timezone.utc)
            else:
                print("⚠️ No timestamp found, using current time")
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
                    print(f"⚠️ Error extracting {key} engagement: {e}")
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
                        print(f"⚠️ Error extracting image: {e}")
                        continue
            except Exception as e:
                print(f"⚠️ Error extracting media: {e}")

            # Enhanced video detection
            video_players = await tweet_element.query_selector_all(
                '[data-testid="videoPlayer"]'
            )
            if video_players:
                print(
                    f"🎬 Found {len(video_players)} video players in tweet {tweet_id}"
                )

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
                                print(f"🎥 Derived video URL: {video_url}")

                        if src:
                            video_urls.append(src)
                            print(f"🎥 Found direct video URL: {src}")

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
                            print(f"🎥 Found video link: {href}")

            # Look for external video links (YouTube, Vimeo, etc.)
            external_video_links = await tweet_element.query_selector_all(
                'a[href*="youtube.com"], a[href*="youtu.be"], a[href*="vimeo.com"]'
            )
            for link in external_video_links:
                href = await link.get_attribute("href")
                if href:
                    video_urls.append(href)
                    print(f"🎥 Found external video: {href}")

            # Combine all media URLs
            all_media_urls = media_urls + video_urls

            hashtags = re.findall(r"#(\w+)", content)
            mentions = re.findall(r"@(\w+)", content)

            # Normalize handle to username form (no @)
            normalized_handle = (author_handle or "").lstrip("@").strip()

            # Create the SocialPost with the generated post_id
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
                analysis={
                    "tweet_id": tweet_id,
                    "tweet_url": tweet_url or f"https://x.com/i/web/status/{tweet_id}"
                    if tweet_id
                    else "",
                },
            )

        except Exception as e:
            print(f"❌ Error extracting tweet data: {e}")
            return None

    async def get_tweet_replies(self, tweet_url: str, limit: int = 10) -> List[Dict]:
        """Extract top replies from a Twitter thread"""
        try:
            if not self.page:
                await self.authenticate()

            print(f"🔍 Extracting replies from: {tweet_url}")
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
                        print(f"⚠️ Error extracting reply: {e}")
                        continue

                if replies:
                    break  # Found replies with this selector

            # Sort by engagement score
            replies.sort(key=lambda x: x["score"], reverse=True)
            print(f"✅ Extracted {len(replies)} replies")
            return replies[:limit]

        except Exception as e:
            print(f"❌ Error extracting Twitter replies: {e}")
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
                print(f"❌ Could not find tweet element for: {tweet_url}")
                return None

            # Extract tweet data
            tweet_data = await self._extract_tweet_data(tweet_element, is_saved=True)
            return tweet_data

        except Exception as e:
            print(f"❌ Error extracting single tweet: {e}")
            return None

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
