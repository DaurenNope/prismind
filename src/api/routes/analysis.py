from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from dateutil.parser import isoparse
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.application.automation.orchestrator import get_orchestrator
from src.services.new_database_manager import NewDatabaseManager

try:
    from src.shared.utils.logging_config import get_logger
except Exception:  # pragma: no cover - fallback if logging module import fails
    import logging

    def get_logger(name: str) -> "logging.Logger":
        return logging.getLogger(name)


logger = get_logger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class AnalysisRunRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=500)
    force: bool = False


def _safe_timestamp(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        if isinstance(value, str):
            return isoparse(value).isoformat()
        return isoparse(str(value)).isoformat()
    except Exception as e:
        logger.warning(f"Error parsing JSON value: {e}")
        return value


def _ensure_list(value: Any) -> List[str]:
    """Convert various formats to a list of strings, handling JSON, comma-separated, etc."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    if isinstance(value, str):
        # Try JSON first (most structured)
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if item is not None]
        except (json.JSONDecodeError, ValueError):
            # Not valid JSON, try comma-separated
            pass

        # Try comma-separated string
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]

        # Single value as list
        return [value.strip()] if value.strip() else []
    return []


async def _run_auto_rewrite_cycle(
    module_logger, analyzed_post_ids: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Trigger the auto rewrite pipeline (without auto posting).

    Args:
        module_logger: Logger instance
        analyzed_post_ids: Optional list of post IDs that were just analyzed.
                         If provided, only these posts will be processed for rewriting.
                         If None, processes all eligible posts (backward compatibility).

    Returns summary dict if rewrites/scheduling occurred, otherwise None.
    """
    try:
        from src.pipeline.auto_pipeline import AutoPipeline

        auto_pipeline = AutoPipeline()
        if not auto_pipeline.enabled:
            return None

        # If specific post IDs were analyzed, only rewrite those
        if analyzed_post_ids:
            module_logger.info(
                f"Rewriting only newly analyzed posts: {len(analyzed_post_ids)} posts"
            )
            rewrite_report = await auto_pipeline.run_rewrite_cycle_for_posts(
                analyzed_post_ids
            )
        else:
            # Backward compatibility: process all eligible posts
            rewrite_report = await auto_pipeline.run_rewrite_cycle()
        
        if rewrite_report:
            module_logger.info(f"Auto rewrite cycle complete: {rewrite_report}")
        else:
            module_logger.info("Auto rewrite cycle finished with no eligible posts")
        return rewrite_report
    except Exception as err:  # pragma: no cover - defensive logging
        module_logger.warning(f"Auto rewrite cycle failed: {err}")
        return None


def _get_supabase_client():
    # Use module-level logger (defined at top of file)
    try:
        from supabase import create_client  # type: ignore
    except ImportError as e:
        logger.warning(f"Module import failed: {e}")
        return None

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        logger.warning(f"Error creating Supabase client: {e}")
        return None


@router.get("/stats")
async def get_analysis_stats() -> Dict[str, Any]:
    """Return aggregated analysis statistics."""
    logger = get_logger(__name__)

    client = _get_supabase_client()
    if client:
        try:
            # Overall counts
            total_resp = (
                client.table("posts").select("id", count="exact").limit(1).execute()
            )
            total_posts = getattr(total_resp, "count", 0) or 0

            unanalyzed_query = (
                client.table("posts")
                .select("*", count="exact")
                .is_("analyzed_at", "null")
                .is_("ai_summary", "null")
                .order("created_at", desc=True)
            )
            queue_resp = unanalyzed_query.limit(500).execute()
            queue_data = queue_resp.data or []
            unanalyzed_count = getattr(queue_resp, "count", 0) or len(queue_data)

            platform_queue: Dict[str, int] = {}
            queue_preview: List[Dict[str, Any]] = []
            for idx, post in enumerate(queue_data):
                platform = (post.get("platform") or "unknown").lower()
                platform_queue[platform] = platform_queue.get(platform, 0) + 1
                if idx < 8:
                    queue_preview.append(
                        {
                            "post_id": post.get("post_id") or post.get("id"),
                            "platform": platform,
                            "author": post.get("author"),
                            "created_at": _safe_timestamp(post.get("created_at")),
                            "content_preview": (post.get("content") or "")[:220],
                        }
                    )

            analyzed_count = total_posts - unanalyzed_count if total_posts else 0

            # Recent analyzed posts for averages/last analysis
            recent_resp = (
                client.table("posts")
                .select(
                    "post_id, platform, author, analyzed_at, ai_summary, quality_score, value_score, sentiment"
                )
                .or_("analyzed_at.not.is.null,ai_summary.not.is.null")
                .order("analyzed_at", desc=True)
                .limit(500)
                .execute()
            )
            recent_data = recent_resp.data or []

            last_analysis_at = None
            if recent_data:
                last_analysis_at = _safe_timestamp(recent_data[0].get("analyzed_at"))

            quality_values: List[float] = []
            quality_distribution = {
                "high_quality": 0,
                "medium_quality": 0,
                "low_quality": 0,
            }
            for post in recent_data:
                score = post.get("quality_score")
                if isinstance(score, (int, float)):
                    quality_values.append(float(score))
                    if score >= 7:
                        quality_distribution["high_quality"] += 1
                    elif score >= 5:
                        quality_distribution["medium_quality"] += 1
                    else:
                        quality_distribution["low_quality"] += 1

            avg_quality = (
                round(sum(quality_values) / len(quality_values), 2)
                if quality_values
                else None
            )

            return {
                "summary": {
                    "analyzed_posts": analyzed_count,
                    "unanalyzed_posts": unanalyzed_count,
                    "rewrite_candidates": 0,
                    "quality_distribution": quality_distribution,
                },
                "platform_queue": platform_queue,
                "queue_preview": queue_preview,
                "last_analysis_at": last_analysis_at,
                "average_quality": avg_quality,
            }
        except Exception as exc:
            logger.warning(
                f"Supabase analysis stats failed, falling back to SQLite: {exc}"
            )

    # Fallback to SQLite cache if Supabase unavailable
    try:
        db = NewDatabaseManager()

        summary = db.get_analysis_stats() or {}
        unanalyzed_posts = db.get_unanalyzed_posts(limit=1000)

        platform_counts: Dict[str, int] = {}
        queue_preview: List[Dict[str, Any]] = []
        for idx, post in enumerate(unanalyzed_posts):
            platform = (post.get("platform") or "unknown").lower()
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            if idx < 8:
                queue_preview.append(
                    {
                        "post_id": post.get("post_id") or post.get("id"),
                        "platform": platform,
                        "author": post.get("author"),
                        "created_at": _safe_timestamp(
                            post.get("created_at") or post.get("timestamp")
                        ),
                        "content_preview": (post.get("content") or "")[:220],
                    }
                )

        recent_posts = db.get_posts(limit=200)
        analyzed_posts = [
            p
            for p in recent_posts
            if p.get("analysis_timestamp") or p.get("analyzed_at")
        ]
        analyzed_posts.sort(
            key=lambda item: (
                item.get("analysis_timestamp") or item.get("analyzed_at") or ""
            ),
            reverse=True,
        )

        last_analysis_at = None
        if analyzed_posts:
            last_analysis_at = _safe_timestamp(
                analyzed_posts[0].get("analysis_timestamp")
                or analyzed_posts[0].get("analyzed_at")
            )

        quality_values: List[float] = []
        for post in analyzed_posts:
            # Standardized field name: quality_score (with legacy fallback)
            score = post.get("quality_score") or post.get("content_quality_score")
            if isinstance(score, (int, float)):
                quality_values.append(float(score))

        avg_quality = (
            round(sum(quality_values) / len(quality_values), 2)
            if quality_values
            else None
        )

        return {
            "summary": {
                "analyzed_posts": summary.get("analyzed_posts", len(analyzed_posts)),
                "unanalyzed_posts": summary.get(
                    "unanalyzed_posts", len(unanalyzed_posts)
                ),
                "rewrite_candidates": summary.get("rewrite_candidates", 0),
                "quality_distribution": summary.get("quality_distribution", {}),
            },
            "platform_queue": platform_counts,
            "queue_preview": queue_preview,
            "last_analysis_at": last_analysis_at,
            "average_quality": avg_quality,
        }
    except Exception as exc:
        logger.error(f"Error getting analysis stats: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/recent")
async def get_recent_analysis(limit: int = 20) -> Dict[str, Any]:
    """Return recently analyzed posts."""
    logger = get_logger(__name__)

    client = _get_supabase_client()
    if client:
        try:
            resp = (
                client.table("posts")
                .select(
                    "post_id, platform, author, analyzed_at, ai_summary, content, value_score, quality_score, sentiment, tags"
                )
                .or_("analyzed_at.not.is.null,ai_summary.not.is.null")
                .order("analyzed_at", desc=True)
                .limit(max(limit, 50))
                .execute()
            )
            data = resp.data or []

            items: List[Dict[str, Any]] = []
            for post in data[:limit]:
                items.append(
                    {
                        "post_id": post.get("post_id") or post.get("id"),
                        "platform": post.get("platform"),
                        "author": post.get("author"),
                        "analysis_timestamp": _safe_timestamp(post.get("analyzed_at")),
                        "quality_score": post.get("quality_score"),
                        "value_score": post.get("value_score"),
                        "sentiment": post.get("sentiment"),
                        "ai_summary": post.get("ai_summary"),
                        "content": post.get("content"),
                        "key_concepts": _ensure_list(post.get("tags")),
                    }
                )

            return {"posts": items}
        except Exception as exc:
            logger.warning(
                f"Supabase recent analysis failed, falling back to SQLite: {exc}"
            )

    # Fallback
    try:
        db = NewDatabaseManager()
        posts = db.get_posts(limit=max(limit * 2, 50))
        analyzed_posts = [
            p for p in posts if p.get("analysis_timestamp") or p.get("analyzed_at")
        ]
        analyzed_posts.sort(
            key=lambda item: (
                item.get("analysis_timestamp") or item.get("analyzed_at") or ""
            ),
            reverse=True,
        )

        items: List[Dict[str, Any]] = []
        for post in analyzed_posts[:limit]:
            items.append(
                {
                    "post_id": post.get("post_id") or post.get("id"),
                    "platform": post.get("platform"),
                    "author": post.get("author"),
                    "analysis_timestamp": _safe_timestamp(
                        post.get("analysis_timestamp") or post.get("analyzed_at")
                    ),
                    # Standardized field name: quality_score (with legacy fallback)
                    "quality_score": post.get("quality_score") or post.get("content_quality_score"),
                    "value_score": post.get("value_score"),
                    "sentiment": post.get("sentiment") or post.get("sentiment_label"),
                    "ai_summary": post.get("ai_summary") or post.get("summary"),
                    "content": post.get("content"),
                    "key_concepts": _ensure_list(
                        post.get("key_concepts") or post.get("tags")
                    ),
                }
            )

        return {"posts": items}
    except Exception as exc:
        logger.error(f"Error getting recent analysis: {exc}")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/run")
async def trigger_analysis(request: AnalysisRunRequest) -> Dict[str, Any]:
    """Kick off an analysis batch."""
    from src.shared.utils.logging_config import get_logger

    logger = get_logger(__name__)

    try:
        logger.info(f"Starting analysis batch with limit={request.limit}")
        orchestrator = get_orchestrator()

        # Check if there are unanalyzed posts available using the orchestrator's storage
        # This ensures we're checking the same source (Supabase) that the analysis will use
        unanalyzed = orchestrator.storage.get_unanalyzed_posts(limit=request.limit)
        logger.info(
            f"Found {len(unanalyzed)} unanalyzed posts available (from storage adapter)"
        )

        if not unanalyzed:
            return {
                "success": True,
                "analyzed": 0,
                "message": "No unanalyzed posts found. All posts are already analyzed.",
            }

        result = await orchestrator.analyze_batch(
            limit=request.limit, force=request.force
        )
        # Handle both old format (int) and new format (dict)
        if isinstance(result, dict):
            analyzed = result.get("count", 0)
            analyzed_post_ids = result.get("analyzed_post_ids", [])
        else:
            # Backward compatibility: old format returned just int
            analyzed = result
            analyzed_post_ids = []
        
        logger.info(f"Analysis batch completed: {analyzed} posts analyzed")
        automation = None
        if analyzed > 0:
            # Only rewrite the newly analyzed posts, not all posts in database
            automation = await _run_auto_rewrite_cycle(logger, analyzed_post_ids=analyzed_post_ids)

        response: Dict[str, Any] = {
            "success": True,
            "analyzed": analyzed,
            "message": f"Analyzed {analyzed} out of {len(unanalyzed)} available posts",
        }
        if analyzed_post_ids:
            response["analyzed_post_ids"] = analyzed_post_ids
        if automation:
            response["automation"] = automation

        return response
    except Exception as exc:
        logger.error(f"Analysis batch failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
