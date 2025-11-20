from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.pipeline.orchestrator import get_orchestrator
from src.publishing.circuit_breaker import get_circuit_breaker
from src.services.profile_content_selector import ProfileContentSelector
from src.services.profile_publishing_orchestrator import ProfilePublishingOrchestrator
from src.utils.config import get_config

logger = logging.getLogger(__name__)

try:
    from src.database.manager import SupabaseManager

    supabase_manager = SupabaseManager  # type: ignore
except Exception as e:  # pragma: no cover - Supabase optional during local tests
    logger.error(f"Error: {e}")
    supabase_manager = None  # type: ignore


class AutoPipeline:
    """Coordinates auto-analysis and rewrite pipeline after collection runs."""

    def __init__(self) -> None:
        self.config = get_config()
        self._orch = get_orchestrator()
        self._profiles: Optional[List[str]] = None

    @property
    def enabled(self) -> bool:
        flags = self.config.flags
        return bool(
            flags.get("auto_analyze_after_collection")
            or flags.get("auto_rewrite_after_analysis")
        )

    def _get_profile_keys(self) -> List[str]:
        if self._profiles is None:
            try:
                from src.services.profile_content_pipeline import (
                    list_available_profiles,
                )

                self._profiles = [
                    profile["profile_key"]
                    for profile in list_available_profiles()
                    if profile.get("profile_key")
                ]
            except Exception as e:
                logger.error(f"Error: {e}")
                self._profiles = []
        return self._profiles or []

    async def handle_collection(
        self, platform: str, posts_collected: int
    ) -> Dict[str, Any]:
        """
        Execute follow-up automation after a successful collection run.

        Returns a summary that can be surfaced in the UI for transparency.
        """
        summary: Dict[str, Any] = {
            "platform": platform,
            "collected": int(posts_collected),
        }
        if posts_collected <= 0:
            return summary

        flags = self.config.flags
        batch_limit = int(flags.get("auto_pipeline_batch_limit", 25))

        if flags.get("auto_analyze_after_collection", True):
            analyzed = await self._safe_analyze_batch(max(posts_collected, batch_limit))
            summary["analyzed"] = analyzed

        if flags.get("auto_rewrite_after_analysis", True):
            rewrite_report = await self._auto_rewrite_cycle()
            if rewrite_report:
                summary["rewritten"] = rewrite_report

        return summary

    async def _safe_analyze_batch(self, limit: int) -> int:
        try:
            return await self._orch.analyze_batch(limit=limit)
        except Exception as e:
            logger.error(f"Error: {e}")
            return 0

    async def _auto_rewrite_cycle(self) -> Dict[str, Any]:
        return await self.run_rewrite_cycle()

    async def run_rewrite_cycle(
        self,
        profiles: Optional[List[str]] = None,
        posts_per_profile: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Rewrite/schedule posts for the specified profiles (or all profiles by default).

        This is separated so external callers (e.g., manual analysis runs) can trigger
        the rewrite pipeline without re-running collection/analysis.
        """
        targets = profiles or self._get_profile_keys()
        if not targets:
            return {}

        flags = self.config.flags
        limit = max(
            0, int(posts_per_profile or flags.get("auto_rewrite_posts_per_profile", 3))
        )
        if limit <= 0:
            return {}

        report: Dict[str, Any] = {}
        for profile_key in targets:
            processed = await self._process_profile(profile_key, limit)
            if processed:
                report[profile_key] = processed
        return report

    async def process_backlog_for_profiles(
        self,
        profiles: Optional[List[str]] = None,
        posts_per_profile: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process existing posts (no new collection) end-to-end:
        - analyze batch (if enabled)
        - rewrite for each profile (fast-path controlled by flags)
        - schedule immediately if enabled
        """
        flags = self.config.flags
        report: Dict[str, Any] = {}

        # Optional analysis pass on existing pool
        if flags.get("auto_analyze_after_collection", True):
            try:
                analyzed = await self._safe_analyze_batch(
                    limit=int(flags.get("auto_pipeline_batch_limit", 25))
                )
                report["analyzed"] = analyzed
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

        # Rewrite + schedule from backlog
        targets = profiles or self._get_profile_keys()
        if not targets:
            return report

        limit = int(posts_per_profile or flags.get("auto_rewrite_posts_per_profile", 3))
        per_profile: Dict[str, Any] = {}
        for profile_key in targets:
            processed = await self._process_profile(profile_key, limit)
            if processed:
                per_profile[profile_key] = processed

        if per_profile:
            report["rewritten"] = per_profile
        return report

    async def _process_single_post_for_rewrite(
        self, post: Dict[str, Any], profile_key: str, schedule: bool = False
    ) -> Dict[str, Any]:
        """
        Process a single post for rewriting after angles are generated.
        Called automatically after angle generation in curation.
        """
        try:
            from src.services.profile_publishing_orchestrator import (
                ProfilePublishingOrchestrator,
            )

            orchestrator = ProfilePublishingOrchestrator(
                profile_key, auto_schedule=schedule
            )
            result = await orchestrator.process_post(post, dry_run=not schedule)
            rewrites = result.get("rewrites") or {}

            if not rewrites:
                return {"transformations": 0, "scheduled": 0}

            created = self._persist_rewrites(
                profile_key, post, rewrites, schedule=schedule
            )
            return created
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(
                f"❌ Error processing single post {post.get('post_id', 'unknown')} for {profile_key}: {e}",
                exc_info=True,
            )
            return {"transformations": 0, "scheduled": 0, "error": str(e)}

    async def _process_profile(self, profile_key: str, limit: int) -> Dict[str, Any]:
        # 🚨 CHECK CIRCUIT BREAKER FIRST
        circuit_breaker = get_circuit_breaker()
        if circuit_breaker.all_providers_exhausted():
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "🚫 Circuit breaker: All API providers exhausted. "
                "Skipping rewrite automation. Will retry after recovery timeout."
            )
            return {
                "skipped": True,
                "reason": "circuit_breaker_open",
                "status": circuit_breaker.get_status(),
            }

        selector = ProfileContentSelector(profile_key)

        # Prioritize posts that will route to Twitter and Threads (this-week, 24-72h)
        # Only fall back to evergreen if we don't have enough
        posts = []
        priority_windows = ["this-week", "24-72h", "same-day"]
        for window in priority_windows:
            window_posts = selector.select_posts_for_rewrite(
                limit=limit, time_windows=[window]
            )
            posts.extend(window_posts)
            if len(posts) >= limit:
                posts = posts[:limit]
                break

        # If we still need more, get evergreen posts
        if len(posts) < limit:
            evergreen_posts = selector.select_posts_for_rewrite(
                limit=limit - len(posts), time_windows=["evergreen"]
            )
            posts.extend(evergreen_posts)

        if not posts:
            return {}

        schedule_enabled = self.config.flags.get("auto_schedule_after_rewrite", False)
        orchestrator = ProfilePublishingOrchestrator(
            profile_key, auto_schedule=schedule_enabled
        )
        dry_run = not schedule_enabled

        stored = 0
        scheduled = 0
        errors: List[str] = []

        for post in posts:
            try:
                result = await orchestrator.process_post(post, dry_run=dry_run)
                rewrites = result.get("rewrites") or {}
                if not rewrites:
                    continue

                created = self._persist_rewrites(
                    profile_key, post, rewrites, schedule=not dry_run
                )
                stored += created.get("transformations", 0)
                scheduled += created.get("scheduled", 0)
            except Exception as exc:  # pragma: no cover - defensive guard
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    f"❌ Error processing post {post.get('post_id', 'unknown')} for {profile_key}: {exc}",
                    exc_info=True,
                )
                errors.append(str(exc))

        summary: Dict[str, Any] = {}
        if stored:
            summary["transformations"] = stored
        if scheduled:
            summary["scheduled"] = scheduled
        if errors:
            summary["errors"] = errors[:3]
        return summary

    def _persist_rewrites(
        self,
        profile_key: str,
        source_post: Dict[str, Any],
        rewrites: Dict[str, Any],
        schedule: bool = False,
    ) -> Dict[str, int]:
        if SupabaseManager is None:
            return {}

        try:
            manager = SupabaseManager()
        except Exception as e:
            logger.error(f"Error: {e}")
            return {}

        post_id = str(source_post.get("post_id") or "")
        if not post_id:
            return {}

        now_iso = datetime.now(timezone.utc).isoformat()
        transformations_created = 0
        scheduled_created = 0

        for platform, payload in rewrites.items():
            rewritten_content = payload.get("rewritten_content")
            if not rewritten_content:
                continue

            # Avoid duplicates in mimesis_transformations
            existing = (
                manager.client.table("mimesis_transformations")
                .select("id")
                .eq("persona_key", profile_key)
                .eq("source_post_id", post_id)
                .eq("platform", platform)
                .limit(1)
                .execute()
            )
            if existing.data:
                continue

            try:
                manager.client.table("mimesis_transformations").insert(
                    {
                        "persona_key": profile_key,
                        "source_post_id": post_id,
                        "platform": platform,
                        "content": rewritten_content,
                        "score": float(payload.get("quality_score") or 0),
                        "ready_for_posting": False,
                        "created_at": now_iso,
                    }
                ).execute()
                transformations_created += 1
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"⚠️ Failed to insert transformation for {profile_key}/{platform}: {e}",
                    exc_info=True,
                )
                continue

            if schedule:
                content_type = payload.get("platform_fit", "single_post")
                existing_sched = (
                    manager.client.table("scheduled_posts")
                    .select("id")
                    .eq("persona_key", profile_key)
                    .eq("platform", platform)
                    .eq("content", rewritten_content)
                    .limit(1)
                    .execute()
                )
                if existing_sched.data:
                    continue
                scheduled_payload = {
                    "persona_key": profile_key,
                    "personality_key": profile_key,  # Required by database schema
                    "platform": platform,
                    "content": rewritten_content,
                    "content_type": _map_content_type(content_type),
                    "scheduled_time": _compute_schedule_time(
                        self.config.flags.get("auto_schedule_delay_minutes", 90)
                    ),
                    "scheduled_at": _compute_schedule_time(  # Also include scheduled_at for compatibility
                        self.config.flags.get("auto_schedule_delay_minutes", 90)
                    ),
                    "status": "pending",
                }
                try:
                    manager.client.table("scheduled_posts").insert(
                        scheduled_payload
                    ).execute()
                    scheduled_created += 1
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"⚠️ Failed to schedule post for {profile_key}/{platform}: {e}",
                        exc_info=True,
                    )
                    continue

        return {
            "transformations": transformations_created,
            "scheduled": scheduled_created,
        }


def _map_content_type(platform_fit: str) -> str:
    fit = (platform_fit or "").lower()
    if "thread" in fit:
        return "thread"
    return "single_tweet"


def _compute_schedule_time(delay_minutes: int) -> str:
    delay_minutes = max(5, int(delay_minutes or 0))
    scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)
    return scheduled_at.isoformat()
