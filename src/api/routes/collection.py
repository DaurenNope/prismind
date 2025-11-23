from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dateutil.parser import isoparse
from fastapi import APIRouter, Query

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
        return isoparse(value).astimezone(timezone.utc).isoformat()
    except Exception as e:
        logger.error(f"Error: {e}")
        return value


@router.get("/status")
async def get_collection_status() -> Dict[str, Any]:
    """Get collection status - optimized with timeouts and error handling"""
    import asyncio

    try:
        client = _make_supabase_client()

        # Query with timeout protection (10s max)
        try:
            # Run Supabase query in executor to avoid blocking
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: (
                        client.table("collection_metrics")
                        .select("*")
                        .order("updated_at", desc=True)
                        .limit(20)  # Limit to prevent slow queries
                        .execute()
                    ),
                ),
                timeout=10.0,
            )
            rows = getattr(response, "data", []) or []
        except asyncio.TimeoutError:
            logger.warning("Collection status query timed out after 10s")
            return {"collectors": []}
        except Exception as e:
            logger.error(f"Error: {e}")
            # If table doesn't exist or query fails, return empty
            return {"collectors": []}

        latest_logs: Dict[str, Dict[str, Any]] = {}
        if rows:
            try:
                # Optimize: only get latest log per platform (limit to 10 platforms max)
                loop = asyncio.get_event_loop()
                log_resp = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: (
                            client.table("collection_logs")
                            .select(
                                "platform,message,status,started_at,finished_at,posts_collected"
                            )
                            .order("started_at", desc=True)
                            .limit(30)  # Limit to prevent slow queries
                            .execute()
                        ),
                    ),
                    timeout=10.0,
                )
                for entry in getattr(log_resp, "data", []) or []:
                    platform = entry.get("platform")
                    if platform and platform not in latest_logs:
                        latest_logs[str(platform).lower()] = entry
            except asyncio.TimeoutError:
                logger.warning("Collection logs query timed out after 10s")
                latest_logs = {}
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
    """Get collection logs - optimized with error handling and timeout protection"""
    import asyncio
    
    try:
        client = _make_supabase_client()

        # Cap limit to prevent slow queries
        limit = min(limit, 50)

        # Run Supabase query in executor with timeout (10s max)
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: (
                    client.table("collection_logs")
                    .select("*")
                    .order("started_at", desc=True)
                    .limit(limit)
                    .execute()
                ),
            ),
            timeout=10.0,
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
    except asyncio.TimeoutError:
        logger.warning("Collection logs query timed out after 10s")
        return {"logs": [], "error": "Query timeout"}
    except Exception as exc:
        logger.error(f"Error: {exc}")
        # Return empty instead of raising - prevents UI from breaking
        return {"logs": [], "error": str(exc)}


@router.post("/stop")
async def stop_collection() -> Dict[str, Any]:
    """Stop the current collection process"""
    try:
        from src.domain.collection.services.telegram_collection_commands import get_collection_service

        service = get_collection_service()
        stopped = service.stop_collection()

        if stopped:
            return {"success": True, "message": "Collection stop requested"}
        else:
            return {"success": False, "message": "No collection in progress"}
    except Exception as exc:
        logger.error(f"Error stopping collection: {exc}")
        return {"success": False, "error": str(exc)}


