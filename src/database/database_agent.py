#!/usr/bin/env python3
"""
DatabaseAgent

Centralized database operations layer for BEYONDLINES.
 - Supabase is the primary source of truth
 - SQLite is a local cache/mirror for resilience and fast reads
 - Validates schema-related fields and post payloads
 - Applies duplicate checking and normalized IDs/URLs
 - Provides health and recent-activity reports
 - Encapsulates retry/backoff for transient failures
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.utils.logging_config import get_logger
from src.utils.observability_hub import get_observability_hub

logger = get_logger(__name__)


class DatabaseAgent:
    def __init__(self) -> None:
        # IMPORTANT: Use StorageFacade as the single source of truth for all saves
        from src.storage.db import get_storage

        self._storage = get_storage()
        logger.info("✅ StorageFacade initialized (single source of truth)")

        # Primary: Supabase (for direct queries and monitoring)
        try:
            from src.database.manager import SupabaseManager  # lazy import

            self._supabase_manager = SupabaseManager()
            self._supabase = self._supabase_manager.client
            logger.info("✅ Supabase connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ Supabase initialization failed: {e}", exc_info=True)
            self._supabase_manager = None
            self._supabase = None

        # Local cache: SQLite
        try:
            from src.storage.sqlite_adapter import SQLiteAdapter

            self._sqlite = SQLiteAdapter()
            logger.info("✅ SQLite connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ SQLite initialization failed: {e}", exc_info=True)
            self._sqlite = None

        # Duplicate detection (uses storage facade-like logic but scoped here)
        try:
            from src.utils.duplicate_detector import DuplicateDetector

            self._dupes = DuplicateDetector(
                db_manager=None, supabase_manager=self._supabase_manager
            )
            logger.info("✅ Duplicate detector initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Duplicate detector initialization failed: {e}", exc_info=True
            )
            self._dupes = None

        # Post validation / insertion mapping
        try:
            from src.services.supabase.post_inserter import PostInserter
            from src.utils.post_validator import validate_post

            self._validate_post = validate_post
            duplicate_checker = None
            if self._dupes is not None:

                class DuplicateCheckerWrapper:
                    def __init__(self, detector):
                        self.detector = detector

                    def check_duplicate_post(self, content, author, platform, url=None):
                        item = {
                            "content": content,
                            "author": author,
                            "platform": platform,
                            "url": url,
                        }
                        return self.detector.is_duplicate(item)

                duplicate_checker = DuplicateCheckerWrapper(self._dupes)
            self._post_inserter = (
                PostInserter(self._supabase, duplicate_checker)
                if self._supabase
                else None
            )
        except Exception as e:
            logger.warning(
                f"⚠️ Post inserter initialization failed: {e}", exc_info=True
            )
            self._validate_post = None
            self._post_inserter = None

        # Initialize metrics module (will set record_post_operation callback later)
        try:
            from src.database.metrics import DatabaseMetrics

            self._metrics = DatabaseMetrics(self._supabase, self._sqlite)
            logger.info("✅ Database metrics initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Database metrics initialization failed: {e}", exc_info=True
            )
            self._metrics = None

        # Initialize repair module
        try:
            from src.database.repair import DatabaseRepair

            self._repair = DatabaseRepair(
                self._supabase, self._sqlite, self._post_inserter
            )
            logger.info("✅ Database repair module initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Database repair module initialization failed: {e}", exc_info=True
            )
            self._repair = None

        # Initialize validation module
        try:
            from src.database.validation import DatabaseValidation

            self._validation = DatabaseValidation(validate_post_fn=self._validate_post)
            logger.info("✅ Database validation module initialized")
        except Exception as e:
            logger.warning(
                f"⚠️ Database validation module initialization failed: {e}",
                exc_info=True,
            )
            self._validation = None

        # Initialize sync module (will be set up after _normalize_post_data is available)
        self._sync = None

        # Initialize monitoring module
        try:
            from src.database.monitoring import DatabaseMonitoring

            self._monitoring = DatabaseMonitoring(
                get_collection_metrics_fn=self.get_collection_metrics
                if hasattr(self, "get_collection_metrics")
                else None
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            self._monitoring = None

        # Initialize curation module
        try:
            from src.database.curation import DatabaseCuration

            self._curation = DatabaseCuration(supabase=self._supabase)
        except Exception as e:
            logger.error(f"Error: {e}")
            self._curation = None

        # Initialize health/reporting module
        try:
            from src.database.health import DatabaseHealth

            self._health = DatabaseHealth(
                supabase_client=self._supabase,
                sqlite_adapter=self._sqlite,
                get_last_post_id_fn=self.get_last_post_id,
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            self._health = None

    # --------------- Metrics / Freshness ---------------
    # Delegated to metrics module for better organization
    def ensure_metrics_table(self) -> None:
        """Ensure local cache has the metrics table. Supabase handled via migration."""
        if self._metrics:
            self._metrics.ensure_metrics_table()

    def get_collection_metrics(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get collection metrics for a platform"""
        if self._metrics:
            return self._metrics.get_collection_metrics(platform)
        # Fallback implementation
        if self._supabase is not None:
            try:
                r = (
                    self._supabase.table("collection_metrics")
                    .select("*")
                    .eq("platform", platform)
                    .limit(1)
                    .execute()
                )
                if getattr(r, "data", None):
                    return r.data[0]
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        return None

    def record_post_operation(
        self,
        post_id: str,
        platform: str,
        operation: str = "insert",
        quality_score: Optional[float] = None,
        value_score: Optional[float] = None,
        has_analysis: bool = False,
    ) -> bool:
        """Track individual post operations (insert/update) for monitoring"""
        if self._metrics:
            return self._metrics.record_post_operation(
                post_id, platform, operation, quality_score, value_score, has_analysis
            )
        return False

    def record_collection_result(
        self,
        platform: str,
        count: int,
        success: bool = True,
        failure_reason: Optional[str] = None,
        *,
        started_at: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_details: Optional[str] = None,
    ) -> bool:
        """Record collection result for a platform"""
        if self._metrics:
            return self._metrics.record_collection_result(
                platform,
                count,
                success,
                failure_reason,
                started_at=started_at,
                duration_seconds=duration_seconds,
                message=message,
                metadata=metadata,
                error_details=error_details,
            )
        return False

    # --------------- Completeness / Repair ---------------
    # Delegated to repair module for better organization
    def _is_empty(self, v: Any) -> bool:
        """Check if a value is empty"""
        if self._repair:
            return self._repair._is_empty(v)
        # Fallback implementation
        try:
            if v is None:
                return True
            if isinstance(v, str) and not v.strip():
                return True
            if isinstance(v, (list, dict)) and not v:
                return True
        except Exception as e:
            logger.error(f"Error: {e}")
            return False
        return False

    def count_incomplete_posts(self) -> int:
        """Count posts in Supabase missing required fields."""
        if self._repair:
            return self._repair.count_incomplete_posts()
        return 0

    def repair_incomplete_posts(self, limit: int = 200) -> int:
        """Fetch incomplete posts and backfill required fields with safe defaults."""
        if self._repair:
            return self._repair.repair_incomplete_posts(limit)
            return 0

    def _infer_platform(self, post: Dict[str, Any]) -> Optional[str]:
        """Infer platform from post data"""
        if self._repair:
            return self._repair._infer_platform(post)
        return None

    def fix_invalid_platforms(
        self,
        *,
        limit: int = 2000,
        dry_run: bool = True,
        auto: bool = False,
        interval_minutes: int = 720,
    ) -> Dict[str, Any]:
        """Normalize posts with invalid or blank platform values."""
        if self._repair:
            return self._repair.fix_invalid_platforms(
                limit=limit,
                dry_run=dry_run,
                auto=auto,
                interval_minutes=interval_minutes,
            )
        return {"updated": 0, "skipped": True, "reason": "Repair module not available"}

    # --------------- Monitoring ---------------
    # Delegated to monitoring module for better organization
    def detect_stale_collections(
        self, thresholds_minutes: Optional[Dict[str, int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Detect stale collections based on last run time"""
        if self._monitoring:
            return self._monitoring.detect_stale_collections(thresholds_minutes)
        return {}

    def notify_stale(self, stale: Dict[str, Dict[str, Any]]) -> None:
        """Notify about stale collections"""
        if self._monitoring:
            self._monitoring.notify_stale(stale)

    async def trigger_collections(self, platforms: List[str]) -> Dict[str, int]:
        from src.pipeline.orchestrator import Orchestrator

        results: Dict[str, int] = {}
        orch = Orchestrator()
        for p in platforms:
            try:
                cnt = await orch.collect_platform(p)
                results[p] = cnt
                self.record_collection_result(p, cnt, success=True)
            except Exception as e:
                logger.error(f"Error: {e}")
                self.record_collection_result(
                    p, 0, success=False, failure_reason=str(e)[:200]
                )
                results[p] = 0
        return results

    # --------------- Proactive DBA Functions ---------------
    # Delegated to validation module for better organization
    def validate_and_monitor_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Validate, check quality, and monitor every post"""
        if self._validation:
            # Set record_post_operation callback dynamically
            if not self._validation._record_post_operation_set:
                self._validation._record_post_operation = self.record_post_operation
                self._validation._record_post_operation_set = True
            return self._validation.validate_and_monitor_post(post)
        # Fallback to empty result if validation module not available
        return {
            "validated": False,
            "quality_checked": False,
            "issues_found": [],
            "warnings": [],
            "monitored": False,
        }

    # --------------- Core Operations ---------------
    # Delegated to validation module for better organization
    def _normalize_post_data(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and clean post data BEFORE validation"""
        if self._validation:
            return self._validation.normalize_post_data(post)
        # Fallback: return post as-is if validation module not available
        return post

    def _ensure_sync_module(self):
        """Ensure sync module is initialized with proper callbacks"""
        if self._sync is None:
            try:
                from src.database.sync import DatabaseSync

                self._sync = DatabaseSync(
                    supabase=self._supabase,
                    sqlite=self._sqlite,
                    post_inserter=self._post_inserter,
                    normalize_post_data_fn=self._normalize_post_data,
                )
            except Exception as e:
                logger.warning(
                    f"⚠️ Database sync module initialization failed: {e}", exc_info=True
                )
                self._sync = None

    def save_post(
        self, post: Dict[str, Any], retries: int = 3, backoff_seconds: float = 1.5
    ) -> bool:
        """
        Save a post - DELEGATES TO StorageFacade (single source of truth).
        - NORMALIZES and cleans data FIRST (prevents corruption)
        - Delegates to StorageFacade.save_post() for actual save
        - Adds monitoring/validation on top
        - Ensures post_id is set using PostIDGenerator
        """
        hub = get_observability_hub()
        post_id = post.get("post_id", "unknown")
        platform = post.get("platform", "unknown")

        # Track metrics
        hub.metrics.increment(
            "database_agent.save_post.called", labels={"platform": platform}
        )

        try:
            # Sanity
            if not isinstance(post, dict):
                logger.error("save_post: invalid post type")
                return False

            # CRITICAL: Normalize and clean data FIRST (this prevents all the corruption issues)
            post = self._normalize_post_data(post)

            # Ensure post_id is set (use ID generator)
            if not post.get("post_id"):
                from src.storage.id_generator import PostIDGenerator

                post["post_id"] = PostIDGenerator.generate_post_id(post)
            else:
                # Normalize existing post_id
                from src.storage.id_generator import PostIDGenerator

                platform = post.get("platform", "")
                post["post_id"] = PostIDGenerator._normalize_id(
                    str(post["post_id"]), platform
                )

            # DELEGATE TO StorageFacade (single source of truth)
            # StorageFacade handles: duplicate checks, SQLite + Supabase sync, collected_at
            result = self._storage.save_post(post)

            post_id = post.get("post_id", post_id)
            platform = post.get("platform", platform)

            # Track success
            if result:
                hub.metrics.increment(
                    "database_agent.save_post.success", labels={"platform": platform}
                )
            else:
                hub.metrics.increment(
                    "database_agent.save_post.failed",
                    labels={
                        "platform": platform,
                        "reason": "storage_facade_returned_false",
                    },
                )

            # Optional: Track sync status in SQLite for monitoring (if needed)
            if result and post_id and self._sqlite:
                try:
                    # Check if synced to Supabase by querying Supabase
                    if self._supabase:
                        try:
                            existing = (
                                self._supabase.table("posts")
                                .select("post_id")
                                .eq("platform", platform)
                                .eq("post_id", post_id)
                                .limit(1)
                                .execute()
                            )
                            if existing.data:
                                self._sqlite.mark_synced_to_supabase(
                                    post_id, synced=True
                                )
                            else:
                                self._sqlite.mark_synced_to_supabase(
                                    post_id, synced=False, error="Not found in Supabase"
                                )
                        except Exception as e:
                            logger.error(f"Error: {e}")
                            pass  # Don't fail if monitoring fails
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass  # Don't fail if monitoring fails

            # AUTOMATIC CURATION: Check if post should be in usable_posts (only if saved successfully)
            if result:
                has_analysis = bool(
                    post.get("analyzed_at")
                    and post.get("ai_summary")
                    and len(str(post.get("ai_summary", "")).strip()) >= 30
                )

                if has_analysis:
                    try:
                        curated = False
                        if self._curation:
                            curated = self._curation.auto_curate_to_usable_posts(post)
                        if curated:
                            logger.info(
                                f"✅ Auto-curated post {post_id} ({platform}) to usable_posts"
                            )
                        else:
                            logger.debug(
                                f"Post {post_id} did not meet usable_posts criteria"
                            )
                    except Exception as e:
                        # Don't fail save_post if auto-curation fails - log and continue
                        logger.warning(f"Auto-curation failed for post {post_id}: {e}")
                        import traceback

                        logger.debug(traceback.format_exc())

            return result

        except Exception as e:
            logger.error(f"DB Agent save_post error: {e}")
            import traceback

            logger.debug(traceback.format_exc())

            # Track error
            hub.metrics.increment(
                "database_agent.save_post.error",
                labels={"platform": platform, "error_type": type(e).__name__},
            )
            hub.errors.capture_exception(
                e,
                context={
                    "operation": "save_post",
                    "post_id": post_id,
                    "platform": platform,
                },
            )

            return False

    def get_last_post_id(self, platform: str) -> Optional[str]:
        """
        Fetch the most recent post_id for a platform from Supabase.
        Returns normalized Reddit IDs with t3_ prefix if platform == 'reddit'.
        """
        if not self._supabase:
            return None
        try:
            r = (
                self._supabase.table("posts")
                .select("post_id")
                .eq("platform", platform)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            if getattr(r, "data", None):
                pid = (r.data[0].get("post_id") or "").strip()
                if platform == "reddit" and pid and not pid.startswith("t3_"):
                    pid = f"t3_{pid}"
                return pid or None
        except Exception as e:
            logger.debug(f"get_last_post_id failed for {platform}: {e}")
            return None
        return None

    # --------------- Health / Maintenance ---------------
    def health_report(self) -> Dict[str, Any]:
        """Return a quick health summary for DB components."""
        if getattr(self, "_health", None):
            return self._health.health_report()
        return {
            "supabase_ok": False,
            "sqlite_ok": False,
            "latest_ids": {"twitter": None, "reddit": None, "threads": None},
            "sync_status": {},
            "generated_at": datetime.utcnow().isoformat(),
        }

    # --------------- Sync Operations ---------------
    # Delegated to sync module for better organization
    def retry_failed_syncs(self, limit: int = 100) -> Dict[str, Any]:
        """Retry syncing unsynced posts from SQLite to Supabase"""
        self._ensure_sync_module()
        if self._sync:
            return self._sync.retry_failed_syncs(limit)
        return {"attempted": 0, "succeeded": 0, "failed": 0, "errors": []}

    def get_sync_status_report(self) -> Dict[str, Any]:
        """Get detailed sync status report for visibility"""
        if self._sync:
            return self._sync.get_sync_status_report()
            return {
                "error": "Sync module not available",
                "total": 0,
                "synced": 0,
                "unsynced": 0,
                "failed": 0,
                "sync_percentage": 0.0,
            }

    def recent_activity(self, minutes: int = 60) -> Dict[str, int]:
        """Counts posts created in the last N minutes (Supabase)."""
        if getattr(self, "_health", None):
            return self._health.recent_activity(minutes)
        return {"twitter": 0, "reddit": 0, "threads": 0}

    # --------------- Posted Performance APIs ---------------
    def _get_posted_content_id(
        self, platform: str, platform_post_id: str
    ) -> Optional[int]:
        if not self._supabase:
            return None
        try:
            r = (
                self._supabase.table("posted_content")
                .select("id")
                .eq("platform", platform)
                .eq("platform_post_id", platform_post_id)
                .limit(1)
                .execute()
            )
            if getattr(r, "data", None):
                return int(r.data[0]["id"])
        except Exception as e:
            logger.debug(
                f"_get_posted_content_id failed for {platform}/{platform_post_id}: {e}"
            )
            return None
        return None

    def record_post_publication(
        self,
        platform: str,
        platform_post_id: str,
        *,
        url: str = "",
        persona: str = "",
        content_hash: str = "",
        posted_at: Optional[str] = None,
        initial_text: str = "",
        topic: str = "",
        tags: Optional[List[str]] = None,
        has_media: bool = False,
        lang: str = "",
    ) -> Optional[Dict[str, Any]]:
        if not self._supabase:
            return None
        try:
            row = {
                "platform": platform,
                "platform_post_id": platform_post_id,
                "url": url,
                "persona": persona,
                "content_hash": content_hash,
                "posted_at": posted_at or datetime.utcnow().isoformat(),
                "initial_text": initial_text,
                "topic": topic,
                "tags": tags or [],
                "has_media": bool(has_media),
                "lang": lang,
            }
            r = (
                self._supabase.table("posted_content")
                .upsert(row, on_conflict="platform,platform_post_id")
                .execute()
            )
            if getattr(r, "data", None):
                return r.data[0]
        except Exception as e:
            logger.warning(
                f"record_post_publication failed for {platform}/{platform_post_id}: {e}"
            )
            return None
        return None

    def _compute_engagement_score(
        self, views: int, likes: int, comments: int, shares: int, bookmarks: int
    ) -> float:
        try:
            num = likes + 2 * comments + 3 * shares + 2 * bookmarks
            den = max(1, views)
            return float(num) / float(den)
        except Exception as e:
            logger.debug(f"_compute_engagement_score failed: {e}")
            return 0.0

    def upsert_posted_metrics(
        self,
        platform: str,
        platform_post_id: str,
        snapshot: Dict[str, Any],
    ) -> bool:
        if not self._supabase:
            return False
        try:
            pc_id = self._get_posted_content_id(platform, platform_post_id)
            if not pc_id:
                # Create shell row if missing
                created = self.record_post_publication(platform, platform_post_id)
                pc_id = int(created["id"]) if created and created.get("id") else None
                if not pc_id:
                    return False

            snap_at = snapshot.get("snapshot_at") or datetime.utcnow().isoformat()
            row = {
                "posted_content_id": pc_id,
                "snapshot_at": snap_at,
                "views": int(snapshot.get("views") or 0),
                "likes": int(snapshot.get("likes") or 0),
                "comments": int(snapshot.get("comments") or 0),
                "shares": int(snapshot.get("shares") or 0),
                "bookmarks": int(snapshot.get("bookmarks") or 0),
            }
            # Upsert by unique key (posted_content_id, snapshot_at) is not supported directly → emulate
            self._supabase.table("posted_metrics").upsert(
                row, on_conflict="posted_content_id,snapshot_at"
            ).execute()

            # Recompute aggregates on posted_content
            agg = self._supabase.rpc(
                "exec",
                {
                    "sql": f"select coalesce(sum(views),0) v, coalesce(sum(likes),0) l, coalesce(sum(comments),0) c, coalesce(sum(shares),0) s, coalesce(sum(bookmarks),0) b from posted_metrics where posted_content_id={pc_id}"
                },
            )
            # Fallback if RPC not available: fetch and sum in client
            if not getattr(agg, "data", None):
                res = (
                    self._supabase.table("posted_metrics")
                    .select("views,likes,comments,shares,bookmarks")
                    .eq("posted_content_id", pc_id)
                    .execute()
                )
                v = l = c = s = b = 0
                for r in res.data or []:
                    v += int(r.get("views") or 0)
                    l += int(r.get("likes") or 0)
                    c += int(r.get("comments") or 0)
                    s += int(r.get("shares") or 0)
                    b += int(r.get("bookmarks") or 0)
            else:
                d0 = (
                    agg.data[0] if isinstance(agg.data, list) and agg.data else agg.data
                )
                v = int(d0.get("v") or 0)
                l = int(d0.get("l") or 0)
                c = int(d0.get("c") or 0)
                s = int(d0.get("s") or 0)
                b = int(d0.get("b") or 0)

            escore = self._compute_engagement_score(v, l, c, s, b)
            self._supabase.table("posted_content").update(
                {
                    "total_views": v,
                    "total_likes": l,
                    "total_comments": c,
                    "total_shares": s,
                    "total_bookmarks": b,
                    "engagement_score": escore,
                }
            ).eq("id", pc_id).execute()
            return True
        except Exception as e:
            logger.warning(
                f"upsert_posted_metrics failed for {platform}/{platform_post_id}: {e}"
            )
            return False

    def get_top_posts(
        self,
        since_minutes: int = 10080,
        limit: int = 20,
        platform: Optional[str] = None,
        persona: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self._supabase:
            return []
        try:
            q = (
                self._supabase.table("posted_content")
                .select("*")
                .gt(
                    "posted_at",
                    (
                        datetime.utcnow() - timedelta(minutes=max(1, since_minutes))
                    ).isoformat(),
                )
                .order("engagement_score", desc=True)
                .limit(max(1, min(100, limit)))
            )
            if platform:
                q = q.eq("platform", platform)
            if persona:
                q = q.eq("persona", persona)
            r = q.execute()
            return getattr(r, "data", []) or []
        except Exception as e:
            logger.debug(f"get_top_posts failed: {e}")
            return []

    # --------------- Quality Metrics ---------------
    # Delegated to metrics module for better organization
    def get_quality_metrics(
        self,
        platform: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Get quality metrics for monitoring and reporting"""
        if self._metrics:
            return self._metrics.get_quality_metrics(platform, hours, limit)
            return {
                "avg_quality": 0.0,
                "avg_value": 0.0,
                "count": 0,
                "low_quality_count": 0,
            }

    def get_quality_trends(
        self,
        platform: Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, list]:
        """Get quality score trends over time"""
        if self._metrics:
            return self._metrics.get_quality_trends(platform, days)
            return {"quality": [], "value": [], "timestamps": []}

    def backfill_quality_metrics(self, limit: int = 1000) -> int:
        """Backfill quality metrics for existing posts"""
        if self._metrics:
            # Set callback to self.record_post_operation for backfill
            if not self._metrics._record_post_operation_set:
                self._metrics._record_post_operation = self.record_post_operation
                self._metrics._record_post_operation_set = True
            return self._metrics.backfill_quality_metrics(limit)
            return 0

    def audit_database(
        self, limit: int = 100, platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Proactive DBA function: Audit database for issues.
        Like a human DBA would do - check everything.

        Returns:
            Dict with audit results, issues found, and recommendations
        """
        results = {
            "posts_checked": 0,
            "issues_found": [],
            "warnings": [],
            "critical_issues": [],
            "recommendations": [],
        }

        try:
            # Get recent posts to audit
            if self._supabase:
                query = (
                    self._supabase.table("posts")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                )

                if platforms:
                    query = query.in_("platform", platforms)

                result = query.execute()
                posts = getattr(result, "data", []) or []
            elif self._sqlite:
                # Fallback to SQLite
                posts = self._sqlite.get_posts(limit=limit)
            else:
                return results

            results["posts_checked"] = len(posts)

            # Audit each post
            for post in posts:
                # Validate and check quality
                audit_result = self.validate_and_monitor_post(post)

                if audit_result.get("issues_found"):
                    results["issues_found"].extend(audit_result["issues_found"])

                    # Categorize issues
                    critical = [
                        issue
                        for issue in audit_result["issues_found"]
                        if any(
                            keyword in issue.lower()
                            for keyword in [
                                "missing",
                                "invalid",
                                "failed",
                                "impossible",
                                "error",
                            ]
                        )
                    ]
                    if critical:
                        results["critical_issues"].append(
                            {
                                "post_id": post.get("post_id"),
                                "platform": post.get("platform"),
                                "issues": critical,
                            }
                        )

                if audit_result.get("warnings"):
                    results["warnings"].extend(audit_result["warnings"])

            # Generate recommendations
            if results["critical_issues"]:
                results["recommendations"].append(
                    f"Found {len(results['critical_issues'])} posts with critical issues. Review and fix them."
                )

            if len(results["issues_found"]) > len(posts) * 0.3:
                results["recommendations"].append(
                    f"High issue rate ({len(results['issues_found'])}/{len(posts)}). Review collection process."
                )

            # Check for common patterns
            placeholder_count = sum(
                1
                for post in posts
                if any(
                    placeholder in (post.get("content", "") or "").lower()
                    for placeholder in [
                        "scraping failed",
                        "extraction failed",
                        "placeholder",
                    ]
                )
            )
            if placeholder_count > 0:
                results["recommendations"].append(
                    f"Found {placeholder_count} posts with placeholder content. Check extractors."
                )

            truncated_count = sum(
                1 for post in posts if (post.get("content", "") or "").endswith("...")
            )
            if truncated_count > 0:
                results["recommendations"].append(
                    f"Found {truncated_count} posts with truncated content. Check extractors."
                )

        except Exception as e:
            logger.error(f"DB Agent audit_database failed: {e}")

        return results

    def check_recent_posts_quality(
        self, hours: int = 24, limit: int = 100
    ) -> Dict[str, Any]:
        """
        Check quality of recently collected posts.
        Like a DBA monitoring recent activity.
        """
        results = {
            "posts_checked": 0,
            "quality_issues": [],
            "collection_issues": [],
            "integrity_issues": [],
        }

        try:
            since = (datetime.utcnow() - timedelta(hours=max(1, hours))).isoformat()

            if self._supabase:
                query = (
                    self._supabase.table("posts")
                    .select("*")
                    .gt("created_at", since)
                    .order("created_at", desc=True)
                    .limit(limit)
                )
                result = query.execute()
                posts = getattr(result, "data", []) or []
            else:
                return results

            results["posts_checked"] = len(posts)

            for post in posts:
                # Check data quality
                quality_issues = self._check_data_quality(post)
                if quality_issues:
                    results["quality_issues"].append(
                        {
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "issues": quality_issues,
                        }
                    )

                # Check collection issues
                collection_issues = self._check_collection_issues(post)
                if collection_issues:
                    results["collection_issues"].append(
                        {
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "issues": collection_issues,
                        }
                    )

                # Check integrity
                integrity_issues = self._check_data_integrity(post)
                if integrity_issues:
                    results["integrity_issues"].append(
                        {
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "issues": integrity_issues,
                        }
                    )

        except Exception as e:
            logger.error(f"DB Agent check_recent_posts_quality failed: {e}")

        return results

    def cleanup_bad_posts(
        self,
        limit: int = 1000,
        platforms: Optional[List[str]] = None,
        min_issues: int = 2,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        Cleanup wrongly collected posts.
        Like a DBA cleaning up bad data.

        Args:
            limit: Maximum number of posts to check
            platforms: Filter by platforms (None = all)
            min_issues: Minimum number of issues to consider a post "bad"
            dry_run: If True, only report issues without deleting

        Returns:
            Dict with cleanup results
        """
        results = {
            "posts_checked": 0,
            "bad_posts_found": 0,
            "posts_deleted": 0,
            "posts_failed": 0,
            "bad_posts": [],
            "errors": [],
        }

        try:
            # Get all posts to check
            if self._supabase:
                query = (
                    self._supabase.table("posts")
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                )

                if platforms:
                    query = query.in_("platform", platforms)

                result = query.execute()
                posts = getattr(result, "data", []) or []
            elif self._sqlite:
                posts = self._sqlite.get_posts(limit=limit)
            else:
                return results

            results["posts_checked"] = len(posts)

            # Check each post
            for post in posts:
                # Validate and check for issues
                audit_result = self.validate_and_monitor_post(post)
                issues = audit_result.get("issues_found", [])

                # Check if post is "bad" (has critical issues)
                # BE CONSERVATIVE: Only delete clearly broken posts
                is_bad = False
                critical_keywords = [
                    "placeholder",
                    "truncated",
                    "missing",
                    "invalid",
                    "failed",
                    "error",
                    "impossible",
                    "scraping failed",
                    "extraction failed",
                ]

                # Count critical issues (excluding Reddit post_id format warnings - those might be false positives)
                critical_issues = [
                    issue
                    for issue in issues
                    if any(keyword in issue.lower() for keyword in critical_keywords)
                    and "reddit post_id" not in issue.lower()
                ]  # Exclude Reddit post_id format warnings

                # Also check for placeholder content directly (MOST IMPORTANT)
                content = post.get("content", "")
                if content:
                    content_lower = content.lower()
                    # Only flag if content is clearly a placeholder/error
                    if any(
                        placeholder in content_lower
                        for placeholder in [
                            "scraping failed",
                            "extraction failed",
                            "content extraction in progress",
                            "post from",
                            "placeholder",
                            "error extracting",
                        ]
                    ):
                        is_bad = True

                # Check for truncated content (ends with ...) - but be careful, some posts legitimately end with ...
                # Only flag if content is very short and ends with ...
                if content and len(content) < 50 and content.endswith("..."):
                    is_bad = True

                # Check for missing essential fields (MOST IMPORTANT)
                # Only delete if BOTH author AND url are missing/invalid
                has_valid_author = post.get("author") and post.get(
                    "author", ""
                ).lower() not in ["unknown", "n/a", ""]
                has_valid_url = post.get("url") and post.get("url", "").startswith(
                    "http"
                )

                if not has_valid_author and not has_valid_url:
                    is_bad = True  # Both missing = definitely bad
                elif not has_valid_author and not content:
                    is_bad = True  # No author and no content = bad

                # If has enough critical issues (excluding Reddit format warnings), mark as bad
                if len(critical_issues) >= min_issues:
                    is_bad = True

                if is_bad:
                    results["bad_posts_found"] += 1
                    results["bad_posts"].append(
                        {
                            "id": post.get("id"),
                            "post_id": post.get("post_id"),
                            "platform": post.get("platform"),
                            "author": post.get("author"),
                            "content_preview": (content or "")[:100],
                            "issues": issues,
                            "critical_issues": critical_issues,
                        }
                    )

                    # Delete if not dry run
                    if not dry_run:
                        try:
                            # Delete from Supabase
                            if self._supabase and post.get("id"):
                                self._supabase.table("posts").delete().eq(
                                    "id", post.get("id")
                                ).execute()

                            # Delete from SQLite
                            if self._sqlite and post.get("post_id"):
                                try:
                                    cur = self._sqlite.conn.cursor()
                                    cur.execute(
                                        "DELETE FROM posts WHERE post_id = ?",
                                        (post.get("post_id"),),
                                    )
                                    self._sqlite.conn.commit()
                                except Exception as e:
                                    logger.error(f"Error: {e}")
                                    pass

                            results["posts_deleted"] += 1
                            logger.info(
                                f"🗑️ Deleted bad post: {post.get('post_id')} ({post.get('platform')})"
                            )
                        except Exception as e:
                            results["posts_failed"] += 1
                            results["errors"].append(
                                f"Failed to delete {post.get('post_id')}: {e}"
                            )
                            logger.error(
                                f"Failed to delete post {post.get('post_id')}: {e}"
                            )

        except Exception as e:
            logger.error(f"DB Agent cleanup_bad_posts failed: {e}")
            results["errors"].append(str(e))

        return results

    def get_performance_cohorts(self, window_minutes: int = 10080) -> Dict[str, Any]:
        # Simple client-side cohorts by buckets
        items = self.get_top_posts(since_minutes=window_minutes, limit=500)
        cohorts: Dict[str, Dict[str, Any]] = {
            "platform": {},
            "persona": {},
            "has_media": {"true": {"n": 0, "avg": 0.0}, "false": {"n": 0, "avg": 0.0}},
        }

        def add(bucket: Dict[str, Any], key: str, esc: float):
            if key not in bucket:
                bucket[key] = {"n": 0, "avg": 0.0}
            b = bucket[key]
            n = b["n"] + 1
            b["avg"] = (b["avg"] * b["n"] + esc) / n
            b["n"] = n

        for it in items:
            esc = float(it.get("engagement_score") or 0)
            add(cohorts["platform"], str(it.get("platform")), esc)
            add(cohorts["persona"], str(it.get("persona")), esc)
            add(cohorts["has_media"], "true" if it.get("has_media") else "false", esc)
        return cohorts

    # --------------- ID Format Checks ---------------
    def id_format_report(self, sample_limit: int = 1000) -> Dict[str, Any]:
        """Report on ID format issues per platform (e.g., Reddit t3_ prefix)."""
        if getattr(self, "_health", None):
            return self._health.id_format_report(sample_limit)
        return {
            "reddit": {"bad": 0, "checked": 0},
            "twitter": {"bad": 0, "checked": 0},
            "threads": {"bad": 0, "checked": 0},
        }

    # --------------- Curation ---------------
    # Delegated to curation module for better organization
    def auto_curate_to_usable_posts(self, post: Dict[str, Any]) -> bool:
        """Automatically curate post to usable_posts table if it meets criteria"""
        if self._curation:
            return self._curation.auto_curate_to_usable_posts(post)
        return False

    # --------------- Publishing Table Methods ---------------
    # All publishing table operations delegate to StorageFacade (single source of truth)

    def save_transformation(self, transformation: Dict[str, Any]) -> bool:
        """Save a rewrite transformation - delegates to StorageFacade"""
        return self._storage.save_transformation(transformation)

    def save_scheduled_post(self, scheduled: Dict[str, Any]) -> bool:
        """Save a scheduled post - delegates to StorageFacade"""
        return self._storage.save_scheduled_post(scheduled)

    def update_scheduled_post(self, scheduled_id: int, updates: Dict[str, Any]) -> bool:
        """Update a scheduled post - delegates to StorageFacade"""
        return self._storage.update_scheduled_post(scheduled_id, updates)

    def save_posted_content(self, posted: Dict[str, Any]) -> bool:
        """Save posted content record - delegates to StorageFacade"""
        return self._storage.save_posted_content(posted)

    def save_rewrite_feedback(self, feedback: Dict[str, Any]) -> bool:
        """Save rewrite feedback - delegates to StorageFacade"""
        return self._storage.save_rewrite_feedback(feedback)
