import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import Browser, Page, async_playwright

from .social_extractor_base import SocialExtractorBase, SocialPost


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
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None
        self.page: Optional[Page] = None
        self.is_authenticated = False

        # Load configuration
        config = load_collection_config()
        self.extract_threads = config.get("twitter", {}).get("extract_threads", False)

    def _load_cookies(self) -> Optional[List[Dict]]:
        """Load cookies from file if it exists"""
        try:
            cookie_path = Path(self.cookie_file)
            if cookie_path.exists():
                with open(cookie_path, "r") as f:
                    cookies = json.load(f)
                print(f"🍪 Loaded {len(cookies)} cookies from {cookie_path}")
                return cookies
        except Exception as e:
            print(f"⚠️ Could not load cookies: {e}")
        return None

    def _save_cookies(self, cookies: List[Dict]):
        """Save cookies to file"""
        try:
            cookie_path = Path(self.cookie_file)
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cookie_path, "w") as f:
                json.dump(cookies, f)
            print(f"🍪 Saved {len(cookies)} cookies to {cookie_path}")
        except Exception as e:
            print(f"⚠️ Could not save cookies: {e}")

    async def _try_cookie_authentication(self) -> bool:
        """Try to authenticate using existing cookies"""
        cookies = self._load_cookies()
        if not cookies:
            return False

        try:
            print("🍪 Attempting cookie-based authentication...")

            # Set cookies in the browser context
            await self.context.add_cookies(cookies)

            # Navigate to X.com home to test if cookies work
            await self.page.goto(
                "https://x.com/home", wait_until="domcontentloaded", timeout=60000
            )
            await self.page.wait_for_timeout(5000)

            # Check if we're logged in - if URL is /home and not /login, we're good
            current_url = self.page.url
            if '/login' not in current_url and '/home' in current_url:
                print("✅ Cookie authentication successful!")
                self.is_authenticated = True
                return True
            
            # Also try to find timeline
            try:
                element = await self.page.wait_for_selector('[data-testid="primaryColumn"]', timeout=10000)
                if element:
                    print("✅ Cookie authentication successful!")
                    self.is_authenticated = True
                    return True
            except:
                pass

            print("❌ Cookie authentication failed - cookies may be expired")
            return False

        except Exception as e:
            print(f"❌ Cookie authentication error: {e}")
            return False

    async def authenticate(self, max_retries: int = 3) -> bool:
        """Authenticate with Twitter using Playwright, with retries and more robust selectors."""
        for attempt in range(max_retries):
            try:
                print(f"🔄 Authentication attempt {attempt + 1}/{max_retries}...")
                if not self.playwright:
                    self.playwright = await async_playwright().start()

                if not self.browser or not self.browser.is_connected():
                    self.browser = await self.playwright.chromium.launch(
                        headless=self.headless,
                        args=["--no-sandbox", "--disable-dev-shm-usage"],
                    )

                if not self.context:
                    self.context = await self.browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    )

                if not self.page or self.page.is_closed():
                    self.page = await self.context.new_page()

                # Try cookie authentication first
                if await self._try_cookie_authentication():
                    self.is_authenticated = True
                    return True

                if not self.password:
                    print("❌ Cookie authentication failed and no password provided.")
                    return False

                print("🔐 Falling back to password authentication...")
                await self.page.goto(
                    "https://x.com/login", wait_until="domcontentloaded", timeout=60000
                )
                await self.page.wait_for_timeout(3000)

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
                except:
                    print("✅ No special verification prompt detected.")

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

                # Step 5: Verify login success
                home_timeline_selector = '[data-testid="primaryColumn"]'
                await self.page.wait_for_selector(home_timeline_selector, timeout=30000)

                self.is_authenticated = True
                print(f"✅ Successfully logged in to Twitter as {self.username}")

                cookies = await self.context.cookies()
                self._save_cookies(cookies)

                return True

            except Exception as e:
                print(f"❌ Authentication attempt {attempt + 1} failed: {e}")
                await self.page.screenshot(
                    path=f"logs/auth_failure_attempt_{attempt + 1}.png"
                )
                if self.page and not self.page.is_closed():
                    await self.page.close()
                if self.context:
                    await self.context.close()
                    self.context = None
                if attempt >= max_retries - 1:
                    print("❌ All authentication attempts failed.")
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
            await self.page.goto(
                "https://x.com/i/bookmarks",
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await self.page.wait_for_timeout(5000)

            # Check if bookmarks page loaded
            try:
                await self.page.wait_for_selector(
                    '[data-testid="primaryColumn"]', timeout=15000
                )
            except:
                print(
                    "❌ Could not access bookmarks page - check if account has bookmarks enabled"
                )
                return []

            print(f"📥 Starting to extract Twitter bookmarks (target: {limit})...")

            # Improved scrolling mechanism
            scroll_attempts = 0
            max_scroll_attempts = 50  # Increased for more scrolling
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
                            except:
                                print(f"⚠️ Tweet element {i} no longer valid, skipping")
                                continue

                            # Extract tweet data with thread handling
                            tweet_data = await self._extract_tweet_data_with_threads(
                                tweet_element
                            )
                            if tweet_data:
                                # Check if we've reached the stop post
                                if stop_at_post_id and tweet_data.post_id == stop_at_post_id:
                                    print(f"🛑 Reached stop post ID: {stop_at_post_id}")
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
                        if no_new_content_count >= 3:
                            print("🛑 No new content loaded after 3 attempts, stopping...")
                            break

                        if current_tweet_count > last_tweet_count:
                            last_tweet_count = current_tweet_count
                            scroll_attempts += 1
                            print("📜 Scrolling to load more content...")
                            await self._scroll_page()
                            await self.page.wait_for_timeout(2000)
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
            await self.page.goto(
                f"https://x.com/{self.username}/likes",
                wait_until="domcontentloaded",
                timeout=15000,
            )
            await self.page.wait_for_timeout(3000)

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
                await self.page.wait_for_timeout(2000)
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
                except:
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
                    except:
                        print("❌ Failed to return to bookmarks")

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
        except:
            # Force return to bookmarks
            try:
                await self.page.goto("https://x.com/i/bookmarks", wait_until="load", timeout=30000)
                await self.page.wait_for_timeout(2000)
                print("✅ Force navigated back to bookmarks after failure")
            except:
                print("❌ Failed to return to bookmarks after thread extraction failure")

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
            
            # Click "Show more" to expand truncated tweets
            expanded = False
            try:
                # IMPORTANT: Scroll tweet into view first
                try:
                    await tweet_element.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(500)
                except:
                    pass
                
                # Try multiple selectors for "Show more" button
                show_more_selectors = [
                    '[data-testid="tweet-text-show-more-button"]',
                    'div[role="button"]:has-text("Show more")',
                    'span:has-text("Show more")',
                    '[dir="ltr"]:has-text("Show more")',
                ]
                
                for selector in show_more_selectors:
                    try:
                        show_more_button = await tweet_element.query_selector(selector)
                        if show_more_button:
                            # Make sure button is visible
                            try:
                                is_visible = await show_more_button.is_visible()
                                if not is_visible:
                                    continue
                            except:
                                pass
                            
                            print("🔽 Clicking 'Show more' to expand full tweet...")
                            # Force click even if obscured
                            await show_more_button.click(force=True)
                            await self.page.wait_for_timeout(2000)  # Increased wait time
                            expanded = True
                            print("✅ Tweet expanded")
                            break
                    except Exception as e:
                        # print(f"   Debug: selector {selector} failed: {e}")
                        continue
            except Exception as e:
                pass  # Ignore if not found or error clicking

            # Extract tweet content (AFTER expansion if button was clicked)
            try:
                # If we expanded, wait a bit longer and re-query the element
                if expanded:
                    await self.page.wait_for_timeout(1000)  # Extra wait for DOM update
                
                # Query for text element (fresh query after expansion)
                text_element = await tweet_element.query_selector(
                    '[data-testid="tweetText"]'
                )
                
                if text_element:
                    # Try to get ALL text content, including nested spans
                    content = await text_element.inner_text()
                    
                    # If still seems truncated, try getting all text nodes
                    if content and (content.endswith('…') or len(content) < 280):
                        try:
                            # Get all text from nested elements too
                            all_spans = await text_element.query_selector_all('span')
                            if all_spans:
                                texts = []
                                for span in all_spans:
                                    text = await span.inner_text()
                                    if text and text not in texts:  # Avoid duplicates
                                        texts.append(text)
                                if texts:
                                    alt_content = ' '.join(texts)
                                    if len(alt_content) > len(content):
                                        content = alt_content
                        except:
                            pass
                else:
                    content = ""
                
                if expanded:
                    print(f"📝 Extracted expanded content: {len(content)} chars")
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
                    except:
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
                    except:
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

            # Create the SocialPost with the generated post_id
            return SocialPost(
                platform="twitter",
                author=author or "Unknown",
                author_handle=author_handle or "",
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
        except:
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
            except:
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