@router.get("/latest-posts")
async def get_latest_posts_by_platform(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (1-168)"),
    limit_per_platform: int = Query(10, ge=1, le=100, description="Max posts per platform (1-100)"),
) -> Dict[str, Any]:
    """
    Get latest collected posts grouped by platform.
    
    Returns posts collected within the specified time window, grouped by platform,
    with a limit per platform.
    """
    try:
        # Calculate cutoff time
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_iso = cutoff_time.isoformat()
        
        # Try to use NewDatabaseManager first, but fall back to Supabase if needed
        # Since NewDatabaseManager doesn't have time-based filtering, we'll use Supabase directly
        # (following the pattern of other endpoints in this router)
        client = _make_supabase_client()
        
        # Query posts from Supabase with time filter
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: (
                        client.table("posts")
                        .select("post_id,content,author,url,created_at,title,platform")
                        .gte("created_at", cutoff_iso)
                        .order("created_at", desc=True)
                        .limit(1000)  # Reasonable limit to prevent slow queries
                        .execute()
                    ),
                ),
                timeout=10.0,
            )
            all_posts = getattr(response, "data", []) or []
        except asyncio.TimeoutError:
            logger.warning("Latest posts query timed out after 10s")
            return {
                "platforms": {},
                "hours": hours,
                "total_posts": 0,
            }
        except Exception as e:
            logger.error(f"Error querying latest posts: {e}")
            return {
                "platforms": {},
                "hours": hours,
                "total_posts": 0,
            }
        
        # Group posts by platform and apply limit
        platforms_dict: Dict[str, List[Dict[str, Any]]] = {}
        
        for post in all_posts:
            platform = (post.get("platform") or "unknown").lower()
            
            # Initialize platform list if needed
            if platform not in platforms_dict:
                platforms_dict[platform] = []
            
            # Apply limit per platform
            if len(platforms_dict[platform]) < limit_per_platform:
                # Format post data according to requirements
                content = post.get("content", "") or ""
                # Truncate content to 200 chars
                content_truncated = content[:200] + "..." if len(content) > 200 else content
                
                formatted_post = {
                    "post_id": post.get("post_id"),
                    "content": content_truncated,
                    "author": post.get("author"),
                    "url": post.get("url"),
                    "created_at": _safe_iso(post.get("created_at")),
                    "title": post.get("title"),
                }
                
                platforms_dict[platform].append(formatted_post)
        
        # Calculate total posts
        total_posts = sum(len(posts) for posts in platforms_dict.values())
        
        return {
            "platforms": platforms_dict,
            "hours": hours,
            "total_posts": total_posts,
        }
        
    except Exception as exc:
        logger.error(f"Error getting latest posts: {exc}", exc_info=True)
        # Return empty structure on error
        return {
            "platforms": {},
            "hours": hours,
            "total_posts": 0,
        }


@router.get("/search")
async def search_posts(
    q: str = Query(..., description="Search query (searches content and author)"),
    platform: Optional[str] = Query(None, description="Filter by platform"),
    limit: int = Query(20, ge=1, le=100, description="Max results (1-100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> Dict[str, Any]:
    """
    Search posts by content or author.
    
    Performs case-insensitive partial matching on:
    - Post content
    - Author name
    - Author handle/username
    
    Returns paginated results.
    """
    try:
        if not q or not q.strip():
            return {
                "posts": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "query": q,
                "platform": platform,
                "error": "Search query cannot be empty",
            }

        client = _make_supabase_client()

        # Build query with OR conditions for content/author search
        # Use ilike for case-insensitive partial matching
        search_term = f"%{q.strip()}%"

        query_builder = (
            client.table("posts")
            .select("post_id,content,author,url,created_at,title,platform,collected_at,author_handle")
            .or_(f"content.ilike.{search_term},author.ilike.{search_term},author_handle.ilike.{search_term}")
        )

        # Add platform filter if specified
        if platform:
            query_builder = query_builder.eq("platform", platform.lower())

        # Order by collected_at first (most recent collected), then created_at
        # Note: If collected_at doesn't exist, we'll order by created_at
        # Supabase will handle nulls appropriately
        query_builder = query_builder.order("collected_at", desc=True, nulls_last=True)
        query_builder = query_builder.order("created_at", desc=True)

        # Apply pagination
        query_builder = query_builder.range(offset, offset + limit - 1)

        # Execute with timeout protection
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: query_builder.execute(),
            ),
            timeout=10.0,
        )

        posts = getattr(response, "data", []) or []

        # Format posts for response
        formatted_posts = []
        for post in posts:
            formatted_posts.append({
                "post_id": post.get("post_id"),
                "platform": post.get("platform"),
                "author": post.get("author"),
                "content": post.get("content"),
                "url": post.get("url"),
                "created_at": _safe_iso(post.get("created_at")),
                "title": post.get("title"),
                "collected_at": _safe_iso(post.get("collected_at")),
            })

        # Get total count (for pagination info)
        # Note: Supabase doesn't return count by default, so we'll estimate
        # For exact count, would need separate count query (can be added later)
        # Using len(posts) as approximate count - actual count would require separate query

        return {
            "posts": formatted_posts,
            "total": len(formatted_posts),  # Approximate - actual count would require separate query
            "limit": limit,
            "offset": offset,
            "query": q,
            "platform": platform,
        }

    except asyncio.TimeoutError:
        logger.warning("Post search query timed out after 10s")
        return {
            "posts": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "query": q,
            "platform": platform,
            "error": "Query timeout",
        }
    except Exception as exc:
        logger.error(f"Error searching posts: {exc}", exc_info=True)
        return {
            "posts": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "query": q,
            "platform": platform,
            "error": str(exc),
        }
