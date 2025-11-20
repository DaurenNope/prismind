"""
Profile Publishing Orchestrator

Orchestrates the full pipeline:
usable_posts → select → prepare → rewrite → schedule → publish

This is the main service that ties everything together for profile-based publishing.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.publishing.bridge import MimesisDB
from src.publishing.modular_rewriter import (
    ModularRewriter,
    RewriteRequest,
    build_persona_context,
)
from src.services.profile_content_pipeline import ProfileContentPipeline
from src.services.profile_content_selector import ProfileContentSelector
from src.storage.db import get_storage
from src.utils.config import get_config

logger = logging.getLogger(__name__)


class ProfilePublishingOrchestrator:
    """
    Orchestrate the complete publishing pipeline for a profile.

    Flow:
    1. Select posts from usable_posts (ProfileContentSelector)
    2. Route to platforms (ProfileContentPipeline)
    3. Prepare prompts (ProfileContentPipeline)
    4. Rewrite content (ModularRewriter)
    5. Schedule for publishing (DatabaseManager)
    6. Publish (PublisherWorker - separate service)
    """

    def __init__(
        self,
        profile_key: str,
        *,
        auto_schedule: Optional[bool] = None,
        schedule_delay_minutes: Optional[int] = None,
    ):
        """
        Initialize orchestrator for a profile

        Args:
            profile_key: Profile identifier (e.g., 'qronoya', 'aspandead')
        """
        self.profile_key = profile_key
        self.selector = ProfileContentSelector(profile_key)
        self.pipeline = ProfileContentPipeline(profile_key)
        self.rewriter = ModularRewriter()
        self.db = get_storage()

        config = get_config()
        flags = getattr(config, "flags", {}) if config else {}
        self.auto_schedule_enabled = (
            bool(auto_schedule)
            if auto_schedule is not None
            else bool(flags.get("auto_schedule_after_rewrite"))
        )
        self.schedule_delay_minutes = int(
            schedule_delay_minutes
            if schedule_delay_minutes is not None
            else flags.get("auto_schedule_delay_minutes", 90)
        )

        logger.info(
            f"✅ Initialized ProfilePublishingOrchestrator for {self.pipeline.profile_name}"
        )

    async def process_post(
        self,
        post: Dict[str, Any],
        platforms: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a single post: prepare → rewrite → schedule

        Args:
            post: Post dict from usable_posts
            platforms: Override automatic platform selection
            dry_run: If True, don't actually schedule, just return results

        Returns:
            Dict with results:
            {
                'post_id': '...',
                'platforms_processed': ['twitter', 'threads'],
                'rewrites': {
                    'twitter': {'content': '...', 'quality': 95, ...},
                    'threads': {'content': '...', 'quality': 98, ...}
                },
                'scheduled': {
                    'twitter': {'scheduled_for': '...', 'priority': 95},
                    'threads': {'scheduled_for': '...', 'priority': 98}
                }
            }
        """
        post_id = post.get("post_id")
        title = post.get("title", post.get("content", "")[:50])

        logger.info(f"🔄 Processing post: {title[:60]}...")

        # Prepare for platforms
        if platforms is None:
            prepared_by_platform = self.selector.prepare_post_for_platforms(post)
            platforms = list(prepared_by_platform.keys())
        else:
            prepared_by_platform = {}
            for platform in platforms:
                content_type = self.pipeline.match_content_type(
                    post_category=post.get("category", "general"), platform=platform
                )
                if content_type:
                    prepared_content = self.pipeline.prepare_content_for_rewrite(
                        post=post, platform=platform, content_type=content_type
                    )
                    prepared_by_platform[platform] = [prepared_content]

        if not prepared_by_platform:
            logger.warning(f"⚠️  No platforms prepared for post {post_id}")
            return {
                "post_id": post_id,
                "error": "No platforms could be prepared",
                "platforms_processed": [],
            }

        # Rewrite for each platform
        rewrites = {}
        scheduled = {}

        for platform, content_list in prepared_by_platform.items():
            for prepared_content in content_list:
                try:
                    logger.info(
                        f"✍️  Rewriting for {platform} ({prepared_content['content_type']})"
                    )

                    # Call rewriter with prepared prompt
                    # Note: We'll use the rewriter directly with the prepared prompt
                    # For now, create a simple analyzed_content structure
                    analyzed_content = {
                        "post_id": post_id,
                        "platform": post.get("platform", "custom"),
                        "content": post["content"],
                        "title": post.get("title", ""),
                        "summary": post.get("ai_summary", ""),
                        "category": post.get("category", ""),
                        "topics": post.get("tags", []),
                        "key_concepts": post.get("key_concepts", []),
                        "rewrite_angles": [
                            {
                                "persona": self.profile_key,
                                "angle": prepared_content["content_type"],
                                "tone": "analytical",
                                "platform_fit": "single_post",
                            }
                        ],
                    }

                    # Rewrite using the existing rewriter with custom prompt from profile pipeline
                    logger.info(
                        f"✍️  Calling rewriter with profile-specific prompt for {platform}/{prepared_content['content_type']}"
                    )
                    persona_context = build_persona_context(
                        self.profile_key, self.pipeline.config.get("persona", {})
                    )
                    rewrite_request = RewriteRequest(
                        analyzed_content=analyzed_content,
                        persona=persona_context,
                        platform=platform,
                        custom_prompt=prepared_content.get("prompt"),
                        platform_constraints=prepared_content.get("constraints"),
                        target_content_type=prepared_content.get("content_type"),
                    )
                    modular_result = await self.rewriter.rewrite(rewrite_request)
                    result = modular_result.metadata.copy()
                    result["rewritten_content"] = modular_result.rewritten_content
                    result["quality_score"] = modular_result.quality_score
                    result["voice_consistency_score"] = modular_result.voice_consistency_score
                    result["fact_preservation_score"] = modular_result.fact_preservation_score

                    if "error" in result:
                        logger.error(
                            f"❌ Rewrite error for {platform}: {result['error']}"
                        )
                        continue

                    rewrites[platform] = result

                    # Schedule if not dry run
                    if not dry_run:
                        schedule_result = await self._schedule_rewrite(
                            post=post, rewrite_result=result, platform=platform
                        )
                        scheduled[platform] = schedule_result
                    else:
                        logger.info(f"🔍 DRY RUN: Would schedule {platform} rewrite")

                except Exception as e:
                    logger.error(f"Error processing {platform}: {e}", exc_info=True)

        return {
            "post_id": post_id,
            "title": title,
            "platforms_processed": list(rewrites.keys()),
            "rewrites": rewrites,
            "scheduled": scheduled if not dry_run else {},
        }

    async def _schedule_rewrite(
        self, post: Dict[str, Any], rewrite_result: Dict[str, Any], platform: str
    ) -> Dict[str, Any]:
        """
        Schedule a rewritten post for publishing

        Args:
            post: Original post from usable_posts
            rewrite_result: Result from rewriter
            platform: Target platform

        Returns:
            Dict with scheduling info
        """
        if not self.auto_schedule_enabled:
            logger.info(
                "🛑 Auto-scheduling disabled for %s – storing rewrite only",
                self.profile_key,
            )
            return {"skipped": True, "reason": "auto_schedule_disabled"}

        content = rewrite_result.get("rewritten_content", "")
        quality_score = rewrite_result.get("quality_score", 0) or 0

        # Calculate priority based on urgency and quality
        # NOTE: urgency_score is 0-1 scale, not 0-10
        urgency_score = post.get("urgency_score")
        if urgency_score is None:
            urgency_score = 0.5  # Default to medium urgency (0-1 scale)
        # Scale urgency_score from 0-1 to 0-50, then add quality_score contribution
        priority = min(
            100, int((float(urgency_score) * 50) + (float(quality_score) * 0.5))
        )

        # Determine posting time based on relevance_window
        relevance_window = post.get("relevance_window") or "evergreen"
        scheduled_for = self._calculate_posting_time(
            relevance_window, priority, self.schedule_delay_minutes
        )

        # Store in scheduled_posts table
        try:
            # Use existing database methods
            metadata = {
                "profile_key": self.profile_key,
                "source_post_id": post.get("post_id"),
                "platform": platform,
                "priority": priority,
                "urgency_score": urgency_score,
                "quality_score": quality_score,
                "relevance_window": relevance_window,
                "content_type": rewrite_result.get("content_type", ""),
                "original_url": post.get("url", ""),
            }

            scheduled_time_iso = scheduled_for.isoformat()

            payload = {
                "persona_key": self.profile_key,
                "personality_key": self.profile_key,  # Required by database schema
                "platform": platform,
                "content": content,
                "content_type": _map_platform_to_content_type(
                    platform, rewrite_result.get("platform_fit")
                ),
                "scheduled_at": scheduled_time_iso,  # Use scheduled_at (database column name)
                "scheduled_time": scheduled_time_iso,  # Also include scheduled_time for compatibility
                "status": "pending",
            }

            # Ensure personality_key is never None
            if not payload.get("personality_key"):
                payload["personality_key"] = self.profile_key

            db = MimesisDB()
            created = db.insert_scheduled(payload)
            logger.info(
                f"📅 Scheduled {platform} post at {scheduled_time_iso} (priority: {priority})"
            )

            return {
                "scheduled_for": scheduled_for,
                "priority": priority,
                "metadata": metadata,
                "scheduled_id": created.get("id"),
            }

        except Exception as e:
            logger.error(f"Error scheduling post: {e}")
            return {"error": str(e)}

    def _calculate_posting_time(
        self, relevance_window: str, priority: int, override_delay: Optional[int] = None
    ) -> datetime:
        """
        Calculate when to post based on time sensitivity and priority.
        """
        from datetime import timedelta

        now = datetime.now()

        windows = {
            "same-day": (5, 30),  # 5-30 minutes
            "24-72h": (60, 480),  # 1-8 hours
            "this-week": (480, 1440),  # 8-24 hours
            "evergreen": (1440, 4320),  # 1-3 days
        }

        min_delay, max_delay = windows.get(relevance_window, (60, 480))

        if override_delay is not None:
            delay = override_delay
        elif priority >= 80:
            delay = min_delay
        elif priority >= 50:
            delay = (min_delay + max_delay) // 2
        else:
            delay = max_delay

        return now + timedelta(minutes=delay)


