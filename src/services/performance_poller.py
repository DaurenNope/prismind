#!/usr/bin/env python3
"""
PerformancePoller - polls platform metrics for posted content at scheduled windows.

Windows: T+15m, T+60m, T+24h, T+72h

Fetcher stubs should be implemented per platform.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from src.infrastructure.database.database_agent import get_database_agent


class PerformancePoller:
    def __init__(self, agent=None) -> None:
        self.agent = agent or get_database_agent()
        # minutes since posting
        self.windows_minutes: List[int] = [15, 60, 24 * 60, 72 * 60]

    async def _fetch_metrics(
        self, platform: str, platform_post_id: str, url: str
    ) -> Dict[str, Any]:
        """Lightweight per-platform fetchers. Threads implemented; others return zeros for now."""
        if platform == "threads" and url:
            try:
                # Reuse ThreadsExtractor DOM logic to get basic engagement signals
                from src.domain.collection.extractors.threads_extractor import ThreadsExtractor

                extractor = ThreadsExtractor()
                posts = await extractor.scrape_posts_from_urls_async([url])
                if posts:
                    p = posts[0]
                    eng = getattr(p, "engagement", {}) or {}
                    likes = int(eng.get("likes") or 0)
                    replies = int(eng.get("replies") or 0)
                    shares = int(eng.get("shares") or 0)
                    return {
                        "views": 0,  # Threads views are not easily accessible without API
                        "likes": likes,
                        "comments": replies,
                        "shares": shares,
                        "bookmarks": 0,
                        "snapshot_at": datetime.utcnow().isoformat(),
                    }
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
        # Fallback zeros
        return {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "bookmarks": 0,
            "snapshot_at": datetime.utcnow().isoformat(),
        }

    async def poll_once(self) -> int:
        """Poll metrics for posted_content items near a window; returns number processed."""
        processed = 0
        try:
            # Pull recently posted items (last 4 days)
            items = self.agent.get_top_posts(since_minutes=4 * 24 * 60, limit=500)
            now = datetime.utcnow()
            for it in items:
                try:
                    posted_at = it.get("posted_at")
                    if not posted_at:
                        continue
                    try:
                        posted_dt = datetime.fromisoformat(
                            str(posted_at).replace("Z", "")
                        )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        continue
                    age_min = int((now - posted_dt).total_seconds() / 60)
                    # Find closest window within tolerance (±10 min)
                    if not any(abs(age_min - w) <= 10 for w in self.windows_minutes):
                        continue

                    platform = it.get("platform")
                    pid = it.get("platform_post_id")
                    url = it.get("url") or ""
                    if not platform or not pid:
                        continue

                    snap = await self._fetch_metrics(str(platform), str(pid), url)
                    # Skip pure zeros to avoid noise
                    if any(
                        (
                            snap.get("views") or 0,
                            snap.get("likes") or 0,
                            snap.get("comments") or 0,
                            snap.get("shares") or 0,
                            snap.get("bookmarks") or 0,
                        )
                    ):
                        ok = self.agent.upsert_posted_metrics(
                            str(platform), str(pid), snap
                        )
                        if ok:
                            processed += 1
                except Exception as e:
                    logger.error(f"Error: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error: {e}")
            return processed
        return processed

    async def run_forever(self, interval_seconds: int = 600) -> None:
        while True:
            try:
                await self.poll_once()
            except Exception as e:
                logger.error(f"Error: {e}")
                pass
            await asyncio.sleep(max(60, interval_seconds))


async def main() -> None:
    agent = get_database_agent()
    poller = PerformancePoller(agent)
    await poller.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
