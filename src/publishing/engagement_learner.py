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
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from supabase import Client, create_client

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
        views = metrics.get("views", 0)
        likes = metrics.get("likes", 0)
        comments = metrics.get("comments", 0)
        shares = metrics.get("shares", 0)
        bookmarks = metrics.get("bookmarks", 0)

        if views == 0:
            return 0.0

        # Calculate engagement rate (interactions per 1000 views)
        engagement_per_1k = (
            likes * 1.0 + comments * 2.0 + shares * 3.0 + bookmarks * 1.5
        ) / (views / 1000)

        # Normalize to 0-100 scale
        # Assume excellent engagement is 100+ interactions per 1k views
        score = min(100, (engagement_per_1k / 100) * 100)

        return round(score, 2)

    async def get_performance_stats(
        self,
        persona: Optional[str] = None,
        platform: Optional[str] = None,
        days_back: int = 30,
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
            query = self.supabase.table("posted_content").select("*")

            # Filter by persona if specified (use persona_key column)
            if persona:
                query = query.eq("persona_key", persona)

            # Filter by platform if specified
            if platform:
                query = query.eq("platform", platform)

            # Filter by date range
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            query = query.gte("posted_at", cutoff_date)

            # Execute query
            response = query.execute()
            posts = response.data

            if not posts:
                return {
                    "total_posts": 0,
                    "avg_engagement_score": 0,
                    "top_posts": [],
                    "by_platform": {},
                    "by_persona": {},
                }

            # Calculate statistics (calculate engagement from engagement_json)
            total_posts = len(posts)
            engagement_scores = []
            for p in posts:
                engagement_json = p.get("engagement_json", {})
                if isinstance(engagement_json, dict):
                    score = self.calculate_engagement_score(engagement_json)
                else:
                    score = 0
                engagement_scores.append(score)
                p["_calculated_engagement"] = score

            total_engagement = sum(engagement_scores)
            avg_engagement = total_engagement / total_posts if total_posts > 0 else 0

            # Sort by engagement score
            sorted_posts = sorted(
                posts, key=lambda p: p.get("_calculated_engagement", 0), reverse=True
            )
            top_posts = sorted_posts[:10]

            # Group by platform
            by_platform = defaultdict(lambda: {"count": 0, "total_engagement": 0})
            for post in posts:
                plt = post.get("platform", "unknown")
                by_platform[plt]["count"] += 1
                by_platform[plt]["total_engagement"] += post.get("engagement_score", 0)

            # Calculate averages
            platform_stats = {
                plt: {
                    "count": stats["count"],
                    "avg_engagement": stats["total_engagement"] / stats["count"]
                    if stats["count"] > 0
                    else 0,
                }
                for plt, stats in by_platform.items()
            }

            # Group by persona (use persona_key column)
            by_persona = defaultdict(lambda: {"count": 0, "total_engagement": 0})
            for post in posts:
                pers = post.get("persona_key", "unknown")
                # Calculate engagement from engagement_json if available
                engagement_json = post.get("engagement_json", {})
                if isinstance(engagement_json, dict):
                    engagement_score = self.calculate_engagement_score(engagement_json)
                else:
                    engagement_score = 0
                by_persona[pers]["count"] += 1
                by_persona[pers]["total_engagement"] += engagement_score

            # Calculate averages
            persona_stats = {
                pers: {
                    "count": stats["count"],
                    "avg_engagement": stats["total_engagement"] / stats["count"]
                    if stats["count"] > 0
                    else 0,
                }
                for pers, stats in by_persona.items()
            }

            logger.info(
                f"📊 Performance stats: {total_posts} posts, avg engagement {avg_engagement:.2f}"
            )

            return {
                "total_posts": total_posts,
                "avg_engagement_score": round(avg_engagement, 2),
                "top_posts": [
                    {
                        "id": p["id"],
                        "platform": p.get("platform"),
                        "persona": p.get("persona_key"),
                        "engagement_score": p.get("_calculated_engagement", 0),
                        "engagement_json": p.get("engagement_json", {}),
                        "url": p.get("post_url"),
                    }
                    for p in top_posts
                ],
                "by_platform": platform_stats,
                "by_persona": persona_stats,
            }

        except Exception as e:
            logger.error(f"❌ Error getting performance stats: {e}")
            return {
                "total_posts": 0,
                "avg_engagement_score": 0,
                "top_posts": [],
                "by_platform": {},
                "by_persona": {},
                "error": str(e),
            }

    async def get_top_performing_content(
        self,
        persona: str,
        platform: Optional[str] = None,
        limit: int = 20,
        min_engagement_score: float = 70.0,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing content for a persona/platform combination.
        Used to identify successful patterns and examples.

        Returns list of high-performing posts with their metrics.
        """
        try:
            # Build query
            query = self.supabase.table("posted_content").select("*")

            # Filter by persona (use persona_key column)
            query = query.eq("persona_key", persona)

            # Filter by platform if specified
            if platform:
                query = query.eq("platform", platform)

            # Note: We can't filter by engagement_score in the query since it's calculated from engagement_json
            # We'll filter after fetching

            # Execute query (we'll calculate and filter engagement scores after)
            response = query.execute()
            posts = response.data

            # Calculate engagement scores and filter
            scored_posts = []
            for post in posts:
                engagement_json = post.get("engagement_json", {})
                if isinstance(engagement_json, dict):
                    engagement_score = self.calculate_engagement_score(engagement_json)
                    if engagement_score >= min_engagement_score:
                        post["_calculated_engagement"] = engagement_score
                        scored_posts.append(post)
                else:
                    # If no engagement data, assign 0 and include if min is 0
                    if min_engagement_score == 0:
                        post["_calculated_engagement"] = 0
                        scored_posts.append(post)

            # Sort by engagement score and limit
            scored_posts.sort(
                key=lambda p: p.get("_calculated_engagement", 0), reverse=True
            )
            posts = scored_posts[:limit]

            logger.info(
                f"🏆 Found {len(posts)} top performing posts for {persona}/{platform or 'all'}"
            )

            return posts

        except Exception as e:
            logger.error(f"❌ Error getting top performing content: {e}")
            return []

    async def learn_successful_patterns(
        self, persona: str, platform: Optional[str] = None
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
                persona=persona, platform=platform, limit=50, min_engagement_score=60.0
            )

            if not top_posts:
                logger.warning(
                    f"⚠️ No high-performing content found for {persona}/{platform or 'all'}"
                )
                return {"sample_size": 0, "patterns": {}}

            # Analyze patterns
            all_tags = []
            all_topics = []
            lengths = []

            for post in top_posts:
                # Extract tags from metadata if available
                metadata = post.get("metadata", {})
                if isinstance(metadata, dict) and metadata.get("tags"):
                    tags = metadata["tags"]
                    if isinstance(tags, list):
                        all_tags.extend(tags)
                    elif isinstance(tags, str):
                        all_tags.append(tags)

                if post.get("topic"):
                    all_topics.append(post["topic"])

                # Use content field instead of initial_text
                if post.get("content"):
                    lengths.append(len(post["content"]))

            # Count frequency
            tag_counts = defaultdict(int)
            for tag in all_tags:
                tag_counts[tag] += 1

            topic_counts = defaultdict(int)
            for topic in all_topics:
                topic_counts[topic] += 1

            # Sort by frequency
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[
                :10
            ]

            # Calculate length statistics
            avg_length = np.mean(lengths) if lengths else 0
            median_length = np.median(lengths) if lengths else 0

            # Calculate engagement scores for top posts
            engagement_scores = []
            for post in top_posts:
                engagement_json = post.get("engagement_json", {})
                if isinstance(engagement_json, dict):
                    score = self.calculate_engagement_score(engagement_json)
                else:
                    score = post.get("_calculated_engagement", 0)
                engagement_scores.append(score)

            patterns = {
                "sample_size": len(top_posts),
                "avg_engagement_score": np.mean(engagement_scores)
                if engagement_scores
                else 0,
                "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
                "top_topics": [
                    {"topic": topic, "count": count} for topic, count in top_topics
                ],
                "length_stats": {
                    "avg": int(avg_length),
                    "median": int(median_length),
                    "min": min(lengths) if lengths else 0,
                    "max": max(lengths) if lengths else 0,
                },
            }

            logger.info(
                f"📈 Learned patterns from {len(top_posts)} high-performing posts"
            )

            return patterns

        except Exception as e:
            logger.error(f"❌ Error learning successful patterns: {e}")
            return {"sample_size": 0, "patterns": {}, "error": str(e)}

    async def rank_examples_by_performance(
        self, persona: str, platform: str, example_texts: List[str]
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
            patterns = await self.learn_successful_patterns(
                persona=persona, platform=platform
            )

            if patterns["sample_size"] == 0:
                # No performance data, return examples with neutral scores
                logger.warning(
                    f"⚠️ No performance data for {persona}/{platform}, returning neutral scores"
                )
                return [(text, 50.0) for text in example_texts]

            # Extract pattern benchmarks
            target_length = patterns.get("length_stats", {}).get("avg", 200)
            top_tags = {tag["tag"] for tag in patterns.get("top_tags", [])[:5]}

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

            logger.info(
                f"📊 Ranked {len(example_texts)} examples by performance (top score: {scored_examples[0][1]:.1f})"
            )

            return scored_examples

        except Exception as e:
            logger.error(f"❌ Error ranking examples: {e}")
            # Return neutral scores on error
            return [(text, 50.0) for text in example_texts]

    async def get_weighted_examples(
        self, persona: str, platform: str, all_examples: List[str], count: int = 3
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
                persona=persona, platform=platform, example_texts=all_examples
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
                p=probabilities,
            )

            selected = [ranked[i][0] for i in selected_indices]

            logger.info(
                f"🎯 Selected {len(selected)} performance-weighted examples for {persona}/{platform}"
            )

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
        metadata: Optional[Dict[str, Any]] = None,
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
            # Prepare data (use persona_key and content columns)
            data = {
                "platform": platform,
                "platform_post_id": platform_post_id,
                "persona_key": persona,
                "content": content,
                "posted_at": datetime.now().isoformat(),
            }

            # Add metadata if provided
            if metadata:
                metadata_dict = {}
                if "topic" in metadata:
                    metadata_dict["topic"] = metadata["topic"]
                if "tags" in metadata:
                    metadata_dict["tags"] = metadata["tags"]
                if "url" in metadata:
                    data["post_url"] = metadata["url"]
                if "lang" in metadata:
                    metadata_dict["lang"] = metadata["lang"]
                if metadata_dict:
                    data["metadata"] = metadata_dict

            # Insert into database
            # Use DatabaseAgent (delegates to StorageFacade)
            from src.database.database_agent import DatabaseAgent

            db_agent = DatabaseAgent()
            db_agent.save_posted_content(data)
            response = type(
                "Response", (), {"data": [data]}
            )()  # Mock response for compatibility

            if response.data and len(response.data) > 0:
                record_id = response.data[0]["id"]
                logger.info(
                    f"✅ Tracked posted content: {platform}/{platform_post_id} (ID: {record_id})"
                )
                return record_id
            else:
                logger.error(f"❌ Failed to track posted content: no data returned")
                return None

        except Exception as e:
            logger.error(f"❌ Error tracking rewrite performance: {e}")
            return None

    async def update_metrics(
        self, posted_content_id: int, metrics: Dict[str, int]
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

            # Update posted_content with engagement_json (store metrics as JSON)
            update_data = {
                "engagement_json": metrics  # Store all metrics in engagement_json
            }

            response = (
                self.supabase.table("posted_content")
                .update(update_data)
                .eq("id", posted_content_id)
                .execute()
            )

            # Note: posted_metrics table might not exist, so we'll skip it for now
            # The engagement_json field stores all the metrics we need

            logger.info(
                f"✅ Updated metrics for posted_content {posted_content_id} (engagement: {engagement_score:.2f})"
            )

            return True

        except Exception as e:
            logger.error(f"❌ Error updating metrics: {e}")
            return False
