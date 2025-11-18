#!/usr/bin/env python3
"""
Storage facade: Supabase primary with optional SQLite cache.

Provides a minimal, stable interface for saving and reading posts.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.utils.config import get_config
from src.utils.duplicate_detector import DuplicateDetector
from src.utils.logging_config import get_logger


class StorageFacade:
    """Facade that writes to Supabase and optionally mirrors to SQLite cache."""

    def __init__(self) -> None:
        self.config = get_config()
        self.logger = get_logger(__name__)
        self._supabase = None
        self._sqlite = None
        self._dupes = None

        if self.config.flags.get("supabase_enabled", True):
            from src.storage.supabase_adapter import SupabaseAdapter

            self._supabase = SupabaseAdapter()

        if self.config.flags.get("enable_sqlite_cache", True):
            try:
                from src.storage.sqlite_adapter import SQLiteAdapter

                self._sqlite = SQLiteAdapter()
            except Exception as exc:
                self.logger.warning(
                    f"SQLite cache unavailable (continuing without local cache): {exc}"
                )
                self._sqlite = None
        # Initialize duplicate detector with available backends
        self._dupes = DuplicateDetector(db_manager=self, supabase_manager=None)

    # Write operations
    def save_post(self, post: Dict[str, Any]) -> bool:
        post_id = post.get("post_id")
        platform_value = str(post.get("platform") or "").lower()
        if platform_value == "reddit":
            normalized_id = self._normalize_reddit_post_id(post_id)
            if normalized_id:
                post["post_id"] = normalized_id
                post_id = normalized_id

        supabase_ok = False
        sqlite_ok = False

        # ALWAYS stamp ingest time for reliable "latest arrivals" sorting
        # This is critical - collected_at must ALWAYS be set
        try:
            if "collected_at" not in post or not post.get("collected_at"):
                post["collected_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            # If setting collected_at fails, log it but continue
            self.logger.warning(f"Failed to set collected_at: {e}")
            try:
                post["collected_at"] = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

        # First attempt to update existing local record; if it succeeds, skip duplicate gate
        updated_existing = False
        if post_id and self._sqlite is not None:
            try:
                updated_existing = bool(self._sqlite.update_post(post_id, post))
                if updated_existing:
                    sqlite_ok = True
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"⚠️ SQLite update failed during save_post: {e}", exc_info=True
                )

        # If no existing record was updated, enforce duplicate rules before insert
        duplicate_detected = False
        if not updated_existing:
            try:
                if self._dupes:
                    url = post.get("url", "")
                    if url and self._dupes.is_duplicate_url(url):
                        self.logger.info(
                            f"🔁 Duplicate URL detected, updating existing entry: {url} (post_id: {post_id})"
                        )
                        duplicate_detected = True

                    content = post.get("content", "")
                    if content and self._dupes.is_duplicate_content(content):
                        self.logger.info(
                            f"🔁 Duplicate content detected, refreshing entry (post_id: {post_id})"
                        )
                        duplicate_detected = True

                    if self._dupes.is_duplicate(post):
                        self.logger.info(
                            f"🔁 Duplicate post detected via is_duplicate(); refreshing (post_id: {post_id}, platform: {post.get('platform')})"
                        )
                        duplicate_detected = True
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ Duplicate check failed: {e}", exc_info=True)

            # Try SQLite insert (primary storage)
            if self._sqlite is not None and not duplicate_detected:
                try:
                    sqlite_ok = self._sqlite.save_post(post)
                except Exception as e:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"❌ SQLite save failed: {e}", exc_info=True)

        # Supabase write (upsert) -- attempt even if local update succeeded
        if self._supabase is not None:
            try:
                supabase_ok = self._supabase.save_post(post) or supabase_ok
                if not supabase_ok:
                    self.logger.warning(
                        f"❌ Supabase save returned False (post_id: {post_id}, platform: {post.get('platform')})"
                    )
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"❌ Supabase save failed: {e}", exc_info=True)

        success = sqlite_ok or supabase_ok

        if not success:
            self.logger.warning(
                f"❌ StorageFacade save_post failed for post_id: {post_id}, "
                f"platform: {post.get('platform')}, "
                f"sqlite_ok: {sqlite_ok}, supabase_ok: {supabase_ok}, "
                f"url: {post.get('url', 'N/A')[:50]}"
            )

        # DatabaseAgent: Proactive validation and monitoring (like a DBA)
        if success:
            try:
                from src.database.database_agent import DatabaseAgent

                agent = DatabaseAgent()

                # Let DatabaseAgent do comprehensive validation and monitoring
                # It will:
                # 1. Validate the post (double-check)
                # 2. Check data quality
                # 3. Check for common issues
                # 4. Track the operation
                # 5. Alert on problems
                agent.validate_and_monitor_post(post)
            except Exception as e:
                # Log but don't fail - monitoring shouldn't break saves
                import logging

                logging.debug(f"DatabaseAgent monitoring failed: {e}")

        return success

    @staticmethod
    def _normalize_reddit_post_id(post_id: Any) -> Optional[str]:
        """Ensure Reddit post IDs always include the t3_ prefix."""
        if not post_id:
            return None
        post_id_str = str(post_id).strip()
        if not post_id_str:
            return None
        cleaned_suffix = post_id_str.replace("t3_", "").replace("T3_", "").strip()
        return f"t3_{cleaned_suffix}"

    def save_posts(self, posts: List[Dict[str, Any]]) -> int:
        saved = 0
        for p in posts:
            if self.save_post(p):
                saved += 1
        return saved

    # Read operations (prefer Supabase; fallback to SQLite cache)
    def get_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get posts from storage."""
        if self._supabase is not None:
            try:
                return self._supabase.get_posts(limit=limit)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_posts(limit=limit)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        return []

    def get_unanalyzed_posts(
        self, limit: int = 100, platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get posts that haven't been analyzed yet (prefer Supabase; fallback to SQLite cache)."""
        if self._supabase is not None:
            try:
                return self._supabase.get_unanalyzed_posts(
                    limit=limit, platforms=platforms
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_unanalyzed_posts(
                    limit=limit, platforms=platforms
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        return []

    def save_github_trending_repo(self, repo_data: Dict[str, Any]) -> bool:
        """Save GitHub trending repository to native table."""
        try:
            if self._dupes and self._dupes.is_duplicate_github(repo_data):
                return False
        except Exception as e:
            logger.error(f"Error: {e}")
            pass
        ok = False
        if self._supabase is not None:
            ok = self._supabase.save_github_trending_repo(repo_data) or ok
        if self._sqlite is not None:
            try:
                self._sqlite.save_github_trending_repo(repo_data)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        return ok

    def save_telegram_message(self, message_data: Dict[str, Any]) -> bool:
        """Save Telegram message to native table."""
        ok = False
        if self._supabase is not None:
            ok = self._supabase.save_telegram_message(message_data) or ok
        if self._sqlite is not None:
            try:
                self._sqlite.save_telegram_message(message_data)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        return ok

    def get_github_trending_repos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get GitHub trending repositories."""
        if self._supabase is not None:
            try:
                return self._supabase.get_github_trending_repos(limit=limit)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_github_trending_repos(limit=limit)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        return []

    def get_telegram_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get Telegram messages."""
        if self._supabase is not None:
            try:
                return self._supabase.get_telegram_messages(limit=limit)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_telegram_messages(limit=limit)
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        return []

    def query_usable_posts(
        self,
        profile_key: str,
        limit: int = 20,
        min_quality_score: float = 7.0,
        min_value_score: float = 7.0,
        min_rewrite_score: float = 7.0,
        time_windows: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Query usable_posts table for a specific profile.

        Args:
            profile_key: Profile identifier (e.g., 'qronoya')
            limit: Maximum number of posts
            min_quality_score: Minimum quality threshold
            min_value_score: Minimum value threshold
            min_rewrite_score: Minimum rewrite threshold
            time_windows: Filter by relevance_window

        Returns:
            List of post dicts
        """
        if self._supabase is not None:
            try:
                from supabase import create_client

                # Build query
                query = self._supabase.client.table("usable_posts").select("*")
                query = query.eq("best_persona_key", profile_key)
                query = query.gte("quality_score", min_quality_score)
                query = query.gte("value_score", min_value_score)
                query = query.gte("rewrite_score", min_rewrite_score)

                if time_windows:
                    query = query.in_("relevance_window", time_windows)

                query = query.order("urgency_score", desc=True)
                query = query.order("rewrite_score", desc=True)
                query = query.order("created_at", desc=True)
                query = query.limit(limit)

                response = query.execute()
                return response.data if response.data else []

            except Exception as e:
                import logging

                logging.error(f"Error querying usable_posts: {e}")
                pass

        return []

    # --------------- Publishing Table Methods ---------------
    # These methods handle all publishing-related tables through StorageFacade

    def save_transformation(self, transformation: Dict[str, Any]) -> bool:
        """
        Save a rewrite transformation to mimesis_transformations table.
        Syncs to Supabase (publishing tables are Supabase-only).
        """
        if not transformation.get("persona_key"):
            self.logger.error("save_transformation: missing persona_key")
            return False

        if not self._supabase:
            self.logger.warning("save_transformation: Supabase not available")
            return False

        try:
            result = (
                self._supabase.client.table("mimesis_transformations")
                .upsert(transformation, on_conflict="id")  # Update if exists
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            self.logger.error(f"❌ Supabase transformation save failed: {e}")
            return False

    def save_scheduled_post(self, scheduled: Dict[str, Any]) -> bool:
        """Save a scheduled post to scheduled_posts table."""
        if not scheduled.get("content"):
            self.logger.error("save_scheduled_post: missing content")
            return False

        if not self._supabase:
            self.logger.warning("save_scheduled_post: Supabase not available")
            return False

        # Ensure personality_key is set (schema requires it)
        if "personality_key" not in scheduled and "persona_key" in scheduled:
            scheduled["personality_key"] = scheduled["persona_key"]
        elif "persona_key" not in scheduled and "personality_key" in scheduled:
            scheduled["persona_key"] = scheduled["personality_key"]

        try:
            result = (
                self._supabase.client.table("scheduled_posts")
                .upsert(scheduled, on_conflict="id")
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            self.logger.error(f"❌ Supabase scheduled_post save failed: {e}")
            return False

    def update_scheduled_post(self, scheduled_id: int, updates: Dict[str, Any]) -> bool:
        """Update a scheduled post by ID."""
        if not self._supabase:
            return False

        try:
            result = (
                self._supabase.client.table("scheduled_posts")
                .update(updates)
                .eq("id", scheduled_id)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            self.logger.error(f"❌ Supabase scheduled_post update failed: {e}")
            return False

    def save_posted_content(self, posted: Dict[str, Any]) -> bool:
        """Save posted content record to posted_content table."""
        if not self._supabase:
            return False

        try:
            result = (
                self._supabase.client.table("posted_content")
                .upsert(posted, on_conflict="id")
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            self.logger.error(f"❌ Supabase posted_content save failed: {e}")
            return False

    def save_rewrite_feedback(self, feedback: Dict[str, Any]) -> bool:
        """Save rewrite feedback to rewrite_feedback table."""
        if not self._supabase:
            return False

        try:
            result = (
                self._supabase.client.table("rewrite_feedback")
                .upsert(feedback, on_conflict="id")
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            self.logger.error(f"❌ Supabase rewrite_feedback save failed: {e}")
            return False


_storage_singleton: Optional[StorageFacade] = None


def get_storage() -> StorageFacade:
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = StorageFacade()
    return _storage_singleton
