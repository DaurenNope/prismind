import logging

logger = logging.getLogger(__name__)
"""
Publishing API Routes
Handles scheduled posts, transformations, and publishing operations
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.utils.logging_config import get_logger

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
        from src.database.publishing.bridge import MimesisDB

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
        from src.database.publishing.bridge import MimesisDB

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
        from src.database.publishing.bridge import MimesisDB

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
        from src.database.publishing.bridge import MimesisDB

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
        from src.database.publishing.bridge import MimesisDB

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
        from src.database.publishing.bridge import MimesisDB

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

        from src.database.publishing.bridge import MimesisDB
        from src.publishing.worker import (
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
