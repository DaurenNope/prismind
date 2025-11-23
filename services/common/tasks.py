"""RQ task definitions bridging to existing pipeline functionality."""

from __future__ import annotations

import asyncio
from typing import Iterable, Optional

from src.pipeline.auto_pipeline import AutoPipeline
from src.pipeline.orchestrator import get_orchestrator
from src.infrastructure.database.scrape_state_manager import ScrapeStateManager


async def _collect(platform: str) -> int:
    orchestrator = get_orchestrator()
    return await orchestrator.collect_platform(platform)


def collect_platform(platform: str, force_once: bool = False) -> int:
    """Collect content for a platform using the existing orchestrator."""
    if force_once:
        try:
            ScrapeStateManager().reset_platform_state(platform)
        except Exception:
            # Non-fatal: if state reset fails we still attempt collection
            pass
    return asyncio.run(_collect(platform))


async def _process_backlog(
    profiles: Optional[Iterable[str]] = None,
    posts_per_profile: Optional[int] = None,
) -> dict:
    pipeline = AutoPipeline()
    return await pipeline.process_backlog_for_profiles(
        profiles=list(profiles) if profiles else None,
        posts_per_profile=posts_per_profile,
    )


def process_backlog(
    profiles: Optional[Iterable[str]] = None,
    posts_per_profile: Optional[int] = None,
) -> dict:
    """Process rewrite backlog without new collection."""
    return asyncio.run(_process_backlog(profiles, posts_per_profile))


def publish_due() -> dict:
    """Publish due posts using PublisherWorker."""
    from src.publishing.worker import get_publisher_worker

    worker = get_publisher_worker()
    result = worker.post_due_items()

    if not result:
        return {
            "posted": 0,
            "failed": 0,
            "total": 0,
            "message": "No posts published (none due).",
        }

    return {
        "posted": result.get("posted", 0),
        "failed": result.get("failed", 0),
        "total": result.get("total", 0),
        "message": f"Posted {result.get('posted', 0)}/{result.get('total', 0)} posts",
    }
