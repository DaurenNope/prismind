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
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.database.database_agent import get_database_agent
from src.infrastructure.database.manager import SupabaseManager
from src.domain.publishing.modular_rewriter import (
    ModularRewriter,
    RewriteRequest,
    build_persona_context,
)
from src.domain.analysis.services.post_analyzer import analyze_and_store_post
from src.domain.analysis.services.analysis_lock import acquire_analysis_lock, release_analysis_lock
from src.services.new_database_manager import NewDatabaseManager
from src.services.persona_matcher import get_persona_matcher
from src.domain.collection.services.unified_collection_service import UnifiedCollectionService
from src.shared.utils.logging_config import get_logger
from src.publishing.scheduler import PublishingScheduler
from src.publishing.content_planner import ContentPlanGenerator

logger = get_logger(__name__)


class FullAutomationLoop:
    """
    Orchestrates the complete automated loop: Collection → Analysis → Transformation → Scheduling → Posting.
    
    This is the SINGLE SOURCE OF TRUTH for automation.
    Other files (integrated_automation.py) are wrappers that use this class.
    
    Entry Points:
    - CLI: python -m src.pipeline.full_automation_loop
    - API: via IntegratedAutomationOrchestrator
    - Direct: FullAutomationLoop().run_full_loop()
    
    Location: src/pipeline/full_automation_loop.py
    """

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
        # Initialize proper content rewriter (not SimpleTransformer)
        self.rewriter = ModularRewriter()
        
        # Initialize Publishing Scheduler and Content Planner
        self.scheduler = PublishingScheduler()
        self.content_planner = ContentPlanGenerator()
        
        # Initialize Agent Graph (The Brain)
        from src.application.orchestration.agent_graph import AgentGraph
        self.agent_graph = AgentGraph()
        
        # Initialize Publisher Worker
        from src.domain.publishing.worker import PublisherWorker
        self.publisher = PublisherWorker()

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
        self, limit: Optional[int] = None, resume: bool = True, use_agent_graph: bool = False
    ) -> Dict[str, Any]:
        """Step 2: Analyze unanalyzed posts (with persona matching built-in)

        Args:
            limit: Maximum number of posts to analyze (None = all)
            resume: If True, skip already analyzed posts (analyzed_at IS NOT NULL)
            use_agent_graph: If True, use the Multi-Agent Graph for analysis
        """
        if use_agent_graph:
            return await self._run_agent_graph_analysis(limit=limit)
        logger.info("\n" + "=" * 70)
        logger.info("🤖 STEP 2: ANALYSIS (with Persona Matching)")
        logger.info("=" * 70)

        if not acquire_analysis_lock():
            logger.info("Analysis skipped: an analysis run is already in progress")
            return {"analyzed": 0, "failed": 0, "skipped": True}

        try:
            # Opportunistic platform normalization (once per interval)
            try:
                from src.infrastructure.database.database_agent import get_database_agent
                agent = get_database_agent()
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
            if not unanalyzed:
                unanalyzed = self.db.get_unanalyzed_posts(limit=effective_limit)
            logger.info(f"Found {len(unanalyzed)} unanalyzed posts")

            if not unanalyzed:
                logger.info("✅ All posts are analyzed!")
                return {"analyzed": 0, "failed": 0}

            successful = 0
            failed = 0
            invalid = 0
            validation_issues = {}  # Track common issues

            def validate_analysis_quality(analysis_result: Dict[str, Any]) -> tuple[bool, List[str]]:
                """
                Validate analysis quality.
                
                Returns:
                    (is_valid, list_of_issues)
                """
                issues = []
                
                # Check required fields
                if not analysis_result.get("value_score") and analysis_result.get("value_score") != 0:
                    issues.append("Missing value_score")
                else:
                    value_score = analysis_result.get("value_score")
                    if value_score is not None and not (0 <= float(value_score) <= 10):
                        issues.append(f"Invalid value_score: {value_score} (expected 0-10)")
                
                if analysis_result.get("viral_potential") is None:
                    issues.append("Missing viral_potential")
                else:
                    viral_potential = analysis_result.get("viral_potential")
                    if viral_potential is not None and not (0 <= float(viral_potential) <= 100):
                        issues.append(f"Invalid viral_potential: {viral_potential} (expected 0-100)")
                
                if not analysis_result.get("time_sensitivity"):
                    issues.append("Missing time_sensitivity")
                else:
                    time_sensitivity = analysis_result.get("time_sensitivity", "").lower()
                    if time_sensitivity not in ["breaking", "trending", "timely", "evergreen"]:
                        issues.append(f"Invalid time_sensitivity: {time_sensitivity}")
                
                # Check rewrite_angles (can be stored as JSON string or list)
                rewrite_angles = analysis_result.get("rewrite_angles")
                if not rewrite_angles:
                    issues.append("Missing rewrite_angles")
                else:
                    # Handle JSON string
                    if isinstance(rewrite_angles, str):
                        import json
                        try:
                            rewrite_angles = json.loads(rewrite_angles)
                        except (json.JSONDecodeError, ValueError):
                            issues.append("Invalid rewrite_angles format (not valid JSON)")
                            rewrite_angles = []
                    
                    if not isinstance(rewrite_angles, list) or len(rewrite_angles) == 0:
                        issues.append("Empty rewrite_angles")
                
                # Check ai_summary
                ai_summary = analysis_result.get("ai_summary") or analysis_result.get("summary")
                if not ai_summary:
                    issues.append("Missing ai_summary")
                elif len(str(ai_summary).strip()) < 10:
                    issues.append("ai_summary too short")
                
                # Check key_concepts (optional but important)
                key_concepts = analysis_result.get("key_concepts")
                if key_concepts:
                    if isinstance(key_concepts, str):
                        import json
                        try:
                            key_concepts = json.loads(key_concepts)
                        except (json.JSONDecodeError, ValueError):
                            pass  # Not JSON, might be comma-separated or other format
                    if isinstance(key_concepts, list) and len(key_concepts) == 0:
                        issues.append("Empty key_concepts")
                
                return len(issues) == 0, issues

            for i, post in enumerate(unanalyzed, 1):
                post.get("post_id", "unknown")
                platform = post.get("platform", "unknown")
                author = post.get("author", "Unknown")[:30]

                logger.info(
                    f"\n[{i}/{len(unanalyzed)}] Analyzing: {platform} - {author}"
                )

                try:
                    result = await analyze_and_store_post(self.db, post, self.supabase)
                    if result:
                        # Fetch the analyzed post to validate quality
                        post_id = post.get("post_id")
                        analyzed_post = None
                        
                        # Try to get from Supabase first
                        if self.supabase:
                            try:
                                response = (
                                    self.supabase.client.table("posts")
                                    .select("*")
                                    .eq("post_id", post_id)
                                    .limit(1)
                                    .execute()
                                )
                                if response.data:
                                    analyzed_post = response.data[0]
                            except Exception as e:
                                logger.debug(f"Could not fetch from Supabase: {e}")
                        
                        # Fallback to local DB
                        if not analyzed_post:
                            analyzed_post = self.db.get_post(post_id)
                        
                        # Validate analysis quality
                        if analyzed_post:
                            is_valid, issues = validate_analysis_quality(analyzed_post)
                            if not is_valid:
                                invalid += 1
                                # Track common issues
                                for issue in issues:
                                    validation_issues[issue] = validation_issues.get(issue, 0) + 1
                                
                                logger.warning(
                                    f"  ⚠️  Analysis quality issues: {', '.join(issues)}"
                                )
                                
                                # Option B: Flag but continue (lenient approach)
                                # Store quality flag in database if possible
                                if self.supabase:
                                    try:
                                        self.supabase.client.table("posts").update({
                                            "analysis_quality": "low",
                                            "analysis_quality_issues": issues
                                        }).eq("post_id", post_id).execute()
                                    except Exception as e:
                                        logger.debug(f"Could not update analysis_quality: {e}")
                                
                                # Continue processing (lenient mode)
                                successful += 1
                                logger.info(f"  ✅ Analyzed (quality: LOW - flagged)")
                            else:
                                successful += 1
                                logger.info(f"  ✅ Successfully analyzed (quality: OK)")
                                
                                # Mark as high quality if possible
                                if self.supabase:
                                    try:
                                        self.supabase.client.table("posts").update({
                                            "analysis_quality": "high"
                                        }).eq("post_id", post_id).execute()
                                    except Exception as e:
                                        logger.debug(f"Could not update analysis_quality: {e}")
                        else:
                            # Could not fetch analyzed post, assume valid
                            successful += 1
                            logger.info(f"  ✅ Successfully analyzed (validation skipped)")
                    else:
                        failed += 1
                        logger.warning(f"  ❌ Analysis returned False")
                except Exception as e:
                    failed += 1
                    logger.error(f"  ❌ Error: {str(e)[:100]}")

            # Enhanced summary with validation stats
            summary_parts = [
                f"✅ Valid: {successful - invalid}",
                f"⚠️  Invalid (flagged): {invalid}",
                f"❌ Failed: {failed}"
            ]
            if validation_issues:
                common_issues = sorted(validation_issues.items(), key=lambda x: x[1], reverse=True)[:5]
                issues_str = ", ".join([f"{issue} ({count})" for issue, count in common_issues])
                summary_parts.append(f"Common issues: {issues_str}")
            
            logger.info(f"\n📊 Analysis Summary: {' | '.join(summary_parts)}")
            return {
                "analyzed": successful,
                "failed": failed,
                "invalid": invalid,
                "validation_issues": validation_issues
            }
        finally:
            release_analysis_lock()

    async def _run_agent_graph_analysis(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Run analysis using AgentGraph"""
        logger.info("\n" + "=" * 70)
        logger.info("🧠 STEP 2: AGENTIC ANALYSIS")
        logger.info("=" * 70)

        unanalyzed = self.db.get_unanalyzed_posts(limit=limit or 100)
        logger.info(f"Found {len(unanalyzed)} unanalyzed posts for agentic analysis")
        
        analyzed = 0
        failed = 0
        
        for post in unanalyzed:
            try:
                logger.info(f"Analyzing post {post.get('post_id')} with AgentGraph...")
                
                # Create initial state for AgentGraph
                initial_state = {
                    "messages": [],
                    "current_agent": "user",
                    "next_agent": "director",
                    "task_status": "started",
                    "artifacts": {"current_post": post},
                    "errors": []
                }
                
                # Run the graph
                final_state = await self.agent_graph.app.ainvoke(initial_state)
                
                # Extract results
                artifacts = final_state.get("artifacts", {})
                analysis_result = artifacts.get("analysis_result")
                
                if analysis_result:
                    # Map agent result to DB schema
                    update_data = {
                        "ai_summary": analysis_result.get("summary"),
                        "value_score": analysis_result.get("value_score"),
                        "analyzed_at": datetime.now().isoformat(),
                        "analysis_metadata": {
                            "agent_analysis": analysis_result,
                            "verification": artifacts.get("verification_result"),
                            "history": artifacts.get("historical_context")
                        }
                    }
                    
                    # Update DB
                    if self.supabase:
                        self.supabase.client.table("posts").update(update_data).eq("post_id", post["post_id"]).execute()
                    
                    analyzed += 1
                    logger.info(f"✅ Agentic Analysis Complete for {post.get('post_id')}")
                else:
                    failed += 1
                    logger.warning(f"⚠️ Agentic Analysis produced no result for {post.get('post_id')}")
                    
            except Exception as e:
                failed += 1
                logger.error(f"❌ Agentic Analysis Failed for {post.get('post_id')}: {e}")
                
        return {"analyzed": analyzed, "failed": failed}

    async def run_transformation_and_scheduling(
        self,
        min_match_score: float = 0.65,
        schedule_minutes: int = 60,
        auto_schedule: bool = False,
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
                    # Use modular rewriter to rewrite the analyzed post
                    persona_context = build_persona_context(persona_key)
                    
                    # Extract language from analyzed content
                    from src.domain.publishing.modular_rewriter.schemas import PersonaContext
                    analyzed_language = post.get("language", "").lower()
                    normalized_language = None
                    if analyzed_language in ["ru", "russian", "ru-ru"]:
                        normalized_language = "russian"
                    elif analyzed_language in ["en", "english", "en-us", "en-us"]:
                        normalized_language = "english"
                    
                    # Override persona language if analyzed content has language
                    if normalized_language:
                        persona_context = PersonaContext(
                            key=persona_context.key,
                            name=persona_context.name,
                            language=normalized_language,  # Use analyzed language
                            tone=persona_context.tone,
                            platforms=persona_context.platforms,
                        )
                    
                    rewrite_request = RewriteRequest(
                        analyzed_content=post,
                        persona=persona_context,
                        platform="auto",
                    )
                    modular_result = await self.rewriter.rewrite(rewrite_request)
                    rewrite_result = modular_result.metadata
                    rewrite_result["rewritten_content"] = modular_result.rewritten_content
                    rewrite_result["quality_score"] = modular_result.quality_score
                    rewrite_result["voice_consistency_score"] = modular_result.voice_consistency_score
                    rewrite_result["fact_preservation_score"] = modular_result.fact_preservation_score

                    if rewrite_result.get("error"):
                        logger.warning(
                            f"   ⚠️  {persona_key}: Rewrite failed - {rewrite_result.get('error')}"
                        )
                        continue

                    # Extract quality scores
                    quality_score = modular_result.quality_score
                    voice_score = modular_result.voice_consistency_score
                    fact_score = modular_result.fact_preservation_score

                    # Quality gates - reject low-quality rewrites
                    # Thresholds: quality >= 0.7, voice >= 0.6, fact >= 0.8
                    QUALITY_THRESHOLD = 0.7
                    VOICE_THRESHOLD = 0.6
                    FACT_THRESHOLD = 0.8

                    if quality_score < QUALITY_THRESHOLD or voice_score < VOICE_THRESHOLD or fact_score < FACT_THRESHOLD:
                        logger.warning(
                            f"   ❌ {persona_key}: Low quality rewrite rejected "
                            f"(quality={quality_score:.2f}, voice={voice_score:.2f}, fact={fact_score:.2f})"
                        )
                        continue  # Skip saving this rewrite

                    # Auto-approval for high-quality rewrites
                    # Auto-approve if quality >= 0.9, voice >= 0.8, fact >= 0.9
                    AUTO_APPROVE_QUALITY = 0.9
                    AUTO_APPROVE_VOICE = 0.8
                    AUTO_APPROVE_FACT = 0.9

                    auto_approve = (
                        quality_score >= AUTO_APPROVE_QUALITY and
                        voice_score >= AUTO_APPROVE_VOICE and
                        fact_score >= AUTO_APPROVE_FACT
                    )

                    ready_for_posting = auto_approve
                    if auto_approve:
                        logger.info(f"   ✅ {persona_key}: Auto-approved (high quality)")

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

                    from datetime import datetime, timezone

                    now_iso = datetime.now(timezone.utc).isoformat()

                    if self.supabase:
                        try:
                            # Prepare metadata with quality scores
                            metadata = {
                                "quality_score": quality_score,
                                "voice_consistency_score": voice_score,
                                "fact_preservation_score": fact_score,
                                "auto_approved": auto_approve
                            }
                            
                            self.supabase.client.table(
                                "persona_transformations"
                            ).insert(
                                {
                                    "persona_key": persona_key,
                                    "source_post_id": str(post.get("post_id")),
                                    "platform": platform,
                                    "content": transformed_content,
                                    "score": float(match_score),
                                    "ready_for_posting": ready_for_posting,  # Use variable, not hardcoded False
                                    "created_at": now_iso,
                                    "metadata": metadata,  # Store quality metadata
                                }
                            ).execute()

                            transformed += 1
                            logger.info(
                                f"   ✅ {persona_key}: Rewritten and saved "
                                f"(score: {score_0_10:.2f}/10, quality: {quality_score:.2f}, "
                                f"voice: {voice_score:.2f}, fact: {fact_score:.2f}, length: {len(transformed_content)})"
                            )

                            if auto_schedule:
                                # Only schedule if ready_for_posting = True
                                if not ready_for_posting:
                                    logger.info(f"      ⏸️  {persona_key}: Not ready for posting (needs approval)")
                                else:
                                    try:
                                        # Extract metadata from analyzed post for strategic scheduling
                                        analysis_metadata = post.get("analysis_metadata", {})
                                        if isinstance(analysis_metadata, str):
                                            import json
                                            try:
                                                analysis_metadata = json.loads(analysis_metadata)
                                            except (json.JSONDecodeError, ValueError):
                                                analysis_metadata = {}
                                        
                                        # Prepare rewritten content with metadata for scheduler
                                        rewritten_with_metadata = {
                                            **rewrite_result,
                                            "rewritten_content": transformed_content,
                                            "viral_potential": analysis_metadata.get("viral_potential") or post.get("viral_potential", 0),
                                            "time_sensitivity": analysis_metadata.get("time_sensitivity") or post.get("time_sensitivity", "evergreen"),
                                            "trend_relevance": analysis_metadata.get("trend_relevance") or post.get("trend_relevance", "mainstream"),
                                            "author_authority": analysis_metadata.get("author_authority") or post.get("author_authority", "medium"),
                                            "platform": platform,
                                            "persona": persona_key,
                                        }
                                        
                                        # Use PublishingScheduler for strategic scheduling
                                        decision = self.scheduler.schedule_rewritten_post(
                                            rewritten_with_metadata,
                                            platform_override=platform
                                        )
                                        scheduled_at = decision.when
                                        priority = decision.priority
                                        
                                        # Check for existing scheduled posts to prevent clustering
                                        existing_schedules = []
                                        try:
                                            existing = (
                                                self.supabase.client.table("scheduled_posts")
                                                .select("scheduled_time")
                                                .eq("persona_key", persona_key)
                                                .eq("platform", platform)
                                                .gte("scheduled_time", datetime.now(timezone.utc).isoformat())
                                                .order("scheduled_time")
                                                .execute()
                                            )
                                            existing_schedules = [
                                                datetime.fromisoformat(item["scheduled_time"].replace("Z", "+00:00"))
                                                for item in (existing.data or [])
                                            ]
                                        except Exception as e:
                                            logger.debug(f"Could not fetch existing schedules: {e}")
                                        
                                        # Adjust time to prevent clustering (min 30 min spacing)
                                        if existing_schedules:
                                            adjusted_time = self.content_planner.get_next_available_slot(
                                                persona=persona_key,
                                                platform=platform,
                                                min_time=scheduled_at,
                                                existing_schedules=existing_schedules,
                                            )
                                            if adjusted_time != scheduled_at:
                                                logger.info(
                                                    f"      ⏱️  Adjusted schedule to prevent clustering: {adjusted_time.isoformat()}"
                                                )
                                                scheduled_at = adjusted_time
                                        
                                        # Prepare metadata for storage
                                        schedule_metadata = {
                                            "priority": priority,
                                            "scheduling_reason": decision.reason,
                                            "viral_potential": rewritten_with_metadata.get("viral_potential", 0),
                                            "time_sensitivity": rewritten_with_metadata.get("time_sensitivity", "evergreen"),
                                            "trend_relevance": rewritten_with_metadata.get("trend_relevance", "mainstream"),
                                            "author_authority": rewritten_with_metadata.get("author_authority", "medium"),
                                            "persona": persona_key,
                                            "source_post_id": str(post.get("post_id")),  # Store in metadata
                                            "scheduled_by": "PublishingScheduler",
                                            "scheduled_at": datetime.now(timezone.utc).isoformat(),
                                        }
                                        
                                        # Insert into scheduled_posts with metadata
                                        insert_data = {
                                            "persona_key": persona_key,
                                            "platform": platform,
                                            "content": transformed_content,
                                            "scheduled_time": scheduled_at.isoformat(),
                                            "metadata": schedule_metadata,  # Store metadata as JSONB
                                        }
                                        
                                        # Try to insert with metadata, fallback if column doesn't exist
                                        try:
                                            self.supabase.client.table("scheduled_posts").insert(insert_data).execute()
                                        except Exception as metadata_error:
                                            # If metadata column doesn't exist, insert without it
                                            logger.debug(f"Metadata column may not exist, trying without: {metadata_error}")
                                            insert_data.pop("metadata", None)
                                            self.supabase.client.table("scheduled_posts").insert(insert_data).execute()
                                        
                                        scheduled += 1
                                        logger.info(
                                            f"      📅 Scheduled for {scheduled_at.strftime('%Y-%m-%d %H:%M:%S')} (priority: {priority}, reason: {decision.reason[:50]}...)"
                                        )
                                    except Exception as schedule_error:
                                        logger.warning(
                                            f"      ⚠️ Scheduling failed: {schedule_error}",
                                            exc_info=True
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

    def run_curation_backfill(
        self, batch_size: int = 500, max_batches: int = 2
    ) -> Dict[str, Any]:
        """Ensure analyzed posts land in usable_posts"""
        if not self.supabase:
            logger.warning("Supabase unavailable; skipping curation backfill")
            return {"checked": 0, "curated": 0, "batches": 0}

        from src.infrastructure.database.database_agent import get_database_agent
        agent = get_database_agent()
        total_curated = 0
        total_checked = 0
        batches_ran = 0
        offset = 0

        while batches_ran < max_batches:
            resp = (
                self.supabase.client.table("posts")
                .select("*")
                .order("created_at", desc=True)
                .range(offset, offset + batch_size - 1)
                .execute()
            )
            posts = resp.data or []
            if not posts:
                break

            for post in posts:
                if not post.get("ai_summary") or not post.get("content"):
                    continue
                total_checked += 1
                try:
                    if agent.auto_curate_to_usable_posts(post):
                        total_curated += 1
                except Exception as curation_error:
                    logger.debug(f"Curation backfill error: {curation_error}")

            offset += batch_size
            batches_ran += 1

        logger.info(
            f"📦 Curation backfill checked {total_checked} posts, curated {total_curated}"
        )
        return {
            "checked": total_checked,
            "curated": total_curated,
            "batches": batches_ran,
        }

    async def run_full_loop(
        self,
        platforms: Optional[List[str]] = None,
        analyze_limit: Optional[int] = None,
        min_match_score: float = 0.65,
        schedule_minutes: int = 60,
        auto_schedule: bool = False,
        use_agent_graph: bool = False,
        curation_batch_size: int = 500,
        curation_batches: int = 2,
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
            "curation": {},
            "started_at": datetime.now().isoformat(),
        }

        # Step 1: Collection
        collection_results = await self.run_collection(platforms=platforms)
        results["collection"] = collection_results

        # Step 2: Analysis (with persona matching built-in)
        analysis_results = await self.run_analysis(limit=analyze_limit, use_agent_graph=use_agent_graph)
        results["analysis"] = analysis_results

        # Step 2b: Make sure usable_posts reflects most recent analysis
        curation_results = self.run_curation_backfill(
            batch_size=curation_batch_size, max_batches=curation_batches
        )
        results["curation"] = curation_results

        # Step 3: Transformation & Scheduling
        transformation_results = await self.run_transformation_and_scheduling(
            min_match_score=min_match_score,
            schedule_minutes=schedule_minutes,
            auto_schedule=auto_schedule,
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
        logger.info("\n📤 STEP 4: POSTING (PublisherWorker)")
        posting_results = self.publisher.post_due_items()
        results["posting"] = posting_results
        logger.info(f"   ✅ Posted: {posting_results.get('posted', 0)}, Failed: {posting_results.get('failed', 0)}")

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
    parser.add_argument(
        "--auto-schedule",
        action="store_true",
        help="Also push rewrites into scheduled_posts table (default: off)",
    )
    parser.add_argument(
        "--use-agent-graph",
        action="store_true",
        help="Use Multi-Agent Graph for analysis (default: off)",
    )
    parser.add_argument(
        "--curation-batch-size",
        type=int,
        default=500,
        help="Posts per batch for curation backfill (default: 500)",
    )
    parser.add_argument(
        "--curation-batches",
        type=int,
        default=2,
        help="How many curation batches to run after analysis (default: 2)",
    )

    args = parser.parse_args()

    loop = FullAutomationLoop()
    results = await loop.run_full_loop(
        platforms=args.platforms,
        analyze_limit=args.analyze_limit,
        min_match_score=args.min_match_score,
        schedule_minutes=args.schedule_minutes,
        auto_schedule=args.auto_schedule,
        use_agent_graph=args.use_agent_graph,
        curation_batch_size=args.curation_batch_size,
        curation_batches=args.curation_batches,
    )

    logger.info("\n✅ Full loop complete!")
    logger.info(f"Results: {results}")


if __name__ == "__main__":
    asyncio.run(main())
