from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseHealth:
    """
    Health and reporting utilities extracted from DatabaseAgent.
    """

    def __init__(
        self,
        supabase_client: Any = None,
        sqlite_adapter: Any = None,
        get_last_post_id_fn: Optional[Callable[[str], Optional[str]]] = None,
    ) -> None:
        self._supabase = supabase_client
        self._sqlite = sqlite_adapter
        self._get_last_post_id = get_last_post_id_fn

    # --------------- Health / Maintenance ---------------
    def health_report(self) -> Dict[str, Any]:
        """Return a quick health summary for DB components."""
        supabase_ok = False
        sqlite_ok = False
        latest_per_platform: Dict[str, Optional[str]] = {}
        sync_status = {}

        # Supabase
        if self._supabase is not None:
            try:
                r = (
                    self._supabase.table("posts")
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
                # Get sync status
                if hasattr(self._sqlite, "get_sync_status"):
                    sync_status = self._sqlite.get_sync_status()
            except Exception as e:
                logger.warning(f"SQLite health check failed: {e}")

        # Latest IDs (best-effort)
        if self._get_last_post_id:
            for plat in ("twitter", "reddit", "threads"):
                try:
                    latest_per_platform[plat] = self._get_last_post_id(plat)
                except Exception:
                    latest_per_platform[plat] = None

        return {
            "supabase_ok": supabase_ok,
            "sqlite_ok": sqlite_ok,
            "latest_ids": latest_per_platform,
            "sync_status": sync_status,
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
                        self._supabase.table("posts")
                        .select("id", count="exact")
                        .eq("platform", plat)
                        .gt("created_at", since)
                        .execute()
                    )
                    c = getattr(r, "count", None)
                    if isinstance(c, int):
                        counts[plat] = c
                except Exception as e:
                    logger.debug(f"recent_activity: failed to get count for {plat}: {e}")
                    continue
        except Exception as e:
            logger.debug(f"recent_activity failed: {e}")
        return counts

    def id_format_report(self, sample_limit: int = 1000) -> Dict[str, Any]:
        """Report on ID format issues per platform (e.g., Reddit t3_ prefix)."""
        report: Dict[str, Any] = {
            "reddit": {"bad": 0, "checked": 0},
            "twitter": {"bad": 0, "checked": 0},
            "threads": {"bad": 0, "checked": 0},
        }
        if not self._supabase:
            return report
        try:
            r = (
                self._supabase.table("posts")
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
                        if pid.startswith("t3_"):
                            pass
                        else:
                            base = pid
                            if not base.isalnum() or len(base) > 12:
                                report[plat]["bad"] += 1
                else:
                    # Add other platform rules as needed
                    pass
        except Exception as e:
            logger.debug(f"id_format_report failed: {e}")
        return report


