"""
Engagement Learning System

Learns from real performance data to improve rewrite quality over time.
Connects to posted_content and posted_metrics tables to:
- Track which rewrites perform well (high engagement)
- Identify successful patterns by persona, platform, content_type
- Rank examples by historical performance
- Auto-tune example selection based on what works
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class EngagementLearner:
    """
    Learns from posted content performance to improve rewrite quality.

    Core Functions:
    1. Track performance metrics for posted content
    2. Identify high-performing patterns (voice, tone, structure)
    3. Rank examples by historical success
    4. Weight example selection by performance
    """

    def __init__(self):
        """Initialize the engagement learner with Supabase connection"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_cache_update = None

        logger.info("✅ EngagementLearner initialized with Supabase connection")

    def calculate_engagement_score(self, metrics: Dict[str, int]) -> float:
        """
        Calculate normalized engagement score from metrics.

        Weighted formula:
        - Views: baseline (weight 0.1)
        - Likes: strong signal (weight 1.0)
        - Comments: very strong signal (weight 2.0)
        - Shares: strongest signal (weight 3.0)
        - Bookmarks: strong signal (weight 1.5)

        Returns score 0-100.
        """
        views = metrics.get('views', 0)
        likes = metrics.get('likes', 0)
        comments = metrics.get('comments', 0)
        shares = metrics.get('shares', 0)
        bookmarks = metrics.get('bookmarks', 0)

        if views == 0:
            return 0.0

        # Calculate engagement rate (interactions per 1000 views)
        engagement_per_1k = (
            (likes * 1.0 +
             comments * 2.0 +
             shares * 3.0 +
             bookmarks * 1.5) / (views / 1000)
        )

        # Normalize to 0-100 scale
        # Assume excellent engagement is 100+ interactions per 1k views
        score = min(100, (engagement_per_1k / 100) * 100)

        return round(score, 2)

    async def get_performance_stats(
        self,
        persona: Optional[str] = None,
        platform: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance statistics for posted content.

        Returns:
        - Average engagement score
        - Total posts analyzed
        - Top performing posts
        - Performance by platform
        - Performance by persona
        """
        try:
            # Build query
            query = self.supabase.table('posted_content').select('*')

            # Filter by persona if specified
            if persona:
                query = query.eq('persona', persona)

            # Filter by platform if specified
            if platform:
                query = query.eq('platform', platform)

            # Filter by date range
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            query = query.gte('posted_at', cutoff_date)

            # Execute query
            response = query.execute()
            posts = response.data

            if not posts:
                return {
                    'total_posts': 0,
                    'avg_engagement_score': 0,
                    'top_posts': [],
                    'by_platform': {},
                    'by_persona': {}
                }

            # Calculate statistics
            total_posts = len(posts)
            total_engagement = sum(p.get('engagement_score', 0) for p in posts)
            avg_engagement = total_engagement / total_posts if total_posts > 0 else 0

            # Sort by engagement score
            sorted_posts = sorted(posts, key=lambda p: p.get('engagement_score', 0), reverse=True)
            top_posts = sorted_posts[:10]

            # Group by platform
            by_platform = defaultdict(lambda: {'count': 0, 'total_engagement': 0})
            for post in posts:
                plt = post.get('platform', 'unknown')
                by_platform[plt]['count'] += 1
                by_platform[plt]['total_engagement'] += post.get('engagement_score', 0)

            # Calculate averages
            platform_stats = {
                plt: {
                    'count': stats['count'],
                    'avg_engagement': stats['total_engagement'] / stats['count'] if stats['count'] > 0 else 0
                }
                for plt, stats in by_platform.items()
            }

            # Group by persona
            by_persona = defaultdict(lambda: {'count': 0, 'total_engagement': 0})
            for post in posts:
                pers = post.get('persona', 'unknown')
                by_persona[pers]['count'] += 1
                by_persona[pers]['total_engagement'] += post.get('engagement_score', 0)

            # Calculate averages
            persona_stats = {
                pers: {
                    'count': stats['count'],
                    'avg_engagement': stats['total_engagement'] / stats['count'] if stats['count'] > 0 else 0
                }
                for pers, stats in by_persona.items()
            }

            logger.info(f"📊 Performance stats: {total_posts} posts, avg engagement {avg_engagement:.2f}")

            return {
                'total_posts': total_posts,
                'avg_engagement_score': round(avg_engagement, 2),
                'top_posts': [
                    {
                        'id': p['id'],
                        'platform': p.get('platform'),
                        'persona': p.get('persona'),
                        'engagement_score': p.get('engagement_score', 0),
                        'likes': p.get('total_likes', 0),
                        'comments': p.get('total_comments', 0),
                        'shares': p.get('total_shares', 0),
                        'url': p.get('url')
                    }
                    for p in top_posts
                ],
                'by_platform': platform_stats,
                'by_persona': persona_stats
            }

        except Exception as e:
            logger.error(f"❌ Error getting performance stats: {e}")
            return {
                'total_posts': 0,
                'avg_engagement_score': 0,
                'top_posts': [],
                'by_platform': {},
                'by_persona': {},
                'error': str(e)
            }

    async def get_top_performing_content(
        self,
        persona: str,
        platform: Optional[str] = None,
        limit: int = 20,
        min_engagement_score: float = 70.0
    ) -> List[Dict[str, Any]]:
        """
        Get top performing content for a persona/platform combination.
        Used to identify successful patterns and examples.

        Returns list of high-performing posts with their metrics.
        """
        try:
            # Build query
            query = self.supabase.table('posted_content').select('*')

            # Filter by persona
            query = query.eq('persona', persona)

            # Filter by platform if specified
            if platform:
                query = query.eq('platform', platform)

            # Filter by minimum engagement score
            query = query.gte('engagement_score', min_engagement_score)

            # Order by engagement score and limit
            query = query.order('engagement_score', desc=True).limit(limit)

            # Execute query
            response = query.execute()
            posts = response.data

            logger.info(f"🏆 Found {len(posts)} top performing posts for {persona}/{platform or 'all'}")

            return posts

        except Exception as e:
            logger.error(f"❌ Error getting top performing content: {e}")
            return []

    async def learn_successful_patterns(
        self,
        persona: str,
        platform: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze top performing content to identify successful patterns.

        Returns:
        - Common topics/tags in high-performing content
        - Average length of successful posts
        - Common structural patterns
        - Performance benchmarks
        """
        try:
            # Get top performing content
            top_posts = await self.get_top_performing_content(
                persona=persona,
                platform=platform,
                limit=50,
                min_engagement_score=60.0
            )

            if not top_posts:
                logger.warning(f"⚠️ No high-performing content found for {persona}/{platform or 'all'}")
                return {
                    'sample_size': 0,
                    'patterns': {}
                }

            # Analyze patterns
            all_tags = []
            all_topics = []
            lengths = []

            for post in top_posts:
                if post.get('tags'):
                    all_tags.extend(post['tags'])

                if post.get('topic'):
                    all_topics.append(post['topic'])

                if post.get('initial_text'):
                    lengths.append(len(post['initial_text']))

            # Count frequency
            tag_counts = defaultdict(int)
            for tag in all_tags:
                tag_counts[tag] += 1

            topic_counts = defaultdict(int)
            for topic in all_topics:
                topic_counts[topic] += 1

            # Sort by frequency
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            # Calculate length statistics
            avg_length = np.mean(lengths) if lengths else 0
            median_length = np.median(lengths) if lengths else 0

            patterns = {
                'sample_size': len(top_posts),
                'avg_engagement_score': np.mean([p.get('engagement_score', 0) for p in top_posts]),
                'top_tags': [{'tag': tag, 'count': count} for tag, count in top_tags],
                'top_topics': [{'topic': topic, 'count': count} for topic, count in top_topics],
                'length_stats': {
                    'avg': int(avg_length),
                    'median': int(median_length),
                    'min': min(lengths) if lengths else 0,
                    'max': max(lengths) if lengths else 0
                }
            }

            logger.info(f"📈 Learned patterns from {len(top_posts)} high-performing posts")

            return patterns

        except Exception as e:
            logger.error(f"❌ Error learning successful patterns: {e}")
            return {
                'sample_size': 0,
                'patterns': {},
                'error': str(e)
            }

    async def rank_examples_by_performance(
        self,
        persona: str,
        platform: str,
        example_texts: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Rank example texts by their similarity to high-performing content.

        This uses simple heuristics for now:
        - Length similarity to successful posts
        - Tag/topic overlap
        - Structure similarity

        Returns list of (example_text, performance_score) tuples, sorted by score.
        """
        try:
            # Get successful patterns
            patterns = await self.learn_successful_patterns(persona=persona, platform=platform)

            if patterns['sample_size'] == 0:
                # No performance data, return examples with neutral scores
                logger.warning(f"⚠️ No performance data for {persona}/{platform}, returning neutral scores")
                return [(text, 50.0) for text in example_texts]

            # Extract pattern benchmarks
            target_length = patterns.get('length_stats', {}).get('avg', 200)
            top_tags = {tag['tag'] for tag in patterns.get('top_tags', [])[:5]}

            # Score each example
            scored_examples = []
            for text in example_texts:
                score = 50.0  # Start at neutral

                # Length similarity (max ±20 points)
                text_length = len(text)
                length_diff = abs(text_length - target_length)
                length_score = max(0, 20 - (length_diff / target_length * 20))
                score += length_score - 10  # Center around 0

                # Simple tag matching (max ±30 points)
                # Check if any of the top tags appear in the text
                text_lower = text.lower()
                matches = sum(1 for tag in top_tags if tag.lower() in text_lower)
                tag_score = min(30, matches * 10)
                score += tag_score - 15  # Center around 0

                # Clamp to 0-100
                score = max(0, min(100, score))

                scored_examples.append((text, score))

            # Sort by score descending
            scored_examples.sort(key=lambda x: x[1], reverse=True)

            logger.info(f"📊 Ranked {len(example_texts)} examples by performance (top score: {scored_examples[0][1]:.1f})")

            return scored_examples

        except Exception as e:
            logger.error(f"❌ Error ranking examples: {e}")
            # Return neutral scores on error
            return [(text, 50.0) for text in example_texts]

    async def get_weighted_examples(
        self,
        persona: str,
        platform: str,
        all_examples: List[str],
        count: int = 3
    ) -> List[str]:
        """
        Select examples weighted by their performance similarity.

        Higher-scoring examples (more similar to successful posts) are more likely
        to be selected, but there's still randomness to maintain variety.

        Args:
            persona: Persona key (e.g., 'qronoya', 'aspandead')
            platform: Platform name (e.g., 'twitter', 'threads')
            all_examples: List of all available example texts
            count: Number of examples to select

        Returns:
            List of selected example texts
        """
        try:
            if not all_examples:
                return []

            if len(all_examples) <= count:
                return all_examples

            # Rank examples by performance
            ranked = await self.rank_examples_by_performance(
                persona=persona,
                platform=platform,
                example_texts=all_examples
            )

            # Extract scores and normalize to probabilities
            scores = np.array([score for _, score in ranked])

            # Avoid division by zero
            if scores.sum() == 0:
                # All scores are 0, use uniform distribution
                probabilities = np.ones(len(scores)) / len(scores)
            else:
                # Normalize to probabilities (higher score = higher probability)
                probabilities = scores / scores.sum()

            # Sample without replacement
            selected_indices = np.random.choice(
                len(ranked),
                size=min(count, len(ranked)),
                replace=False,
                p=probabilities
            )

            selected = [ranked[i][0] for i in selected_indices]

            logger.info(f"🎯 Selected {len(selected)} performance-weighted examples for {persona}/{platform}")

            return selected

        except Exception as e:
            logger.error(f"❌ Error getting weighted examples: {e}")
            # Fall back to random selection
            import random
            return random.sample(all_examples, min(count, len(all_examples)))

    async def track_rewrite_performance(
        self,
        platform: str,
        platform_post_id: str,
        persona: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Track a newly posted rewrite for future performance analysis.

        Args:
            platform: Platform name (twitter, threads, telegram)
            platform_post_id: Platform-specific post ID
            persona: Persona used for rewrite
            content: Posted content text
            metadata: Optional metadata (topic, tags, etc.)

        Returns:
            Database ID of the posted_content record, or None if failed
        """
        try:
            # Prepare data
            data = {
                'platform': platform,
                'platform_post_id': platform_post_id,
                'persona': persona,
                'initial_text': content,
                'posted_at': datetime.now().isoformat(),
            }

            # Add metadata if provided
            if metadata:
                if 'topic' in metadata:
                    data['topic'] = metadata['topic']
                if 'tags' in metadata:
                    data['tags'] = metadata['tags']
                if 'url' in metadata:
                    data['url'] = metadata['url']
                if 'lang' in metadata:
                    data['lang'] = metadata['lang']

            # Insert into database
            response = self.supabase.table('posted_content').insert(data).execute()

            if response.data and len(response.data) > 0:
                record_id = response.data[0]['id']
                logger.info(f"✅ Tracked posted content: {platform}/{platform_post_id} (ID: {record_id})")
                return record_id
            else:
                logger.error(f"❌ Failed to track posted content: no data returned")
                return None

        except Exception as e:
            logger.error(f"❌ Error tracking rewrite performance: {e}")
            return None

    async def update_metrics(
        self,
        posted_content_id: int,
        metrics: Dict[str, int]
    ) -> bool:
        """
        Update metrics for a posted content record.

        Args:
            posted_content_id: ID from posted_content table
            metrics: Dict with keys: views, likes, comments, shares, bookmarks

        Returns:
            True if successful, False otherwise
        """
        try:
            # Calculate engagement score
            engagement_score = self.calculate_engagement_score(metrics)

            # Update posted_content with latest totals and engagement score
            update_data = {
                'total_views': metrics.get('views', 0),
                'total_likes': metrics.get('likes', 0),
                'total_comments': metrics.get('comments', 0),
                'total_shares': metrics.get('shares', 0),
                'total_bookmarks': metrics.get('bookmarks', 0),
                'engagement_score': engagement_score
            }

            response = self.supabase.table('posted_content')\
                .update(update_data)\
                .eq('id', posted_content_id)\
                .execute()

            # Also insert a snapshot into posted_metrics
            metrics_data = {
                'posted_content_id': posted_content_id,
                'snapshot_at': datetime.now().isoformat(),
                'views': metrics.get('views'),
                'likes': metrics.get('likes'),
                'comments': metrics.get('comments'),
                'shares': metrics.get('shares'),
                'bookmarks': metrics.get('bookmarks')
            }

            self.supabase.table('posted_metrics').insert(metrics_data).execute()

            logger.info(f"✅ Updated metrics for posted_content {posted_content_id} (engagement: {engagement_score:.2f})")

            return True

        except Exception as e:
            logger.error(f"❌ Error updating metrics: {e}")
            return False
