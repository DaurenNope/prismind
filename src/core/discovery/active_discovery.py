#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Active Discovery for BEYONDLINES
Actively searches for new content matching user interests
"""

import asyncio
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.discovery.discovery_engine import DiscoveryEngine
from src.core.discovery.topic_tracker import TopicTracker
from src.domain.collection.extractors.social_extractor_base import SocialPost


class ActiveDiscovery:
    """Actively discover new content from various sources"""

    def __init__(self, topic_tracker: Optional[TopicTracker] = None):
        self.topic_tracker = topic_tracker or TopicTracker()
        self.discovery_engine = DiscoveryEngine(self.topic_tracker)

    async def search_twitter(self, query: str, limit: int = 20) -> List[SocialPost]:
        """
        Search Twitter for recent tweets matching query using Nitter.net
        No API keys required - uses web scraping for unlimited access
        """
        logger.info(f"🐦 Searching Twitter via Nitter for: {query}")

        try:
            import random
            import time
            from urllib.parse import quote

            import requests
            from bs4 import BeautifulSoup

            posts = []

            # Use multiple nitter instances for reliability
            nitter_instances = [
                "https://nitter.net",
                "https://nitter.it",
                "https://nitter.privacydev.net",
                "https://nitter.42l.fr",
            ]

            # Shuffle instances for load balancing
            random.shuffle(nitter_instances)

            for instance in nitter_instances[:2]:  # Try up to 2 instances
                try:
                    # Construct search URL
                    encoded_query = quote(query)
                    search_url = f"{instance}/search?q={encoded_query}&f=tweets&eo=all"

                    logger.debug(f"   🔍 Searching: {search_url}")

                    # Make request with headers to avoid blocking
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.5",
                        "Accept-Encoding": "gzip, deflate",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                    }

                    response = requests.get(search_url, headers=headers, timeout=10)

                    if response.status_code != 200:
                        logger.warning(
                            f"   ⚠️ Instance {instance} returned {response.status_code}"
                        )
                        continue

                    soup = BeautifulSoup(response.text, "html.parser")

                    # Find tweet containers
                    tweet_elements = soup.find_all("div", class_="timeline-item")

                    if not tweet_elements:
                        # Try alternative selectors
                        tweet_elements = soup.find_all("div", class_="tweet-content")

                    found_count = 0
                    for tweet_elem in tweet_elements:
                        if found_count >= limit:
                            break

                        try:
                            # Extract tweet data with multiple fallback selectors
                            content_elem = (
                                tweet_elem.find("div", class_="tweet-content")
                                or tweet_elem.find("div", class_="tweet-text")
                                or tweet_elem.find("p")
                            )

                            if not content_elem:
                                continue

                            content = content_elem.get_text(strip=True)
                            if (
                                not content or len(content) < 20
                            ):  # Skip short/empty tweets
                                continue

                            # Extract author info
                            author_elem = tweet_elem.find(
                                "a", class_="username"
                            ) or tweet_elem.find("span", class_="username")

                            author = (
                                author_elem.get_text(strip=True).replace("@", "")
                                if author_elem
                                else "Unknown"
                            )

                            # Extract timestamp
                            time_elem = tweet_elem.find(
                                "span", class_="tweet-date"
                            ) or tweet_elem.find("time")

                            tweet_time = datetime.now()  # Default to now
                            if time_elem and time_elem.get("title"):
                                try:
                                    # Parse timestamp format like "Nov 15, 2024 · 2:30 PM UTC"
                                    time_str = time_elem.get("title")
                                    if "UTC" in time_str:
                                        # Remove timezone for parsing
                                        time_str = time_str.replace(" UTC", "")
                                    tweet_time = datetime.strptime(
                                        time_str, "%b %d, %Y · %I:%M %p"
                                    )
                                except Exception as e:
                                    logger.error(f"Error: {e}")
                                    pass  # Use current time as fallback

                            # Extract tweet link
                            link_elem = tweet_elem.find("a", class_="tweet-link")
                            tweet_url = (
                                f"{instance}{link_elem.get('href')}"
                                if link_elem
                                else f"{instance}/search"
                            )

                            # Create SocialPost
                            post = SocialPost(
                                post_id=f"nitter_{hash(content)}_{int(time.time())}",
                                platform="twitter",
                                author=author,
                                author_handle=f"@{author}",
                                content=content,
                                url=tweet_url,
                                created_at=tweet_time,
                                post_type="tweet",
                            )

                            posts.append(post)
                            found_count += 1

                        except Exception as e:
                            logger.error(f"   ⚠️ Error parsing tweet: {e}")
                            continue

                    if posts:
                        logger.info(f"   ✅ Found {len(posts)} tweets from {instance}")
                        break  # Success, no need to try other instances
                    else:
                        logger.warning(f"   ⚠️ No tweets found in {instance}")

                except requests.RequestException as e:
                    logger.error(f"   ❌ Request error from {instance}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"   ❌ Error with {instance}: {e}")
                    continue

            if not posts:
                logger.warning(
                    f"   ⚠️ No tweets found for '{query}' on any Nitter instance"
                )

            # Rate limiting - be respectful to Nitter instances
            await asyncio.sleep(random.uniform(1.0, 3.0))

            return posts[:limit]

        except ImportError as e:
            logger.error(f"   ❌ Missing dependencies for Twitter scraping: {e}")
            logger.info("   Install with: pip install requests beautifulsoup4")
            return []
        except Exception as e:
            logger.error(f"   ❌ Twitter search error: {e}")
            return []

    async def search_reddit(self, query: str, limit: int = 20) -> List[SocialPost]:
        """
        Search Reddit for recent posts matching query
        """
        logger.info(f"🤖 Searching Reddit for: {query}")

        try:
            import os

            import praw

            # Use existing Reddit credentials
            reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT", "BEYONDLINES/1.0"),
            )

            posts = []

            # Search across multiple subreddits
            subreddits = ["all", "technology", "programming", "startups", "artificial"]

            for subreddit_name in subreddits[:2]:  # Limit to 2 to avoid rate limits
                try:
                    subreddit = reddit.subreddit(subreddit_name)

                    # Search hot posts
                    for submission in subreddit.search(
                        query, limit=limit // 2, time_filter="day"
                    ):
                        post = SocialPost(
                            post_id=f"reddit_{submission.id}",
                            platform="reddit",
                            author=str(submission.author)
                            if submission.author
                            else "Unknown",
                            author_handle=str(submission.author)
                            if submission.author
                            else "Unknown",
                            content=f"{submission.title}\n\n{submission.selftext[:500]}",
                            url=f"https://reddit.com{submission.permalink}",
                            created_at=datetime.fromtimestamp(submission.created_utc),
                            post_type="post",
                        )
                        posts.append(post)

                except Exception as e:
                    logger.error(f"   Error searching r/{subreddit_name}: {e}")
                    continue

            logger.info(f"   ✅ Found {len(posts)} Reddit posts")
            return posts[:limit]

        except Exception as e:
            logger.error(f"   ❌ Reddit search error: {e}")
            return []

    async def scan_rss_feeds(
        self, keywords: List[str], limit: int = 20
    ) -> List[SocialPost]:
        """
        Scan RSS feeds for articles matching keywords
        """
        logger.info(f"📰 Scanning RSS feeds for: {', '.join(keywords[:3])}...")

        try:
            from src.domain.collection.extractors.article_extractor import (
                DEFAULT_RSS_FEEDS,
                ArticleExtractor,
            )

            extractor = ArticleExtractor()

            # Get articles from default feeds
            all_articles = extractor.extract_from_multiple_feeds(
                DEFAULT_RSS_FEEDS[:3], limit_per_feed=10  # Limit to 3 feeds
            )

            # Filter by keywords
            relevant = []
            for article in all_articles:
                content_lower = article.content.lower()

                # Check if any keyword matches
                for keyword in keywords:
                    if keyword.lower() in content_lower:
                        relevant.append(article)
                        break

            logger.info(f"   ✅ Found {len(relevant)} relevant articles")
            return relevant[:limit]

        except Exception as e:
            logger.error(f"   ❌ RSS scan error: {e}")
            return []

    async def discover_by_topics(
        self, max_per_source: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Main discovery method - search all sources for tracked topics

        Returns:
            List of discovered posts with metadata
        """
        logger.info("\n🔍 Starting Active Discovery")
        logger.info("=" * 60)

        # Get all keywords from enabled topics
        keywords = self.topic_tracker.get_all_keywords()

        logger.info(f"📋 Tracking {len(keywords)} keywords across topics")

        # Build search queries (combine related keywords)
        queries = self._build_search_queries(keywords)

        logger.info(f"🔎 Generated {len(queries)} search queries\n")

        all_posts = []

        # Search Reddit
        for query in queries[:3]:  # Limit to 3 queries to avoid rate limits
            reddit_posts = await self.search_reddit(query, limit=max_per_source)
            all_posts.extend(reddit_posts)
            await asyncio.sleep(2)  # Rate limiting

        # Search Twitter (when implemented)
        # for query in queries[:3]:
        #     twitter_posts = await self.search_twitter(query, limit=max_per_source)
        #     all_posts.extend(twitter_posts)

        # Scan RSS feeds
        rss_posts = await self.scan_rss_feeds(keywords[:10], limit=max_per_source)
        all_posts.extend(rss_posts)

        logger.info(f"\n📊 Total posts found: {len(all_posts)}")

        # Run discovery engine to filter by quality
        logger.info("\n🎯 Filtering by relevance and quality...")

        discovered = self.discovery_engine.discover_from_posts(all_posts)

        logger.info(f"\n✅ Active Discovery Complete!")
        logger.info(f"   Total found: {len(all_posts)}")
        logger.info(f"   High-quality: {len(discovered)}")
        logger.info("=" * 60)

        return discovered

    def _build_search_queries(self, keywords: List[str]) -> List[str]:
        """
        Build effective search queries from keywords
        Combines related keywords for better results
        """
        queries = []

        # Group keywords by topic
        enabled_topics = self.topic_tracker.get_enabled_topics()

        for topic in enabled_topics:
            topic_keywords = topic.get("keywords", [])

            # Take top 3 keywords per topic
            top_keywords = topic_keywords[:3]

            if len(top_keywords) >= 2:
                # Combine first 2 keywords
                query = f"{top_keywords[0]} {top_keywords[1]}"
                queries.append(query)

        return queries

    async def auto_discover_loop(self, interval_hours: int = 4):
        """
        Continuous discovery loop - runs every N hours

        Args:
            interval_hours: Hours between discovery runs (default 4)
        """
        logger.info(f"🤖 Starting auto-discovery loop (every {interval_hours} hours)")

        while True:
            try:
                logger.info(f"\n⏰ Auto-discovery triggered at {datetime.now()}")

                # Run discovery
                discovered = await self.discover_by_topics(max_per_source=15)

                # Store discovered posts in database
                await self._store_discovered_posts(discovered)

                # Send notification if high-value content found
                await self._notify_high_value_content(discovered)

                logger.info(f"💤 Sleeping for {interval_hours} hours...\n")

                # Reset daily counter at midnight
                now = datetime.now()
                if now.hour == 0:
                    self.discovery_engine.reset_daily_counter()

                # Sleep until next run
                await asyncio.sleep(interval_hours * 3600)

            except Exception as e:
                logger.error(f"❌ Auto-discovery error: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _store_discovered_posts(self, posts: List[SocialPost]):
        """Store discovered posts in the database"""
        if not posts:
            return

        logger.info(f"💾 Storing {len(posts)} discovered posts in database...")

        try:
            from src.infrastructure.database.storage.db import get_storage

            storage = get_storage()
            stored_count = 0

            for post in posts:
                try:
                    # Convert to storage format
                    post_data = {
                        "post_id": post.post_id,
                        "platform": post.platform,
                        "author": post.author,
                        "author_handle": post.author_handle,
                        "content": post.content,
                        "url": post.url,
                        "created_at": post.created_at.isoformat()
                        if post.created_at
                        else None,
                        "post_type": post.post_type,
                        "discovery_method": "autonomous_discovery",
                        "collected_at": datetime.now().isoformat(),
                        "needs_analysis": True,  # Mark for AI analysis
                    }

                    # Store using DatabaseAgent
                    await storage.insert_post(post_data)
                    stored_count += 1

                except Exception as e:
                    logger.error(f"   ⚠️ Error storing post {post.post_id}: {e}")
                    continue

            logger.info(f"   ✅ Successfully stored {stored_count}/{len(posts)} posts")

        except Exception as e:
            logger.error(f"   ❌ Failed to store discovered posts: {e}")

    async def _notify_high_value_content(self, posts: List[SocialPost]):
        """Send notification if high-value content is discovered"""
        if not posts:
            return

        logger.info(f"🔍 Analyzing {len(posts)} posts for high-value content...")

        # Quick high-value detection
        high_value_indicators = [
            "breakthrough",
            "revolutionary",
            "game changer",
            "disruptive",
            "milestone",
            "record-breaking",
            "unprecedented",
            "first time",
            "announcement",
            "launched",
            "released",
            "acquired",
            "funded",
            "ai",
            "machine learning",
            "blockchain",
            "quantum",
            "biotech",
            "security vulnerability",
            "data breach",
            "cyber attack",
        ]

        high_value_posts = []

        for post in posts:
            content_lower = post.content.lower()

            # Check for high-value indicators
            score = 0
            for indicator in high_value_indicators:
                if indicator in content_lower:
                    score += 1

            # Check for trending topics (hashtags, mentions)
            if "#" in post.content or "@" in post.content:
                score += 0.5

            # Check for content length (substantial content)
            if len(post.content) > 200:
                score += 0.5

            # Consider posts with score >= 2 as high-value
            if score >= 2:
                post.value_score = score
                high_value_posts.append(post)

        if high_value_posts:
            logger.info(f"🚨 Found {len(high_value_posts)} high-value posts!")

            # Send notification via Telegram bot
            await self._send_telegram_notification(high_value_posts)

            # Log high-value discoveries
            await self._log_high_value_discoveries(high_value_posts)
        else:
            logger.info("   ✅ No high-value content detected in this batch")

    async def _send_telegram_notification(self, high_value_posts: List[SocialPost]):
        """Send Telegram notification about high-value content"""
        try:
            # Import only when needed to avoid circular imports
            from src.domain.publishing.platforms.telegram.bot import send_notification

            for post in high_value_posts[:5]:  # Limit to top 5 posts
                message = f"🚨 **HIGH-VALUE CONTENT DISCOVERED**\n\n"
                message += f"📱 Platform: {post.platform}\n"
                message += f"✍️  Author: {post.author} ({post.author_handle})\n"
                message += f"📊 Value Score: {getattr(post, 'value_score', 0):.1f}\n\n"
                message += f"📄 Content:\n{post.content[:300]}{'...' if len(post.content) > 300 else ''}\n\n"
                message += f"🔗 [View Original]({post.url})"

                # Send notification
                await send_notification(
                    message=message,
                    chat_id=os.getenv("TELEGRAM_ADMIN_CHAT_ID"),
                    parse_mode="Markdown",
                )

                logger.info(f"   📤 Telegram notification sent for post {post.post_id}")

        except Exception as e:
            logger.error(f"   ⚠️ Failed to send Telegram notification: {e}")

    async def _log_high_value_discoveries(self, high_value_posts: List[SocialPost]):
        """Log high-value discoveries for tracking and analysis"""
        try:
            log_data = []

            for post in high_value_posts:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "post_id": post.post_id,
                    "platform": post.platform,
                    "author": post.author,
                    "value_score": getattr(post, "value_score", 0),
                    "content_preview": post.content[:200],
                    "url": post.url,
                    "discovery_method": "autonomous_discovery",
                }
                log_data.append(log_entry)

            # Store in a separate log table or file
            from src.infrastructure.database.storage.db import get_storage

            storage = get_storage()

            # Try to store in high_value_discoveries table if exists, otherwise use logs
            try:
                for entry in log_data:
                    await storage.supabase.table("high_value_discoveries").insert(
                        entry
                    ).execute()
                logger.info(
                    f"   📊 Logged {len(log_data)} high-value discoveries to database"
                )
            except Exception:
                # Fallback: store in a local log file
                import json

                log_file = "logs/high_value_discoveries.jsonl"

                with open(log_file, "a") as f:
                    for entry in log_data:
                        f.write(json.dumps(entry) + "\n")

                logger.info(
                    f"   📝 Logged {len(log_data)} high-value discoveries to {log_file}"
                )

        except Exception as e:
            logger.error(f"   ⚠️ Failed to log high-value discoveries: {e}")
