#!/usr/bin/env python3
"""
Backfill relevance_window/time-sensitive flags so older posts are treated as evergreen.

Usage:
    python scripts/backfill_evergreen_posts.py --days 7 --batch-size 500 --max-batches 20
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.manager import SupabaseManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def chunk_posts(
    supabase: SupabaseManager,
    cutoff_iso: str,
    batch_size: int,
    max_batches: int,
) -> List[Dict]:
    offset = 0
    fetched_batches = 0

    while fetched_batches < max_batches:
        resp = (
            supabase.client.table("posts")
            .select(
                "post_id, platform, relevance_window, time_sensitive, urgency_score, created_at"
            )
            .lte("created_at", cutoff_iso)
            .order("created_at", desc=False)
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            break

        yield rows

        offset += batch_size
        fetched_batches += 1


def needs_evergreen_update(post: Dict, days_threshold: int) -> bool:
    window = (post.get("relevance_window") or "").lower().strip()
    created_at = post.get("created_at")
    if not created_at:
        return True

    try:
        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        return True

    age_days = (datetime.now(timezone.utc) - created_dt).days

    if age_days < days_threshold:
        return False

    if window in ("evergreen", "future-proof"):
        if post.get("time_sensitive") or post.get("urgency_score"):
            return True
        return False

    return True


def run(days: int, batch_size: int, max_batches: int, dry_run: bool) -> None:
    try:
        supabase = SupabaseManager()
    except Exception as exc:
        logger.error(f"❌ Supabase unavailable: {exc}")
        return

    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    total_checked = 0
    total_updates = 0

    for rows in chunk_posts(supabase, cutoff, batch_size, max_batches):
        updates = []
        for post in rows:
            total_checked += 1
            if needs_evergreen_update(post, days_threshold=days):
                updates.append(
                    {
                        "post_id": post.get("post_id"),
                        "platform": post.get("platform"),
                        "relevance_window": "evergreen",
                        "time_sensitive": False,
                        "urgency_score": 0.0,
                    }
                )

        if not updates:
            continue

        total_updates += len(updates)
        logger.info(
            f"Preparing {len(updates)} updates (total so far: {total_updates})"
        )

        if dry_run:
            continue

        supabase.client.table("posts").upsert(
            updates, on_conflict="platform,post_id"
        ).execute()

    if dry_run:
        logger.info(
            f"✅ Dry run complete. Posts checked: {total_checked}, would update: {total_updates}"
        )
    else:
        logger.info(
            f"✅ Evergreen backfill complete. Posts checked: {total_checked}, updated: {total_updates}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Normalize older posts to evergreen relevance window."
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Only convert posts older than this many days (default: 7)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of posts to fetch per batch (default: 500)",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=20,
        help="Maximum batches to process (default: 20)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write changes, only log what would happen",
    )
    args = parser.parse_args()

    run(
        days=args.days,
        batch_size=args.batch_size,
        max_batches=args.max_batches,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()

