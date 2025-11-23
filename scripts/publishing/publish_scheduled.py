#!/usr/bin/env python3
"""
Publish scheduled posts that are due.
Run this periodically (cron, systemd timer, or manually) to post due items.
"""

import logging
import os
import sys
import time
from pathlib import Path

import requests

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Use the newer database bridge (supabase-backed) instead of legacy mimesis module
from src.infrastructure.database.publishing.bridge import MimesisDB

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def post_due_items():
    """Post all due scheduled items via webhooks."""
    db = MimesisDB()

    # Get webhook URLs
    threads_webhook = os.getenv("THREADS_WEBHOOK_URL", "")
    twitter_webhook = os.getenv("TWITTER_WEBHOOK_URL", "")

    if not threads_webhook and not twitter_webhook:
        logger.warning(
            "No webhook URLs configured. Set THREADS_WEBHOOK_URL and/or TWITTER_WEBHOOK_URL"
        )
        return

    # Get due posts
    try:
        due = db.list_due_posts()
    except Exception as e:
        logger.error(f"Failed to list due posts: {e}")
        return

    if not due:
        logger.info("No posts due for posting")
        return

    logger.info(f"Found {len(due)} post(s) due for posting")

    posted_count = 0
    failed_count = 0

    for item in due:
        platform = item.get("platform", "")
        content = item.get("content", "")
        item_id = item.get("id")

        # Determine webhook URL
        webhook_url = ""
        if platform == "threads":
            webhook_url = threads_webhook
        elif platform == "twitter":
            webhook_url = twitter_webhook

        if not webhook_url:
            logger.warning(f"No webhook configured for platform: {platform}")
            failed_count += 1
            continue

        try:
            # Post via webhook
            response = requests.post(webhook_url, json={"content": content}, timeout=10)
            response.raise_for_status()

            # Mark as posted
            db.mark_posted(item_id, platform_post_id=None)
            posted_count += 1
            logger.info(f"✅ Posted {item_id} to {platform}")

        except Exception as e:
            logger.error(f"❌ Failed to post {item_id} to {platform}: {e}")
            # Mark for retry
            try:
                db.sb.client.table("scheduled_posts").update({"status": "retry"}).eq(
                    "id", item_id
                ).execute()
            except Exception:
                pass
            failed_count += 1

    logger.info(f"Posted {posted_count}, failed {failed_count}")
    return posted_count, failed_count


if __name__ == "__main__":
    logger.info("🚀 Starting scheduled post publisher...")
    post_due_items()
    logger.info("✅ Publisher cycle complete")
