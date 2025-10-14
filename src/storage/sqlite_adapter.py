#!/usr/bin/env python3
"""
SQLite adapter used as optional local cache mirror.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List
from pathlib import Path


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
        cur.execute("SELECT id, post_id, platform, source, title, content, url, author, created_at FROM posts ORDER BY inserted_at DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return [dict(zip(cols, r)) for r in rows]

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
            print(f"SQLite save failed: {e}")
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


