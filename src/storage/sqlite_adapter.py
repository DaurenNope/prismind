#!/usr/bin/env python3
"""
SQLite adapter used as optional local cache mirror.
"""

from __future__ import annotations

import sqlite3
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SQLiteAdapter:
    def __init__(self, db_path: str | None = None) -> None:
        # Use actual prismind.db in root, not var/prismind.db!
        path = Path(db_path) if db_path else Path("prismind.db")
        self.conn = sqlite3.connect(str(path))
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        # Don't create schema - prismind.db already exists with proper schema
        # Just ensure connection works
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
        if not cur.fetchone():
            raise Exception("prismind.db posts table not found - database may be missing or corrupted")
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

    def get_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        try:
            cur.execute("SELECT id, post_id, platform, source, title, content, url, author, created_at FROM posts ORDER BY created_at DESC LIMIT ?", (limit,))
        except Exception:
            # Fallback: order by rowid if created_at not available
            cur.execute("SELECT id, post_id, platform, source, title, content, url, author, created_at FROM posts ORDER BY rowid DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def get_unanalyzed_posts(self, limit: int = 100, platforms: Optional[List[str]] = None) -> List[Dict[str, Any]]:
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
                placeholders = ','.join(['?'] * len(platforms))
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
                    placeholders = ','.join(['?'] * len(platforms))
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

    def save_post(self, post: Dict[str, Any]) -> bool:
        cur = self.conn.cursor()
        try:
            # Use actual prismind.db schema
            cur.execute(
                """
                INSERT OR IGNORE INTO posts (
                    post_id, platform, title, content, url, author, author_handle,
                    created_at, post_type, media_urls, hashtags, engagement, is_saved
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.get('post_id'),
                    post.get('platform'),
                    post.get('title', ''),
                    post.get('content', ''),
                    post.get('url', ''),
                    post.get('author', ''),
                    post.get('username') or post.get('author_handle', ''),
                    post.get('created_at'),
                    post.get('post_type', 'post'),
                    str(post.get('media_urls', [])) if post.get('media_urls') else None,
                    str(post.get('hashtags', [])) if post.get('hashtags') else None,
                    str(post.get('engagement', {})) if post.get('engagement') else None,
                    True
                )
            )
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite save failed: {e}")
            return False

    def update_post(self, post_id: str, post: Dict[str, Any]) -> bool:
        if not post_id:
            return False
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
                  analysis_model = COALESCE(?, analysis_model)
                WHERE post_id = ?
                """,
                (
                    post.get('title'),
                    post.get('content'),
                    post.get('url'),
                    post.get('author'),
                    post.get('username') or post.get('author_handle'),
                    post.get('post_type'),
                    str(post.get('media_urls')) if post.get('media_urls') is not None else None,
                    str(post.get('hashtags')) if post.get('hashtags') is not None else None,
                    str(post.get('engagement')) if post.get('engagement') is not None else None,
                    post.get('ai_summary'),
                    post.get('value_score'),
                    post.get('quality_score'),
                    post.get('sentiment'),
                    json.dumps(post.get('key_concepts')) if isinstance(post.get('key_concepts'), list) else None,
                    json.dumps(post.get('tags')) if isinstance(post.get('tags'), list) else None,
                    post.get('analysis_model'),
                    post_id,
                ),
            )
            self.conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.error(f"SQLite update failed: {e}")
            return False

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
        except Exception:
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
        except Exception:
            return False

    def get_github_trending_repos(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT period, full_name, url, description, language, stars, collected_at FROM github_trending ORDER BY collected_at DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]

    def get_telegram_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT channel_username, message_id, date, content, sender, message_url, views, forwards, replies, reactions, collected_at FROM telegram_messages ORDER BY date DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]


