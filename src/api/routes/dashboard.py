"""
Dashboard API Routes
Provides enriched telemetry for the Beyondlines mission control UI.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from src.utils.logging_config import get_logger

try:
    from supabase import create_client  # type: ignore
except ImportError:  # pragma: no cover
    logger.error(f"Error: {e}")
    create_client = None  # type: ignore


logger = get_logger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _make_supabase_client():
    """
    Create a Supabase client using either the service role key (preferred)
    or the anon key.
    """
    if create_client is None:
        raise RuntimeError("supabase-py is not installed")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials are missing")

    return create_client(url, key)


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except Exception as e:
        logger.error(f"Error: {e}")
        return None


def _humanize_delta(reference: datetime, target: datetime) -> str:
    delta = reference - target
    suffix = "ago"
    if delta.total_seconds() < 0:
        delta = -delta
        suffix = "from now"

    minutes = int(delta.total_seconds() // 60)
    hours = minutes // 60
    days = hours // 24

    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m {suffix}"
    if hours < 24:
        return f"{hours}h {suffix}"
    return f"{days}d {suffix}"


def _safe_select(client, table: str, *fields: str, **kwargs):
    """
    Execute a Supabase select with defensive error handling.
    Returns response.data or an empty list on failure.
    """
    try:
        query = client.table(table).select(*fields)
        if "filters" in kwargs:
            for fn, args in kwargs["filters"]:
                query = getattr(query, fn)(*args)
        if "order" in kwargs:
            order_field, order_kwargs = kwargs["order"]
            query = query.order(order_field, **order_kwargs)
        if "limit" in kwargs:
            query = query.limit(kwargs["limit"])
        return query.execute().data or []
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Supabase select failed for {table}: {exc}")
        return []


@router.get("/overview")
async def get_dashboard_overview() -> Dict[str, Any]:
    """
    Aggregated dashboard telemetry for mission control.
    """
    try:
        client = _make_supabase_client()
    except RuntimeError as exc:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)

    # Collectors
    collector_rows = _safe_select(client, "collection_metrics", "*")
    latest_collector = None
    if collector_rows:
        collector_rows = [
            {
                **row,
                "last_run_at": _parse_timestamp(row.get("last_run_at")),
                "updated_at": _parse_timestamp(row.get("updated_at")),
            }
            for row in collector_rows
        ]
        collector_rows = sorted(
            collector_rows,
            key=lambda row: row.get("last_run_at")
            or datetime.fromtimestamp(0, tz=timezone.utc),
            reverse=True,
        )
        latest_collector = collector_rows[0]

    # Rewrites / transformations
    ready_transformations = 0
    total_transformations = 0
    last_transformation_at: Optional[datetime] = None
    try:
        resp_ready = (
            client.table("mimesis_transformations")
            .select("id", count="exact")
            .eq("ready_for_posting", True)
            .execute()
        )
        ready_transformations = resp_ready.count or 0

        resp_total = (
            client.table("mimesis_transformations")
            .select("id", count="exact")
            .execute()
        )
        total_transformations = resp_total.count or 0

        latest_transformation = _safe_select(
            client,
            "mimesis_transformations",
            "created_at",
            order=("created_at", {"desc": True}),
            limit=1,
        )
        if latest_transformation:
            last_transformation_at = _parse_timestamp(
                latest_transformation[0].get("created_at")
            )
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Failed to query transformation stats: {exc}")

    # Scheduled posts queue
    scheduled_queue = 0
    try:
        resp_sched = (
            client.table("scheduled_posts").select("id", count="exact").execute()
        )
        scheduled_queue = resp_sched.count or 0
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Failed to query scheduled posts: {exc}")

    # Posted content (live deployments)
    latest_posted = _safe_select(
        client,
        "posted_content",
        "persona_key",
        "platform",
        "posted_at",
        "created_at",
        order=("posted_at", {"desc": True, "nullsfirst": False}),
        limit=1,
    )
    latest_posted_record = None
    if latest_posted:
        record = latest_posted[0]
        record["posted_at"] = _parse_timestamp(
            record.get("posted_at") or record.get("created_at")
        )
        latest_posted_record = record

    # Telegram digest / executive summaries
    latest_digest = _safe_select(
        client,
        "telegram_messages",
        "channel_username",
        "date",
        "created_at",
        order=("date", {"desc": True}),
        limit=1,
    )
    latest_digest_record = None
    if latest_digest:
        digest = latest_digest[0]
        digest["date"] = _parse_timestamp(
            digest.get("date") or digest.get("created_at")
        )
        latest_digest_record = digest

    # Build operations feed
    operations: List[Dict[str, Any]] = []
    if latest_posted_record and latest_posted_record.get("posted_at"):
        operations.append(
            {
                "label": "Rewrites deployed",
                "detail": f"Persona {latest_posted_record.get('persona_key', 'unknown')} published to {latest_posted_record.get('platform', 'platform')}.",
                "timestamp_label": _humanize_delta(
                    now, latest_posted_record["posted_at"]
                ),
                "tone": "positive",
            }
        )

    if latest_collector and latest_collector.get("last_run_at"):
        detail_count = latest_collector.get("last_count")
        if detail_count is None:
            collector_detail = f"{latest_collector.get('platform', 'collector').capitalize()} sweep completed."
        else:
            collector_detail = f"{latest_collector.get('platform', 'collector').capitalize()} sweep captured {detail_count} posts."
        tone = "positive" if latest_collector.get("last_success") else "alert"
        if latest_collector.get("last_success") is False and latest_collector.get(
            "failure_reason"
        ):
            collector_detail = latest_collector["failure_reason"]
        operations.append(
            {
                "label": f"{latest_collector.get('platform', 'Collector').capitalize()} collection",
                "detail": collector_detail,
                "timestamp_label": _humanize_delta(
                    now, latest_collector["last_run_at"]
                ),
                "tone": tone,
            }
        )

    if latest_digest_record and latest_digest_record.get("date"):
        channel = latest_digest_record.get("channel_username") or "Telegram digest"
        operations.append(
            {
                "label": "Telegram digest",
                "detail": f"Latest brief delivered via {channel}.",
                "timestamp_label": _humanize_delta(now, latest_digest_record["date"]),
                "tone": "informational",
            }
        )

    # System heartbeat summary
    if latest_collector and latest_collector.get("last_run_at"):
        last_run_ts = latest_collector["last_run_at"]
        heartbeat_summary = (
            f"{latest_collector.get('platform', 'Collector').capitalize()} automation ran "
            f"{_humanize_delta(now, last_run_ts)}."
        )
        next_cycle_ts = last_run_ts + timedelta(minutes=90)
        next_cycle_label = (
            _humanize_delta(next_cycle_ts, now) if next_cycle_ts > now else "due now"
        )
    else:
        last_run_ts = None
        heartbeat_summary = "Collector automation telemetry unavailable."
        next_cycle_label = "unscheduled"

    system_payload = {
        "summary": heartbeat_summary,
        "last_run": last_run_ts.isoformat() if last_run_ts else None,
        "next_cycle_label": next_cycle_label,
    }

    # Workflow matrix payload
    workflow_payload = {
        "rewrites": {
            "queue": ready_transformations,
            "total_transformations": total_transformations,
            "last_activity": (
                _humanize_delta(now, last_transformation_at)
                if last_transformation_at
                else "no activity logged"
            ),
        },
        "collectors": {
            "platforms_monitored": len(collector_rows) if collector_rows else 0,
            "healthy": sum(
                1 for row in collector_rows or [] if row.get("last_success")
            ),
            "last_activity": (
                _humanize_delta(now, latest_collector["last_run_at"])
                if latest_collector and latest_collector.get("last_run_at")
                else "no runs recorded"
            ),
        },
        "learning": {
            "posted_total": 0,
            "with_engagement": 0,
            "last_posted": None,
        },
    }

    # Learning stats require posted_content counts
    try:
        posted_counts = (
            client.table("posted_content").select("id", count="exact").execute()
        )
        workflow_payload["learning"]["posted_total"] = posted_counts.count or 0

        engaged_counts = (
            client.table("posted_content")
            .select("id", count="exact")
            .not_.is_("engagement_json", "null")
            .execute()
        )
        workflow_payload["learning"]["with_engagement"] = engaged_counts.count or 0

        if latest_posted_record and latest_posted_record.get("posted_at"):
            workflow_payload["learning"]["last_posted"] = _humanize_delta(
                now, latest_posted_record["posted_at"]
            )
    except Exception as exc:  # pragma: no cover
        logger.warning(f"Failed to compute learning stats: {exc}")

    return {
        "system_heartbeat": system_payload,
        "operations": operations,
        "workflow": workflow_payload,
    }
