#!/usr/bin/env python3
"""
DatabaseAgent

Centralized database operations layer for PrisMind.
 - Supabase is the primary source of truth
 - SQLite is a local cache/mirror for resilience and fast reads
 - Validates schema-related fields and post payloads
 - Applies duplicate checking and normalized IDs/URLs
 - Provides health and recent-activity reports
 - Encapsulates retry/backoff for transient failures
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseAgent:
    def __init__(self) -> None:
        # Primary: Supabase
        try:
            from src.database.manager import SupabaseManager  # lazy import
            self._supabase_manager = SupabaseManager()
            self._supabase = self._supabase_manager.client
        except Exception:
            self._supabase_manager = None
            self._supabase = None

        # Local cache: SQLite
        try:
            from src.storage.sqlite_adapter import SQLiteAdapter
            self._sqlite = SQLiteAdapter()
        except Exception:
            self._sqlite = None

        # Duplicate detection (uses storage facade-like logic but scoped here)
        try:
            from src.utils.duplicate_detector import DuplicateDetector
            self._dupes = DuplicateDetector(db_manager=None, supabase_manager=self._supabase_manager)
        except Exception:
            self._dupes = None

        # Post validation / insertion mapping
        try:
            from src.services.supabase.post_inserter import PostInserter
            from src.utils.post_validator import validate_post
            self._validate_post = validate_post
            self._post_inserter = PostInserter(self._supabase, self._dupes) if self._supabase else None
        except Exception:
            self._validate_post = None
            self._post_inserter = None

    # --------------- Metrics / Freshness ---------------
    def ensure_metrics_table(self) -> None:
        """Ensure local cache has the metrics table. Supabase handled via migration."""
        if self._sqlite is None:
            return
        try:
            cur = self._sqlite.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS collection_metrics (
                  platform TEXT PRIMARY KEY,
                  last_run_at TEXT,
                  last_count INTEGER DEFAULT 0,
                  last_success BOOLEAN DEFAULT FALSE,
                  failure_reason TEXT,
                  consecutive_failures INTEGER DEFAULT 0,
                  updated_at TEXT
                )
                """
            )
            self._sqlite.conn.commit()
        except Exception:
            pass

    def get_collection_metrics(self, platform: str) -> Optional[Dict[str, Any]]:
        # Prefer Supabase
        if self._supabase is not None:
            try:
                r = (
                    self._supabase
                    .table("collection_metrics")
                    .select("*")
                    .eq("platform", platform)
                    .limit(1)
                    .execute()
                )
                if getattr(r, "data", None):
                    return r.data[0]
            except Exception:
                pass
        # Fallback to SQLite
        if self._sqlite is not None:
            try:
                cur = self._sqlite.conn.cursor()
                cur.execute(
                    "SELECT platform,last_run_at,last_count,last_success,failure_reason,consecutive_failures,updated_at FROM collection_metrics WHERE platform=? LIMIT 1",
                    (platform,),
                )
                row = cur.fetchone()
                if row:
                    cols = [
                        "platform",
                        "last_run_at",
                        "last_count",
                        "last_success",
                        "failure_reason",
                        "consecutive_failures",
                        "updated_at",
                    ]
                    return dict(zip(cols, row))
            except Exception:
                pass
        return None

    def record_collection_result(
        self,
        platform: str,
        count: int,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ) -> bool:
        now_iso = datetime.utcnow().isoformat()
        # Upsert to Supabase (primary)
        if self._supabase is not None:
            try:
                # compute new consecutive_failures
                prev = self.get_collection_metrics(platform) or {}
                prev_failures = int(prev.get("consecutive_failures") or 0)
                row = {
                    "platform": platform,
                    "last_run_at": now_iso,
                    "last_count": int(count),
                    "last_success": bool(success),
                    "failure_reason": failure_reason,
                    "consecutive_failures": 0 if success else (prev_failures + 1),
                    "updated_at": now_iso,
                }
                self._supabase.table("collection_metrics").upsert(row, on_conflict="platform").execute()
            except Exception:
                return False
        # Mirror to SQLite (best-effort)
        if self._sqlite is not None:
            try:
                self.ensure_metrics_table()
                cur = self._sqlite.conn.cursor()
                cur.execute(
                    """
                    INSERT INTO collection_metrics(platform,last_run_at,last_count,last_success,failure_reason,consecutive_failures,updated_at)
                    VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(platform) DO UPDATE SET
                      last_run_at=excluded.last_run_at,
                      last_count=excluded.last_count,
                      last_success=excluded.last_success,
                      failure_reason=excluded.failure_reason,
                      consecutive_failures=excluded.consecutive_failures,
                      updated_at=excluded.updated_at
                    """,
                    (
                        platform,
                        now_iso,
                        int(count),
                        1 if success else 0,
                        failure_reason,
                        0 if success else (int((self.get_collection_metrics(platform) or {}).get("consecutive_failures") or 0) + 1),
                        now_iso,
                    ),
                )
                self._sqlite.conn.commit()
            except Exception:
                pass
        return True

    def detect_stale_collections(self, thresholds_minutes: Optional[Dict[str, int]] = None) -> Dict[str, Dict[str, Any]]:
        thresholds = thresholds_minutes or {"twitter": 180, "reddit": 180, "threads": 180}
        stale: Dict[str, Dict[str, Any]] = {}
        now = datetime.utcnow()
        for plat, mins in thresholds.items():
            m = self.get_collection_metrics(plat) or {}
            last = m.get("last_run_at")
            last_dt = None
            if isinstance(last, str):
                try:
                    last_dt = datetime.fromisoformat(last.replace("Z", ""))
                except Exception:
                    last_dt = None
            age_min = (now - last_dt).total_seconds() / 60 if last_dt else float("inf")
            if age_min > mins:
                stale[plat] = {"age_minutes": int(age_min), "threshold": mins, "metrics": m}
        return stale

    def notify_stale(self, stale: Dict[str, Dict[str, Any]]) -> None:
        if not stale:
            return
        try:
            lines = ["⚠️ Collection stale:"] + [f" - {k}: {v['age_minutes']}m (> {v['threshold']}m)" for k, v in stale.items()]
            message = "\n".join(lines)

            # Try Telegram first if configured
            import os, requests
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID")
            if token and chat_id:
                try:
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    payload = {"chat_id": chat_id, "text": message}
                    requests.post(url, json=payload, timeout=10)
                except Exception:
                    logger.warning(message)
            else:
                # Fallback to logs
                logger.warning(message)
        except Exception:
            pass

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
                self.record_collection_result(p, 0, success=False, failure_reason=str(e)[:200])
                results[p] = 0
        return results

    # --------------- Core Operations ---------------
    def save_post(self, post: Dict[str, Any], retries: int = 3, backoff_seconds: float = 1.5) -> bool:
        """
        Save a post with Supabase as primary and SQLite as cache.
        - Validates the post structure (strict) before Supabase insert
        - Duplicate checks (URL/content hash/platform-specific) if available
        - Retries transient Supabase failures with backoff
        - Mirrors to SQLite cache on success (best-effort)
        """
        try:
            # Sanity
            if not isinstance(post, dict):
                logger.error("save_post: invalid post type")
                return False

            # Duplicate short-circuit (best-effort)
            try:
                if self._dupes:
                    url = post.get("url", "")
                    content = post.get("content", "")
                    if url and self._dupes.is_duplicate_url(url):
                        return False
                    if content and self._dupes.is_duplicate_content(content):
                        return False
                    if self._dupes.is_duplicate(post):
                        return False
            except Exception:
                pass

            # Validate for Supabase schema (strict)
            if self._validate_post is not None:
                validation = self._validate_post(post, strict=True)
                if not getattr(validation, "is_valid", True):
                    logger.error("❌ DB Agent: Post validation failed for Supabase")
                    return False

            # Primary insert
            supabase_ok = False
            attempt = 0
            last_error: Optional[Exception] = None
            while attempt < max(1, retries):
                try:
                    if self._post_inserter is None:
                        # No Supabase configured
                        break
                    result = self._post_inserter.insert_post(post)
                    supabase_ok = bool(result)
                    if supabase_ok:
                        break
                except Exception as e:
                    last_error = e
                attempt += 1
                if attempt < retries:
                    time.sleep(backoff_seconds * attempt)

            if not supabase_ok:
                if last_error:
                    logger.warning(f"Supabase insert failed after {attempt} attempts: {last_error}")
                return False

            # Cache locally (best-effort)
            if self._sqlite is not None:
                try:
                    self._sqlite.save_post(post)
                except Exception:
                    pass

            return True

        except Exception as e:
            logger.error(f"DB Agent save_post error: {e}")
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
                self._supabase
                .table("posts")
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
        except Exception:
            return None
        return None

    # --------------- Health / Maintenance ---------------
    def health_report(self) -> Dict[str, Any]:
        """Return a quick health summary for DB components."""
        supabase_ok = False
        sqlite_ok = False
        latest_per_platform: Dict[str, Optional[str]] = {}

        # Supabase
        if self._supabase is not None:
            try:
                r = (
                    self._supabase
                    .table("posts")
                    .select("id,created_at")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                supabase_ok = True if r is not None else False
            except Exception as e:
                logger.warning(f"Supabase health check failed: {e}")

        # SQLite
        if self._sqlite is not None:
            try:
                _ = self._sqlite.get_posts(limit=1)
                sqlite_ok = True
            except Exception as e:
                logger.warning(f"SQLite health check failed: {e}")

        # Latest IDs (best-effort)
        for plat in ("twitter", "reddit", "threads"):
            latest_per_platform[plat] = self.get_last_post_id(plat)

        return {
            "supabase_ok": supabase_ok,
            "sqlite_ok": sqlite_ok,
            "latest_ids": latest_per_platform,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def recent_activity(self, minutes: int = 60) -> Dict[str, int]:
        """Counts posts created in the last N minutes (Supabase)."""
        counts: Dict[str, int] = {"twitter": 0, "reddit": 0, "threads": 0}
        if not self._supabase:
            return counts
        try:
            since = (datetime.utcnow() - timedelta(minutes=max(1, minutes))).isoformat()
            for plat in counts.keys():
                try:
                    r = (
                        self._supabase
                        .table("posts")
                        .select("id", count='exact')
                        .eq("platform", plat)
                        .gt("created_at", since)
                        .execute()
                    )
                    # Some clients return count on r.count; data may be []
                    c = getattr(r, 'count', None)
                    if isinstance(c, int):
                        counts[plat] = c
                except Exception:
                    continue
        except Exception:
            pass
        return counts


    # --------------- Posted Performance APIs ---------------
    def _get_posted_content_id(self, platform: str, platform_post_id: str) -> Optional[int]:
        if not self._supabase:
            return None
        try:
            r = (
                self._supabase
                .table("posted_content")
                .select("id")
                .eq("platform", platform)
                .eq("platform_post_id", platform_post_id)
                .limit(1)
                .execute()
            )
            if getattr(r, "data", None):
                return int(r.data[0]["id"])
        except Exception:
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
            r = self._supabase.table("posted_content").upsert(row, on_conflict="platform,platform_post_id").execute()
            if getattr(r, "data", None):
                return r.data[0]
        except Exception:
            return None
        return None

    def _compute_engagement_score(self, views: int, likes: int, comments: int, shares: int, bookmarks: int) -> float:
        try:
            num = likes + 2 * comments + 3 * shares + 2 * bookmarks
            den = max(1, views)
            return float(num) / float(den)
        except Exception:
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
            self._supabase.table("posted_metrics").upsert(row, on_conflict="posted_content_id,snapshot_at").execute()

            # Recompute aggregates on posted_content
            agg = (
                self._supabase
                .rpc(
                    "exec",
                    {
                        "sql": f"select coalesce(sum(views),0) v, coalesce(sum(likes),0) l, coalesce(sum(comments),0) c, coalesce(sum(shares),0) s, coalesce(sum(bookmarks),0) b from posted_metrics where posted_content_id={pc_id}"
                    },
                )
            )
            # Fallback if RPC not available: fetch and sum in client
            if not getattr(agg, "data", None):
                res = (
                    self._supabase
                    .table("posted_metrics")
                    .select("views,likes,comments,shares,bookmarks")
                    .eq("posted_content_id", pc_id)
                    .execute()
                )
                v = l = c = s = b = 0
                for r in (res.data or []):
                    v += int(r.get("views") or 0)
                    l += int(r.get("likes") or 0)
                    c += int(r.get("comments") or 0)
                    s += int(r.get("shares") or 0)
                    b += int(r.get("bookmarks") or 0)
            else:
                d0 = agg.data[0] if isinstance(agg.data, list) and agg.data else agg.data
                v = int(d0.get("v") or 0)
                l = int(d0.get("l") or 0)
                c = int(d0.get("c") or 0)
                s = int(d0.get("s") or 0)
                b = int(d0.get("b") or 0)

            escore = self._compute_engagement_score(v, l, c, s, b)
            self._supabase.table("posted_content").update({
                "total_views": v,
                "total_likes": l,
                "total_comments": c,
                "total_shares": s,
                "total_bookmarks": b,
                "engagement_score": escore,
            }).eq("id", pc_id).execute()
            return True
        except Exception:
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
                self._supabase
                .table("posted_content")
                .select("*")
                .gt("posted_at", (datetime.utcnow() - timedelta(minutes=max(1, since_minutes))).isoformat())
                .order("engagement_score", desc=True)
                .limit(max(1, min(100, limit)))
            )
            if platform:
                q = q.eq("platform", platform)
            if persona:
                q = q.eq("persona", persona)
            r = q.execute()
            return getattr(r, "data", []) or []
        except Exception:
            return []

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

