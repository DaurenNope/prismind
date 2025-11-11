#!/usr/bin/env python3
"""
Database Metrics Module

Handles collection metrics, quality metrics, and performance tracking.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseMetrics:
    """Handles metrics tracking for database operations"""

    def __init__(self, supabase=None, sqlite=None, record_post_operation_fn=None):
        self._supabase = supabase
        self._sqlite = sqlite
        self._record_post_operation = record_post_operation_fn

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
        """Get collection metrics for a platform"""
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
            except Exception as e:
                logger.debug(f"get_collection_metrics from Supabase failed for {platform}: {e}")
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
            from datetime import timedelta
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
    ) -> Dict[str, list]:
        """Get quality score trends over time"""
        if self._supabase is None:
            return {"quality": [], "value": [], "timestamps": []}
        
        try:
            from datetime import timedelta
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
        if self._supabase is None or not self._record_post_operation:
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
                    self._record_post_operation(
                        post_id=post.get("post_id"),
                        platform=post.get("platform"),
                        operation="update",  # Existing posts
                        quality_score=post.get("quality_score"),
                        value_score=post.get("value_score"),
                        has_analysis=bool(post.get("analyzed_at") or post.get("ai_summary"))
                    )
                    tracked += 1
                except Exception as e:
                    logger.debug(f"backfill_quality_metrics: failed to track post {post.get('post_id')}: {e}")
                    continue
            
            return tracked
        except Exception as e:
            logger.debug(f"backfill_quality_metrics failed: {e}")
            return 0

    def record_collection_result(
        self,
        platform: str,
        count: int,
        success: bool = True,
        failure_reason: Optional[str] = None,
    ) -> bool:
        """Record collection result for a platform"""
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

    def get_quality_metrics(
        self,
        platform: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get quality metrics for a platform or all platforms"""
        if self._supabase is None:
            return {"metrics": [], "summary": {}}
        
        try:
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            
            query = (
                self._supabase
                .table("quality_metrics")
                .select("*")
                .gte("timestamp", cutoff)
                .order("timestamp", desc=True)
                .limit(limit)
            )
            
            if platform:
                query = query.eq("platform", platform)
            
            response = query.execute()
            metrics = getattr(response, "data", []) or []
            
            # Calculate summary statistics
            if metrics:
                avg_quality = sum(m.get("quality_score", 0) for m in metrics) / len(metrics)
                avg_value = sum(m.get("value_score", 0) for m in metrics if m.get("value_score")) / max(1, sum(1 for m in metrics if m.get("value_score")))
                summary = {
                    "count": len(metrics),
                    "avg_quality_score": avg_quality,
                    "avg_value_score": avg_value,
                    "platform": platform or "all"
                }
            else:
                summary = {
                    "count": 0,
                    "avg_quality_score": 0.0,
                    "avg_value_score": 0.0,
                    "platform": platform or "all"
                }
            
            return {"metrics": metrics, "summary": summary}
        except Exception as e:
            logger.debug(f"get_quality_metrics failed: {e}")
            return {"metrics": [], "summary": {}}

    def get_quality_trends(
        self,
        platform: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get quality trends over time"""
        if self._supabase is None:
            return {"trends": []}
        
        try:
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            query = (
                self._supabase
                .table("quality_metrics")
                .select("*")
                .gte("timestamp", cutoff)
                .order("timestamp", desc=True)
            )
            
            if platform:
                query = query.eq("platform", platform)
            
            response = query.execute()
            metrics = getattr(response, "data", []) or []
            
            # Group by day
            trends = {}
            for m in metrics:
                timestamp = m.get("timestamp", "")
                if timestamp:
                    day = timestamp[:10]  # YYYY-MM-DD
                    if day not in trends:
                        trends[day] = {"quality_scores": [], "value_scores": []}
                    trends[day]["quality_scores"].append(m.get("quality_score", 0))
                    if m.get("value_score"):
                        trends[day]["value_scores"].append(m.get("value_score", 0))
            
            # Calculate daily averages
            trend_list = []
            for day, data in sorted(trends.items()):
                avg_quality = sum(data["quality_scores"]) / len(data["quality_scores"]) if data["quality_scores"] else 0
                avg_value = sum(data["value_scores"]) / len(data["value_scores"]) if data["value_scores"] else 0
                trend_list.append({
                    "date": day,
                    "avg_quality_score": avg_quality,
                    "avg_value_score": avg_value,
                    "count": len(data["quality_scores"])
                })
            
            return {"trends": trend_list}
        except Exception as e:
            logger.debug(f"get_quality_trends failed: {e}")
            return {"trends": []}

    def backfill_quality_metrics(self, limit: int = 1000) -> int:
        """Backfill quality metrics from posts table"""
        if self._supabase is None:
            return 0
        
        try:
            # Get posts with quality scores
            response = (
                self._supabase
                .table("posts")
                .select("post_id,platform,quality_score,value_score,created_at")
                .not_.is_("quality_score", "null")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            
            posts = getattr(response, "data", []) or []
            inserted = 0
            
            for post in posts:
                try:
                    quality_score = post.get("quality_score")
                    value_score = post.get("value_score")
                    platform = post.get("platform")
                    created_at = post.get("created_at")
                    
                    if quality_score and platform and created_at:
                        row = {
                            "platform": platform,
                            "quality_score": float(quality_score),
                            "value_score": float(value_score) if value_score else None,
                            "timestamp": created_at,
                        }
                        self._supabase.table("quality_metrics").insert(row).execute()
                        inserted += 1
                except Exception:
                    continue
            
            return inserted
        except Exception as e:
            logger.debug(f"backfill_quality_metrics failed: {e}")
            return 0

