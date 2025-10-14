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
            if self._dupes and self._dupes.is_duplicate(post):
                return False
        except Exception:
            pass
        
        supabase_ok = False
        sqlite_ok = False
        
        # Try Supabase first (optional)
        if self._supabase is not None:
            try:
                supabase_ok = self._supabase.save_post(post)
            except Exception as e:
                # Supabase failed, but that's ok - we'll save locally
                pass
        
        # Always save to SQLite (primary storage)
        if self._sqlite is not None:
            try:
                sqlite_ok = self._sqlite.save_post(post)
            except Exception:
                pass
        
        # Success if EITHER storage succeeded (prioritize local)
        return sqlite_ok or supabase_ok

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


