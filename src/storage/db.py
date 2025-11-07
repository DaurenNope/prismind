#!/usr/bin/env python3
"""
Storage facade: Supabase primary with optional SQLite cache.

Provides a minimal, stable interface for saving and reading posts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.utils.config import get_config
from src.utils.duplicate_detector import DuplicateDetector


class StorageFacade:
    """Facade that writes to Supabase and optionally mirrors to SQLite cache."""

    def __init__(self) -> None:
        self.config = get_config()
        self._supabase = None
        self._sqlite = None
        self._dupes = None

        if self.config.flags.get("supabase_enabled", True):
            from src.storage.supabase_adapter import SupabaseAdapter
            self._supabase = SupabaseAdapter()

        if self.config.flags.get("enable_sqlite_cache", True):
            from src.storage.sqlite_adapter import SQLiteAdapter
            self._sqlite = SQLiteAdapter()
        # Initialize duplicate detector with available backends
        self._dupes = DuplicateDetector(db_manager=self, supabase_manager=None)

    # Write operations
    def save_post(self, post: Dict[str, Any]) -> bool:
        # Final gate: skip duplicates by normalized URL or content hash
        try:
            if self._dupes:
                # Check URL first (fastest)
                url = post.get('url', '')
                if url and self._dupes.is_duplicate_url(url):
                    return False
                
                # Check content hash (catches same content with different URLs)
                content = post.get('content', '')
                if content and self._dupes.is_duplicate_content(content):
                    return False
                
                # Full duplicate check (platform-specific)
                if self._dupes.is_duplicate(post):
                    return False
        except Exception as e:
            import logging
            logging.debug(f"Duplicate check failed: {e}")
            pass
        
        supabase_ok = False
        sqlite_ok = False
        
        # Try SQLite first (primary storage) - should always work even if validation fails
        if self._sqlite is not None:
            try:
                sqlite_ok = self._sqlite.save_post(post)
            except Exception as e:
                # Log SQLite errors but don't fail
                import logging
                logging.debug(f"SQLite save failed: {e}")
        
        # Try Supabase (optional - may fail validation, that's ok)
        if self._supabase is not None:
            try:
                supabase_ok = self._supabase.save_post(post)
            except Exception as e:
                # Supabase failed, but that's ok - we saved locally
                import logging
                logging.debug(f"Supabase save failed: {e}")
        
        # Success if EITHER storage succeeded (prioritize local)
        # SQLite is primary - if it succeeds, we're good
        success = sqlite_ok or supabase_ok
        
        # Track post save/update via DatabaseAgent for monitoring
        if success:
            try:
                from src.database.database_agent import DatabaseAgent
                agent = DatabaseAgent()
                # Track post operation (save or update)
                is_update = post.get('analyzed_at') or post.get('quality_score') or post.get('value_score')
                agent.record_post_operation(
                    post_id=post.get('post_id'),
                    platform=post.get('platform'),
                    operation='update' if is_update else 'insert',
                    quality_score=post.get('quality_score'),
                    value_score=post.get('value_score'),
                    has_analysis=bool(post.get('analyzed_at') or post.get('ai_summary'))
                )
            except Exception:
                # Don't fail if monitoring fails
                pass
        
        return success

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
            except Exception:
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_posts(limit=limit)
            except Exception:
                pass
        return []

    def get_unanalyzed_posts(self, limit: int = 100, platforms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get posts that haven't been analyzed yet (prefer Supabase; fallback to SQLite cache)."""
        if self._supabase is not None:
            try:
                return self._supabase.get_unanalyzed_posts(limit=limit, platforms=platforms)
            except Exception:
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_unanalyzed_posts(limit=limit, platforms=platforms)
            except Exception:
                pass
        return []

    def save_github_trending_repo(self, repo_data: Dict[str, Any]) -> bool:
        """Save GitHub trending repository to native table."""
        try:
            if self._dupes and self._dupes.is_duplicate_github(repo_data):
                return False
        except Exception:
            pass
        ok = False
        if self._supabase is not None:
            ok = self._supabase.save_github_trending_repo(repo_data) or ok
        if self._sqlite is not None:
            try:
                self._sqlite.save_github_trending_repo(repo_data)
            except Exception:
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
            except Exception:
                pass
        return ok

    def get_github_trending_repos(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get GitHub trending repositories."""
        if self._supabase is not None:
            try:
                return self._supabase.get_github_trending_repos(limit=limit)
            except Exception:
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_github_trending_repos(limit=limit)
            except Exception:
                pass
        return []

    def get_telegram_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get Telegram messages."""
        if self._supabase is not None:
            try:
                return self._supabase.get_telegram_messages(limit=limit)
            except Exception:
                pass
        if self._sqlite is not None:
            try:
                return self._sqlite.get_telegram_messages(limit=limit)
            except Exception:
                pass
        return []


_storage_singleton: Optional[StorageFacade] = None


def get_storage() -> StorageFacade:
    global _storage_singleton
    if _storage_singleton is None:
        _storage_singleton = StorageFacade()
    return _storage_singleton


