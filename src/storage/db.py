#!/usr/bin/env python3
"""
Storage facade: Supabase primary with optional SQLite cache.

Provides a minimal, stable interface for saving and reading posts.
"""

from __future__ import annotations

import asyncio
import queue
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.shared.utils.config import get_config
from src.shared.utils.duplicate_detector import DuplicateDetector
from src.shared.utils.logging_config import get_logger


class StorageFacade:
    """Facade that writes to Supabase and optionally mirrors to SQLite cache."""

    def __init__(self) -> None:
        self.config = get_config()
        self.logger = get_logger(__name__)
        self._supabase = None
        self._sqlite = None
        self._dupes = None
        
        # P0-1: Async SQLite sync queue (non-blocking cache sync)
        self._sqlite_sync_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._sync_worker_thread: Optional[threading.Thread] = None
        self._sync_worker_running = False
        self._start_sync_worker()
        
        # P1-1: Thread-safe lock for duplicate detection (prevents race conditions)
        # This makes duplicate check + write operation atomic within a single process
        self._duplicate_check_lock = threading.Lock()

        if self.config.flags.get("supabase_enabled", True):
            from src.infrastructure.database.storage.supabase_adapter import SupabaseAdapter

            self._supabase = SupabaseAdapter()

        if self.config.flags.get("enable_sqlite_cache", True):
            try:
                from src.infrastructure.database.storage.sqlite_adapter import SQLiteAdapter

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
        """P2-3: Refactored save_post with extracted methods for single responsibility"""
        # Step 1: Normalize post ID
        post_id = self._normalize_post_id(post)
        
        # Step 2: Set collected_at timestamp
        self._ensure_collected_at(post)
        
        # P1-1: Atomic duplicate check + write operation (prevents race conditions)
        # Use lock to make duplicate detection and write atomic within a single process
        with self._duplicate_check_lock:
            # Step 3: Check for existing record (read-only)
            updated_existing = self._check_existing_record(post_id)
            
            # Step 4: Detect duplicates (atomic with write)
            duplicate_detected = self._detect_duplicates(post, post_id, updated_existing)
            
            # Step 5: Write to Supabase (PRIMARY) - atomic with duplicate check
            supabase_ok = self._write_to_supabase(post, post_id)
        
        # Step 6: Determine success (Supabase only)
        success = supabase_ok
        
        # Step 7: Queue async SQLite sync (non-blocking)
        if success:
            self._queue_sqlite_sync_safe(post, post_id)
        
        # Step 8: Log failure if needed
        if not success:
            self._log_save_failure(post, post_id, supabase_ok)
        
        # Step 9: Post-save monitoring (non-blocking)
        if success:
            self._monitor_post_save(post)
        
        return success

    def check_batch_duplicates(self, posts: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Check duplicates for multiple posts in single query.

        Args:
            posts: List of post dictionaries

        Returns:
            Dict mapping post_id to is_duplicate (True/False)
        """
        if not posts:
            return {}

        with self._duplicate_check_lock:
            post_ids = [self._normalize_post_id(p) for p in posts if self._normalize_post_id(p)]
            urls = [p.get("url", "").strip() for p in posts if p.get("url")]

            duplicates = {}

            # Batch query Supabase
            if self._supabase and post_ids:
                try:
                    # Process in batches of 100 (Supabase limit)
                    all_existing_ids = set()
                    all_existing_urls = set()

                    for i in range(0, len(post_ids), 100):
                        batch_ids = post_ids[i:i + 100]
                        existing = (
                            self._supabase.client.table("posts")
                            .select("post_id, url")
                            .in_("post_id", batch_ids)
                            .execute()
                        )

                        if existing.data:
                            all_existing_ids.update(row.get("post_id") for row in existing.data if row.get("post_id"))
                            all_existing_urls.update(row.get("url") for row in existing.data if row.get("url"))

                    # Check URLs separately if we have URLs but not IDs
                    if urls:
                        # Query by URL (need to check each URL or use OR conditions)
                        # For simplicity, check unique URLs in batches
                        unique_urls = list(set(urls))
                        for url in unique_urls[:100]:  # Limit to 100 URLs
                            try:
                                url_result = (
                                    self._supabase.client.table("posts")
                                    .select("url")
                                    .eq("url", url)
                                    .limit(1)
                                    .execute()
                                )
                                if url_result.data:
                                    all_existing_urls.add(url)
                            except Exception:
                                pass  # Skip if URL query fails

                    # Build duplicate mapping
                    for post in posts:
                        post_id = self._normalize_post_id(post)
                        url = post.get("url", "").strip()
                        is_dup = (post_id and post_id in all_existing_ids) or (url and url in all_existing_urls)
                        key = post_id or url or f"post_{posts.index(post)}"
                        duplicates[key] = is_dup

                except Exception as e:
                    self.logger.warning(f"Batch duplicate check failed: {e}")
                    # Return all as non-duplicates on error (conservative approach)
                    duplicates = {
                        self._normalize_post_id(p) or p.get("url", "") or str(i): False
                        for i, p in enumerate(posts)
                    }
            else:
                # No Supabase or no post_ids - return all as non-duplicates
                duplicates = {
                    self._normalize_post_id(p) or p.get("url", "") or str(i): False
                    for i, p in enumerate(posts)
                }

            return duplicates

    # P2-3: Extracted methods for single responsibility
    
    def _normalize_post_id(self, post: Dict[str, Any]) -> Optional[str]:
        """Normalize post ID (e.g., Reddit t3_ prefix)"""
        post_id = post.get("post_id")
        platform_value = str(post.get("platform") or "").lower()
        if platform_value == "reddit":
            normalized_id = self._normalize_reddit_post_id(post_id)
            if normalized_id:
                post["post_id"] = normalized_id
                return normalized_id
        return post_id

    def _ensure_collected_at(self, post: Dict[str, Any]) -> None:
        """Ensure collected_at timestamp is set"""
        try:
            if "collected_at" not in post or not post.get("collected_at"):
                post["collected_at"] = datetime.now(timezone.utc).isoformat()
        except Exception as e:
            self.logger.warning(f"Failed to set collected_at: {e}")
            try:
                post["collected_at"] = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                self.logger.error(f"Error: {e}")

    def _check_existing_record(self, post_id: Optional[str]) -> bool:
        """Check if record exists in SQLite cache (read-only)"""
        if post_id and self._sqlite is not None:
            try:
                existing = self._sqlite.get_post(post_id)
                return existing is not None
            except Exception as e:
                self.logger.debug(f"⚠️ SQLite read check failed (non-critical): {e}")
        return False

    def _detect_duplicates(self, post: Dict[str, Any], post_id: Optional[str], updated_existing: bool) -> bool:
        """Detect duplicate posts using duplicate detector"""
        if updated_existing or not self._dupes:
            return False
        
        try:
            url = post.get("url", "")
            if url and self._dupes.is_duplicate_url(url):
                self.logger.info(f"🔁 Duplicate URL detected: {url} (post_id: {post_id})")
                return True

            content = post.get("content", "")
            if content and self._dupes.is_duplicate_content(content):
                self.logger.info(f"🔁 Duplicate content detected (post_id: {post_id})")
                return True

            if self._dupes.is_duplicate(post):
                self.logger.info(f"🔁 Duplicate post detected (post_id: {post_id}, platform: {post.get('platform')})")
                return True
        except Exception as e:
            self.logger.warning(f"⚠️ Duplicate check failed: {e}", exc_info=True)
        
        return False

    def _write_to_supabase(self, post: Dict[str, Any], post_id: Optional[str]) -> bool:
        """Write post to Supabase (PRIMARY storage)"""
        if self._supabase is None:
            return False
        
        try:
            supabase_ok = self._supabase.save_post(post)
            if not supabase_ok:
                self.logger.warning(
                    f"❌ Supabase save returned False (post_id: {post_id}, platform: {post.get('platform')})"
                )
            return supabase_ok
        except Exception as e:
            self.logger.error(f"❌ Supabase save failed: {e}", exc_info=True)
            return False

    def _queue_sqlite_sync_safe(self, post: Dict[str, Any], post_id: Optional[str]) -> None:
        """Queue SQLite sync safely (non-blocking, best effort)"""
        if self._sqlite is None:
            return
        
        try:
            self._queue_sqlite_sync(post)
        except queue.Full:
            self.logger.warning(f"⚠️ SQLite sync queue full (non-critical) for post_id: {post_id}")
        except Exception as e:
            self.logger.debug(f"⚠️ SQLite sync queue error (non-critical): {e}")

    def _log_save_failure(self, post: Dict[str, Any], post_id: Optional[str], supabase_ok: bool) -> None:
        """Log save failure with context"""
        self.logger.warning(
            f"❌ StorageFacade save_post failed for post_id: {post_id}, "
            f"platform: {post.get('platform')}, "
            f"supabase_ok: {supabase_ok}, "
            f"url: {post.get('url', 'N/A')[:50]}"
        )

    def _monitor_post_save(self, post: Dict[str, Any]) -> None:
        """Post-save monitoring via DatabaseAgent (non-blocking)"""
        try:
            from src.infrastructure.database.database_agent import get_database_agent
            agent = get_database_agent()
            agent.validate_and_monitor_post(post)
        except Exception as e:
            import logging
            logging.debug(f"DatabaseAgent monitoring failed: {e}")

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

    def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific post by ID from storage."""
        # Normalize post_id
        normalized_id = self._normalize_post_id({"post_id": post_id}) or post_id

        # Try Supabase first
        if self._supabase is not None:
            try:
                return self._supabase.get_post_by_id(normalized_id)
            except Exception as e:
                self.logger.error(f"Error getting post from Supabase: {e}")

        # Fallback to SQLite
        if self._sqlite is not None:
            try:
                return self._sqlite.get_post_by_id(normalized_id)
            except Exception as e:
                self.logger.error(f"Error getting post from SQLite: {e}")

        return None

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
        Save a rewrite transformation to persona_transformations table.
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
                self._supabase.client.table("persona_transformations")
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

    # P0-1: Async SQLite sync methods
    def _queue_sqlite_sync(self, post: Dict[str, Any]) -> None:
        """Queue post for async SQLite sync (non-blocking)"""
        try:
            self._sqlite_sync_queue.put_nowait(post)
        except queue.Full:
            # Queue full - log warning but don't block
            self.logger.warning(
                f"⚠️ SQLite sync queue full, dropping post {post.get('post_id', 'unknown')}"
            )
            raise

    def _start_sync_worker(self) -> None:
        """Start background thread for async SQLite sync"""
        if self._sync_worker_running:
            return
        
        def sync_worker():
            """Background worker that syncs posts to SQLite cache"""
            self._sync_worker_running = True
            self.logger.info("🔄 SQLite sync worker started")
            
            while self._sync_worker_running:
                try:
                    # Get post from queue (blocking with timeout)
                    try:
                        post = self._sqlite_sync_queue.get(timeout=1.0)
                    except queue.Empty:
                        continue
                    
                    # Sync to SQLite (best effort)
                    if self._sqlite is not None:
                        try:
                            self._sqlite.save_post(post)
                            self.logger.debug(
                                f"✅ SQLite cache synced: {post.get('post_id', 'unknown')}"
                            )
                        except Exception as e:
                            self.logger.debug(
                                f"⚠️ SQLite sync failed (non-critical): {e}"
                            )
                    
                    # Mark task as done
                    self._sqlite_sync_queue.task_done()
                    
                except Exception as e:
                    self.logger.error(f"❌ SQLite sync worker error: {e}", exc_info=True)
            
            self.logger.info("🛑 SQLite sync worker stopped")
        
        # Start worker thread
        self._sync_worker_thread = threading.Thread(
            target=sync_worker,
            daemon=True,
            name="SQLiteSyncWorker"
        )
        self._sync_worker_thread.start()

    def __del__(self):
        """Cleanup: stop sync worker on destruction"""
        self._sync_worker_running = False
        if self._sync_worker_thread and self._sync_worker_thread.is_alive():
            self._sync_worker_thread.join(timeout=1.0)


_storage_singleton: Optional[StorageFacade] = None
_storage_lock = threading.Lock()


def get_storage() -> StorageFacade:
    """Thread-safe singleton for StorageFacade"""
    global _storage_singleton
    if _storage_singleton is None:
        with _storage_lock:
            # Double-check pattern to prevent race condition
            if _storage_singleton is None:
                _storage_singleton = StorageFacade()
    return _storage_singleton
