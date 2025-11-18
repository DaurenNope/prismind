#!/usr/bin/env python3
"""
Supabase adapter for primary storage operations.
"""

import asyncio
import os
from typing import Any, Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

from src.database.manager import SupabaseManager
from src.services.supabase.post_inserter import PostInserter


class SupabaseAdapter:
    def __init__(self) -> None:
        self.client = SupabaseManager().client
        # Create a simple duplicate checker wrapper
        from src.utils.duplicate_detector import DuplicateDetector

        class DuplicateCheckerWrapper:
            def __init__(self, detector):
                self.detector = detector

            def check_duplicate_post(self, content, author, platform, url=None):
                # Convert to the format expected by DuplicateDetector
                item = {
                    "content": content,
                    "author": author,
                    "platform": platform,
                    "url": url,
                }
                return self.detector.is_duplicate(item)

        duplicate_checker = DuplicateCheckerWrapper(
            DuplicateDetector(db_manager=None, supabase_manager=None)
        )
        self.post_inserter = PostInserter(self.client, duplicate_checker)

        # Adapter-level auto-analysis is disabled; analysis handled by post_analyzer pipeline
        self.auto_analyze = False
        self._analyzer = None

    def save_post(self, post: Dict[str, Any]) -> bool:
        try:
            # VALIDATE POST BEFORE SAVING TO SUPABASE
            from src.utils.post_validator import validate_post

            validation = validate_post(post, strict=True)
            if not validation.is_valid:
                logger.error(f"❌ Supabase: Post validation failed - NOT saving")
                logger.error(f"   Post ID: {post.get('post_id')}")
                logger.error(f"   Platform: {post.get('platform')}")
                logger.error(f"   URL: {post.get('url', 'N/A')}")
                logger.error(f"   Errors: {', '.join(validation.errors)}")
                if validation.warnings:
                    logger.warning(f"   Warnings: {', '.join(validation.warnings)}")
                logger.error(f"   Content preview: {post.get('content', '')[:100]}...")
                return False

            # Auto-analysis disabled at adapter level; rely on upstream analysis pipeline

            # Use PostInserter to properly map data to Supabase schema
            result = self.post_inserter.insert_post(post)
            return bool(result)
        except Exception as e:
            error_msg = str(e)
            # Treat duplicate key errors as success (idempotent insert) - don't log as error
            if (
                "23505" in error_msg
                or "duplicate key value" in error_msg.lower()
                or "posts_url_key" in error_msg
            ):
                logger.debug("Supabase duplicate on insert; treating as success")
                return True
            logger.error(f"Error saving post to Supabase: {error_msg}")
            return False

    def _run_analysis(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Deprecated: analysis is handled upstream."""
        return post

    def get_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            result = (
                self.client.table("posts")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return getattr(result, "data", []) or []
        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    def get_unanalyzed_posts(
        self, limit: int = 100, platforms: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get posts that haven't been analyzed yet (analyzed_at IS NULL)"""
        try:
            query = (
                self.client.table("posts")
                .select("*")
                .is_("analyzed_at", "null")
                .order("created_at", desc=True)
            )

            # Filter by platforms if provided
            if platforms:
                query = query.in_("platform", platforms)

            result = query.limit(limit).execute()
            data = getattr(result, "data", []) or []

            # Fallback: if no posts with analyzed_at null, check for missing ai_summary
            if not data:
                query2 = (
                    self.client.table("posts")
                    .select("*")
                    .or_("ai_summary.is.null,ai_summary.eq.")
                    .order("created_at", desc=True)
                )
                if platforms:
                    query2 = query2.in_("platform", platforms)
                result2 = query2.limit(limit).execute()
                data = getattr(result2, "data", []) or []

            return data
        except Exception as e:
            logger.debug(f"get_unanalyzed_posts failed: {e}")
            return []

    def save_github_trending_repo(self, repo_data: Dict[str, Any]) -> bool:
        try:
            result = (
                self.client.table("github_trending")
                .upsert(repo_data, on_conflict="period,full_name")
                .execute()
            )
            return bool(getattr(result, "data", None))
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def save_telegram_message(self, message_data: Dict[str, Any]) -> bool:
        try:
            result = (
                self.client.table("telegram_messages").insert(message_data).execute()
            )
            return bool(getattr(result, "data", None))
        except Exception as e:
            logger.error(f"Error: {e}")
            return False

    def get_github_trending_repos(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            result = (
                self.client.table("github_trending")
                .select("*")
                .order("collected_at", desc=True)
                .limit(limit)
                .execute()
            )
            return getattr(result, "data", []) or []
        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    def get_telegram_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            result = (
                self.client.table("telegram_messages")
                .select("*")
                .order("date", desc=True)
                .limit(limit)
                .execute()
            )
            return getattr(result, "data", []) or []
        except Exception as e:
            logger.error(f"Error: {e}")
            return []
