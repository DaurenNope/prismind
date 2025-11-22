#!/usr/bin/env python3
"""
Re-run database curation for existing posts so usable_posts gets refreshed.

Usage examples:
  python scripts/recache_usable_posts.py --limit 500
  python scripts/recache_usable_posts.py --platforms reddit twitter
  python scripts/recache_usable_posts.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
from collections import Counter
from typing import Iterable, Optional

from src.database.curation import DatabaseCuration
from src.services.new_database_manager import NewDatabaseManager

try:
    from src.database.manager import SupabaseManager
except Exception as exc:  # pragma: no cover - Supabase optional
    SupabaseManager = None  # type: ignore
    logging.getLogger(__name__).warning(
        f"Supabase unavailable for recache script: {exc}"
    )


def fetch_posts(
    limit: Optional[int], platforms: Optional[Iterable[str]], supabase_client=None
):
    """Fetch posts via Supabase when available, else fall back to SQLite."""
    platforms_set = {p.lower() for p in (platforms or [])} or None
    if supabase_client:
        query = (
            supabase_client.table("posts").select("*").order("created_at", desc=True)
        )
        if platforms_set:
            query = query.in_("platform", list(platforms_set))
        resp = query.limit(limit or 1000).execute()
        return resp.data or []

    db = NewDatabaseManager()
    fetched = db.get_posts(limit=limit or 10_000)
    if not platforms_set:
        return fetched
    return [p for p in fetched if (p.get("platform") or "").lower() in platforms_set]


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-run curation for existing posts.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max posts to inspect (default: all available)",
    )
    parser.add_argument(
        "--platforms", nargs="+", help="Optional platform filter e.g. reddit twitter"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report results without writing to Supabase",
    )
    args = parser.parse_args()

    logger = logging.getLogger("recache_usable_posts")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if SupabaseManager is None and not args.dry_run:
        raise SystemExit(
            "Supabase credentials unavailable. Use --dry-run or configure env vars."
        )

    supabase_client = None
    if SupabaseManager:
        try:
            supabase_client = SupabaseManager().client
        except Exception as exc:
            logger.warning("Supabase initialization failed: %s", exc)
            if not args.dry_run:
                raise

    curator = DatabaseCuration(
        supabase=supabase_client if not args.dry_run else supabase_client
    )

    stats = Counter()
    posts = fetch_posts(args.limit, args.platforms, supabase_client)
    for post in posts:
        stats["checked"] += 1
        if args.dry_run:
            ok, reason = curator._check_content_quality_for_curation(post)
            if not ok:
                stats[f"quality:{reason}"] += 1
                continue
            usable, reason = curator._is_post_usable(post)
            if not usable:
                stats[f"usable:{reason or 'unknown'}"] += 1
                continue
            stats["would_curate"] += 1
        else:
            if curator.auto_curate_to_usable_posts(post):
                stats["curated"] += 1
            else:
                stats["skipped"] += 1

        if stats["checked"] % 100 == 0:
            logger.info(
                "Processed %s posts (curated=%s, skipped=%s)",
                stats["checked"],
                stats.get("curated", 0),
                stats.get("skipped", 0),
            )

    logger.info("=== Recache summary ===")
    for key, value in sorted(stats.items()):
        logger.info("%s: %s", key, value)


if __name__ == "__main__":
    main()
