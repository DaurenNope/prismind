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

    def record_post_operation(
        self,
        post_id: str,
        platform: str,
        operation: str = 'insert',
        quality_score: Optional[float] = None,
        value_score: Optional[float] = None,
        has_analysis: bool = False,
    ) -> bool:
        """Track individual post operations (insert/update) for monitoring"""
        now_iso = datetime.utcnow().isoformat()
        
        # Track to post_operations table (create if needed)
        if self._supabase is not None:
            try:
                # Ensure table exists (best-effort)
                try:
                    self._supabase.table("post_operations").select("id").limit(1).execute()
                except Exception:
                    # Table doesn't exist - create it via migration or skip
                    pass
                
                row = {
                    "post_id": post_id,
                    "platform": platform,
                    "operation": operation,  # 'insert' or 'update'
                    "quality_score": float(quality_score) if quality_score is not None else None,
                    "value_score": float(value_score) if value_score is not None else None,
                    "has_analysis": bool(has_analysis),
                    "timestamp": now_iso,
                }
                self._supabase.table("post_operations").insert(row).execute()
            except Exception:
                # Table might not exist - that's ok
                pass
        
        # Track quality metrics if quality_score is present
        if quality_score is not None:
            self._track_quality_metric(platform, quality_score, value_score, now_iso)
        
        return True

    def _track_quality_metric(
        self,
        platform: str,
        quality_score: float,
        value_score: Optional[float],
        timestamp: str,
    ) -> None:
        """Track quality metrics for monitoring and alerting"""
        if self._supabase is None:
            return
        
        try:
            # Track to quality_metrics table (create if needed)
            try:
                self._supabase.table("quality_metrics").select("id").limit(1).execute()
            except Exception:
                # Table doesn't exist - skip for now
                return
            
            row = {
                "platform": platform,
                "quality_score": float(quality_score),
                "value_score": float(value_score) if value_score is not None else None,
                "timestamp": timestamp,
            }
            self._supabase.table("quality_metrics").insert(row).execute()
        except Exception:
            # Table might not exist - that's ok
            pass

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

    # --------------- Proactive DBA Functions ---------------
    def validate_and_monitor_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """
        Proactive DBA function: Validate, check quality, and monitor every post.
        Like a human DBA would do - double-check everything.
        
        Returns:
            Dict with validation results, issues found, and monitoring status
        """
        results = {
            'validated': False,
            'quality_checked': False,
            'issues_found': [],
            'warnings': [],
            'monitored': False,
        }
        
        try:
            # 1. VALIDATE POST (double-check even if already validated)
            if self._validate_post:
                validation = self._validate_post(post, strict=True)
                results['validated'] = True
                
                if not validation.is_valid:
                    results['issues_found'].extend([
                        f"Validation failed: {err}" for err in validation.errors
                    ])
                    logger.warning(f"🔍 DB Agent: Post {post.get('post_id')} failed validation: {validation.errors}")
                
                if validation.warnings:
                    results['warnings'].extend([
                        f"Warning: {warn}" for warn in validation.warnings
                    ])
                    logger.debug(f"🔍 DB Agent: Post {post.get('post_id')} has warnings: {validation.warnings}")
            
            # 2. CHECK DATA QUALITY
            quality_issues = self._check_data_quality(post)
            results['quality_checked'] = True
            if quality_issues:
                results['issues_found'].extend(quality_issues)
                logger.warning(f"🔍 DB Agent: Post {post.get('post_id')} has quality issues: {quality_issues}")
            
            # 3. CHECK FOR COMMON COLLECTION ISSUES
            collection_issues = self._check_collection_issues(post)
            if collection_issues:
                results['issues_found'].extend(collection_issues)
                logger.warning(f"🔍 DB Agent: Post {post.get('post_id')} has collection issues: {collection_issues}")
            
            # 4. CHECK DATA INTEGRITY
            integrity_issues = self._check_data_integrity(post)
            if integrity_issues:
                results['issues_found'].extend(integrity_issues)
                logger.warning(f"🔍 DB Agent: Post {post.get('post_id')} has integrity issues: {integrity_issues}")
            
            # 5. TRACK OPERATION
            is_update = post.get('analyzed_at') or post.get('quality_score') or post.get('value_score')
            try:
                self.record_post_operation(
                    post_id=post.get('post_id'),
                    platform=post.get('platform'),
                    operation='update' if is_update else 'insert',
                    quality_score=post.get('quality_score'),
                    value_score=post.get('value_score'),
                    has_analysis=bool(post.get('analyzed_at') or post.get('ai_summary'))
                )
                results['monitored'] = True
            except Exception:
                pass
            
            # 6. ALERT ON CRITICAL ISSUES
            if results['issues_found']:
                self._alert_on_issues(post, results['issues_found'])
            
        except Exception as e:
            logger.error(f"DB Agent validate_and_monitor_post failed: {e}")
        
        return results

    def _check_data_quality(self, post: Dict[str, Any]) -> List[str]:
        """Check data quality issues"""
        issues = []
        
        # Check for truncated content
        content = post.get('content', '')
        if content and ('...' in content[-20:] or content.endswith('...')):
            issues.append("Content appears truncated (ends with ...)")
        
        # Check for placeholder content
        if content and any(placeholder in content.lower() for placeholder in [
            'scraping failed', 'extraction failed', 'content extraction in progress',
            'post from', 'placeholder', 'loading', 'error extracting'
        ]):
            issues.append("Content appears to be placeholder/error message")
        
        # Check for missing essential fields
        if not post.get('author') or post.get('author', '').lower() in ['unknown', 'n/a', '']:
            issues.append("Author is missing or placeholder")
        
        if not post.get('url') or not post.get('url', '').startswith('http'):
            issues.append("URL is missing or invalid")
        
        # Check for suspicious quality scores
        quality_score = post.get('quality_score')
        if quality_score is not None:
            try:
                qs = float(quality_score)
                if qs < 0 or qs > 10:
                    issues.append(f"Quality score out of range: {qs} (should be 0-10)")
            except (ValueError, TypeError):
                issues.append(f"Quality score is not numeric: {quality_score}")
        
        value_score = post.get('value_score')
        if value_score is not None:
            try:
                vs = float(value_score)
                if vs < 0 or vs > 10:
                    issues.append(f"Value score out of range: {vs} (should be 0-10)")
            except (ValueError, TypeError):
                issues.append(f"Value score is not numeric: {value_score}")
        
        return issues

    def _check_collection_issues(self, post: Dict[str, Any]) -> List[str]:
        """Check for common collection issues"""
        issues = []
        
        # Check for duplicate indicators
        if post.get('_is_duplicate') or post.get('duplicate'):
            issues.append("Post marked as duplicate but was saved anyway")
        
        # Check for collection errors
        if post.get('collection_error') or post.get('_collection_failed'):
            issues.append("Post has collection error flag")
        
        # Check for missing platform-specific data
        platform = post.get('platform', '').lower()
        if platform == 'threads':
            if not post.get('author_handle') and '@' not in (post.get('url', '')):
                issues.append("Threads post missing author handle")
        elif platform == 'twitter':
            if not post.get('author_handle') and not post.get('author'):
                issues.append("Twitter post missing author information")
        elif platform == 'reddit':
            if not post.get('post_id', '').startswith('t3_'):
                # Reddit IDs should have t3_ prefix
                if post.get('post_id') and not any(c in post.get('post_id', '') for c in ['/', '-']):
                    issues.append("Reddit post_id may be missing t3_ prefix")
        
        return issues

    def _check_data_integrity(self, post: Dict[str, Any]) -> List[str]:
        """Check data integrity issues"""
        issues = []
        
        # Check for conflicting timestamps
        created_at = post.get('created_at')
        analyzed_at = post.get('analyzed_at')
        if created_at and analyzed_at:
            try:
                from dateutil.parser import parse
                created = parse(str(created_at))
                analyzed = parse(str(analyzed_at))
                if analyzed < created:
                    issues.append("analyzed_at is before created_at (impossible)")
            except Exception:
                pass
        
        # Check for analysis without required fields
        if analyzed_at or post.get('ai_summary'):
            if not post.get('ai_summary') and not post.get('value_score'):
                issues.append("Post marked as analyzed but missing ai_summary and value_score")
        
        # Check for quality score without analysis
        if post.get('quality_score') and not (analyzed_at or post.get('ai_summary')):
            issues.append("Post has quality_score but no analysis timestamp")
        
        # Check for empty required fields
        if not post.get('post_id'):
            issues.append("Post missing post_id (required)")
        if not post.get('platform'):
            issues.append("Post missing platform (required)")
        
        # Check for invalid platform
        valid_platforms = ['twitter', 'reddit', 'threads', 'github', 'telegram', 'rss']
        if post.get('platform') and post.get('platform').lower() not in valid_platforms:
            issues.append(f"Invalid platform: {post.get('platform')}")
        
        return issues

    def _alert_on_issues(self, post: Dict[str, Any], issues: List[str]) -> None:
        """Alert on critical issues found"""
        if not issues:
            return
        
        try:
            # Log critical issues
            post_id = post.get('post_id', 'unknown')
            platform = post.get('platform', 'unknown')
            logger.warning(f"⚠️ DB Agent: Post {post_id} ({platform}) has {len(issues)} issues: {', '.join(issues[:3])}")
            
            # If too many issues, send alert
            if len(issues) >= 3:
                message = f"🔍 DB Agent Alert: Post {post_id} ({platform}) has {len(issues)} issues:\n" + "\n".join(f"  - {issue}" for issue in issues[:5])
                
                # Try Telegram if configured
                import os, requests
                token = os.getenv("TELEGRAM_BOT_TOKEN")
                chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_ADMIN_CHAT_ID")
                if token and chat_id:
                    try:
                        url = f"https://api.telegram.org/bot{token}/sendMessage"
                        payload = {"chat_id": chat_id, "text": message[:4000]}  # Telegram limit
                        requests.post(url, json=payload, timeout=10)
                    except Exception:
                        pass
        except Exception:
            pass

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

    def get_quality_metrics(
        self,
        platform: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000,
    ) -> Dict[str, Any]:
        """Get quality metrics for monitoring and reporting"""
        if self._supabase is None:
            return {"avg_quality": 0.0, "avg_value": 0.0, "count": 0, "low_quality_count": 0}
        
        try:
            since = (datetime.utcnow() - timedelta(hours=max(1, hours))).isoformat()
            
            query = (
                self._supabase
                .table("posts")
                .select("quality_score,value_score,platform")
                .not_.is_("quality_score", "null")
                .gt("updated_at", since)
            )
            
            if platform:
                query = query.eq("platform", platform)
            
            result = query.limit(limit).execute()
            posts = getattr(result, "data", []) or []
            
            if not posts:
                return {"avg_quality": 0.0, "avg_value": 0.0, "count": 0, "low_quality_count": 0}
            
            quality_scores = [float(p.get("quality_score", 0)) for p in posts if p.get("quality_score")]
            value_scores = [float(p.get("value_score", 0)) for p in posts if p.get("value_score")]
            
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            avg_value = sum(value_scores) / len(value_scores) if value_scores else 0.0
            low_quality_count = sum(1 for q in quality_scores if q < 5.0)
            
            return {
                "avg_quality": round(avg_quality, 2),
                "avg_value": round(avg_value, 2),
                "count": len(posts),
                "low_quality_count": low_quality_count,
                "low_quality_percentage": round((low_quality_count / len(posts)) * 100, 1) if posts else 0.0,
            }
        except Exception as e:
            logger.debug(f"get_quality_metrics failed: {e}")
            return {"avg_quality": 0.0, "avg_value": 0.0, "count": 0, "low_quality_count": 0}

    def get_quality_trends(
        self,
        platform: Optional[str] = None,
        days: int = 7,
    ) -> Dict[str, List[float]]:
        """Get quality score trends over time"""
        if self._supabase is None:
            return {"quality": [], "value": [], "timestamps": []}
        
        try:
            since = (datetime.utcnow() - timedelta(days=max(1, days))).isoformat()
            
            # Try updated_at first, fallback to analyzed_at
            query = (
                self._supabase
                .table("posts")
                .select("quality_score,value_score,updated_at,analyzed_at")
                .not_.is_("quality_score", "null")
            )
            
            # Filter by date - try updated_at first, then analyzed_at
            try:
                query = query.or_(f"updated_at.gt.{since},analyzed_at.gt.{since}")
            except Exception:
                # Fallback: just check analyzed_at
                query = query.gt("analyzed_at", since)
            
            query = query.order("updated_at", desc=False).limit(1000)
            
            if platform:
                query = query.eq("platform", platform)
            
            result = query.execute()
            posts = getattr(result, "data", []) or []
            
            quality_scores = [float(p.get("quality_score", 0)) for p in posts if p.get("quality_score")]
            value_scores = [float(p.get("value_score", 0)) for p in posts if p.get("value_score")]
            timestamps = [p.get("updated_at") or p.get("analyzed_at", "") for p in posts]
            
            return {
                "quality": quality_scores,
                "value": value_scores,
                "timestamps": timestamps,
            }
        except Exception as e:
            logger.debug(f"get_quality_trends failed: {e}")
            return {"quality": [], "value": [], "timestamps": []}

    def backfill_quality_metrics(self, limit: int = 1000) -> int:
        """Backfill quality metrics for existing posts"""
        if self._supabase is None:
            return 0
        
        try:
            # Get posts with quality scores but not yet tracked
            posts = (
                self._supabase
                .table("posts")
                .select("post_id,platform,quality_score,value_score,analyzed_at,ai_summary")
                .not_.is_("quality_score", "null")
                .limit(limit)
                .execute()
            )
            
            posts_data = getattr(posts, "data", []) or []
            tracked = 0
            
            for post in posts_data:
                try:
                    self.record_post_operation(
                        post_id=post.get("post_id"),
                        platform=post.get("platform"),
                        operation="update",  # Existing posts
                        quality_score=post.get("quality_score"),
                        value_score=post.get("value_score"),
                        has_analysis=bool(post.get("analyzed_at") or post.get("ai_summary"))
                    )
                    tracked += 1
                except Exception:
                    continue
            
            return tracked
        except Exception as e:
            logger.debug(f"backfill_quality_metrics failed: {e}")
            return 0

    def audit_database(self, limit: int = 100, platforms: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Proactive DBA function: Audit database for issues.
        Like a human DBA would do - check everything.
        
        Returns:
            Dict with audit results, issues found, and recommendations
        """
        results = {
            'posts_checked': 0,
            'issues_found': [],
            'warnings': [],
            'critical_issues': [],
            'recommendations': [],
        }
        
        try:
            # Get recent posts to audit
            if self._supabase:
                query = (
                    self._supabase
                    .table("posts")
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
            
            results['posts_checked'] = len(posts)
            
            # Audit each post
            for post in posts:
                # Validate and check quality
                audit_result = self.validate_and_monitor_post(post)
                
                if audit_result.get('issues_found'):
                    results['issues_found'].extend(audit_result['issues_found'])
                    
                    # Categorize issues
                    critical = [issue for issue in audit_result['issues_found'] if any(
                        keyword in issue.lower() for keyword in [
                            'missing', 'invalid', 'failed', 'impossible', 'error'
                        ]
                    )]
                    if critical:
                        results['critical_issues'].append({
                            'post_id': post.get('post_id'),
                            'platform': post.get('platform'),
                            'issues': critical
                        })
                
                if audit_result.get('warnings'):
                    results['warnings'].extend(audit_result['warnings'])
            
            # Generate recommendations
            if results['critical_issues']:
                results['recommendations'].append(
                    f"Found {len(results['critical_issues'])} posts with critical issues. Review and fix them."
                )
            
            if len(results['issues_found']) > len(posts) * 0.3:
                results['recommendations'].append(
                    f"High issue rate ({len(results['issues_found'])}/{len(posts)}). Review collection process."
                )
            
            # Check for common patterns
            placeholder_count = sum(1 for post in posts if any(
                placeholder in (post.get('content', '') or '').lower() 
                for placeholder in ['scraping failed', 'extraction failed', 'placeholder']
            ))
            if placeholder_count > 0:
                results['recommendations'].append(
                    f"Found {placeholder_count} posts with placeholder content. Check extractors."
                )
            
            truncated_count = sum(1 for post in posts if (post.get('content', '') or '').endswith('...'))
            if truncated_count > 0:
                results['recommendations'].append(
                    f"Found {truncated_count} posts with truncated content. Check extractors."
                )
            
        except Exception as e:
            logger.error(f"DB Agent audit_database failed: {e}")
        
        return results

    def check_recent_posts_quality(self, hours: int = 24, limit: int = 100) -> Dict[str, Any]:
        """
        Check quality of recently collected posts.
        Like a DBA monitoring recent activity.
        """
        results = {
            'posts_checked': 0,
            'quality_issues': [],
            'collection_issues': [],
            'integrity_issues': [],
        }
        
        try:
            since = (datetime.utcnow() - timedelta(hours=max(1, hours))).isoformat()
            
            if self._supabase:
                query = (
                    self._supabase
                    .table("posts")
                    .select("*")
                    .gt("created_at", since)
                    .order("created_at", desc=True)
                    .limit(limit)
                )
                result = query.execute()
                posts = getattr(result, "data", []) or []
            else:
                return results
            
            results['posts_checked'] = len(posts)
            
            for post in posts:
                # Check data quality
                quality_issues = self._check_data_quality(post)
                if quality_issues:
                    results['quality_issues'].append({
                        'post_id': post.get('post_id'),
                        'platform': post.get('platform'),
                        'issues': quality_issues
                    })
                
                # Check collection issues
                collection_issues = self._check_collection_issues(post)
                if collection_issues:
                    results['collection_issues'].append({
                        'post_id': post.get('post_id'),
                        'platform': post.get('platform'),
                        'issues': collection_issues
                    })
                
                # Check integrity
                integrity_issues = self._check_data_integrity(post)
                if integrity_issues:
                    results['integrity_issues'].append({
                        'post_id': post.get('post_id'),
                        'platform': post.get('platform'),
                        'issues': integrity_issues
                    })
            
        except Exception as e:
            logger.error(f"DB Agent check_recent_posts_quality failed: {e}")
        
        return results

    def cleanup_bad_posts(
        self,
        limit: int = 1000,
        platforms: Optional[List[str]] = None,
        min_issues: int = 2,
        dry_run: bool = True
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
            'posts_checked': 0,
            'bad_posts_found': 0,
            'posts_deleted': 0,
            'posts_failed': 0,
            'bad_posts': [],
            'errors': [],
        }
        
        try:
            # Get all posts to check
            if self._supabase:
                query = (
                    self._supabase
                    .table("posts")
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
            
            results['posts_checked'] = len(posts)
            
            # Check each post
            for post in posts:
                # Validate and check for issues
                audit_result = self.validate_and_monitor_post(post)
                issues = audit_result.get('issues_found', [])
                
                # Check if post is "bad" (has critical issues)
                # BE CONSERVATIVE: Only delete clearly broken posts
                is_bad = False
                critical_keywords = [
                    'placeholder', 'truncated', 'missing', 'invalid', 'failed',
                    'error', 'impossible', 'scraping failed', 'extraction failed'
                ]
                
                # Count critical issues (excluding Reddit post_id format warnings - those might be false positives)
                critical_issues = [issue for issue in issues if any(
                    keyword in issue.lower() for keyword in critical_keywords
                ) and 'reddit post_id' not in issue.lower()]  # Exclude Reddit post_id format warnings
                
                # Also check for placeholder content directly (MOST IMPORTANT)
                content = post.get('content', '')
                if content:
                    content_lower = content.lower()
                    # Only flag if content is clearly a placeholder/error
                    if any(placeholder in content_lower for placeholder in [
                        'scraping failed', 'extraction failed', 'content extraction in progress',
                        'post from', 'placeholder', 'error extracting'
                    ]):
                        is_bad = True
                
                # Check for truncated content (ends with ...) - but be careful, some posts legitimately end with ...
                # Only flag if content is very short and ends with ...
                if content and len(content) < 50 and content.endswith('...'):
                    is_bad = True
                
                # Check for missing essential fields (MOST IMPORTANT)
                # Only delete if BOTH author AND url are missing/invalid
                has_valid_author = post.get('author') and post.get('author', '').lower() not in ['unknown', 'n/a', '']
                has_valid_url = post.get('url') and post.get('url', '').startswith('http')
                
                if not has_valid_author and not has_valid_url:
                    is_bad = True  # Both missing = definitely bad
                elif not has_valid_author and not content:
                    is_bad = True  # No author and no content = bad
                
                # If has enough critical issues (excluding Reddit format warnings), mark as bad
                if len(critical_issues) >= min_issues:
                    is_bad = True
                
                if is_bad:
                    results['bad_posts_found'] += 1
                    results['bad_posts'].append({
                        'id': post.get('id'),
                        'post_id': post.get('post_id'),
                        'platform': post.get('platform'),
                        'author': post.get('author'),
                        'content_preview': (content or '')[:100],
                        'issues': issues,
                        'critical_issues': critical_issues,
                    })
                    
                    # Delete if not dry run
                    if not dry_run:
                        try:
                            # Delete from Supabase
                            if self._supabase and post.get('id'):
                                self._supabase.table("posts").delete().eq("id", post.get('id')).execute()
                            
                            # Delete from SQLite
                            if self._sqlite and post.get('post_id'):
                                try:
                                    cur = self._sqlite.conn.cursor()
                                    cur.execute("DELETE FROM posts WHERE post_id = ?", (post.get('post_id'),))
                                    self._sqlite.conn.commit()
                                except Exception:
                                    pass
                            
                            results['posts_deleted'] += 1
                            logger.info(f"🗑️ Deleted bad post: {post.get('post_id')} ({post.get('platform')})")
                        except Exception as e:
                            results['posts_failed'] += 1
                            results['errors'].append(f"Failed to delete {post.get('post_id')}: {e}")
                            logger.error(f"Failed to delete post {post.get('post_id')}: {e}")
            
        except Exception as e:
            logger.error(f"DB Agent cleanup_bad_posts failed: {e}")
            results['errors'].append(str(e))
        
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
        report: Dict[str, Any] = {"reddit": {"bad": 0, "checked": 0}, "twitter": {"bad": 0, "checked": 0}, "threads": {"bad": 0, "checked": 0}}
        if not self._supabase:
            return report
        try:
            r = (
                self._supabase
                .table("posts")
                .select("post_id,platform")
                .order("created_at", desc=True)
                .limit(sample_limit)
                .execute()
            )
            for row in (getattr(r, "data", []) or []):
                plat = (row.get("platform") or "").lower()
                pid = (row.get("post_id") or "").strip()
                if plat not in report:
                    continue
                report[plat]["checked"] += 1
                if plat == "reddit":
                    if pid:
                        # Treat bare base36 IDs as acceptable (normalization needed but not "bad")
                        if pid.startswith("t3_"):
                            pass  # OK
                        else:
                            base = pid
                            # Heuristic: Reddit base36 IDs are alphanumeric (no underscore) and short
                            if not base.isalnum() or len(base) > 12:
                                report[plat]["bad"] += 1
                else:
                    # Add other platform rules as needed
                    pass
        except Exception:
            pass
        return report

