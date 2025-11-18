#!/usr/bin/env python3
"""
Re-run analyzer for posts missing required metadata (summary/persona).

Usage examples:
  PYTHONPATH=. python scripts/reanalyze_missing_metadata.py --limit 500 --batch-size 25
  PYTHONPATH=. python scripts/reanalyze_missing_metadata.py --platforms reddit twitter --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from typing import Any, Dict, Iterable, List, Optional

from src.services.analysis.post_analyzer import analyze_and_store_post
from src.services.new_database_manager import NewDatabaseManager

try:
    from src.database.manager import SupabaseManager
except Exception as exc:  # pragma: no cover
    SupabaseManager = None  # type: ignore
    logging.getLogger(__name__).warning(f"Supabase unavailable: {exc}")


def needs_reanalysis(post: Dict[str, Any]) -> bool:
    """Return True if a post is missing critical metadata."""
    summary = (post.get("ai_summary") or "").strip()
    if not summary or len(summary) < 20:
        return True
    profile_matches = post.get("profile_matches")
    if not profile_matches:
        return True
    if isinstance(profile_matches, dict) and not profile_matches:
        return True
    best_persona = (post.get("best_persona_key") or "").strip()
    if not best_persona:
        return True
    return False


def iter_posts(
    limit: Optional[int], platforms: Optional[Iterable[str]]
) -> List[Dict[str, Any]]:
    """Fetch posts from the local DB, optionally filtered by platform."""
    db = NewDatabaseManager()
    posts = db.get_posts(limit=limit or 10_000)
    if not platforms:
        return posts
    targets = {p.lower() for p in platforms}
    return [p for p in posts if (p.get("platform") or "").lower() in targets]


async def reanalyze_posts(
    posts: List[Dict[str, Any]], batch_size: int, dry_run: bool
) -> None:
    logger = logging.getLogger("reanalyze_missing_metadata")
    db = NewDatabaseManager()
    supabase = SupabaseManager() if (SupabaseManager and not dry_run) else None

    to_fix = [p for p in posts if needs_reanalysis(p)]
    logger.info(
        "Found %s posts needing reanalysis (out of %s fetched)", len(to_fix), len(posts)
    )

    if dry_run:
        for post in to_fix[:batch_size]:
            logger.info(
                "Would reanalyze %s (%s): summary_len=%s, personas=%s",
                post.get("post_id"),
                post.get("platform"),
                len((post.get("ai_summary") or "").strip()),
                post.get("profile_matches"),
            )
        return

    async def process_chunk(chunk: List[Dict[str, Any]]) -> None:
        for post in chunk:
            post_id = post.get("post_id")
            platform = post.get("platform")
            try:
                await analyze_and_store_post(db, post, supabase)
                logger.info("✅ Reanalyzed %s (%s)", post_id, platform)
            except Exception as exc:
                logger.error(
                    "❌ Failed to reanalyze %s (%s): %s", post_id, platform, exc
                )

    for i in range(0, len(to_fix), batch_size):
        chunk = to_fix[i : i + batch_size]
        logger.info("Processing posts %s-%s", i + 1, i + len(chunk))
        await process_chunk(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-run analyzer for posts missing metadata."
    )
    parser.add_argument(
        "--limit", type=int, default=1000, help="Max posts to inspect (default: 1000)"
    )
    parser.add_argument(
        "--platforms", nargs="+", help="Optional platform filter (e.g. reddit twitter)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=25, help="How many posts to process per batch"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report counts, do not call the analyzer",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    posts = iter_posts(args.limit, args.platforms)
    asyncio.run(reanalyze_posts(posts, args.batch_size, args.dry_run))


if __name__ == "__main__":
    main()
