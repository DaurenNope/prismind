#!/usr/bin/env python3
"""
SQLite adapter used as optional local cache mirror.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SQLiteAdapter:
    def __init__(self, db_path: str | None = None) -> None:
        # Use actual beyondlines.db in root, not var/beyondlines.db!
        path = Path(db_path) if db_path else Path("beyondlines.db")
        self.conn = sqlite3.connect(str(path))
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        # Don't create schema - beyondlines.db already exists with proper schema
        # Just ensure connection works
        cur = self.conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='posts'"
        )
        if not cur.fetchone():
            raise Exception(
                "beyondlines.db posts table not found - database may be missing or corrupted"
            )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS github_trending (
                period TEXT,
                full_name TEXT,
                url TEXT,
                description TEXT,
                language TEXT,
                stars INTEGER,
                collected_at TEXT,
                PRIMARY KEY (period, full_name)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_messages (
                channel_username TEXT,
                message_id TEXT,
                date TEXT,
                content TEXT,
                sender TEXT,
                message_url TEXT,
                views INTEGER,
                forwards INTEGER,
                replies INTEGER,
                reactions TEXT,
                collected_at TEXT,
                PRIMARY KEY (channel_username, message_id)
            )
            """
        )
        self.conn.commit()

    def get_posts(self, limit: int = 100, timeout: Optional[float] = 30.0) -> List[Dict[str, Any]]:
        """P2-4: Get posts with timeout protection"""
        cur = self.conn.cursor()
        try:
            # P2-4: Set SQLite timeout (in seconds)
            if timeout:
                self.conn.execute(f"PRAGMA busy_timeout = {int(timeout * 1000)}")  # Convert to milliseconds
            
            cur.execute(
                "SELECT id, post_id, platform, source, title, content, url, author, created_at FROM posts ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            # Fallback: order by rowid if created_at not available
            cur.execute(
                "SELECT id, post_id, platform, source, title, content, url, author, created_at FROM posts ORDER BY rowid DESC LIMIT ?",
                (limit,),
            )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def get_unanalyzed_posts(
        self, limit: int = 100, platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get posts that haven't been analyzed yet (analyzed_at IS NULL or ai_summary IS NULL)"""
        cur = self.conn.cursor()
        try:
            # Try analyzed_at first (Supabase schema)
            query = """
                SELECT * FROM posts
                WHERE (analyzed_at IS NULL OR analyzed_at = '')
                AND (ai_summary IS NULL OR ai_summary = '')
            """
            params = []

            if platforms:
                placeholders = ",".join(["?"] * len(platforms))
                query += f" AND platform IN ({placeholders})"
                params.extend(platforms)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cur.execute(query, params)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            result = [dict(zip(cols, r)) for r in rows]

            # Fallback: if no results, try analysis_timestamp (SQLite schema)
            if not result:
                query2 = """
                    SELECT * FROM posts
                    WHERE (analysis_timestamp IS NULL OR analysis_timestamp = '')
                    AND (ai_summary IS NULL OR ai_summary = '')
                """
                params2 = []

                if platforms:
                    placeholders = ",".join(["?"] * len(platforms))
                    query2 += f" AND platform IN ({placeholders})"
                    params2.extend(platforms)

                query2 += " ORDER BY created_at DESC LIMIT ?"
                params2.append(limit)

                cur.execute(query2, params2)
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                result = [dict(zip(cols, r)) for r in rows]

            return result
        except Exception as e:
            logger.error(f"get_unanalyzed_posts failed: {e}")
            return []

    def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific post by ID from SQLite cache."""
        if not post_id:
            return None
        
        cur = self.conn.cursor()
        try:
            cur.execute(
                "SELECT * FROM posts WHERE post_id = ? LIMIT 1",
                (post_id,)
            )
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            if row:
                return dict(zip(cols, row))
            return None
        except Exception as e:
            logger.error(f"Error getting post by ID from SQLite: {e}")
            return None

    def save_post(self, post: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        try:
            # Use actual beyondlines.db schema
            cur.execute(
                """
                INSERT OR IGNORE INTO posts (
                    post_id, platform, title, content, url, author, author_handle,
                    created_at, post_type, media_urls, hashtags, engagement, is_saved
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.get("post_id"),
                    post.get("platform"),
                    post.get("title", ""),
                    post.get("content", ""),
                    post.get("url", ""),
                    post.get("author", ""),
                    post.get("username") or post.get("author_handle", ""),
                    post.get("created_at"),
                    post.get("post_type", "post"),
                    str(post.get("media_urls", [])) if post.get("media_urls") else None,
                    str(post.get("hashtags", [])) if post.get("hashtags") else None,
                    str(post.get("engagement", {})) if post.get("engagement") else None,
                    True,
                ),
            )
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite save failed: {e}")
            return False

    def _ensure_sync_columns(self):
        """Ensure sync tracking columns exist in SQLite posts table"""
        cur = self.conn.cursor()
        try:
            # Check if columns exist
            cur.execute("PRAGMA table_info(posts)")
            columns = [col[1] for col in cur.fetchall()]

            # Add synced_to_supabase if missing
            if "synced_to_supabase" not in columns:
                cur.execute(
                    "ALTER TABLE posts ADD COLUMN synced_to_supabase BOOLEAN DEFAULT 0"
                )

            # Add synced_at if missing
            if "synced_at" not in columns:
                cur.execute("ALTER TABLE posts ADD COLUMN synced_at TIMESTAMP")

            # Add sync_error if missing
            if "sync_error" not in columns:
                cur.execute("ALTER TABLE posts ADD COLUMN sync_error TEXT")

            self.conn.commit()
        except Exception as e:
            logger.debug(f"Error ensuring sync columns: {e}")
            # Ignore if columns already exist

    def update_post(self, post_id: str, post: Dict[str, Any]) -> bool:
        if not post_id:
            return False

        # Ensure sync columns exist
        self._ensure_sync_columns()

        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                UPDATE posts SET
                  title = COALESCE(?, title),
                  content = COALESCE(?, content),
                  url = COALESCE(?, url),
                  author = COALESCE(?, author),
                  author_handle = COALESCE(?, author_handle),
                  post_type = COALESCE(?, post_type),
                  media_urls = COALESCE(?, media_urls),
                  hashtags = COALESCE(?, hashtags),
                  engagement = COALESCE(?, engagement),
                  ai_summary = COALESCE(?, ai_summary),
                  value_score = COALESCE(?, value_score),
                  quality_score = COALESCE(?, quality_score),
                  sentiment = COALESCE(?, sentiment),
                  key_concepts = COALESCE(?, key_concepts),
                  tags = COALESCE(?, tags),
                  analysis_model = COALESCE(?, analysis_model),
                  analyzed_at = COALESCE(?, analyzed_at),
                  analysis_timestamp = COALESCE(?, analysis_timestamp),
                  time_sensitive = COALESCE(?, time_sensitive),
                  urgency_score = COALESCE(?, urgency_score),
                  relevance_window = COALESCE(?, relevance_window),
                  time_sensitive_reasons = COALESCE(?, time_sensitive_reasons)
                WHERE post_id = ?
                """,
                (
                    post.get("title"),
                    post.get("content"),
                    post.get("url"),
                    post.get("author"),
                    post.get("username") or post.get("author_handle"),
                    post.get("post_type"),
                    str(post.get("media_urls"))
                    if post.get("media_urls") is not None
                    else None,
                    str(post.get("hashtags"))
                    if post.get("hashtags") is not None
                    else None,
                    str(post.get("engagement"))
                    if post.get("engagement") is not None
                    else None,
                    post.get("ai_summary"),
                    post.get("value_score"),
                    post.get("quality_score"),
                    post.get("sentiment"),
                    json.dumps(post.get("key_concepts"))
                    if isinstance(post.get("key_concepts"), list)
                    else None,
                    json.dumps(post.get("tags"))
                    if isinstance(post.get("tags"), list)
                    else None,
                    post.get("analysis_model"),
                    post.get("analyzed_at"),
                    post.get("analyzed_at") or post.get("analysis_timestamp"),
                    post.get("time_sensitive"),
                    post.get("urgency_score"),
                    post.get("relevance_window"),
                    json.dumps(post.get("time_sensitive_reasons"))
                    if isinstance(post.get("time_sensitive_reasons"), list)
                    else post.get("time_sensitive_reasons"),
                    post_id,
                ),
            )
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite update failed: {e}")
            return False

    def mark_synced_to_supabase(
        self, post_id: str, synced: bool = True, error: Optional[str] = None
    ):
        """Mark a post as synced (or failed to sync) to Supabase"""
        if not post_id:
            return
        self._ensure_sync_columns()
        cur = self.conn.cursor()
        try:
            from datetime import datetime

            if synced:
                cur.execute(
                    "UPDATE posts SET synced_to_supabase = 1, synced_at = ?, sync_error = NULL WHERE post_id = ?",
                    (datetime.utcnow().isoformat(), post_id),
                )
            else:
                cur.execute(
                    "UPDATE posts SET synced_to_supabase = 0, sync_error = ? WHERE post_id = ?",
                    (error or "Unknown error", post_id),
                )
            self.conn.commit()
        except Exception as e:
            logger.debug(f"Error marking sync status: {e}")

    def get_unsynced_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get posts that haven't been synced to Supabase"""
        self._ensure_sync_columns()
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                SELECT * FROM posts
                WHERE (synced_to_supabase IS NULL OR synced_to_supabase = 0)
                ORDER BY created_timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, r)) for r in rows]
        except Exception as e:
            logger.debug(f"Error getting unsynced posts: {e}")
            return []

    def get_sync_status(self) -> Dict[str, Any]:
        """Get sync status statistics"""
        self._ensure_sync_columns()
        cur = self.conn.cursor()
        try:
            # Total posts
            cur.execute("SELECT COUNT(*) FROM posts")
            total = cur.fetchone()[0]

            # Synced posts
            cur.execute("SELECT COUNT(*) FROM posts WHERE synced_to_supabase = 1")
            synced = cur.fetchone()[0]

            # Unsynced posts
            cur.execute(
                "SELECT COUNT(*) FROM posts WHERE (synced_to_supabase IS NULL OR synced_to_supabase = 0)"
            )
            unsynced = cur.fetchone()[0]

            # Failed syncs (with errors)
            cur.execute("SELECT COUNT(*) FROM posts WHERE sync_error IS NOT NULL")
            failed = cur.fetchone()[0]

            return {
                "total": total,
                "synced": synced,
                "unsynced": unsynced,
                "failed": failed,
                "sync_percentage": (synced / total * 100) if total > 0 else 0.0,
            }
        except Exception as e:
            logger.debug(f"Error getting sync status: {e}")
            return {
                "total": 0,
                "synced": 0,
                "unsynced": 0,
                "failed": 0,
                "sync_percentage": 0.0,
            }

    def save_github_trending_repo(self, repo_data: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT OR IGNORE INTO github_trending (period, full_name, url, description, language, stars, collected_at)
                VALUES (:period, :full_name, :url, :description, :language, :stars, :collected_at)
                """,
                repo_data,
            )
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def save_telegram_message(self, message_data: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        try:
            cur.execute(
                """
                INSERT OR IGNORE INTO telegram_messages (channel_username, message_id, date, content, sender, message_url, views, forwards, replies, reactions, collected_at)
                VALUES (:channel_username, :message_id, :date, :content, :sender, :message_url, :views, :forwards, :replies, :reactions, :collected_at)
                """,
                message_data,
            )
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def get_github_trending_repos(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT period, full_name, url, description, language, stars, collected_at FROM github_trending ORDER BY collected_at DESC LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def get_telegram_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT channel_username, message_id, date, content, sender, message_url, views, forwards, replies, reactions, collected_at FROM telegram_messages ORDER BY date DESC LIMIT ?",
            (limit,),
        )
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]
