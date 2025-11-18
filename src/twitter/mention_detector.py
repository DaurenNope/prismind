"""
Twitter Mention Detector - Web Scraping Approach
Detects @beyondlines mentions without API rate limits
"""

import asyncio
import logging
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup

from ..utils.exceptions import TwitterScrapingError

logger = logging.getLogger(__name__)


@dataclass
class ScrapedMention:
    """Represents a mention found via web scraping"""

    tweet_id: str
    author_username: str
    author_display_name: str
    content: str
    timestamp: datetime
    url: str
    engagement_metrics: Dict[str, int]


class TwitterMentionDetector:
    """
    Web scraping-based mention detection
    Avoids API rate limits by monitoring Twitter via browser requests
    """

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_check: Optional[datetime] = None
        self.base_url = "https://twitter.com"
        self.search_url = "https://twitter.com/search"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        self.last_mention_ids: set = set()

    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=1, force_close=True),
        )
        logger.info("Twitter mention detector initialized")

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            logger.info("Twitter mention detector closed")

    async def search_mentions(self, max_results: int = 20) -> List[ScrapedMention]:
        """
        Search for @beyondlines mentions via web scraping
        Uses Twitter search page to find recent mentions
        """
        if not self.session:
            raise TwitterScrapingError("Detector not initialized")

        try:
            # Search query for mentions
            search_query = f"@beyondlines -from:beyondlines"
            search_url = f"{self.search_url}?q={search_query}&src=typed_query"

            logger.info(f"Searching for mentions: {search_query}")

            # Add random delay to avoid detection
            delay = random.uniform(2, 5)
            await asyncio.sleep(delay)

            async with self.session.get(search_url) as response:
                if response.status != 200:
                    raise TwitterScrapingError(f"Search failed: {response.status}")

                html = await response.text()

            # Parse mentions from HTML
            mentions = await self._parse_mentions_from_html(html)

            # Filter for new mentions (since last check)
            new_mentions = []
            if self.last_check:
                new_mentions = [m for m in mentions if m.timestamp > self.last_check]
            else:
                # First run, take most recent 10
                new_mentions = mentions[:10]

            # Update last check time
            self.last_check = datetime.now(timezone.utc)

            # Update seen mention IDs
            for mention in new_mentions:
                self.last_mention_ids.add(mention.tweet_id)

            logger.info(f"Found {len(new_mentions)} new mentions")
            return new_mentions

        except Exception as e:
            logger.error(f"Error searching mentions: {e}")
            raise TwitterScrapingError(f"Failed to search mentions: {e}")

    async def _parse_mentions_from_html(self, html: str) -> List[ScrapedMention]:
        """Parse tweet mentions from HTML response"""
        mentions = []

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Look for tweet elements (Twitter's structure changes frequently)
            tweet_elements = (
                soup.find_all("article", {"data-testid": "tweet"})
                or soup.find_all("div", {"data-testid": "tweet"})
                or soup.find_all("div", class_=re.compile(r"tweet"))
            )

            if not tweet_elements:
                # Try alternative selectors
                tweet_elements = soup.find_all("div", {"role": "article"})

            logger.info(f"Found {len(tweet_elements)} tweet elements in HTML")

            for tweet_element in tweet_elements:
                try:
                    mention = await self._extract_mention_from_element(tweet_element)
                    if mention and mention.tweet_id not in self.last_mention_ids:
                        mentions.append(mention)
                except Exception as e:
                    logger.debug(f"Error extracting mention from element: {e}")
                    continue

            # Sort by timestamp (newest first)
            mentions.sort(key=lambda x: x.timestamp, reverse=True)

        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")

        return mentions

    async def _extract_mention_from_element(
        self, tweet_element
    ) -> Optional[ScrapedMention]:
        """Extract mention data from tweet HTML element"""
        try:
            # Extract tweet ID from various possible locations
            tweet_id = None
            tweet_links = tweet_element.find_all("a", href=re.compile(r"/status/(\d+)"))
            for link in tweet_links:
                match = re.search(r"/status/(\d+)", link.get("href", ""))
                if match:
                    tweet_id = match.group(1)
                    break

            if not tweet_id:
                return None

            # Extract author information
            author_element = (
                tweet_element.find("span", {"data-testid": "User-Name"})
                or tweet_element.find("a", {"data-testid": "UserLink"})
                or tweet_element.find("div", class_=re.compile(r"user|author"))
            )

            author_username = "unknown"
            author_display_name = "Unknown User"

            if author_element:
                # Try to extract username and display name
                username_span = author_element.find(
                    "span", class_=re.compile(r"username")
                )
                if username_span:
                    username_text = username_span.get_text(strip=True)
                    if username_text.startswith("@"):
                        author_username = username_text[1:]
                    else:
                        author_username = username_text

                display_name_span = author_element.find(
                    "span", class_=re.compile(r"display|name")
                )
                if display_name_span:
                    author_display_name = display_name_span.get_text(strip=True)

            # Extract tweet content
            content_element = (
                tweet_element.find("div", {"data-testid": "tweetText"})
                or tweet_element.find("div", class_=re.compile(r"tweet.*text|content"))
                or tweet_element.find("p")
            )

            content = ""
            if content_element:
                content = content_element.get_text(strip=True)

            # Check if this actually mentions @beyondlines
            if "@beyondlines" not in content.lower():
                return None

            # Extract timestamp
            time_element = tweet_element.find("time")
            timestamp = datetime.now(timezone.utc)  # Default to now
            if time_element and time_element.get("datetime"):
                try:
                    timestamp = datetime.fromisoformat(
                        time_element.get("datetime").replace("Z", "+00:00")
                    )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

            # Extract engagement metrics (likes, retweets, etc.)
            metrics = {"likes": 0, "retweets": 0, "replies": 0}
            metric_elements = tweet_element.find_all(
                "div", {"data-testid": re.compile(r"(like|retweet|reply)")}
            )
            for metric_element in metric_elements:
                text = metric_element.get_text(strip=True)
                if "like" in str(metric_element).lower():
                    metrics["likes"] = self._parse_number(text)
                elif "retweet" in str(metric_element).lower():
                    metrics["retweets"] = self._parse_number(text)
                elif "reply" in str(metric_element).lower():
                    metrics["replies"] = self._parse_number(text)

            return ScrapedMention(
                tweet_id=tweet_id,
                author_username=author_username,
                author_display_name=author_display_name,
                content=content,
                timestamp=timestamp,
                url=f"https://twitter.com/i/status/{tweet_id}",
                engagement_metrics=metrics,
            )

        except Exception as e:
            logger.debug(f"Error extracting mention: {e}")
            return None

    def _parse_number(self, text: str) -> int:
        """Parse number from text (handles K, M suffixes)"""
        try:
            # Remove non-numeric characters except K and M
            clean_text = re.sub(r"[^0-9.KM]", "", text.upper())
            if not clean_text:
                return 0

            if "K" in clean_text:
                return int(float(clean_text.replace("K", "")) * 1000)
            elif "M" in clean_text:
                return int(float(clean_text.replace("M", "")) * 1000000)
            else:
                return int(clean_text)
        except Exception as e:
            logger.error(f"Error: {e}")
            return 0

    async def start_monitoring(self, check_interval: int = 300, callback=None):
        """
        Start continuous monitoring for mentions
        check_interval: seconds between checks (default 5 minutes)
        callback: async function to call when new mentions are found
        """
        logger.info(f"Starting mention monitoring with {check_interval}s interval")

        while True:
            try:
                mentions = await self.search_mentions()

                if mentions and callback:
                    await callback(mentions)

                # Wait before next check with some randomness
                actual_interval = check_interval + random.uniform(-30, 30)
                await asyncio.sleep(actual_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def test_detector(self):
        """Test the mention detector"""
        logger.info("🔍 Testing Twitter Mention Detector (Web Scraping)...")

        try:
            await self.initialize()
            mentions = await self.search_mentions(max_results=5)

            if mentions:
                logger.info(f"✅ Found {len(mentions)} mentions via web scraping:")
                for i, mention in enumerate(mentions, 1):
                    logger.info(f"\n--- Mention {i} ---")
                    logger.info(
                        f"   From: @{mention.author_username} ({mention.author_display_name})"
                    )
                    logger.info(f"   Content: {mention.content[:100]}...")
                    logger.info(f"   Time: {mention.timestamp}")
                    logger.info(f"   URL: {mention.url}")
                    logger.info(f"   Engagement: {mention.engagement_metrics}")
            else:
                logger.error("❌ No mentions found via web scraping")

            return len(mentions) > 0

        except Exception as e:
            logger.error(f"❌ Mention detector test failed: {e}")
            return False
        finally:
            await self.close()


# Global detector instance
mention_detector: Optional[TwitterMentionDetector] = None


async def get_mention_detector() -> TwitterMentionDetector:
    """Get global mention detector instance"""
    global mention_detector
    if not mention_detector:
        mention_detector = TwitterMentionDetector()
        await mention_detector.initialize()
    return mention_detector
