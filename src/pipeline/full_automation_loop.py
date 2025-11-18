#!/usr/bin/env python3
"""
Full Automated Loop Orchestrator

Complete automated pipeline:
1. COLLECTION → Collect posts from platforms
2. ANALYSIS → Analyze posts (with persona matching built-in)
3. TRANSFORMATION → Transform matched posts for personas
4. SCHEDULING → Schedule transformed posts
5. POSTING → Automatic via PublisherWorker
6. LEARNING → Track performance and update matching weights

Everything is automated - this orchestrates the entire flow.
"""

import asyncio
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.database_agent import DatabaseAgent
from src.database.manager import SupabaseManager
from src.publishing.rewriter import ContentRewriter
from src.services.analysis.post_analyzer import analyze_and_store_post
from src.services.analysis_lock import acquire_analysis_lock, release_analysis_lock
from src.services.new_database_manager import NewDatabaseManager
from src.services.persona_matcher import get_persona_matcher
from src.services.unified_collection_service import UnifiedCollectionService
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FullAutomationLoop:
    """Orchestrates the complete automated loop"""

    def __init__(self):
        self.db = NewDatabaseManager()
        self.collection_service = UnifiedCollectionService()
        self.persona_matcher = get_persona_matcher()

        # Initialize Supabase if available
        try:
            self.supabase = SupabaseManager()
            logger.info("✅ Supabase available")
        except Exception as e:
            logger.warning(f"⚠️ Supabase not available: {e}")
            self.supabase = None

        # Initialize proper content rewriter (not SimpleTransformer)
        self.rewriter = ContentRewriter()

    async def run_collection(
        self, platforms: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Step 1: Collect posts from platforms

        If platforms is None, collects from all platforms (twitter, reddit, threads).
        If platforms is specified, only collects from those platforms.
        """
        logger.info("=" * 70)
        logger.info("📥 STEP 1: COLLECTION")
        logger.info("=" * 70)

        try:
            if platforms:
                logger.info(f"Collecting from: {', '.join(platforms)}")
                results = {}
                for platform in platforms:
                    try:
                        result = await self.collection_service.collect(platform)
                        results[platform] = result.posts_collected
                        logger.info(
                            f"✅ {platform}: {result.posts_collected} posts collected"
                        )
                    except Exception as e:
                        logger.error(f"❌ {platform}: Failed - {e}")
                        results[platform] = 0
                total_collected = sum(results.values())
            else:
                # Default to all bookmark platforms (twitter, reddit, threads)
                logger.info(
                    "Collecting from all platforms (twitter, reddit, threads)..."
                )
                default_platforms = ["twitter", "reddit", "threads"]
                results = {}
                for platform in default_platforms:
                    try:
                        result = await self.collection_service.collect(platform)
                        results[platform] = result.posts_collected
                        logger.info(
                            f"✅ {platform}: {result.posts_collected} posts collected"
                        )
                    except Exception as e:
                        logger.error(f"❌ {platform}: Failed - {e}")
                        results[platform] = 0
                total_collected = sum(results.values())

            logger.info(
                f"📊 Collection Summary: {total_collected} total posts collected"
            )
            return (
                results
                if isinstance(results, dict)
                else {k: v.posts_collected for k, v in results.items()}
            )

        except Exception as e:
            logger.error(f"❌ Collection failed: {e}")
            return {}

    async def run_analysis(
        self, limit: Optional[int] = None, resume: bool = True
    ) -> Dict[str, Any]:
        """Step 2: Analyze unanalyzed posts (with persona matching built-in)

        Args:
            limit: Maximum number of posts to analyze (None = all)
            resume: If True, skip already analyzed posts (analyzed_at IS NOT NULL)
        """
        logger.info("\n" + "=" * 70)
        logger.info("🤖 STEP 2: ANALYSIS (with Persona Matching)")
        logger.info("=" * 70)

        if not acquire_analysis_lock():
            logger.info("Analysis skipped: an analysis run is already in progress")
            return {"analyzed": 0, "failed": 0, "skipped": True}

        try:
            # Opportunistic platform normalization (once per interval)
            try:
                agent = DatabaseAgent()
                agent.fix_invalid_platforms(limit=2000, dry_run=False, auto=True)
            except Exception as cleanup_err:
                logger.debug(f"Platform normalization skipped: {cleanup_err}")

            # Get unanalyzed posts (prefer Supabase as primary source)
            unanalyzed: List[Dict[str, Any]] = []
            effective_limit = (
                int(limit) if isinstance(limit, int) and limit > 0 else 100
            )
            if self.supabase is not None:
                try:
                    # Prefer 'analyzed_at' (present in Supabase schema)
                    query = self.supabase.client.table("posts").select("*")
                    if resume:
                        query = query.is_("analyzed_at", "null")
                    query = query.order("created_at", desc=True).limit(effective_limit)
                    r = query.execute()
                    data = getattr(r, "data", []) or []
                    # If empty, fallback to value_score null/zero heuristic
                    if not data:
                        r2 = (
                            self.supabase.client.table("posts")
                            .select("*")
                            .or_("value_score.is.null,value_score.eq.0")
                            .order("created_at", desc=True)
                            .limit(effective_limit)
                            .execute()
                        )
                        data = getattr(r2, "data", []) or []
                    unanalyzed = data
                except Exception as e:
                    logger.warning(
                        f"Supabase unanalyzed fetch failed, falling back to SQLite: {e}"
                    )
                    pass
            if not unanalyzed:
                unanalyzed = self.db.get_unanalyzed_posts(limit=effective_limit)
            logger.info(f"Found {len(unanalyzed)} unanalyzed posts")

            if not unanalyzed:
                logger.info("✅ All posts are analyzed!")
                return {"analyzed": 0, "failed": 0}

            successful = 0
            failed = 0

            for i, post in enumerate(unanalyzed, 1):
                post_id = post.get("post_id", "unknown")
                platform = post.get("platform", "unknown")
                author = post.get("author", "Unknown")[:30]

                logger.info(
                    f"\n[{i}/{len(unanalyzed)}] Analyzing: {platform} - {author}"
                )

                try:
                    result = await analyze_and_store_post(self.db, post, self.supabase)
                    if result:
                        successful += 1
                        logger.info(f"  ✅ Successfully analyzed")
                    else:
                        failed += 1
                        logger.warning(f"  ❌ Analysis returned False")
                except Exception as e:
                    failed += 1
                    logger.error(f"  ❌ Error: {str(e)[:100]}")

            logger.info(
                f"\n📊 Analysis Summary: {successful} successful, {failed} failed"
            )
            return {"analyzed": successful, "failed": failed}
        finally:
            release_analysis_lock()

    async def run_transformation_and_scheduling(
        self, min_match_score: float = 0.65, schedule_minutes: int = 60
    ) -> Dict[str, Any]:
        """Step 3: Transform matched posts and schedule them"""
        logger.info("\n" + "=" * 70)
        logger.info("🎭 STEP 3: TRANSFORMATION & SCHEDULING")
        logger.info("=" * 70)

        # Get analyzed posts with persona matches
        # NEW: Use profile_matches (JSONB field with 0-100 scores for all personas)
        # OLD: Fallback to recommended_personas/persona_match_scores for backward compatibility
        all_posts = self.db.get_all_posts()

        import json

        posts_with_personas = []
        for p in all_posts:
            # NEW: Use profile_matches (dynamic, works with any profiles)
            profile_matches = p.get("profile_matches", {})

            # Parse JSON string if needed
            if isinstance(profile_matches, str):
                try:
                    profile_matches = json.loads(profile_matches)
                except (json.JSONDecodeError, ValueError):
                    profile_matches = {}

            # Check if we have valid profile matches (score >= min_match_score threshold)
            if isinstance(profile_matches, dict) and profile_matches:
                # Filter personas with score >= min_match_score (convert 0-100 to 0-10 scale for comparison)
                valid_personas = [
                    persona_key
                    for persona_key, score in profile_matches.items()
                    if isinstance(score, (int, float))
                    and (score / 10.0) >= min_match_score
                ]
                if valid_personas:
                    posts_with_personas.append(p)
                    continue

            # FALLBACK: Check old fields for backward compatibility
            recommended_personas = p.get("recommended_personas")
            persona_match_scores = p.get("persona_match_scores")

            if isinstance(recommended_personas, str):
                try:
                    recommended_personas = json.loads(recommended_personas)
                except (json.JSONDecodeError, ValueError):
                    recommended_personas = None

            if isinstance(persona_match_scores, str):
                try:
                    persona_match_scores = json.loads(persona_match_scores)
                except (json.JSONDecodeError, ValueError):
                    persona_match_scores = None

            # Check old fields
            if recommended_personas and (
                (
                    isinstance(recommended_personas, list)
                    and len(recommended_personas) > 0
                )
                or (
                    isinstance(recommended_personas, str)
                    and recommended_personas not in ["[]", "null", "None", ""]
                )
            ):
                posts_with_personas.append(p)
            elif persona_match_scores and (
                (
                    isinstance(persona_match_scores, dict)
                    and len(persona_match_scores) > 0
                )
                or (
                    isinstance(persona_match_scores, str)
                    and persona_match_scores not in ["{}", "null", "None", ""]
                )
            ):
                posts_with_personas.append(p)

        logger.info(
            f"Found {len(posts_with_personas)} posts with persona recommendations"
        )

        if not posts_with_personas:
            logger.info("⚠️ No posts with persona matches found")
            return {"transformed": 0, "scheduled": 0}

        transformed = 0
        scheduled = 0

        for post in posts_with_personas:
            # NEW: Use profile_matches (0-100 scale)
            profile_matches = post.get("profile_matches", {})

            # Parse JSON string if needed
            if isinstance(profile_matches, str):
                try:
                    profile_matches = json.loads(profile_matches)
                except (json.JSONDecodeError, ValueError):
                    profile_matches = {}

            # FALLBACK: Use old fields if profile_matches not available
            if not profile_matches or not isinstance(profile_matches, dict):
                recommended_personas = post.get("recommended_personas", [])
                persona_match_scores = post.get("persona_match_scores", {})

                if isinstance(recommended_personas, str):
                    try:
                        recommended_personas = json.loads(recommended_personas)
                    except (json.JSONDecodeError, ValueError):
                        recommended_personas = []

                if isinstance(persona_match_scores, str):
                    try:
                        persona_match_scores = json.loads(persona_match_scores)
                    except (json.JSONDecodeError, ValueError):
                        persona_match_scores = {}

                # Convert old format to profile_matches format
                if recommended_personas and isinstance(recommended_personas, list):
                    profile_matches = {}
                    for persona_key in recommended_personas:
                        # Old scores are 0-10, convert to 0-100
                        old_score = persona_match_scores.get(persona_key, 0.0)
                        profile_matches[persona_key] = old_score * 10.0

            if not profile_matches or not isinstance(profile_matches, dict):
                continue

            post_id = post.get("post_id")
            logger.info(f"\n📝 Post: {post_id} ({post.get('platform', 'unknown')})")

            # Get personas with score >= min_match_score (convert 0-100 to 0-10 for comparison)
            valid_personas = [
                (persona_key, score)
                for persona_key, score in profile_matches.items()
                if isinstance(score, (int, float)) and (score / 10.0) >= min_match_score
            ]

            if not valid_personas:
                logger.debug(f"   ⏭️  No personas with score >= {min_match_score}")
                continue

            # Sort by score (highest first)
            valid_personas.sort(key=lambda x: x[1], reverse=True)
            logger.info(
                f"   Matched personas: {', '.join([f'{p[0]}({p[1]:.1f})' for p in valid_personas[:3]])}"
            )

            # Transform and schedule for each matched persona
            for persona_key, match_score in valid_personas:
                # match_score is already >= min_match_score (filtered above)
                # Convert 0-100 scale to 0-10 for logging
                score_0_10 = match_score / 10.0

                try:
                    # Use ContentRewriter to rewrite the analyzed post
                    rewrite_result = await self.rewriter.rewrite_analyzed_post(
                        analyzed_content=post, persona=persona_key, platform="auto"
                    )

                    if "error" in rewrite_result:
                        logger.warning(
                            f"   ⚠️  {persona_key}: Rewrite failed - {rewrite_result.get('error')}"
                        )
                        continue

                    rewritten_content = rewrite_result.get("rewritten_content", "")

                    # QUALITY VALIDATION: Reject placeholder/short content
                    if not rewritten_content or len(rewritten_content.strip()) < 20:
                        logger.warning(
                            f"   ⚠️  {persona_key}: Content too short/empty, skipping"
                        )
                        continue

                    # Reject placeholder patterns like [persona] T1, X, Y
                    content_lower = rewritten_content.lower().strip()
                    if ("[" in content_lower and "]" in content_lower) and len(
                        content_lower
                    ) < 50:
                        logger.warning(
                            f"   ⚠️  {persona_key}: Placeholder content detected, skipping"
                        )
                        continue

                    transformed_content = rewritten_content

                    # Get persona's platform
                    import json
                    from pathlib import Path

                    persona_file = Path(f"config/personas/{persona_key}.json")
                    persona = None
                    if persona_file.exists():
                        with open(persona_file, "r") as f:
                            persona = json.load(f)

                    if not persona:
                        logger.warning(f"   ⚠️  Persona {persona_key} not found")
                        continue

                    platform = persona.get("platform", "twitter")

                    # Save to mimesis_transformations (not schedule directly)
                    from datetime import datetime, timezone

                    now_iso = datetime.now(timezone.utc).isoformat()

                    if self.supabase:
                        try:
                            self.supabase.client.table(
                                "mimesis_transformations"
                            ).insert(
                                {
                                    "persona_key": persona_key,
                                    "source_post_id": str(post.get("post_id")),
                                    "platform": platform,
                                    "content": transformed_content,
                                    "score": float(match_score),
                                    "ready_for_posting": False,
                                    "created_at": now_iso,
                                }
                            ).execute()

                            transformed += 1
                            logger.info(
                                f"   ✅ {persona_key}: Rewritten and saved (score: {score_0_10:.2f}/10, length: {len(transformed_content)})"
                            )
                        except Exception as e:
                            logger.error(
                                f"   ❌ {persona_key}: Failed to save transformation - {e}"
                            )
                    else:
                        logger.warning(
                            f"   ⚠️  {persona_key}: Supabase not available, cannot save"
                        )

                except Exception as e:
                    logger.error(f"   ❌ {persona_key}: Transformation failed - {e}")

        logger.info(
            f"\n📊 Transformation Summary: {transformed} posts transformed, {scheduled} posts scheduled"
        )
        return {"transformed": transformed, "scheduled": scheduled}

    async def run_full_loop(
        self,
        platforms: Optional[List[str]] = None,
        analyze_limit: Optional[int] = None,
        min_match_score: float = 0.65,
        schedule_minutes: int = 60,
    ) -> Dict[str, Any]:
        """
        Run the complete automated loop

        Args:
            platforms: List of platforms to collect from (None = all)
            analyze_limit: Max posts to analyze (None = all unanalyzed)
            min_match_score: Minimum persona match score threshold
            schedule_minutes: Minutes to schedule posts in the future
        """
        logger.info("\n" + "=" * 70)
        logger.info("🔄 FULL AUTOMATED LOOP - STARTING")
        logger.info("=" * 70)
        logger.info(f"Timestamp: {datetime.now().isoformat()}")

        results = {
            "collection": {},
            "analysis": {},
            "transformation": {},
            "started_at": datetime.now().isoformat(),
        }

        # Step 1: Collection
        collection_results = await self.run_collection(platforms=platforms)
        results["collection"] = collection_results

        # Step 2: Analysis (with persona matching built-in)
        analysis_results = await self.run_analysis(limit=analyze_limit)
        results["analysis"] = analysis_results

        # Step 3: Transformation & Scheduling
        transformation_results = await self.run_transformation_and_scheduling(
            min_match_score=min_match_score, schedule_minutes=schedule_minutes
        )
        results["transformation"] = transformation_results

        results["completed_at"] = datetime.now().isoformat()

        logger.info("\n" + "=" * 70)
        logger.info("✅ FULL AUTOMATED LOOP - COMPLETE")
        logger.info("=" * 70)
        logger.info(
            f"Collection: {sum(results['collection'].values())} posts collected"
        )
        logger.info(
            f"Analysis: {results['analysis'].get('analyzed', 0)} posts analyzed"
        )
        logger.info(
            f"Transformation: {results['transformation'].get('scheduled', 0)} posts scheduled"
        )
        logger.info(
            "\n📤 Posting: Automatic via PublisherWorker (check scheduled_posts table)"
        )

        return results


async def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Run full automated loop")
    parser.add_argument(
        "--platforms",
        nargs="+",
        help="Platforms to collect from (twitter, threads, reddit)",
    )
    parser.add_argument(
        "--analyze-limit",
        type=int,
        help="Max posts to analyze (default: all unanalyzed)",
    )
    parser.add_argument(
        "--min-match-score",
        type=float,
        default=0.65,
        help="Minimum persona match score (0.0-1.0)",
    )
    parser.add_argument(
        "--schedule-minutes",
        type=int,
        default=60,
        help="Minutes to schedule posts in future",
    )

    args = parser.parse_args()

    loop = FullAutomationLoop()
    results = await loop.run_full_loop(
        platforms=args.platforms,
        analyze_limit=args.analyze_limit,
        min_match_score=args.min_match_score,
        schedule_minutes=args.schedule_minutes,
    )

    logger.info("\n✅ Full loop complete!")
    logger.info(f"Results: {results}")


if __name__ == "__main__":
    asyncio.run(main())
