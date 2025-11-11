"""
Profile Content Selector

Queries usable_posts table and selects content for a profile based on:
- Profile's best match (best_persona_key)
- Quality/value thresholds
- Time sensitivity
- Already processed posts
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.storage.db import get_storage
from src.services.profile_content_pipeline import ProfileContentPipeline
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class ProfileContentSelector:
    """
    Select content from usable_posts table for a specific profile.

    Handles:
    - Querying posts matched to profile
    - Filtering by quality/value scores
    - Prioritizing by time sensitivity
    - Tracking already processed posts
    """

    def __init__(self, profile_key: str):
        """
        Initialize selector for a profile

        Args:
            profile_key: Profile identifier (e.g., 'qronoya', 'aspandead')
        """
        self.profile_key = profile_key
        self.pipeline = ProfileContentPipeline(profile_key)
        self.db = get_storage()
        self.config = get_config()

        logger.info(f"✅ Initialized ProfileContentSelector for {self.pipeline.profile_name}")

    def select_posts_for_rewrite(
        self,
        limit: int = 20,
        min_quality_score: float = 7.0,
        min_value_score: float = 7.0,
        min_rewrite_score: float = 7.0,
        time_windows: Optional[List[str]] = None,
        exclude_processed: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Select posts from usable_posts table for this profile

        Args:
            limit: Maximum number of posts to return
            min_quality_score: Minimum quality_score threshold
            min_value_score: Minimum value_score threshold
            min_rewrite_score: Minimum rewrite_score threshold
            time_windows: Filter by relevance_window (e.g., ['same-day', '24-72h'])
            exclude_processed: Exclude posts already rewritten for this profile

        Returns:
            List of post dicts ready for rewriting
        """
        try:
            flags = self.config.flags if self.config else {}
            if flags.get("rewriter_fast_mode"):
                min_quality_score = min(min_quality_score, float(flags.get("rewriter_min_quality_score", min_quality_score)))
                min_value_score = min(min_value_score, float(flags.get("rewriter_min_value_score", min_value_score)))
                min_rewrite_score = min(min_rewrite_score, float(flags.get("rewriter_min_rewrite_score", min_rewrite_score)))
                logger.debug(
                    "⚡ Fast rewrite mode active for %s (thresholds: quality %.2f, value %.2f, rewrite %.2f)",
                    self.profile_key,
                    min_quality_score,
                    min_value_score,
                    min_rewrite_score,
                )

            # Use the new query_usable_posts method
            posts = self.db.query_usable_posts(
                profile_key=self.profile_key,
                limit=limit,
                min_quality_score=min_quality_score,
                min_value_score=min_value_score,
                min_rewrite_score=min_rewrite_score,
                time_windows=time_windows
            )

            logger.info(f"📊 Found {len(posts)} posts for {self.profile_key}")

            # Log breakdown by time window
            if posts:
                breakdown = {}
                for post in posts:
                    window = post.get('relevance_window', 'unknown')
                    breakdown[window] = breakdown.get(window, 0) + 1

                logger.info(f"   Breakdown: {breakdown}")

            return posts

        except Exception as e:
            logger.error(f"Error selecting posts: {e}")
            return []

    def get_posts_by_time_window(
        self,
        relevance_window: str,
        limit: int = 10,
        min_scores: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get posts for a specific time window

        Args:
            relevance_window: One of 'same-day', '24-72h', 'this-week', 'evergreen'
            limit: Maximum number of posts
            min_scores: Dict with min_quality_score, min_value_score, min_rewrite_score

        Returns:
            List of posts
        """
        if min_scores is None:
            min_scores = {
                'min_quality_score': 7.0,
                'min_value_score': 7.0,
                'min_rewrite_score': 7.0
            }

        return self.select_posts_for_rewrite(
            limit=limit,
            time_windows=[relevance_window],
            **min_scores
        )

    def get_urgent_posts(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get urgent posts (same-day, high urgency_score)

        Returns posts that need immediate attention
        """
        posts = self.select_posts_for_rewrite(
            limit=limit,
            time_windows=['same-day'],
            min_quality_score=6.0,  # Lower threshold for urgent content
            min_value_score=6.0,
            min_rewrite_score=6.0
        )

        # Filter to only high urgency
        urgent = [p for p in posts if p.get('urgency_score', 0) >= 7.0]

        if urgent:
            logger.info(f"🚨 Found {len(urgent)} URGENT posts for {self.profile_key}")

        return urgent

    def prepare_post_for_platforms(
        self,
        post: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Prepare a post for rewriting across appropriate platforms

        Args:
            post: Post dict from usable_posts

        Returns:
            Dict mapping platform to list of prepared content dicts:
            {
                'twitter': [prepared_content_dict],
                'threads': [prepared_content_dict],
                'telegram': [prepared_content_dict]
            }
        """
        relevance_window = post.get('relevance_window', 'evergreen')

        # Get platforms for this time window
        platforms = self.pipeline.route_content(relevance_window)

        prepared = {}

        for platform in platforms:
            # Match content type
            content_type = self.pipeline.match_content_type(
                post_category=post.get('category', 'general'),
                platform=platform
            )

            if not content_type:
                logger.warning(f"⚠️  No content type match for {platform}/{post.get('category')}")
                continue

            try:
                prepared_content = self.pipeline.prepare_content_for_rewrite(
                    post=post,
                    platform=platform,
                    content_type=content_type
                )

                if platform not in prepared:
                    prepared[platform] = []

                prepared[platform].append(prepared_content)

                logger.info(f"✅ Prepared {platform}/{content_type} for post {post.get('post_id')}")

            except Exception as e:
                logger.error(f"Error preparing {platform}: {e}")

        return prepared

    def get_daily_queue(
        self,
        max_posts: int = 10
    ) -> Dict[str, Any]:
        """
        Get daily content queue prioritized by time sensitivity

        Returns:
            Dict with categorized posts:
            {
                'urgent': [...],    # same-day posts
                'today': [...],     # 24-72h posts
                'this_week': [...], # this-week posts
                'evergreen': [...]  # evergreen posts
            }
        """
        queue = {
            'urgent': self.get_posts_by_time_window('same-day', limit=3),
            'today': self.get_posts_by_time_window('24-72h', limit=3),
            'this_week': self.get_posts_by_time_window('this-week', limit=2),
            'evergreen': self.get_posts_by_time_window('evergreen', limit=2)
        }

        total = sum(len(posts) for posts in queue.values())
        logger.info(f"📅 Daily queue for {self.profile_key}: {total} posts")

        return queue

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about available content for this profile

        Returns:
            Dict with stats: total_posts, by_time_window, avg_scores, etc.
        """
        try:
            # Get all posts for this profile (with low thresholds to get everything)
            all_posts = self.db.query_usable_posts(
                profile_key=self.profile_key,
                limit=1000,  # Get a large sample
                min_quality_score=0,
                min_value_score=0,
                min_rewrite_score=0
            )

            if not all_posts:
                return {
                    'profile_key': self.profile_key,
                    'profile_name': self.pipeline.profile_name,
                    'total_posts': 0,
                    'by_time_window': {},
                    'overall_avg_quality': 0,
                    'overall_avg_value': 0,
                    'overall_avg_rewrite': 0
                }

            # Calculate stats from posts
            stats = {
                'profile_key': self.profile_key,
                'profile_name': self.pipeline.profile_name,
                'total_posts': len(all_posts),
                'by_time_window': {},
                'overall_avg_quality': 0,
                'overall_avg_value': 0,
                'overall_avg_rewrite': 0
            }

            window_data = {}
            total_quality = 0
            total_value = 0
            total_rewrite = 0

            for post in all_posts:
                window = post.get('relevance_window', 'unknown')

                if window not in window_data:
                    window_data[window] = {
                        'count': 0,
                        'total_quality': 0,
                        'total_value': 0,
                        'total_rewrite': 0,
                        'max_urgency': 0
                    }

                # Handle None values from database
                quality = post.get('quality_score') or 0
                value = post.get('value_score') or 0
                rewrite = post.get('rewrite_score') or 0
                urgency = post.get('urgency_score') or 0

                window_data[window]['count'] += 1
                window_data[window]['total_quality'] += float(quality)
                window_data[window]['total_value'] += float(value)
                window_data[window]['total_rewrite'] += float(rewrite)
                window_data[window]['max_urgency'] = max(
                    window_data[window]['max_urgency'],
                    float(urgency)
                )

                total_quality += float(quality)
                total_value += float(value)
                total_rewrite += float(rewrite)

            # Calculate averages
            for window, data in window_data.items():
                count = data['count']
                stats['by_time_window'][window] = {
                    'count': count,
                    'avg_quality': data['total_quality'] / count if count > 0 else 0,
                    'avg_value': data['total_value'] / count if count > 0 else 0,
                    'avg_rewrite': data['total_rewrite'] / count if count > 0 else 0,
                    'max_urgency': data['max_urgency']
                }

            if stats['total_posts'] > 0:
                stats['overall_avg_quality'] = total_quality / stats['total_posts']
                stats['overall_avg_value'] = total_value / stats['total_posts']
                stats['overall_avg_rewrite'] = total_rewrite / stats['total_posts']

            logger.info(f"📊 Stats for {self.profile_key}: {stats['total_posts']} posts available")

            return stats

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'profile_key': self.profile_key,
                'error': str(e)
            }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("="*80)
    print("PROFILE CONTENT SELECTOR - DEMO")
    print("="*80)

    # Test with qronoya
    selector = ProfileContentSelector('qronoya')

    # Get statistics
    print("\n📊 STATISTICS:\n")
    stats = selector.get_statistics()
    print(f"Profile: {stats['profile_name']}")
    print(f"Total posts: {stats['total_posts']}")
    print(f"Avg Quality: {stats['overall_avg_quality']:.2f}")
    print(f"Avg Value: {stats['overall_avg_value']:.2f}")
    print(f"Avg Rewrite: {stats['overall_avg_rewrite']:.2f}")

    print("\nBy Time Window:")
    for window, data in stats.get('by_time_window', {}).items():
        print(f"  {window:12} - {data['count']:3} posts (quality: {data['avg_quality']:.1f})")

    # Get daily queue
    print("\n" + "="*80)
    print("📅 DAILY QUEUE:\n")
    queue = selector.get_daily_queue(max_posts=10)

    for category, posts in queue.items():
        print(f"{category.upper():12} - {len(posts)} posts")
        for post in posts[:2]:  # Show first 2
            title = post.get('title', post.get('content', '')[:50])
            print(f"  • {title[:60]}...")

    # Test post preparation
    if queue.get('urgent'):
        print("\n" + "="*80)
        print("🔧 PREPARING URGENT POST FOR PLATFORMS:\n")

        post = queue['urgent'][0]
        print(f"Post: {post.get('title', 'No title')[:60]}")
        print(f"Category: {post.get('category')}")
        print(f"Time window: {post.get('relevance_window')}")

        prepared = selector.prepare_post_for_platforms(post)

        print(f"\nPrepared for {len(prepared)} platforms:")
        for platform, content_list in prepared.items():
            print(f"\n  {platform.upper()}:")
            for content in content_list:
                print(f"    Content type: {content['content_type']}")
                print(f"    Constraints: {content['constraints']}")
                prompt_preview = content['prompt'][:100].replace('\n', ' ')
                print(f"    Prompt: {prompt_preview}...")

    print("\n" + "="*80)
    print("✅ Selector demo complete!")
    print("="*80)
