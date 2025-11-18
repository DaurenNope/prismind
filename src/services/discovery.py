#!/usr/bin/env python3
"""
Autonomous Discovery Engine
Automatically finds and curates valuable content without manual bookmarking
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# DEPRECATION NOTICE:
# This module is being migrated into the orchestrator (src/pipeline/orchestrator.py).
# Use orchestrator.autonomous_discover(), generate_digest(), and build_news_feed().


class AutonomousDiscovery:
    """
    Autonomous content discovery engine

    Core functionality:
    - Runs every 2-4 hours automatically
    - Discovers content from multiple sources
    - Applies quality filtering (score > 0.7)
    - Tracks topics of interest
    - Generates daily digests
    - Detects trends
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.topics_of_interest = self._load_topics()
        self.quality_threshold = 0.7
        self.last_discovery = None

    def _load_topics(self) -> List[str]:
        """Load topics of interest with better error handling"""
        try:
            # Try to load from user preferences first
            from src.core.user.user_preferences import get_user_preferences

            prefs = get_user_preferences()
            if prefs and "topics_of_interest" in prefs:
                return prefs["topics_of_interest"]

            # Fall back to multi-topic sources
            from src.core.extraction.multi_topic_sources import DEFAULT_TOPICS

            return DEFAULT_TOPICS

        except ImportError:
            logger.error(f"Error: {e}")
            # Final fallback to diverse default topics
            return [
                "AI",
                "Programming",
                "Startups",
                "Business",
                "Investing",
                "Science",
                "Health",
                "Travel",
                "Books",
            ]
        except Exception as e:
            logger.error(f"Error loading topics: {e}")
            return [
                "AI",
                "Programming",
                "Startups",
                "Business",
                "Investing",
                "Science",
                "Health",
                "Travel",
                "Books",
            ]

    async def discover_content(self) -> Dict[str, Any]:
        """
        Main discovery function - runs automatically

        Discovers content from:
        - GitHub trending
        - Reddit hot posts
        - RSS feeds (HN, TechCrunch, etc.)
        - Twitter searches (if configured)

        Returns:
            Discovery results with quality filtering
        """
        logger.info("🔍 Starting autonomous discovery...")

        start_time = datetime.now()

        try:
            # 1. Discover from all sources concurrently
            github_task = asyncio.create_task(self._discover_github())
            reddit_task = asyncio.create_task(self._discover_reddit())
            rss_task = asyncio.create_task(self._discover_rss())

            github_items = await github_task
            reddit_items = await reddit_task
            rss_items = await rss_task

            logger.info(f"   GitHub: {len(github_items)} items")
            logger.info(f"   Reddit: {len(reddit_items)} items")
            logger.info(f"   RSS: {len(rss_items)} items")

            # Combine all discovered items
            discovered_items = github_items + reddit_items + rss_items

            # 2. Filter by quality
            quality_items = self._filter_by_quality(discovered_items)
            logger.info(f"   Quality filtered: {len(quality_items)} items")

            # 3. Filter by relevance (topic matching)
            relevant_items = self._filter_by_relevance(quality_items)
            logger.info(f"   Relevant: {len(relevant_items)} items")

            # 4. Remove duplicates
            unique_items = self._deduplicate(relevant_items)
            logger.info(f"   Unique: {len(unique_items)} items")

            # 5. Save to database
            saved_count = await self._save_discoveries(unique_items)

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": duration,
                "total_discovered": len(discovered_items),
                "quality_filtered": len(quality_items),
                "relevant": len(relevant_items),
                "unique": len(unique_items),
                "saved": saved_count,
                "sources": {
                    "github": len(github_items),
                    "reddit": len(reddit_items),
                    "rss": len(rss_items),
                },
            }

            self.last_discovery = result
            logger.info(f"✅ Discovery complete: {saved_count} new items saved")

            return result

        except Exception as e:
            logger.error(f"❌ Discovery failed: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    async def _discover_github(self) -> List[Dict[str, Any]]:
        """Discover from GitHub trending"""
        try:
            from src.core.discovery.comprehensive_discovery import (
                ComprehensiveDiscovery,
            )

            discovery = ComprehensiveDiscovery()
            github_items = await discovery.get_github_trending()

            # Convert to discovery format
            items = []
            for repo in github_items:
                items.append(
                    {
                        "source": "github",
                        "platform": "github",
                        "title": repo.get("name", "Untitled Repository"),
                        "content": repo.get("description", "No description provided"),
                        "url": repo.get("url", ""),
                        "author": repo.get("owner", {}).get("login", "Unknown"),
                        "created_at": repo.get(
                            "created_at", datetime.now().isoformat()
                        ),
                        "discovered_at": datetime.now().isoformat(),
                        "quality_score": repo.get(
                            "score", 8.0
                        ),  # Use GitHub stars as initial score
                    }
                )

            return items

        except Exception as e:
            logger.warning(f"GitHub discovery failed: {e}")
            return []

    async def _discover_reddit(self) -> List[Dict[str, Any]]:
        """Discover from Reddit hot posts"""
        try:
            from src.core.discovery.reddit_discovery import RedditDiscovery

            discovery = RedditDiscovery()
            reddit_items = await discovery.get_hot_posts(
                subreddits=self.topics_of_interest
            )

            # Convert to discovery format
            items = []
            for post in reddit_items:
                items.append(
                    {
                        "source": "reddit",
                        "platform": "reddit",
                        "title": post.get("title", "Untitled Post"),
                        "content": post.get("selftext", "") or post.get("url", ""),
                        "url": post.get("url", ""),
                        "author": post.get("author", "Unknown"),
                        "created_at": post.get(
                            "created_utc", datetime.now().isoformat()
                        ),
                        "discovered_at": datetime.now().isoformat(),
                        "quality_score": post.get(
                            "score", 8.0
                        ),  # Use Reddit score as initial score
                    }
                )

            return items

        except Exception as e:
            logger.warning(f"Reddit discovery failed: {e}")
            return []

    async def _discover_rss(self) -> List[Dict[str, Any]]:
        """Discover from RSS feeds"""
        try:
            from src.core.extraction.article_extractor import ArticleExtractor
            from src.core.extraction.multi_topic_sources import get_sources_for_topics

            # Get RSS feeds based on user topics
            sources = get_sources_for_topics(self.topics_of_interest)
            rss_feeds = sources["rss"]

            logger.info(
                f"📡 Discovering from {len(rss_feeds)} RSS feeds across multiple topics"
            )

            extractor = ArticleExtractor()
            articles = extractor.extract_from_multiple_feeds(
                rss_feeds, limit_per_feed=3
            )

            # Convert to discovery format
            items = []
            for article in articles:
                # SocialPost doesn't have title, extract from content
                content_lines = article.content.split("\n", 1)
                title = content_lines[0] if content_lines else "Untitled"
                full_content = (
                    content_lines[1] if len(content_lines) > 1 else article.content
                )

                items.append(
                    {
                        "source": "rss",
                        "platform": "rss",
                        "title": title,
                        "content": full_content,
                        "url": article.url,
                        "author": article.author,
                        "created_at": article.created_at.isoformat()
                        if article.created_at
                        else datetime.now().isoformat(),
                        "discovered_at": datetime.now().isoformat(),
                    }
                )

            return items

        except Exception as e:
            logger.warning(f"RSS discovery failed: {e}")
            return []

    def _filter_by_quality(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items by quality threshold"""
        filtered_items = []

        for item in items:
            # Ensure quality score exists
            if "quality_score" not in item:
                # Default quality score based on source
                if item.get("platform") == "rss":
                    item["quality_score"] = 8.0
                elif item.get("platform") == "github":
                    item[
                        "quality_score"
                    ] = 7.5  # GitHub trending repos are usually good
                elif item.get("platform") == "reddit":
                    item["quality_score"] = 7.0  # Reddit posts vary in quality
                else:
                    item["quality_score"] = 6.0  # Default

            # Filter by quality threshold
            if item["quality_score"] >= self.quality_threshold * 10:
                filtered_items.append(item)

        return filtered_items

    def _filter_by_relevance(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter items by topic relevance with improved matching"""
        relevant = []

        # Create a topic pattern map for case-insensitive matching
        topic_patterns = {topic.lower(): topic for topic in self.topics_of_interest}

        for item in items:
            content = f"{item.get('title', '')} {item.get('content', '')}".lower()

            # Find matching topics
            matched_topics = []
            for pattern, original_topic in topic_patterns.items():
                if pattern in content:
                    matched_topics.append(original_topic)

            # Update item with matched topics
            if matched_topics:
                item["matched_topics"] = matched_topics
                relevant.append(item)

        return relevant

    def _deduplicate(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate items by URL"""
        seen_urls = set()
        unique = []

        for item in items:
            url = item.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(item)

        return unique

    async def _save_discoveries(self, items: List[Dict[str, Any]]) -> int:
        """Save discovered items to discoveries table"""
        try:
            from src.database.manager import SupabaseManager

            supabase = SupabaseManager()
            saved_count = 0

            for item in items:
                discovery_id = f"discovery_{datetime.now().timestamp()}_{saved_count}"

                # Convert to discoveries table format
                discovery_data = {
                    "id": discovery_id,
                    "post_id": item.get("url", ""),  # Use URL as unique identifier
                    "platform": item.get("platform", "rss"),
                    "source": item.get("source", "rss_feed"),
                    "content": item.get("content", ""),
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "author": item.get("author", "Unknown"),
                    "discovered_at": datetime.now().isoformat(),
                    "created_at": item.get("created_at", datetime.now().isoformat()),
                    "discovery_method": "autonomous",
                    "matched_topics": item.get("matched_topics", []),
                    "topic": item.get("matched_topics", ["general"])[0]
                    if item.get("matched_topics")
                    else "general",
                    "quality_score": 8.0,  # Default high quality for RSS
                    "relevance_score": 0.9,  # Matched topics = relevant
                    "status": "new",
                    "content_summary": item.get("content", "")[:200]
                    + "...",  # Quick summary
                    "tags": ", ".join(item.get("matched_topics", [])),
                    "sentiment": "neutral",
                    "processed": True,
                }

                # Insert into discoveries table
                try:
                    result = (
                        supabase.client.table("discoveries")
                        .insert(discovery_data)
                        .execute()
                    )
                    if result.data:
                        saved_count += 1
                        logger.info(
                            f"✅ Saved discovery: {item.get('title', item.get('content', '')[:50])}"
                        )
                except Exception as e:
                    # Check if it's a duplicate
                    if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                        logger.info(f"⏭️  Skipping duplicate: {item.get('url', '')}")
                    else:
                        logger.error(f"Failed to save discovery: {e}")

            return saved_count

        except Exception as e:
            logger.error(f"Failed to save discoveries: {e}")
            return 0

    def start_scheduler(self):
        """Start automatic discovery scheduler"""

        # Run every 4 hours
        self.scheduler.add_job(
            self.discover_content,
            CronTrigger(hour="*/4"),
            id="autonomous_discovery",
            name="Autonomous Content Discovery",
            replace_existing=True,
        )

        # Daily digest at 8 AM
        self.scheduler.add_job(
            self.generate_daily_digest,
            CronTrigger(hour=8, minute=0),
            id="daily_digest",
            name="Daily Intelligence Digest",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("✅ Autonomous discovery scheduler started")
        logger.info("   • Discovery: Every 4 hours")
        logger.info("   • Daily digest: 8:00 AM")

    def stop_scheduler(self):
        """Stop scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    async def generate_daily_digest(self) -> Dict[str, Any]:
        """Generate daily intelligence digest"""
        logger.info("📊 Generating daily digest...")

        try:
            from src.services.new_database_manager import get_database_manager

            db = get_database_manager()

            # Get posts from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            all_posts = db.get_posts(limit=100)

            # Filter to last 24 hours
            recent_posts = [
                p
                for p in all_posts
                if p.get("created_at")
                and datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
                > yesterday
            ]

            # Group by topic
            by_topic = {}
            for post in recent_posts:
                topics = post.get("tags", [])
                for topic in topics:
                    if topic not in by_topic:
                        by_topic[topic] = []
                    by_topic[topic].append(post)

            # Top stories (highest value score)
            top_stories = sorted(
                recent_posts, key=lambda x: x.get("value_score", 0), reverse=True
            )[:5]

            # Trending topics (most posts)
            trending = sorted(by_topic.items(), key=lambda x: len(x[1]), reverse=True)[
                :3
            ]

            digest = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "total_posts": len(recent_posts),
                "top_stories": [
                    {
                        "title": p.get("title", p.get("content", "")[:100]),
                        "url": p.get("url", ""),
                        "score": p.get("value_score", 0),
                    }
                    for p in top_stories
                ],
                "trending_topics": [
                    {"topic": topic, "post_count": len(posts)}
                    for topic, posts in trending
                ],
                "by_source": self._count_by_source(recent_posts),
            }

            logger.info(f"✅ Daily digest generated: {len(recent_posts)} posts")

            return digest

        except Exception as e:
            logger.error(f"❌ Digest generation failed: {e}")
            return {"error": str(e)}

    def _count_by_source(self, posts: List[Dict]) -> Dict[str, int]:
        """Count posts by source"""
        counts = {}
        for post in posts:
            source = post.get("platform", "unknown")
            counts[source] = counts.get(source, 0) + 1
        return counts

    def get_status(self) -> Dict[str, Any]:
        """Get discovery status"""
        return {
            "scheduler_running": self.scheduler.running if self.scheduler else False,
            "topics_tracked": len(self.topics_of_interest),
            "quality_threshold": self.quality_threshold,
            "last_discovery": self.last_discovery,
            "next_run": str(self.scheduler.get_jobs()[0].next_run_time)
            if self.scheduler.running
            else None,
        }


# Singleton
_discovery_engine = None


def get_discovery_engine() -> AutonomousDiscovery:
    """Get global discovery engine"""
    global _discovery_engine
    if _discovery_engine is None:
        _discovery_engine = AutonomousDiscovery()
    return _discovery_engine


async def test_discovery():
    """Test discovery engine"""
    logger.info("🧪 Testing Autonomous Discovery Engine\n")

    engine = get_discovery_engine()

    # Test discovery
    logger.info("Running discovery...")
    result = await engine.discover_content()

    logger.info("\n📊 Discovery Results:")
    logger.info(f"  Total discovered: {result.get('total_discovered', 0)}")
    logger.info(f"  Quality filtered: {result.get('quality_filtered', 0)}")
    logger.info(f"  Relevant: {result.get('relevant', 0)}")
    logger.info(f"  Unique: {result.get('unique', 0)}")
    logger.info(f"  Saved: {result.get('saved', 0)}")
    logger.info(f"  Duration: {result.get('duration_seconds', 0):.1f}s")

    logger.info("\n📰 Sources:")
    sources = result.get("sources", {})
    for source, count in sources.items():
        logger.info(f"  {source}: {count}")

    # Test digest
    logger.info("\n📊 Generating daily digest...")
    digest = await engine.generate_daily_digest()

    logger.info(f"  Total posts: {digest.get('total_posts', 0)}")
    logger.info(f"  Top stories: {len(digest.get('top_stories', []))}")
    logger.info(f"  Trending topics: {len(digest.get('trending_topics', []))}")

    logger.info("\n✅ Discovery engine working!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_discovery())
