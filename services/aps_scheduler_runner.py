#!/usr/bin/env python3
"""
Lightweight APScheduler runner to periodically collect and analyze content.

Environment variables:
- COLLECTION_INTERVAL_MINUTES (default: 60)
- TWITTER_ENABLED (default: 1)
- REDDIT_ENABLED (default: 1)
"""

from __future__ import annotations

import os
import asyncio
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Local imports
from services.database import DatabaseManager
from collect_multi_platform import (
    collect_twitter_bookmarks,
    collect_reddit_bookmarks,
)
from services.notifier_webhook import WebhookNotifier


def _bool_env(name: str, default: str = "1") -> bool:
    return os.getenv(name, default).strip() not in ("0", "false", "False", "")


def run_collection_job() -> None:
    db = DatabaseManager()
    existing = db.get_all_posts(include_deleted=False)
    existing_ids = set(existing["post_id"].tolist()) if not existing.empty else set()
    existing_urls = set(existing["url"].dropna().tolist()) if (not existing.empty and "url" in existing.columns) else set()

    twitter_enabled = _bool_env("TWITTER_ENABLED", "1")
    reddit_enabled = _bool_env("REDDIT_ENABLED", "1")

    total = 0
    if twitter_enabled:
        total += asyncio.run(collect_twitter_bookmarks(db, existing_ids, existing_urls))
    if reddit_enabled:
        total += collect_reddit_bookmarks(db, existing_ids, existing_urls)

    print(f"[{datetime.now().isoformat()}] Collection cycle complete. New items: {total}")

    notifier = WebhookNotifier()
    if notifier.enabled():
        notifier.notify({
            "event": "collection_complete",
            "timestamp": datetime.now().isoformat(),
            "counts": {
                "total_new": total,
            },
        })


def main() -> None:
    interval_minutes = int(os.getenv("COLLECTION_INTERVAL_MINUTES", "60"))

    scheduler = BackgroundScheduler()
    scheduler.add_job(run_collection_job, "interval", minutes=interval_minutes, id="collect_job", replace_existing=True)

    # Run once at startup
    run_collection_job()

    scheduler.start()
    print(f"APScheduler started. Interval: {interval_minutes} minutes. Press Ctrl+C to exit.")

    try:
        # Keep the main thread alive
        import time
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()


