import logging
from typing import Any, Dict, List, Optional

from src.database.manager import SupabaseManager

logger = logging.getLogger(__name__)


class MimesisDB:
    """Thin adapter for Mimesis tables using the shared SupabaseManager."""

    def __init__(self, manager: Optional[SupabaseManager] = None) -> None:
        self.sb = manager or SupabaseManager()

    def list_ready_transformations(
        self, persona_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List ready transformations, with error handling."""
        try:
            q = (
                self.sb.client.table("mimesis_transformations")
                .select("*")
                .eq("ready_for_posting", True)
            )
            if persona_key:
                q = q.eq("persona_key", persona_key)
            return q.order("created_at", desc=True).execute().data
        except Exception as e:
            logger.error(f"Failed to list ready transformations: {e}")
            return []  # Return empty list on error

    def list_due_posts(self) -> List[Dict[str, Any]]:
        """List due posts, with error handling."""
        try:
            # Check if Supabase client is available
            if not self.sb or not self.sb.client:
                logger.warning(
                    "Supabase client not available, skipping due posts check"
                )
                return []

            import socket
            from datetime import datetime, timezone

            now_iso = datetime.now(timezone.utc).isoformat()
            q = (
                self.sb.client.table("scheduled_posts")
                .select("*")
                .lte("scheduled_time", now_iso)  # Posts where scheduled_time <= now
                .in_("status", ["pending", "retry"])  # type: ignore[attr-defined]
            )
            return q.order("scheduled_time", desc=False).execute().data
        except (
            ConnectionError,
            ValueError,
            AttributeError,
            socket.gaierror,
            socket.herror,
        ) as e:
            # Network/DNS errors - fail gracefully (don't spam logs)
            logger.debug(
                f"Supabase unavailable for due posts check (DNS/network error): {e}"
            )
            return []
        except Exception as e:
            error_str = str(e)
            # Check for DNS errors in string form (supabase-py might wrap them)
            if (
                "nodename nor servname provided" in error_str
                or "Name or service not known" in error_str
            ):
                logger.debug(f"Supabase DNS error (Supabase may be unreachable): {e}")
                return []
            # Only log unexpected errors as error level
            logger.debug(f"Failed to list due posts: {e}")
            return []  # Return empty list on error

    def mark_posted(
        self,
        scheduled_id: int,
        platform_post_id: Optional[str] = None,
        post_url: Optional[str] = None,
    ) -> None:
        """Mark a scheduled post as posted and create posted_content record."""
        # First, get the scheduled post to extract required fields
        scheduled_post = (
            self.sb.client.table("scheduled_posts")
            .select("*")
            .eq("id", scheduled_id)
            .limit(1)
            .execute()
            .data
        )

        if not scheduled_post:
            logger.error(f"Scheduled post {scheduled_id} not found")
            return

        post_data = scheduled_post[0]

        # Update status to posted - use DatabaseAgent
        from src.database.database_agent import DatabaseAgent

        db_agent = DatabaseAgent()
        db_agent.update_scheduled_post(scheduled_id, {"status": "posted"})

        # Create posted_content record with all required fields
        posted_content = {
            "scheduled_post_id": scheduled_id,
            "personality_key": post_data.get("personality_key")
            or post_data.get("persona_key"),
            "persona_key": post_data.get("personality_key")
            or post_data.get("persona_key"),  # Support both
            "platform": post_data.get("platform"),
            "content": post_data.get("content"),
            "content_type": post_data.get("content_type"),
            "platform_post_id": platform_post_id,
        }

        # Add URL if provided
        if post_url:
            posted_content["post_url"] = post_url

        # Use DatabaseAgent (delegates to StorageFacade)
        from src.database.database_agent import DatabaseAgent

        db_agent = DatabaseAgent()
        db_agent.save_posted_content(posted_content)

    def insert_scheduled(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a scheduled post - uses DatabaseAgent (delegates to StorageFacade)."""
        try:
            from src.database.database_agent import DatabaseAgent

            db_agent = DatabaseAgent()
            if db_agent.save_scheduled_post(payload):
                # Get the inserted record
                try:
                    result = (
                        self.sb.client.table("scheduled_posts")
                        .select("*")
                        .eq("content", payload.get("content"))
                        .eq("scheduled_time", payload.get("scheduled_time"))
                        .limit(1)
                        .execute()
                    )
                    if result.data:
                        return result.data[0]
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass
                # Fallback: return payload with id if available
                return payload
            else:
                raise Exception("Failed to save scheduled post via DatabaseAgent")
        except Exception as e:
            logger.error(f"Error: {e}")
            error_msg = str(e)
            # Check if it's a Cloudflare 520 or connection error
            if (
                "520" in error_msg
                or "Web server is returning" in error_msg
                or "JSON could not be generated" in error_msg
            ):
                raise ConnectionError(
                    "Supabase is currently unavailable (Cloudflare 520 error). "
                    "Please try again in a few minutes."
                ) from e
            # Re-raise other errors as-is
            raise

    # Transformations editing/approval
    def list_transformations(
        self, persona_key: Optional[str] = None, ready_only: bool = False
    ) -> List[Dict[str, Any]]:
        q = self.sb.client.table("mimesis_transformations").select("*")
        if persona_key:
            q = q.eq("persona_key", persona_key)
        if ready_only:
            q = q.eq("ready_for_posting", True)
        return q.order("created_at", desc=True).execute().data

    def update_transformation(
        self, transformation_id: int, fields: Dict[str, Any]
    ) -> Dict[str, Any]:
        # Get existing transformation first
        existing = (
            self.sb.client.table("mimesis_transformations")
            .select("*")
            .eq("id", transformation_id)
            .limit(1)
            .execute()
        )
        if not existing.data:
            raise ValueError(f"Transformation {transformation_id} not found")

        # Merge fields and save via DatabaseAgent
        updated = {**existing.data[0], **fields}
        from src.database.database_agent import DatabaseAgent

        db_agent = DatabaseAgent()
        if db_agent.save_transformation(updated):
            return updated
        else:
            raise Exception("Failed to update transformation via DatabaseAgent")

    def delete_transformation(self, transformation_id: int) -> None:
        """Delete a transformation by ID"""
        self.sb.client.table("mimesis_transformations").delete().eq(
            "id", transformation_id
        ).execute()

    def delete_old_transformations(self, days: int = 30) -> int:
        """Delete transformations older than specified days. Returns count deleted."""
        from datetime import datetime, timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.isoformat()

        logger.info(
            f"Deleting transformations older than {cutoff_iso} (>{days} days old)"
        )

        # Get count before deletion
        try:
            count_query = (
                self.sb.client.table("mimesis_transformations")
                .select("*", count="exact")
                .lt("created_at", cutoff_iso)
                .execute()
            )
            count = getattr(count_query, "count", 0) or 0
            logger.info(f"Found {count} transformations to delete")
        except Exception as e:
            logger.error(f"Error counting transformations: {e}")
            count = 0

        # Delete old transformations
        try:
            result = (
                self.sb.client.table("mimesis_transformations")
                .delete()
                .lt("created_at", cutoff_iso)
                .execute()
            )
            # Supabase delete doesn't return count, so we use the count from the query
            logger.info(f"Delete operation completed")
            return count
        except Exception as e:
            logger.error(f"Error deleting transformations: {e}")
            raise

    def delete_all_transformations(self) -> int:
        """Delete ALL transformations. Returns count deleted."""
        logger.warning("Deleting ALL transformations")

        # Get count before deletion
        try:
            count_query = (
                self.sb.client.table("mimesis_transformations")
                .select("*", count="exact")
                .execute()
            )
            count = getattr(count_query, "count", 0) or 0
            logger.info(f"Found {count} total transformations to delete")
        except Exception as e:
            logger.error(f"Error counting transformations: {e}")
            count = 0

        # Delete all transformations
        try:
            # Delete all rows (no filter)
            self.sb.client.table("mimesis_transformations").delete().neq(
                "id", 0
            ).execute()
            logger.info(f"All transformations deleted")
            return count
        except Exception as e:
            logger.error(f"Error deleting all transformations: {e}")
            raise

    def approve_to_schedule(
        self,
        transformation_ids: List[int],
        platform: str,
        scheduled_at_iso: str,
    ) -> List[Dict[str, Any]]:
        approved: List[Dict[str, Any]] = []
        for tid in transformation_ids:
            # fetch transformation
            rows = (
                self.sb.client.table("mimesis_transformations")
                .select("*")
                .eq("id", tid)
                .limit(1)
                .execute()
                .data
            )
            if not rows:
                continue
            t = rows[0]
            # Database uses personality_key, normalize from either persona_key or personality_key
            persona_value = t.get("personality_key") or t.get("persona_key")
            # content_type: 'single_tweet' for twitter/threads, 'telegram_message' for telegram
            content_type_map = {
                "twitter": "single_tweet",
                "threads": "single_tweet",
                "telegram": "telegram_message",
            }
            payload = {
                "personality_key": persona_value,  # Support both schema variants
                "persona_key": persona_value,
                "platform": platform,
                "content": t.get("content"),
                "content_type": content_type_map.get(
                    platform, "single_tweet"
                ),  # Required by DB
                "scheduled_time": scheduled_at_iso,  # Mimesis uses scheduled_time, not scheduled_at
                "status": "pending",  # Database uses 'pending', not 'scheduled'
            }
            created = self.insert_scheduled(payload)
            # mark as ready
            self.update_transformation(tid, {"ready_for_posting": True})
            approved.append(created)
        return approved
