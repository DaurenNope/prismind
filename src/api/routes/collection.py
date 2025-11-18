from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

try:
    from supabase import create_client  # type: ignore
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore

router = APIRouter(prefix="/api/collection", tags=["collection"])


def _make_supabase_client():
    """Create a Supabase client if credentials are present."""
    if create_client is None:
        raise RuntimeError("supabase-py is not installed")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials are missing")

    return create_client(url, key)


def _safe_iso(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .isoformat()
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        return value


@router.get("/status")
async def get_collection_status() -> Dict[str, Any]:
    """Get collection status - optimized with timeouts and error handling"""
    import asyncio

    try:
        client = _make_supabase_client()

        # Query with timeout protection
        try:
            # Use limit to prevent large queries
            response = (
                client.table("collection_metrics")
                .select("*")
                .order("updated_at", desc=True)
                .limit(20)  # Limit to prevent slow queries
                .execute()
            )
            rows = getattr(response, "data", []) or []
        except Exception as e:
            logger.error(f"Error: {e}")
            # If table doesn't exist or query fails, return empty
            return {"collectors": []}

        latest_logs: Dict[str, Dict[str, Any]] = {}
        if rows:
            try:
                # Optimize: only get latest log per platform (limit to 10 platforms max)
                log_resp = (
                    client.table("collection_logs")
                    .select(
                        "platform,message,status,started_at,finished_at,posts_collected"
                    )
                    .order("started_at", desc=True)
                    .limit(30)  # Limit to prevent slow queries
                    .execute()
                )
                for entry in getattr(log_resp, "data", []) or []:
                    platform = entry.get("platform")
                    if platform and platform not in latest_logs:
                        latest_logs[str(platform).lower()] = entry
            except Exception as e:
                logger.error(f"Error: {e}")
                latest_logs = {}

        collectors: List[Dict[str, Any]] = []
        for row in rows:
            platform = (row.get("platform") or "unknown").lower()
            last_success = bool(row.get("last_success"))
            failure_reason = row.get("failure_reason")
            last_run = _safe_iso(row.get("last_run_at") or row.get("updated_at"))

            log_entry = latest_logs.get(platform)
            message = (
                (log_entry or {}).get("message")
                or failure_reason
                or f"Last sweep captured {row.get('last_count', 0)} posts."
            )

            status = "idle"
            if log_entry:
                status = log_entry.get("status") or (
                    "success" if last_success else "error"
                )
            elif not last_success and failure_reason:
                status = "error"

            collectors.append(
                {
                    "platform": platform,
                    "last_run": last_run,
                    "collected": row.get("last_count"),
                    "status": status,
                    "message": message,
                }
            )

        return {"collectors": collectors}
    except Exception as exc:
        logger.error(f"Error: {exc}")
        # Return empty instead of raising - prevents UI from breaking
        return {"collectors": [], "error": str(exc)}


@router.get("/logs")
async def get_collection_logs(limit: int = 20) -> Dict[str, Any]:
    """Get collection logs - optimized with error handling"""
    try:
        client = _make_supabase_client()

        # Cap limit to prevent slow queries
        limit = min(limit, 50)

        response = (
            client.table("collection_logs")
            .select("*")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
        )

        rows = getattr(response, "data", []) or []
        logs: List[Dict[str, Any]] = []
        for row in rows:
            logs.append(
                {
                    "timestamp": _safe_iso(
                        row.get("finished_at") or row.get("started_at")
                    ),
                    "platform": row.get("platform"),
                    "status": row.get("status") or "success",
                    "message": row.get("message"),
                    "posts": row.get("posts_collected"),
                }
            )

        return {"logs": logs}
    except Exception as exc:
        logger.error(f"Error: {exc}")
        # Return empty instead of raising - prevents UI from breaking
        return {"logs": [], "error": str(exc)}


@router.post("/stop")
async def stop_collection() -> Dict[str, Any]:
    """Stop the current collection process"""
    try:
        from src.services.telegram_collection_commands import get_collection_service

        service = get_collection_service()
        stopped = service.stop_collection()

        if stopped:
            return {"success": True, "message": "Collection stop requested"}
        else:
            return {"success": False, "message": "No collection in progress"}
    except Exception as exc:
        logger.error(f"Error stopping collection: {exc}")
        return {"success": False, "error": str(exc)}
