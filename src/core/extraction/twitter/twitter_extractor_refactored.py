import logging

logger = logging.getLogger(__name__)
"""Refactored Twitter Extractor with separated concerns"""

import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional

from playwright.async_api import Browser, Page, async_playwright

from src.core.rate_limiting.rate_limit_config import RateLimitConfig
from ..social_extractor_base import SocialExtractorBase, SocialPost
from .auth_manager import TwitterAuthManager
from .data_extractor import TwitterDataExtractor


def load_collection_config():
    """Load collection configuration from config file"""
    import json
    from pathlib import Path

    config_path = Path("config/collection.json")
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {"twitter": {"extract_threads": False}}


class TwitterExtractorPlaywright(SocialExtractorBase):
    """Extract saved tweets and bookmarks from Twitter using Playwright (Refactored)"""

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

        # Load configuration
        config = load_collection_config()
        self.extract_threads = config.get("twitter", {}).get("extract_threads", False)

        # Initialize component managers
        self.auth_manager = TwitterAuthManager(username, password, cookie_file)
        self.data_extractor = TwitterDataExtractor()

        # Playwright instances
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        # Rate limiting and safety parameters
        self.rate_config = RateLimitConfig("twitter")
        self.min_delay = 2.0  # Minimum delay between actions
        self.max_delay = 5.0  # Maximum delay between actions
        self.max_scroll_attempts = 50
        self.scroll_pause_min = 1.5
        self.scroll_pause_max = 3.0

    async def authenticate(self, max_retries: int = 3) -> bool:
        """Authenticate with Twitter"""
        if self.is_authenticated and self.page:
            return True

        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)

            self.page = await self.auth_manager.authenticate(self.browser, max_retries)
            if self.page:
                self.is_authenticated = True
                return True

        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}")
            await self.close()
            return False

        return False

    async def _jitter(self, extra_ms: int = 0):
        """Add random jitter to delays"""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        extra_delay = random.uniform(0, extra_ms / 1000.0)
        await asyncio.sleep(base_delay + extra_delay)

    async def _scroll_page(self, scroll_pause_time: float = None):
        """Scroll page with safety measures"""
        if not self.page:
            return

        try:
            scroll_pause_time = scroll_pause_time or random.uniform(
                self.scroll_pause_min, self.scroll_pause_max
            )

            # Scroll to bottom of page
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for new content to load
            await asyncio.sleep(scroll_pause_time)

        except Exception as e:
            logger.error(f"❌ Error during scroll: {e}")

    async def get_saved_posts(self, limit: int = 50) -> List[SocialPost]:
        """Get saved tweets/bookmarks from authenticated user"""
        if not await self.authenticate():
            return []

        posts = []
        scroll_attempts = 0
        collected_ids = set()

        try:
            # Navigate to bookmarks page
            await self.page.goto(
                "https://twitter.com/i/bookmarks", wait_until="networkidle"
            )
            await self._jitter(2000)

            logger.info("📚 Starting to collect saved tweets...")

            while len(posts) < limit and scroll_attempts < self.max_scroll_attempts:
                # Wait for tweets to load
                await self.page.wait_for_selector(
                    'article[data-testid="tweet"]', timeout=10000
                )

                # Get current tweets
                tweets = await self._extract_tweets_from_current_page()
                scroll_attempts += 1

                # Filter and add new tweets
                new_tweets = 0
                for tweet in tweets:
                    if tweet.id not in collected_ids and len(posts) < limit:
                        posts.append(tweet)
                        collected_ids.add(tweet.id)
                        new_tweets += 1

                logger.warning(
                    f"📄 Scroll {scroll_attempts}: Found {len(tweets)} tweets, {new_tweets} new (Total: {len(posts)})"
                )

                if len(posts) >= limit:
                    break

                # Check if we've reached the end
                if new_tweets == 0:
                    logger.info(
                        "🔚 No new tweets found, checking if we've reached the end..."
                    )
                    # Try one more scroll to be sure
                    await self._scroll_page()
                    await self._jitter()

                    final_tweets = await self._extract_tweets_from_current_page()
                    final_new = sum(
                        1 for tweet in final_tweets if tweet.id not in collected_ids
                    )

                    if final_new == 0:
                        logger.info("✅ Reached the end of saved tweets")
                        break

                # Scroll down to load more
                await self._scroll_page()
                await self._jitter(1000)  # Extra jitter

                # Rate limiting check
                if scroll_attempts % 10 == 0:
                    await self._jitter(5000)  # Longer pause every 10 scrolls

        except Exception as e:
            logger.error(f"❌ Error getting saved posts: {e}")

        logger.info(f"✅ Collected {len(posts)} saved tweets")
        return posts[:limit]

    async def get_liked_posts(self, limit: int = 50) -> List[SocialPost]:
        """Get liked tweets from authenticated user"""
        if not await self.authenticate():
            return []

        posts = []
        scroll_attempts = 0
        collected_ids = set()

        try:
            # Navigate to likes page
            await self.page.goto(
                f"https://twitter.com/{self.username}/likes", wait_until="networkidle"
            )
            await self._jitter(2000)

            logger.info("❤️ Starting to collect liked tweets...")

            while len(posts) < limit and scroll_attempts < self.max_scroll_attempts:
                # Wait for tweets to load
                await self.page.wait_for_selector(
                    'article[data-testid="tweet"]', timeout=10000
                )

                # Get current tweets
                tweets = await self._extract_tweets_from_current_page()

                # Filter and add new tweets
                new_tweets = 0
                for tweet in tweets:
                    if tweet.id not in collected_ids and len(posts) < limit:
                        posts.append(tweet)
                        collected_ids.add(tweet.id)
                        new_tweets += 1

                logger.warning(
                    f"📄 Scroll {scroll_attempts}: Found {len(tweets)} tweets, {new_tweets} new (Total: {len(posts)})"
                )

                if len(posts) >= limit:
                    break

                # Check if we've reached the end
                if new_tweets == 0:
                    logger.info(
                        "🔚 No new tweets found, checking if we've reached the end..."
                    )
                    break

                # Scroll down to load more
                await self._scroll_page()
                await self._jitter(1000)

                scroll_attempts += 1

        except Exception as e:
            logger.error(f"❌ Error getting liked posts: {e}")

        logger.info(f"✅ Collected {len(posts)} liked tweets")
        return posts[:limit]

    async def _extract_tweets_from_current_page(self) -> List[SocialPost]:
        """Extract tweets from the current page"""
        tweets = []

        try:
            # Get tweet elements
            tweet_elements = await self.page.query_selector_all(
                'article[data-testid="tweet"]'
            )

            for element in tweet_elements:
                try:
                    # Extract tweet data
                    tweet_data = (
                        await self.data_extractor.extract_tweet_data_from_element(
                            element
                        )
                    )
                    if tweet_data:
                        # Convert to SocialPost
                        tweet = self._convert_tweet_data_to_social_post(tweet_data)
                        if tweet:
                            tweets.append(tweet)

                except Exception as e:
                    logger.error(f"❌ Error extracting individual tweet: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Error extracting tweets from current page: {e}")

        return tweets

    def _convert_tweet_data_to_social_post(
        self, tweet_data: Dict
    ) -> Optional[SocialPost]:
        """Convert extracted tweet data to SocialPost format"""
        try:
            return SocialPost(
                id=tweet_data.get("id", ""),
                content=tweet_data.get("content", ""),
                author=tweet_data.get("authorHandle", ""),
                author_name=tweet_data.get("authorName", ""),
                created_at=self._parse_timestamp(tweet_data.get("timestamp", "")),
                url=tweet_data.get("url", ""),
                reply_count=self.data_extractor._parse_count(
                    tweet_data.get("replies", "0")
                ),
                retweet_count=self.data_extractor._parse_count(
                    tweet_data.get("retweets", "0")
                ),
                like_count=self.data_extractor._parse_count(
                    tweet_data.get("likes", "0")
                ),
                quote_count=0,  # Not available in page extraction
                media=tweet_data.get("images", []),
                hashtags=[],  # Would need additional parsing
                mentions=[],  # Would need additional parsing
                urls=[],  # Would need additional parsing
                user_info={
                    "username": tweet_data.get("authorHandle", ""),
                    "name": tweet_data.get("authorName", ""),
                    "profile_image_url": "",
                    "verified": False,
                    "followers_count": 0,
                },
            )
        except Exception as e:
            logger.error(f"❌ Error converting tweet data to SocialPost: {e}")
            return None

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse timestamp string"""
        if not timestamp_str:
            return datetime.now(timezone.utc)

        try:
            # Try ISO format first
            return datetime.fromisoformat(
                timestamp_str.replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except ValueError:
            logger.error(f"Error: {e}")
            return datetime.now(timezone.utc)

    async def extract_single_tweet(self, tweet_url: str) -> Optional[SocialPost]:
        """Extract a single tweet from its URL"""
        if not await self.authenticate():
            return None

        try:
            # Navigate to tweet URL
            await self.page.goto(tweet_url, wait_until="networkidle")
            await self._jitter(2000)

            # Extract tweet data
            tweet_data = await self.data_extractor.extract_tweet_data_from_page(
                self.page
            )
            if tweet_data:
                return self._convert_tweet_data_to_social_post(tweet_data)

        except Exception as e:
            logger.error(f"❌ Error extracting single tweet: {e}")

        return None

    async def get_tweet_replies(self, tweet_url: str, limit: int = 10) -> List[Dict]:
        """Get replies to a specific tweet"""
        # This is a placeholder implementation
        # In practice, this would require navigating to the tweet and extracting replies
        logger.warning(
            f"⚠️ Tweet replies extraction not fully implemented for {tweet_url}"
        )
        return []

    async def close(self):
        """Clean up resources"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")

        self.page = None
        self.browser = None
        self.playwright = None
        self.is_authenticated = False