def _map_platform_to_content_type(platform: str, platform_fit: Optional[str]) -> str:
    fit = (platform_fit or "").lower()
    if "thread" in fit:
        return "thread"
    if platform == "telegram":
        return "telegram_message"
    return "single_tweet"

    async def process_daily_queue(
        self, max_posts: int = 10, dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Process the daily content queue

        Selects and processes posts prioritized by time sensitivity

        Args:
            max_posts: Maximum posts to process
            dry_run: If True, don't actually schedule

        Returns:
            Dict with processing results
        """
        logger.info(f"📅 Processing daily queue for {self.pipeline.profile_name}")

        # Get daily queue
        queue = self.selector.get_daily_queue(max_posts=max_posts)

        results = {
            "profile_key": self.profile_key,
            "processed_at": datetime.now().isoformat(),
            "total_posts": 0,
            "successful": 0,
            "failed": 0,
            "by_category": {},
            "details": [],
        }

        # Process in priority order: urgent → today → this_week → evergreen
        for category in ["urgent", "today", "this_week", "evergreen"]:
            posts = queue.get(category, [])

            if not posts:
                continue

            logger.info(f"📋 Processing {len(posts)} {category} posts")

            for post in posts:
                try:
                    result = await self.process_post(post, dry_run=dry_run)

                    results["total_posts"] += 1

                    if result.get("platforms_processed"):
                        results["successful"] += 1
                    else:
                        results["failed"] += 1

                    if category not in results["by_category"]:
                        results["by_category"][category] = {"total": 0, "successful": 0}

                    results["by_category"][category]["total"] += 1
                    if result.get("platforms_processed"):
                        results["by_category"][category]["successful"] += 1

                    results["details"].append(
                        {
                            "category": category,
                            "post_id": result.get("post_id"),
                            "title": result.get("title", "")[:60],
                            "platforms": result.get("platforms_processed", []),
                            "success": bool(result.get("platforms_processed")),
                        }
                    )

                except Exception as e:
                    logger.error(f"Error processing post: {e}", exc_info=True)
                    results["failed"] += 1

        logger.info(
            f"✅ Queue processing complete: {results['successful']}/{results['total_posts']} successful"
        )

        return results

    async def process_urgent_only(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process only urgent posts (same-day, high urgency)

        Returns:
            Dict with processing results
        """
        urgent_posts = self.selector.get_urgent_posts(limit=5)

        if not urgent_posts:
            logger.info("No urgent posts found")
            return {"profile_key": self.profile_key, "urgent_posts": 0, "processed": 0}

        results = {
            "profile_key": self.profile_key,
            "urgent_posts": len(urgent_posts),
            "processed": 0,
            "details": [],
        }

        for post in urgent_posts:
            try:
                result = await self.process_post(post, dry_run=dry_run)
                results["processed"] += 1
                results["details"].append(result)
            except Exception as e:
                logger.error(f"Error processing urgent post: {e}")

        return results


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    async def demo():
        logger.info("=" * 80)
        logger.info("PROFILE PUBLISHING ORCHESTRATOR - DEMO")
        logger.info("=" * 80)

        # Initialize orchestrator
        orchestrator = ProfilePublishingOrchestrator("qronoya")

        # Get stats first
        stats = orchestrator.selector.get_statistics()
        logger.info(f"\n📊 Available content: {stats['total_posts']} posts")

        # Process daily queue (DRY RUN)
        logger.info("\n" + "=" * 80)
        logger.info("Processing daily queue (DRY RUN)...")
        logger.info("=" * 80)

        results = await orchestrator.process_daily_queue(max_posts=3, dry_run=True)

        logger.info(f"\n✅ Results:")
        logger.info(f"   Total processed: {results['total_posts']}")
        logger.info(f"   Successful: {results['successful']}")
        logger.error(f"   Failed: {results['failed']}")

        logger.info(f"\n📋 By Category:")
        for category, data in results.get("by_category", {}).items():
            logger.info(
                f"   {category:12} - {data['successful']}/{data['total']} successful"
            )

        if results.get("details"):
            logger.debug(f"\n📝 Details:")
            for detail in results["details"][:3]:  # Show first 3
                logger.debug(f"   • {detail['title']}")
                logger.debug(f"     Platforms: {', '.join(detail['platforms'])}")
                logger.info(f"     Success: {detail['success']}")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Demo complete!")
        logger.info("=" * 80)

    asyncio.run(demo())
