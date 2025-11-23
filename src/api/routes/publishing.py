import logging

logger = logging.getLogger(__name__)
"""
Publishing API Routes
Handles scheduled posts, transformations, and publishing operations
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/publishing", tags=["publishing"])


# Request/Response models
class SchedulePostRequest(BaseModel):
    persona_key: str
    platform: str
    content: str
    scheduled_time: str  # ISO format
    content_type: str = "single_tweet"  # single_tweet, thread, telegram_message


class UpdateTransformationRequest(BaseModel):
    content: Optional[str] = None
    ready_for_posting: Optional[bool] = None


@router.get("/scheduled")
async def get_scheduled_posts(
    persona_key: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
):
    """Get scheduled posts with filters"""
    try:
        from src.infrastructure.database.publishing.bridge import MimesisDB

        db = MimesisDB()

        # Get due posts (this is what the UI uses)
        due = db.list_due_posts()

        # Apply filters
        filtered = due
        if persona_key:
            filtered = [
                p
                for p in filtered
                if p.get("persona_key") == persona_key
                or p.get("personality_key") == persona_key
            ]
        if platform:
            filtered = [p for p in filtered if p.get("platform") == platform]
        if status:
            filtered = [p for p in filtered if p.get("status") == status]

        return {"posts": filtered[:limit], "total": len(filtered)}
    except Exception as e:
        logger.error(f"Error getting scheduled posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule")
async def schedule_post(request: SchedulePostRequest):
    """Schedule a post for future publishing"""
    try:
        from src.infrastructure.database.publishing.bridge import MimesisDB

        db = MimesisDB()

        payload = {
            "persona_key": request.persona_key,
            "personality_key": request.persona_key,  # Support both
            "platform": request.platform,
            "content": request.content,
            "content_type": request.content_type,
            "scheduled_time": request.scheduled_time,
        }

        row = db.insert_scheduled(payload)

        return {
            "success": True,
            "post": row,
            "message": f"Post scheduled for {request.scheduled_time}",
        }
    except Exception as e:
        logger.error(f"Error scheduling post: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transformations")
async def get_transformations(
    persona_key: Optional[str] = None, ready_only: bool = False, limit: int = 50
):
    """Get transformations (rewrites)"""
    try:
        from src.infrastructure.database.publishing.bridge import MimesisDB

        db = MimesisDB()
        transformations = db.list_transformations(
            persona_key=persona_key, ready_only=ready_only
        )

        return {
            "transformations": transformations[:limit],
            "total": len(transformations),
        }
    except Exception as e:
        logger.error(f"Error getting transformations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/transformations/{transformation_id}")
async def update_transformation(
    transformation_id: int, request: UpdateTransformationRequest
):
    """Update a transformation"""
    try:
        from src.infrastructure.database.publishing.bridge import MimesisDB

        db = MimesisDB()

        update_data = {}
        if request.content is not None:
            update_data["content"] = request.content
        if request.ready_for_posting is not None:
            update_data["ready_for_posting"] = request.ready_for_posting

        db.update_transformation(transformation_id, update_data)

        return {"success": True, "message": "Transformation updated"}
    except Exception as e:
        logger.error(f"Error updating transformation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/transformations/{transformation_id}")
async def delete_transformation(transformation_id: int):
    """Delete a transformation"""
    try:
        from src.infrastructure.database.publishing.bridge import MimesisDB

        db = MimesisDB()
        db.delete_transformation(transformation_id)

        return {"success": True, "message": "Transformation deleted"}
    except Exception as e:
        logger.error(f"Error deleting transformation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/transformations/cleanup/old")
async def cleanup_old_transformations(days: int = 30, all: bool = False):
    """Delete transformations older than specified days, or all if all=True"""
    try:
        from src.infrastructure.database.publishing.bridge import MimesisDB

        db = MimesisDB()

        if all:
            deleted_count = db.delete_all_transformations()
            message = f"Deleted all {deleted_count} transformations"
        else:
            deleted_count = db.delete_old_transformations(days=days)
            message = f"Deleted {deleted_count} transformations older than {days} days"

        logger.info(message)

        return {"success": True, "message": message, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Error cleaning up old transformations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scheduled/{post_id}")
async def delete_scheduled_post(post_id: int):
    """Delete a scheduled post"""
    try:
        import os

        from supabase import create_client

        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Check if posted
        posted_check = (
            client.table("posted_content")
            .select("id")
            .eq("scheduled_post_id", post_id)
            .execute()
        )

        if posted_check.data:
            # Set foreign key to NULL first
            client.table("posted_content").update({"scheduled_post_id": None}).eq(
                "scheduled_post_id", post_id
            ).execute()

        # Delete scheduled post
        client.table("scheduled_posts").delete().eq("id", post_id).execute()

        return {"success": True, "message": "Post deleted"}
    except Exception as e:
        logger.error(f"Error deleting scheduled post: {e}")
        # Try to mark as cancelled instead
        try:
            client.table("scheduled_posts").update({"status": "cancelled"}).eq(
                "id", post_id
            ).execute()
            return {
                "success": True,
                "message": "Post marked as cancelled (was already posted)",
            }
        except Exception as e:
            logger.error(f"Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.post("/publish/{post_id}")
async def publish_post(post_id: int):
    """Publish a scheduled post immediately"""
    try:
        import os

        from supabase import create_client

        from src.infrastructure.database.publishing.bridge import MimesisDB
        from src.domain.publishing.worker import (
            post_to_telegram_direct,
            post_to_threads_direct,
            post_to_twitter_direct,
        )

        client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        db = MimesisDB()

        # Get scheduled post
        post = client.table("scheduled_posts").select("*").eq("id", post_id).execute()

        if not post.data:
            raise HTTPException(status_code=404, detail="Post not found")

        post_data = post.data[0]
        platform = post_data.get("platform")
        content = post_data.get("content")

        # Publish based on platform
        result = None
        if platform == "telegram":
            result = post_to_telegram_direct(content)
        elif platform == "twitter":
            result = post_to_twitter_direct(content)
        elif platform == "threads":
            result = post_to_threads_direct(content)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown platform: {platform}")

        if result and result.get("success"):
            # Mark as posted
            platform_post_id = result.get("message_id") or result.get("tweet_id")
            db.mark_posted(post_id, platform_post_id=platform_post_id)

            return {
                "success": True,
                "message": f"Posted to {platform}",
                "platform_post_id": platform_post_id,
            }
        else:
            error = result.get("error", "Unknown error") if result else "No result"
            raise HTTPException(status_code=500, detail=f"Failed to post: {error}")

    except HTTPException:
        logger.error(f"Error: {e}")
        raise
    except Exception as e:
        logger.error(f"Error publishing post: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _fetch_content_plan_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    persona: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = "scheduled",
) -> Dict[str, Any]:
    """Helper function to fetch and format content plan data"""
    from src.infrastructure.database.publishing.bridge import MimesisDB
    import os
    from supabase import create_client
    import json

    db = MimesisDB()
    client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

    # Parse dates with defaults
    if start_date:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    else:
        start_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    if end_date:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    else:
        end_dt = start_dt + timedelta(days=7)

    # Build query
    query = (
        client.table("scheduled_posts")
        .select("*")
        .gte("scheduled_time", start_dt.isoformat())
        .lte("scheduled_time", end_dt.isoformat())
    )

    if persona:
        # Support both persona_key and personality_key
        query = query.or_(f"persona_key.eq.{persona},personality_key.eq.{persona}")
    if platform:
        query = query.eq("platform", platform)
    if status:
        # Map "scheduled" to "pending" if needed
        status_value = "pending" if status == "scheduled" else status
        query = query.eq("status", status_value)

    result = query.order("scheduled_time", desc=False).execute()
    posts = result.data or []

    # Format response
    plan = []
    for post in posts:
        # Extract metadata if it exists (could be JSONB column or separate fields)
        metadata = post.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}

        # Get priority from metadata or default
        priority = metadata.get("priority") if metadata else None
        if priority is None:
            # Try to calculate from metadata fields if available
            viral = metadata.get("viral_potential", 0) if metadata else 0
            priority = min(100, max(0, viral))  # Simple fallback

        # Format scheduled_for (handle both scheduled_time and scheduled_at)
        scheduled_for = post.get("scheduled_time") or post.get("scheduled_at")
        if scheduled_for:
            if isinstance(scheduled_for, str):
                scheduled_for = scheduled_for.replace("+00:00", "Z")
            else:
                scheduled_for = scheduled_for.isoformat().replace("+00:00", "Z")

        plan_item = {
            "id": post.get("id"),
            "persona_key": post.get("persona_key") or post.get("personality_key") or post.get("profile"),
            "platform": post.get("platform"),
            "content": post.get("content", ""),
            "scheduled_for": scheduled_for,
            "priority": priority,
            "status": post.get("status", "scheduled"),
            "metadata": {
                "viral_potential": metadata.get("viral_potential") if metadata else None,
                "time_sensitivity": metadata.get("time_sensitivity") if metadata else None,
                "trend_relevance": metadata.get("trend_relevance") if metadata else None,
                "source_post_id": metadata.get("source_post_id") or post.get("source_post_id") if metadata else None,
            },
        }
        plan.append(plan_item)

    # Calculate summary statistics
    summary = {
        "total_scheduled": len(plan),
        "by_persona": defaultdict(int),
        "by_platform": defaultdict(int),
        "by_status": defaultdict(int),
        "date_range": {
            "start": start_dt.date().isoformat(),
            "end": end_dt.date().isoformat(),
        },
    }

    for item in plan:
        persona_key = item.get("persona_key")
        if persona_key:
            summary["by_persona"][persona_key] += 1
        platform_key = item.get("platform")
        if platform_key:
            summary["by_platform"][platform_key] += 1
        status_key = item.get("status")
        if status_key:
            summary["by_status"][status_key] += 1

    # Convert defaultdicts to regular dicts
    summary["by_persona"] = dict(summary["by_persona"])
    summary["by_platform"] = dict(summary["by_platform"])
    summary["by_status"] = dict(summary["by_status"])

    return {"plan": plan, "summary": summary}


@router.get("/content-plan")
async def get_content_plan(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    persona: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query("scheduled"),
):
    """Get content plan for calendar view"""
    try:
        return _fetch_content_plan_data(
            start_date=start_date,
            end_date=end_date,
            persona=persona,
            platform=platform,
            status=status,
        )
    except Exception as e:
        logger.error(f"Error getting content plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content-plan/by-day")
async def get_content_plan_by_day(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    persona: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query("scheduled"),
):
    """Get content plan grouped by day"""
    try:
        # Get the base content plan
        response = _fetch_content_plan_data(
            start_date=start_date,
            end_date=end_date,
            persona=persona,
            platform=platform,
            status=status,
        )

        # Group by day
        by_day = defaultdict(list)
        for item in response["plan"]:
            scheduled_for = item.get("scheduled_for")
            if scheduled_for:
                # Parse date from ISO string
                if isinstance(scheduled_for, str):
                    dt = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
                else:
                    dt = scheduled_for
                day_key = dt.date().isoformat()
                by_day[day_key].append(item)

        # Convert to list of day objects
        days = []
        for day, posts in sorted(by_day.items()):
            days.append({"date": day, "posts": posts, "count": len(posts)})

        return {
            "by_day": days,
            "summary": response["summary"],
        }

    except Exception as e:
        logger.error(f"Error getting content plan by day: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content-plan/by-persona")
async def get_content_plan_by_persona(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    persona: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query("scheduled"),
):
    """Get content plan grouped by persona"""
    try:
        # Get the base content plan
        response = _fetch_content_plan_data(
            start_date=start_date,
            end_date=end_date,
            persona=persona,
            platform=platform,
            status=status,
        )

        # Group by persona
        by_persona = defaultdict(list)
        for item in response["plan"]:
            persona_key = item.get("persona_key")
            if persona_key:
                by_persona[persona_key].append(item)

        # Convert to list of persona objects
        personas = []
        for persona_key, posts in sorted(by_persona.items()):
            personas.append({"persona": persona_key, "posts": posts, "count": len(posts)})

        return {
            "by_persona": personas,
            "summary": response["summary"],
        }

    except Exception as e:
        logger.error(f"Error getting content plan by persona: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content-plan/stats")
async def get_content_plan_stats(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    persona: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query("scheduled"),
):
    """Get content plan statistics with comprehensive metrics"""
    try:
        # Get the base content plan
        response = _fetch_content_plan_data(
            start_date=start_date,
            end_date=end_date,
            persona=persona,
            platform=platform,
            status=status,
        )

        plan = response.get("plan", [])
        summary = response.get("summary", {})
        
        # Parse date range from summary or calculate defaults
        date_range = summary.get("date_range", {})
        if date_range.get("start"):
            start_dt = datetime.fromisoformat(date_range["start"])
        else:
            start_dt = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        if date_range.get("end"):
            end_dt = datetime.fromisoformat(date_range["end"])
        else:
            end_dt = start_dt + timedelta(days=7)
        
        # Calculate comprehensive statistics
        stats = {
            "total_scheduled_next_7d": len(plan),
            "posts_per_persona": defaultdict(int),
            "posts_per_platform": defaultdict(int),
            "posts_by_time_sensitivity": defaultdict(int),
            "average_priority_score": 0.0,
            "gaps": [],  # Days with no posts
            "date_range": {
                "start": start_dt.date().isoformat(),
                "end": end_dt.date().isoformat(),
            },
        }

        # Track posts by day to find gaps
        posts_by_day = defaultdict(int)
        priorities = []
        
        for item in plan:
            # Posts per persona
            persona_key = item.get("persona_key")
            if persona_key:
                stats["posts_per_persona"][persona_key] += 1
            
            # Posts per platform
            platform_key = item.get("platform")
            if platform_key:
                stats["posts_per_platform"][platform_key] += 1
            
            # Time sensitivity
            metadata = item.get("metadata", {})
            time_sensitivity = metadata.get("time_sensitivity") if metadata else None
            if time_sensitivity:
                # Normalize time sensitivity values
                sensitivity = str(time_sensitivity).lower()
                if "breaking" in sensitivity:
                    stats["posts_by_time_sensitivity"]["breaking"] += 1
                elif "trending" in sensitivity:
                    stats["posts_by_time_sensitivity"]["trending"] += 1
                elif "timely" in sensitivity:
                    stats["posts_by_time_sensitivity"]["timely"] += 1
                else:
                    stats["posts_by_time_sensitivity"]["evergreen"] += 1
            else:
                # Default to evergreen if not specified
                stats["posts_by_time_sensitivity"]["evergreen"] += 1
            
            # Priority score
            priority = item.get("priority")
            if priority is not None:
                try:
                    priority_float = float(priority)
                    priorities.append(priority_float)
                except (ValueError, TypeError):
                    pass
            
            # Track posts by day
            scheduled_for = item.get("scheduled_for")
            if scheduled_for:
                try:
                    if isinstance(scheduled_for, str):
                        post_dt = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
                    else:
                        post_dt = scheduled_for
                    day_key = post_dt.date().isoformat()
                    posts_by_day[day_key] += 1
                except (ValueError, TypeError):
                    pass
        
        # Calculate average priority
        if priorities:
            stats["average_priority_score"] = round(sum(priorities) / len(priorities), 2)
        
        # Find gaps (days with no posts)
        current_date = start_dt.date()
        end_date_obj = end_dt.date()
        
        while current_date <= end_date_obj:
            day_key = current_date.isoformat()
            if posts_by_day[day_key] == 0:
                stats["gaps"].append(day_key)
            current_date += timedelta(days=1)
        
        # Convert defaultdicts to regular dicts
        stats["posts_per_persona"] = dict(stats["posts_per_persona"])
        stats["posts_per_platform"] = dict(stats["posts_per_platform"])
        stats["posts_by_time_sensitivity"] = dict(stats["posts_by_time_sensitivity"])
        
        return {"stats": stats}

    except Exception as e:
        logger.error(f"Error getting content plan stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/published")
async def get_published_posts(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    limit: int = Query(50, ge=1, le=200, description="Number of posts to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get list of published posts with filters"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        query = supabase.client.table("posted_content").select("*")
        
        # Apply filters
        if platform:
            query = query.eq("platform", platform)
        # Note: posted_content table doesn't have status field, filter by posted_at instead
        # if status:
        #     query = query.eq("status", status)
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                query = query.gte("posted_at", start_dt.isoformat())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_date format")
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                query = query.lte("posted_at", end_dt.isoformat())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_date format")
        
        # Get total count for pagination
        count_query = query.select("id", count="exact")
        count_result = count_query.execute()
        total = getattr(count_result, "count", 0) or 0
        
        # Apply ordering and pagination
        query = query.order("posted_at", desc=True).limit(limit).offset(offset)
        result = query.execute()
        
        posts = result.data or []
        
        # Normalize field names for frontend
        normalized_posts = []
        for post in posts:
            normalized = {
                "id": post.get("id"),
                "content": post.get("content") or post.get("initial_text", ""),
                "platform": post.get("platform"),
                "posted_at": post.get("posted_at"),
                "post_url": post.get("post_url") or post.get("url"),
                "platform_post_id": post.get("platform_post_id"),
                "status": "posted",  # All posts in posted_content are considered posted
                "persona_key": post.get("persona_key") or post.get("persona"),
                "engagement": {
                    "likes": post.get("total_likes") or post.get("engagement", {}).get("likes"),
                    "replies": post.get("total_comments") or post.get("engagement", {}).get("replies"),
                    "views": post.get("total_views") or post.get("engagement", {}).get("views"),
                    "shares": post.get("total_shares") or post.get("engagement", {}).get("shares"),
                } if (post.get("total_likes") or post.get("engagement")) else None,
            }
            # Remove None values from engagement
            if normalized["engagement"]:
                normalized["engagement"] = {k: v for k, v in normalized["engagement"].items() if v is not None}
                if not normalized["engagement"]:
                    normalized["engagement"] = None
            normalized_posts.append(normalized)
        
        # Format response
        return {
            "posts": normalized_posts,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting published posts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/published/{post_id}")
async def get_published_post(post_id: str):
    """Get single published post with full details"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        result = (
            supabase.client.table("posted_content")
            .select("*")
            .eq("id", post_id)
            .single()
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {"post": result.data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting published post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/published/stats")
async def get_published_posts_stats():
    """Get statistics about published posts"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        now = datetime.now(timezone.utc)
        one_day_ago = now - timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)
        
        # Get all published posts
        all_posts = (
            supabase.client.table("posted_content")
            .select("platform, posted_at, status")
            .execute()
        ).data or []
        
        # Calculate statistics
        total_published = len(all_posts)
        
        # Count by platform
        by_platform = defaultdict(int)
        for post in all_posts:
            platform = post.get("platform", "unknown")
            by_platform[platform] += 1
        
        # Note: posted_content table doesn't have status field
        # Count by status (all are considered "posted" since they're in posted_content)
        by_status = {"posted": total_published}
        
        # Count in last 24 hours
        last_24h = sum(
            1 for post in all_posts
            if post.get("posted_at")
            and datetime.fromisoformat(post["posted_at"].replace("Z", "+00:00")) >= one_day_ago
        )
        
        # Count in last 7 days
        last_7d = sum(
            1 for post in all_posts
            if post.get("posted_at")
            and datetime.fromisoformat(post["posted_at"].replace("Z", "+00:00")) >= seven_days_ago
        )
        
        # Calculate success rate (all posts in posted_content are considered successful)
        # If we had status field, we'd check for failed posts
        success_rate = 1.0 if total_published > 0 else 0.0
        
        # Calculate average per day (last 7 days)
        avg_per_day = round(last_7d / 7.0, 1) if last_7d > 0 else 0.0
        
        return {
            "total_published": total_published,
            "by_platform": dict(by_platform),
            "by_status": dict(by_status),
            "success_rate": round(success_rate, 2),
            "last_24h": last_24h,
            "last_7d": last_7d,
            "avg_per_day": avg_per_day
        }
    except Exception as e:
        logger.error(f"Error getting published posts stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Pending Approval Queue API
@router.get("/pending-approval")
async def get_pending_approvals(
    persona: Optional[str] = Query(None, description="Filter by persona"),
    min_quality: Optional[float] = Query(None, ge=0, le=1, description="Minimum quality score"),
    limit: int = Query(50, ge=1, le=200, description="Number of rewrites to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """Get list of rewrites pending approval"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        
        # Query pending rewrites (ready_for_posting = false)
        query = (
            supabase.client.table("persona_transformations")
            .select("*, posts!persona_transformations_source_post_id_fkey(*)")
            .eq("ready_for_posting", False)
            .order("created_at", desc=False)
        )
        
        # Apply filters
        if persona:
            query = query.eq("persona_key", persona)
        
        # Get total count
        count_query = query.select("id", count="exact")
        count_result = count_query.execute()
        total = getattr(count_result, "count", 0) or 0
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        result = query.execute()
        
        rewrites = result.data or []
        
        # Filter by quality score if specified (from metadata)
        if min_quality is not None:
            filtered_rewrites = []
            for rewrite in rewrites:
                metadata = rewrite.get("metadata", {})
                if isinstance(metadata, str):
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                quality_score = metadata.get("quality_score", 0)
                if quality_score >= min_quality:
                    filtered_rewrites.append(rewrite)
            rewrites = filtered_rewrites
            total = len(filtered_rewrites)
        
        # Normalize response format
        normalized_rewrites = []
        for rewrite in rewrites:
            metadata = rewrite.get("metadata", {})
            if isinstance(metadata, str):
                try:
                    import json
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            original_post = rewrite.get("posts") if isinstance(rewrite.get("posts"), dict) else None
            if isinstance(rewrite.get("posts"), list) and len(rewrite.get("posts", [])) > 0:
                original_post = rewrite["posts"][0]
            
            normalized = {
                "id": rewrite.get("id"),
                "content": rewrite.get("content"),
                "persona_key": rewrite.get("persona_key"),
                "platform": rewrite.get("platform"),
                "quality_score": metadata.get("quality_score"),
                "voice_consistency_score": metadata.get("voice_consistency_score"),
                "fact_preservation_score": metadata.get("fact_preservation_score"),
                "ready_for_posting": rewrite.get("ready_for_posting", False),
                "created_at": rewrite.get("created_at"),
                "source_post_id": rewrite.get("source_post_id"),
                "original_post": original_post,
            }
            normalized_rewrites.append(normalized)
        
        return {
            "rewrites": normalized_rewrites,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting pending approvals: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pending-approval/{id}/approve")
async def approve_rewrite(
    id: int,
    edited_content: Optional[str] = None
):
    """Approve a rewrite for posting"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        
        # Get current rewrite
        result = (
            supabase.client.table("persona_transformations")
            .select("*")
            .eq("id", id)
            .single()
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Rewrite not found")
        
        rewrite = result.data
        
        # Prepare update
        update_data = {
            "ready_for_posting": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Update metadata to mark as approved
        metadata = rewrite.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        metadata["approved_at"] = datetime.now(timezone.utc).isoformat()
        metadata["approved"] = True
        update_data["metadata"] = metadata
        
        # Update content if edited
        if edited_content:
            update_data["content"] = edited_content
        
        # Update in database
        updated = (
            supabase.client.table("persona_transformations")
            .update(update_data)
            .eq("id", id)
            .execute()
        )
        
        return {"success": True, "rewrite": updated.data[0] if updated.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving rewrite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pending-approval/{id}/reject")
async def reject_rewrite(
    id: int,
    reason: Optional[str] = None
):
    """Reject a rewrite"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        
        # Get current rewrite
        result = (
            supabase.client.table("persona_transformations")
            .select("*")
            .eq("id", id)
            .single()
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Rewrite not found")
        
        rewrite = result.data
        
        # Update metadata to mark as rejected
        metadata = rewrite.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        metadata["rejected_at"] = datetime.now(timezone.utc).isoformat()
        metadata["rejected"] = True
        if reason:
            metadata["rejection_reason"] = reason
        
        # Update in database
        updated = (
            supabase.client.table("persona_transformations")
            .update({
                "status": "rejected",
                "metadata": metadata,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", id)
            .execute()
        )
        
        return {"success": True, "rewrite": updated.data[0] if updated.data else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting rewrite: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pending-approval/bulk-approve")
async def bulk_approve_rewrites(
    ids: List[int]
):
    """Bulk approve rewrites"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        results = []
        
        for rewrite_id in ids:
            try:
                # Get current rewrite
                result = (
                    supabase.client.table("persona_transformations")
                    .select("*")
                    .eq("id", rewrite_id)
                    .single()
                    .execute()
                )
                
                if not result.data:
                    results.append({"id": rewrite_id, "success": False, "error": "Not found"})
                    continue
                
                rewrite = result.data
                
                # Update metadata
                metadata = rewrite.get("metadata", {})
                if isinstance(metadata, str):
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                metadata["approved_at"] = datetime.now(timezone.utc).isoformat()
                metadata["approved"] = True
                
                # Update in database
                updated = (
                    supabase.client.table("persona_transformations")
                    .update({
                        "ready_for_posting": True,
                        "metadata": metadata,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    .eq("id", rewrite_id)
                    .execute()
                )
                
                results.append({"id": rewrite_id, "success": True})
            except Exception as e:
                results.append({"id": rewrite_id, "success": False, "error": str(e)})
        
        return {"results": results}
    except Exception as e:
        logger.error(f"Error bulk approving rewrites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pending-approval/bulk-reject")
async def bulk_reject_rewrites(
    requests: List[Dict[str, Any]]
):
    """Bulk reject rewrites"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        results = []
        
        for req in requests:
            rewrite_id = req.get("id")
            reason = req.get("reason")
            
            try:
                # Get current rewrite
                result = (
                    supabase.client.table("persona_transformations")
                    .select("*")
                    .eq("id", rewrite_id)
                    .single()
                    .execute()
                )
                
                if not result.data:
                    results.append({"id": rewrite_id, "success": False, "error": "Not found"})
                    continue
                
                rewrite = result.data
                
                # Update metadata
                metadata = rewrite.get("metadata", {})
                if isinstance(metadata, str):
                    try:
                        import json
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}
                
                metadata["rejected_at"] = datetime.now(timezone.utc).isoformat()
                metadata["rejected"] = True
                if reason:
                    metadata["rejection_reason"] = reason
                
                # Update in database
                updated = (
                    supabase.client.table("persona_transformations")
                    .update({
                        "status": "rejected",
                        "metadata": metadata,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    .eq("id", rewrite_id)
                    .execute()
                )
                
                results.append({"id": rewrite_id, "success": True})
            except Exception as e:
                results.append({"id": rewrite_id, "success": False, "error": str(e)})
        
        return {"results": results}
    except Exception as e:
        logger.error(f"Error bulk rejecting rewrites: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/pending-approval/{id}")
async def update_rewrite_content(
    id: int,
    content: str
):
    """Update rewrite content"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        
        # Update content
        updated = (
            supabase.client.table("persona_transformations")
            .update({
                "content": content,
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
            .eq("id", id)
            .execute()
        )
        
        if not updated.data:
            raise HTTPException(status_code=404, detail="Rewrite not found")
        
        return {"success": True, "rewrite": updated.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rewrite content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Post Verification API
@router.post("/verify/{post_id}")
async def verify_post_endpoint(
    post_id: str,
    verify_content: bool = Query(False, description="Also verify content matches")
):
    """Manually verify a posted content"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        from src.services.post_verification import verify_post
        
        supabase = SupabaseManager()
        
        # Get post
        result = (
            supabase.client.table("posted_content")
            .select("*")
            .eq("id", post_id)
            .single()
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        post = result.data
        post_url = post.get("post_url") or post.get("url")
        
        if not post_url:
            raise HTTPException(status_code=400, detail="Post URL not available")
        
        # Verify URL
        expected_content = post.get("content") or post.get("initial_text")
        verification = await verify_post(
            post_url,
            expected_content=expected_content,
            verify_content=verify_content
        )
        
        # Update database
        verification_status = "verified" if verification.get("verified") else "failed"
        update_data = {
            "verification_status": verification_status,
            "verified_at": verification.get("verified_at"),
            "verification_result": verification
        }
        
        updated = (
            supabase.client.table("posted_content")
            .update(update_data)
            .eq("id", post_id)
            .execute()
        )
        
        return {
            "post_id": post_id,
            "verification": verification,
            "updated": updated.data[0] if updated.data else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying post: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/verify/bulk")
async def bulk_verify_posts(
    post_ids: List[str],
    verify_content: bool = False
):
    """Bulk verify multiple posts"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        from src.services.post_verification import verify_post
        
        supabase = SupabaseManager()
        results = []
        
        for post_id in post_ids:
            try:
                # Get post
                result = (
                    supabase.client.table("posted_content")
                    .select("*")
                    .eq("id", post_id)
                    .single()
                    .execute()
                )
                
                if not result.data:
                    results.append({"post_id": post_id, "success": False, "error": "Not found"})
                    continue
                
                post = result.data
                post_url = post.get("post_url") or post.get("url")
                
                if not post_url:
                    results.append({"post_id": post_id, "success": False, "error": "No URL"})
                    continue
                
                # Verify
                expected_content = post.get("content") or post.get("initial_text")
                verification = await verify_post(
                    post_url,
                    expected_content=expected_content,
                    verify_content=verify_content
                )
                
                # Update database
                verification_status = "verified" if verification.get("verified") else "failed"
                update_data = {
                    "verification_status": verification_status,
                    "verified_at": verification.get("verified_at"),
                    "verification_result": verification
                }
                
                updated = (
                    supabase.client.table("posted_content")
                    .update(update_data)
                    .eq("id", post_id)
                    .execute()
                )
                
                results.append({
                    "post_id": post_id,
                    "success": True,
                    "verification": verification
                })
            except Exception as e:
                results.append({"post_id": post_id, "success": False, "error": str(e)})
        
        return {"results": results}
    except Exception as e:
        logger.error(f"Error bulk verifying posts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify/status/{post_id}")
async def get_verification_status(post_id: str):
    """Get verification status for a post"""
    try:
        from src.infrastructure.database.manager import SupabaseManager
        
        supabase = SupabaseManager()
        result = (
            supabase.client.table("posted_content")
            .select("id, verification_status, verified_at, verification_result")
            .eq("id", post_id)
            .single()
            .execute()
        )
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {
            "post_id": post_id,
            "verification_status": result.data.get("verification_status", "pending"),
            "verified_at": result.data.get("verified_at"),
            "verification_result": result.data.get("verification_result")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
