"""
Engagement Metrics Tracker

Tracks engagement metrics (likes, views, comments, etc.) for published posts
and updates the EngagementLearner database.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.database.manager import SupabaseManager
from src.publishing.engagement_learner import EngagementLearner

logger = logging.getLogger(__name__)


class EngagementTracker:
    """Tracks engagement metrics for published posts"""

    def __init__(self):
        self.engagement_learner = EngagementLearner()
        self.supabase = SupabaseManager().client

    async def track_post_publication(
        self,
        scheduled_post_id: str,
        platform: str,
        platform_post_id: str,
        persona_key: str,
        content: str,
        post_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        Track a newly published post for engagement monitoring.

        Note: posted_content record may already exist from mark_posted().
        This function ensures it's tracked for engagement monitoring.

        Args:
            scheduled_post_id: ID from scheduled_posts table
            platform: Platform name (twitter, threads, telegram)
            platform_post_id: Platform-specific post ID
            persona_key: Persona used for rewrite
            content: Posted content text
            post_url: Optional post URL
            metadata: Optional metadata (topic, tags, etc.)

        Returns:
            posted_content record ID, or None if failed
        """
        try:
            # Check if posted_content already exists (created by mark_posted)
            try:
                existing = (
                    self.supabase.table("posted_content")
                    .select("id")
                    .eq("scheduled_post_id", scheduled_post_id)
                    .eq("platform_post_id", platform_post_id)
                    .single()
                    .execute()
                )

                if existing.data:
                    record_id = existing.data["id"]
                    logger.debug(f"📝 Using existing posted_content record: {record_id}")
                    return record_id
            except Exception as e:
                logger.error(f"Error: {e}")
                # Record doesn't exist yet, will create it
                pass

            # Get metadata from scheduled_post if available
            if not metadata:
                try:
                    scheduled_post = (
                        self.supabase.table("scheduled_posts")
                        .select("metadata")
                        .eq("id", scheduled_post_id)
                        .single()
                        .execute()
                    )
                    if scheduled_post.data:
                        metadata = scheduled_post.data.get("metadata", {})
                except Exception as e:
                    logger.error(f"Error: {e}")
                    metadata = {}

            # Track using EngagementLearner (creates new record if needed)
            record_id = await self.engagement_learner.track_rewrite_performance(
                platform=platform,
                platform_post_id=platform_post_id,
                persona=persona_key,
                content=content,
                metadata={
                    **(metadata or {}),
                    "url": post_url,
                    "scheduled_post_id": scheduled_post_id,
                },
            )

            if record_id:
                logger.info(
                    f"✅ Tracked post publication: {platform}/{platform_post_id} (ID: {record_id})"
                )
            else:
                logger.warning(
                    f"⚠️ Failed to track post publication: {platform}/{platform_post_id}"
                )

            return record_id

        except Exception as e:
            logger.error(f"❌ Error tracking post publication: {e}")
            return None

    async def fetch_and_update_metrics(
        self, posted_content_id: str, platform: str, platform_post_id: str
    ) -> bool:
        """
        Fetch current engagement metrics from platform and update database.

        Args:
            posted_content_id: ID from posted_content table
            platform: Platform name
            platform_post_id: Platform-specific post ID

        Returns:
            True if successful, False otherwise
        """
        try:
            metrics = await self._fetch_platform_metrics(platform, platform_post_id)

            if metrics:
                success = await self.engagement_learner.update_metrics(
                    posted_content_id=posted_content_id, metrics=metrics
                )
                if success:
                    logger.info(
                        f"✅ Updated metrics for {platform}/{platform_post_id}: {metrics}"
                    )
                return success
            else:
                logger.warning(
                    f"⚠️ No metrics available for {platform}/{platform_post_id}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Error updating metrics: {e}")
            return False

    async def _fetch_platform_metrics(
        self, platform: str, platform_post_id: str
    ) -> Optional[Dict[str, int]]:
        """
        Fetch engagement metrics from platform API.

        Returns:
            Dict with keys: views, likes, comments, shares, bookmarks
            or None if unavailable
        """
        try:
            if platform == "threads":
                return await self._fetch_threads_metrics(platform_post_id)
            elif platform == "twitter":
                return await self._fetch_twitter_metrics(platform_post_id)
            elif platform == "telegram":
                return await self._fetch_telegram_metrics(platform_post_id)
            else:
                logger.warning(f"⚠️ Unknown platform for metrics: {platform}")
                return None

        except Exception as e:
            logger.error(f"❌ Error fetching {platform} metrics: {e}")
            return None

    async def _fetch_threads_metrics(self, thread_id: str) -> Optional[Dict[str, int]]:
        """Fetch Threads engagement metrics"""
        try:
            from src.publishing.platforms.threads import ThreadsPoster

            poster = ThreadsPoster()
            insights = poster.get_thread_insights(thread_id)

            if insights:
                return {
                    "views": insights.get("views", 0),
                    "likes": insights.get("likes", 0),
                    "comments": insights.get("replies", 0),
                    "shares": insights.get("reposts", 0) + insights.get("quotes", 0),
                    "bookmarks": 0,  # Threads doesn't have bookmarks
                }
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching Threads metrics: {e}")
            return None

    async def _fetch_twitter_metrics(self, tweet_id: str) -> Optional[Dict[str, int]]:
        """Fetch Twitter engagement metrics using Twitter API v2"""
        try:
            import os

            import tweepy

            # Get Twitter API credentials from environment
            api_key = os.getenv("TWITTER_API_KEY")
            api_secret = os.getenv("TWITTER_API_SECRET")
            access_token = os.getenv("TWITTER_ACCESS_TOKEN")
            access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
            bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

            if not all([bearer_token]):
                logger.warning("Twitter API credentials missing, cannot fetch metrics")
                return None

            # Use Twitter API v2 client
            client = tweepy.Client(bearer_token=bearer_token)

            # Get tweet metrics
            tweet = client.get_tweet(
                tweet_id, tweet_fields=["public_metrics", "created_at", "author_id"]
            )

            if not tweet.data:
                logger.warning(f"Tweet {tweet_id} not found or deleted")
                return None

            metrics = tweet.data.public_metrics

            return {
                "likes": metrics.get("like_count", 0),
                "retweets": metrics.get("retweet_count", 0),
                "replies": metrics.get("reply_count", 0),
                "quotes": metrics.get("quote_count", 0),
                "impressions": metrics.get("impression_count", 0),
                "total_engagement": (
                    metrics.get("like_count", 0)
                    + metrics.get("retweet_count", 0)
                    + metrics.get("reply_count", 0)
                    + metrics.get("quote_count", 0)
                ),
            }

        except ImportError:
            logger.error("tweepy library not available for Twitter metrics fetching")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching Twitter metrics for {tweet_id}: {e}")
            return None

    async def _fetch_telegram_metrics(
        self, message_id: str
    ) -> Optional[Dict[str, int]]:
        """Fetch Telegram engagement metrics"""
        try:
            # Telegram Bot API doesn't provide engagement metrics
            # Would need to track manually or use channel statistics
            # For now, return None
            logger.debug(
                f"Telegram metrics fetching not yet implemented for {message_id}"
            )
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching Telegram metrics: {e}")
            return None

    async def update_all_recent_posts(self, hours_back: int = 24) -> Dict[str, int]:
        """
        Update metrics for all posts published in the last N hours.

        Args:
            hours_back: How many hours back to check

        Returns:
            Dict with 'updated', 'failed', 'skipped' counts
        """
        try:
            cutoff_time = (datetime.now() - timedelta(hours=hours_back)).isoformat()

            # Get all posted content from last N hours
            response = (
                self.supabase.table("posted_content")
                .select("id, platform, platform_post_id, posted_at")
                .gte("posted_at", cutoff_time)
                .execute()
            )

            posts = response.data or []

            updated = 0
            failed = 0
            skipped = 0

            for post in posts:
                posted_content_id = post["id"]
                platform = post["platform"]
                platform_post_id = post.get("platform_post_id")

                if not platform_post_id:
                    skipped += 1
                    continue

                success = await self.fetch_and_update_metrics(
                    posted_content_id=posted_content_id,
                    platform=platform,
                    platform_post_id=platform_post_id,
                )

                if success:
                    updated += 1
                else:
                    failed += 1

            logger.info(
                f"📊 Updated {updated} posts, {failed} failed, {skipped} skipped"
            )

            return {
                "updated": updated,
                "failed": failed,
                "skipped": skipped,
                "total": len(posts),
            }

        except Exception as e:
            logger.error(f"❌ Error updating recent posts: {e}")
            return {
                "updated": 0,
                "failed": 0,
                "skipped": 0,
                "total": 0,
                "error": str(e),
            }


# Global instance
_tracker_instance: Optional[EngagementTracker] = None


def get_engagement_tracker() -> EngagementTracker:
    """Get or create global EngagementTracker instance"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = EngagementTracker()
    return _tracker_instance
