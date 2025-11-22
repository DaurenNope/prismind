#!/usr/bin/env python3
"""
Batch Rewrite Script for usable_posts

Processes all ready posts from usable_posts and generates rewrites based on:
- best_persona_key (primary persona)
- persona_fit_scores (additional personas if score > threshold)
- relevance_window (scheduling priority)

This ensures all curated posts get rewritten for their matching personas.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from src.database.manager import SupabaseManager
from src.database.publishing.bridge import MimesisDB
from src.publishing.scheduler import PublishingScheduler
from src.services.profile_publishing_orchestrator import ProfilePublishingOrchestrator

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def batch_rewrite_usable_posts(
    persona_fit_threshold: float = 0.3,
    max_posts_per_persona: Optional[int] = None,
    dry_run: bool = False,
    schedule_immediately: bool = False,
) -> Dict[str, Any]:
    """
    Batch process usable_posts and generate rewrites.

    Args:
        persona_fit_threshold: Minimum persona_fit_score to rewrite for additional personas
        max_posts_per_persona: Limit posts per persona (None = all)
        dry_run: If True, don't actually create rewrites
        schedule_immediately: If True, schedule posts immediately (not dry_run)

    Returns:
        Dict with processing statistics
    """
    supabase = SupabaseManager().client
    db = MimesisDB()

    # Get all ready posts
    response = (
        supabase.table("usable_posts")
        .select("*")
        .eq("rewrite_readiness", "ready")
        .execute()
    )

    ready_posts = response.data
    logger.info(f"📊 Found {len(ready_posts)} ready posts in usable_posts")

    # Group by persona
    posts_by_persona: Dict[str, List[Dict]] = {}
    posts_without_persona = []

    for post in ready_posts:
        best_persona = post.get("best_persona_key")
        if best_persona:
            if best_persona not in posts_by_persona:
                posts_by_persona[best_persona] = []
            posts_by_persona[best_persona].append(post)
        else:
            posts_without_persona.append(post)

    logger.info(f"\n📊 Posts by Persona:")
    for persona, posts in posts_by_persona.items():
        logger.info(f"   {persona}: {len(posts)} posts")
    if posts_without_persona:
        logger.info(f"   ⚠️  No persona: {len(posts_without_persona)} posts")

    # Statistics
    stats = {
        "total_posts": len(ready_posts),
        "by_persona": {},
        "rewrites_created": 0,
        "scheduled": 0,
        "errors": [],
    }

    # Process each persona
    for persona_key, posts in posts_by_persona.items():
        if max_posts_per_persona:
            posts = posts[:max_posts_per_persona]

        logger.info(f"\n{'='*70}")
        logger.info(f"🎭 Processing {len(posts)} posts for {persona_key}")
        logger.info(f"{'='*70}")

        persona_stats = {
            "total": len(posts),
            "rewrites_created": 0,
            "scheduled": 0,
            "errors": 0,
        }

        orchestrator = ProfilePublishingOrchestrator(
            persona_key, auto_schedule=(schedule_immediately and not dry_run)
        )

        for i, post in enumerate(posts, 1):
            post_id = post.get("post_id", "unknown")
            logger.info(f"\n[{i}/{len(posts)}] Processing: {post_id}")

            try:
                # Determine which personas to rewrite for
                personas_to_rewrite = [persona_key]  # Always include best_persona

                # Check persona_fit_scores for additional personas
                persona_fit_scores = post.get("persona_fit_scores", {})
                if isinstance(persona_fit_scores, str):
                    import json

                    persona_fit_scores = json.loads(persona_fit_scores)

                for other_persona, score in persona_fit_scores.items():
                    if (
                        other_persona != persona_key
                        and isinstance(score, (int, float))
                        and float(score) >= persona_fit_threshold
                    ):
                        personas_to_rewrite.append(other_persona)
                        logger.info(
                            f"   ✅ Also rewriting for {other_persona} (fit score: {score})"
                        )

                # Process post for primary persona
                result = await orchestrator.process_post(post, dry_run=dry_run)

                if result.get("error"):
                    logger.error(f"   ❌ Error: {result['error']}")
                    persona_stats["errors"] += 1
                    continue

                rewrites = result.get("rewrites", {})
                if rewrites:
                    persona_stats["rewrites_created"] += len(rewrites)
                    stats["rewrites_created"] += len(rewrites)
                    logger.info(f"   ✅ Created {len(rewrites)} rewrite(s)")

                    # Schedule if requested
                    if schedule_immediately and not dry_run:
                        scheduled = result.get("scheduled", {})
                        if scheduled:
                            persona_stats["scheduled"] += len(scheduled)
                            stats["scheduled"] += len(scheduled)
                            logger.info(f"   📅 Scheduled {len(scheduled)} post(s)")
                else:
                    logger.warning(f"   ⚠️  No rewrites created")

                # Process for additional personas if any
                for other_persona in personas_to_rewrite[
                    1:
                ]:  # Skip first (already processed)
                    logger.info(f"   🎭 Also processing for {other_persona}")
                    other_orchestrator = ProfilePublishingOrchestrator(
                        other_persona, auto_schedule=(schedule_immediately and not dry_run)
                    )
                    other_result = await other_orchestrator.process_post(
                        post, dry_run=dry_run
                    )
                    if other_result.get("rewrites"):
                        stats["rewrites_created"] += len(other_result["rewrites"])
                        persona_stats["rewrites_created"] += len(
                            other_result["rewrites"]
                        )

            except Exception as e:
                logger.error(f"   ❌ Exception processing {post_id}: {e}", exc_info=True)
                persona_stats["errors"] += 1
                stats["errors"].append(f"{persona_key}/{post_id}: {str(e)}")

        stats["by_persona"][persona_key] = persona_stats
        logger.info(
            f"\n✅ {persona_key} complete: {persona_stats['rewrites_created']} rewrites, {persona_stats['scheduled']} scheduled"
        )

    # Summary
    logger.info(f"\n{'='*70}")
    logger.info(f"📊 BATCH REWRITE SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total posts processed: {stats['total_posts']}")
    logger.info(f"Total rewrites created: {stats['rewrites_created']}")
    logger.info(f"Total scheduled: {stats['scheduled']}")
    logger.info(f"Errors: {len(stats['errors'])}")

    if stats["by_persona"]:
        logger.info(f"\nBy Persona:")
        for persona, persona_stats in stats["by_persona"].items():
            logger.info(
                f"  {persona}: {persona_stats['rewrites_created']} rewrites, {persona_stats['scheduled']} scheduled"
            )

    if dry_run:
        logger.info(f"\n🔍 DRY RUN: No rewrites were actually created")
        logger.info(f"   Run without --dry-run to create rewrites")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch rewrite usable_posts based on persona flags"
    )
    parser.add_argument(
        "--persona-fit-threshold",
        type=float,
        default=0.3,
        help="Minimum persona_fit_score to rewrite for additional personas (default: 0.3)",
    )
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Maximum posts per persona (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - don't actually create rewrites",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Schedule posts immediately after rewriting",
    )

    args = parser.parse_args()

    result = asyncio.run(
        batch_rewrite_usable_posts(
            persona_fit_threshold=args.persona_fit_threshold,
            max_posts_per_persona=args.max_posts,
            dry_run=args.dry_run,
            schedule_immediately=args.schedule,
        )
    )

    print(f"\n✅ Batch rewrite complete!")
    print(f"   Rewrites created: {result['rewrites_created']}")
    print(f"   Scheduled: {result['scheduled']}")
    print(f"   Errors: {len(result['errors'])}")
