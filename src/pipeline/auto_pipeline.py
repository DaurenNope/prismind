from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

from src.pipeline.orchestrator import get_orchestrator
from src.utils.config import get_config
from src.services.profile_content_selector import ProfileContentSelector
from src.services.profile_publishing_orchestrator import ProfilePublishingOrchestrator
from src.publishing.circuit_breaker import get_circuit_breaker

try:
    from src.database.manager import SupabaseManager
except Exception:  # pragma: no cover - Supabase optional during local tests
    SupabaseManager = None  # type: ignore


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
                from src.services.profile_content_pipeline import list_available_profiles

                self._profiles = [
                    profile["profile_key"]
                    for profile in list_available_profiles()
                    if profile.get("profile_key")
                ]
            except Exception:
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
            analyzed = await self._safe_analyze_batch(
                max(posts_collected, batch_limit)
            )
            summary["analyzed"] = analyzed

        if flags.get("auto_rewrite_after_analysis", True):
            rewrite_report = await self._auto_rewrite_cycle()
            if rewrite_report:
                summary["rewritten"] = rewrite_report

        return summary

    async def _safe_analyze_batch(self, limit: int) -> int:
        try:
            return await self._orch.analyze_batch(limit=limit)
        except Exception:
            return 0

    async def _auto_rewrite_cycle(self) -> Dict[str, Any]:
        profiles = self._get_profile_keys()
        if not profiles:
            return {}

        flags = self.config.flags
        posts_per_profile = max(
            0, int(flags.get("auto_rewrite_posts_per_profile", 3))
        )
        if posts_per_profile <= 0:
            return {}

        report: Dict[str, Any] = {}
        for profile_key in profiles:
            processed = await self._process_profile(profile_key, posts_per_profile)
            if processed:
                report[profile_key] = processed
        return report

    async def process_backlog_for_profiles(
        self, profiles: Optional[List[str]] = None, posts_per_profile: Optional[int] = None
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
            except Exception:
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

    async def _process_profile(
        self, profile_key: str, limit: int
    ) -> Dict[str, Any]:
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
                "status": circuit_breaker.get_status()
            }
        
        selector = ProfileContentSelector(profile_key)
        posts = selector.select_posts_for_rewrite(limit=limit)
        if not posts:
            return {}

        orchestrator = ProfilePublishingOrchestrator(profile_key)
        dry_run = not self.config.flags.get("auto_schedule_after_rewrite", False)

        stored = 0
        scheduled = 0
        errors: List[str] = []

        for post in posts:
            try:
                result = await orchestrator.process_post(post, dry_run=True)
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
                    exc_info=True
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
        except Exception:
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
                    exc_info=True
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
                    "platform": platform,
                    "content": rewritten_content,
                    "content_type": _map_content_type(content_type),
                    "scheduled_time": _compute_schedule_time(
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
                        exc_info=True
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

