#!/usr/bin/env python3
"""
Orchestrator: single integration entry for Collect → Analyze → Store → Surface.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from src.utils.config import get_config
from src.storage.db import get_storage
from src.utils.logging import get_logger
from src.scrape_state_manager import ScrapeStateManager

logger = get_logger(__name__)


class Orchestrator:
    def __init__(self) -> None:
        self.config = get_config()
        self.storage = get_storage()
        self._ensure_state_sync()

    def _ensure_state_sync(self):
        """Ensure state database is synced with main database on initialization"""
        try:
            state_manager = ScrapeStateManager()
            state_manager.sync_state_from_main_db(force=False)
        except Exception as e:
            # Silent - state sync is automatic recovery, not critical
            pass

    async def collect_all(
        self, platforms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        # Default to bookmark platforms only; RSS discovery is separate
        plat = platforms or ["twitter", "reddit", "threads"]
        if not self.config.flags.get("enable_threads"):
            plat = [p for p in plat if p != "threads"]

        # Add optional sources based on flags
        if (
            self.config.flags.get("enable_github_trending")
            and "github_trending" not in plat
        ):
            plat.append("github_trending")
        if (
            self.config.flags.get("enable_telegram_channels")
            and "telegram_channels" not in plat
        ):
            plat.append("telegram_channels")

        results: Dict[str, Any] = {p: 0 for p in plat}
        results["errors"] = []

        async def run_one(name: str):
            try:
                count = await self.collect_platform(name)
                results[name] = count
                try:
                    from src.database.database_agent import DatabaseAgent
                    DatabaseAgent().record_collection_result(name, count, success=True)
                except Exception:
                    pass
            except Exception as exc:
                results["errors"].append(f"{name}: {exc}")
                try:
                    from src.database.database_agent import DatabaseAgent
                    DatabaseAgent().record_collection_result(name, 0, success=False, failure_reason=str(exc)[:200])
                except Exception:
                    pass

        # Bounded concurrency
        semaphore = asyncio.Semaphore(3)

        async def guarded(name: str):
            async with semaphore:
                await run_one(name)

        await asyncio.gather(*(guarded(p) for p in plat))
        results["total"] = sum(v for k, v in results.items() if isinstance(v, int))
        return results

    async def collect_platform(self, platform: str) -> int:
        # Shim DB manager that writes through storage facade
        class _ShimDB:
            def __init__(self, storage):
                self._s = storage

            def add_post(self, post):
                return self._s.save_post(post)

            def update_post(self, post_id: str, post_data: dict):
                # For the shim, we'll just save the post (upsert behavior)
                return self._s.save_post(post_data)

            def get_all_posts(self, include_deleted: bool = False):
                return self._s.get_posts(limit=10000)

            def get_post_by_id(self, post_id: str):
                # Simple implementation to check if post exists
                posts = self._s.get_posts(limit=10000)
                for post in posts:
                    if post.get("post_id") == post_id:
                        return post
                return None

        shim_db = _ShimDB(self.storage)

        # Optional Supabase manager for collectors that support cloud sync
        supabase_manager = None
        try:
            from src.database.manager import SupabaseManager

            supabase_manager = SupabaseManager()
        except Exception:
            supabase_manager = None

        # Get existing IDs and URLs to avoid duplicates (Supabase-first, no local fallback to avoid phantom duplicates)
        existing_ids = set()
        existing_urls = set()
        if supabase_manager:
            try:
                result = (
                    supabase_manager.client
                    .table("posts")
                    .select("post_id,url")
                    .eq("platform", platform)
                    .order("created_at", desc=True)
                    .limit(10000)
                    .execute()
                )
                for row in (result.data or []):
                    pid = (row.get("post_id") or "").strip()
                    url = (row.get("url") or "").strip()
                    if pid:
                        if platform == "reddit":
                            # Add both raw and fullname variants
                            if pid.startswith("t3_"):
                                existing_ids.add(pid)
                                existing_ids.add(pid.replace("t3_", ""))
                            else:
                                existing_ids.add(pid)
                                existing_ids.add(f"t3_{pid}")
                        else:
                            existing_ids.add(pid)
                    if url:
                        existing_urls.add(url)
            except Exception:
                # keep sets empty if Supabase unavailable to avoid false duplicates
                pass

        if platform == "twitter":
            from src.services.collection.platform_collectors import (
                collect_twitter_bookmarks,
            )

            count = await collect_twitter_bookmarks(
                db_manager=shim_db,
                existing_ids=existing_ids,
                existing_urls=existing_urls,
                supabase_manager=supabase_manager,
            )
            try:
                from src.database.database_agent import DatabaseAgent
                DatabaseAgent().record_collection_result(platform, count, success=True)
            except Exception:
                pass
            return count
        if platform == "reddit":
            from src.services.collection.platform_collectors import (
                collect_reddit_bookmarks,
            )

            count = await collect_reddit_bookmarks(
                db_manager=shim_db,
                existing_ids=existing_ids,
                existing_urls=existing_urls,
                supabase_manager=supabase_manager,
            )
            try:
                from src.database.database_agent import DatabaseAgent
                DatabaseAgent().record_collection_result(platform, count, success=True)
            except Exception:
                pass
            return count
        if platform == "threads":
            from src.services.collection.platform_collectors import (
                collect_threads_bookmarks,
            )

            count = await collect_threads_bookmarks(
                db_manager=shim_db,
                existing_ids=existing_ids,
                existing_urls=existing_urls,
                supabase_manager=supabase_manager,
            )
            # Optionally run analysis in a separate phase if enabled
            if os.environ.get("ANALYZE_AFTER_COLLECTION", "true").lower() in ("true", "1", "yes"):
                try:
                    from src.services.collection.platform_collectors import analyze_threads_posts
                    await analyze_threads_posts(shim_db, supabase_manager)
                except Exception:
                    pass
            try:
                from src.database.database_agent import DatabaseAgent
                DatabaseAgent().record_collection_result(platform, count, success=True)
            except Exception:
                pass
            return count
        if platform == "rss":
            # RSS discovery is separate from bookmarks collection
            # This should not be called when collecting bookmarks
            logger.info("RSS collection skipped - RSS discovery is handled separately")
            return 0
        if platform == "github_trending":
            if not self.config.flags.get("enable_github_trending"):
                return 0
            try:
                from scripts.github_trending_scraper import scrape_trending
                from datetime import datetime

                logger.info("Collecting GitHub trending repositories...")
                trending_data = scrape_trending()
                saved_count = 0

                for period, repos in trending_data.items():
                    for repo in repos:
                        repo_data = {
                            "period": period,
                            "full_name": repo["full_name"],
                            "url": repo["url"],
                            "description": repo.get("description", ""),
                            "language": repo.get("language", ""),
                            "stars": int(repo["stars"]),
                            "collected_at": datetime.now().isoformat(),
                        }
                        try:
                            # Save to native github_trending table
                            result = self.storage.save_github_trending_repo(repo_data)
                            if result:
                                saved_count += 1
                        except Exception as e:
                            logger.warning(
                                f"Failed to save GitHub repo {repo['full_name']}: {e}"
                            )

                logger.info(
                    f"GitHub trending collection completed: {saved_count} new repos."
                )
                return saved_count
            except Exception as e:
                logger.error(f"GitHub trending collection failed: {e}")
                return 0
        if platform == "telegram_channels":
            if not self.config.flags.get("enable_telegram_channels"):
                return 0
            try:
                from src.core.extraction.telegram_channel_extractor import (
                    TelegramChannelExtractor,
                )
                from src.supabase_manager import SupabaseManager
                from datetime import datetime
                import json

                logger.info("Collecting Telegram channel messages...")

                # Get all channels to collect
                all_channels_to_collect = []
                telegram_channels_config = self.config.get("telegram_channels", {})
                for persona_key, persona_channels in telegram_channels_config.items():
                    for channel_data in persona_channels:
                        channel_username = (
                            channel_data.get(
                                "username", channel_data.get("channel", "")
                            )
                            if isinstance(channel_data, dict)
                            else channel_data
                        )
                        if channel_username:
                            all_channels_to_collect.append(channel_username)

                if not all_channels_to_collect:
                    logger.warning("No Telegram channels configured")
                    return 0

                # Initialize extractor and Supabase
                extractor = TelegramChannelExtractor()
                supabase = SupabaseManager()

                saved_count = 0
                await extractor.connect()

                for channel_username in all_channels_to_collect:
                    try:
                        # Fetch existing messages for this channel to avoid duplicates
                        existing_messages_data = (
                            supabase.client.table("telegram_messages")
                            .select("message_id")
                            .eq("channel_username", channel_username)
                            .execute()
                        )
                        existing_message_ids = {
                            m["message_id"] for m in existing_messages_data.data
                        }

                        messages = await extractor.get_messages_from_channel(
                            channel_username, limit=50
                        )

                        for msg in messages:
                            if msg.get("id") and msg["id"] not in existing_message_ids:
                                message_data = {
                                    "channel_username": channel_username,
                                    "message_id": msg["id"],
                                    "date": msg["date"].isoformat()
                                    if isinstance(msg["date"], datetime)
                                    else msg["date"],
                                    "content": msg.get("content", ""),
                                    "sender": msg.get("sender", ""),
                                    "message_url": msg.get("message_url", ""),
                                    "views": msg.get("views", 0),
                                    "forwards": msg.get("forwards", 0),
                                    "replies": msg.get("replies", 0),
                                    "reactions": json.dumps(msg.get("reactions", {})),
                                    "collected_at": datetime.now().isoformat(),
                                }
                                try:
                                    result = self.storage.save_telegram_message(
                                        message_data
                                    )
                                    if result:
                                        saved_count += 1
                                        existing_message_ids.add(msg["id"])
                                except Exception as e:
                                    if (
                                        "duplicate" in str(e).lower()
                                        or "unique" in str(e).lower()
                                    ):
                                        logger.debug(
                                            f"Skipping duplicate Telegram message {msg['id']} in {channel_username}"
                                        )
                                    else:
                                        logger.warning(
                                            f"Failed to save Telegram message {msg['id']} from {channel_username}: {e}"
                                        )
                            else:
                                logger.debug(
                                    f"Skipping existing Telegram message {msg.get('id')} in {channel_username}"
                                )
                    except Exception as e:
                        logger.error(
                            f"Error collecting from Telegram channel {channel_username}: {e}",
                            exc_info=True,
                        )

                await extractor.disconnect()
                logger.info(
                    f"Telegram channels collection completed: {saved_count} new messages."
                )
                return saved_count
            except Exception as e:
                logger.error(f"Telegram channels collection failed: {e}")
                return 0
        raise ValueError(f"Unsupported platform: {platform}")

    async def autonomous_discover(self) -> Dict[str, Any]:
        from src.services.autonomous_discovery import AutonomousDiscovery

        engine = AutonomousDiscovery()
        return await engine.discover_content()

    async def analyze_batch(self, limit: int = 20) -> int:
        if not self.config.flags.get("enable_analysis", True):
            return 0
        try:
            from src.services.analysis.post_analyzer import analyze_and_store_post
            from src.services.cancel_manager import is_cancelled

            # Get unanalyzed posts instead of all posts
            posts = self.storage.get_unanalyzed_posts(limit=limit)
            count = 0
            for p in posts:
                try:
                    if is_cancelled("analysis") or is_cancelled("all"):
                        break

                    class _ShimDB:
                        def __init__(self, storage):
                            self._s = storage

                        def add_post(self, post):
                            return self._s.save_post(post)

                        def update_post(self, post_id: str, post_data: dict):
                            # Allow analyzer to persist updates; reuse save_post behavior
                            return self._s.save_post(post_data)

                    shim = _ShimDB(self.storage)
                    await analyze_and_store_post(shim, p)
                    count += 1
                except Exception:
                    continue
            return count
        except Exception:
            return 0

    async def generate_digest(self) -> Dict[str, Any]:
        # Simplified digest generation
        try:
            posts = self.storage.get_posts(limit=20)
            return {"items": posts, "generated_at": asyncio.get_event_loop().time()}
        except Exception as e:
            return {"error": str(e)}

    async def build_news_feed(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return digestible, news-format items with summaries and links."""
        try:
            posts = self.storage.get_posts(limit=limit)
            github_repos = self.storage.get_github_trending_repos(limit=limit)
            telegram_msgs = self.storage.get_telegram_messages(limit=limit)

            feed: List[Dict[str, Any]] = []

            # Add posts
            for p in posts:
                feed.append(
                    {
                        "title": p.get("title") or (p.get("content") or "")[:80],
                        "summary": p.get("summary") or (p.get("content") or "")[:200],
                        "url": p.get("url"),
                        "platform": p.get("platform"),
                        "source": p.get("source"),
                        "created_at": p.get("created_at"),
                        "value_score": p.get("value_score", 0.0),
                        "tags": p.get("suggested_tags") or [],
                        "type": "post",
                    }
                )

            # Add GitHub trending repos
            for repo in github_repos:
                feed.append(
                    {
                        "title": f"GitHub Trending: {repo.get('full_name')}",
                        "summary": repo.get("description", "")[:200],
                        "url": repo.get("url"),
                        "platform": "github",
                        "source": "github_trending",
                        "created_at": repo.get("collected_at"),
                        "value_score": repo.get("stars", 0)
                        / 1000.0,  # Scale stars to a score
                        "tags": [repo.get("language")] if repo.get("language") else [],
                        "type": "github_repo",
                    }
                )

            # Add Telegram messages
            for msg in telegram_msgs:
                feed.append(
                    {
                        "title": f"Telegram: {msg.get('channel_username')}",
                        "summary": msg.get("content", "")[:200],
                        "url": msg.get("message_url"),
                        "platform": "telegram",
                        "source": msg.get("channel_username"),
                        "created_at": msg.get("date"),
                        "value_score": (
                            msg.get("views", 0) + msg.get("forwards", 0) * 2
                        )
                        / 100.0,  # Simple score
                        "tags": [],
                        "type": "telegram_message",
                    }
                )

            # Sort by creation date (most recent first)
            feed.sort(
                key=lambda x: x.get("created_at", "0000-00-00T00:00:00"), reverse=True
            )
            return feed[:limit]
        except Exception as e:
            logger.error(f"Error building news feed: {e}")
            return []


# Global orchestrator instance
_orchestrator_singleton: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator_singleton
    if _orchestrator_singleton is None:
        _orchestrator_singleton = Orchestrator()
    return _orchestrator_singleton
