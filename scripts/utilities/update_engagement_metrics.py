#!/usr/bin/env python3
"""
Update Engagement Metrics Script

Periodically fetches and updates engagement metrics (likes, views, comments, etc.)
for recently published posts.

Usage:
    python scripts/update_engagement_metrics.py [--hours 24] [--once]

Options:
    --hours N    Update posts from last N hours (default: 24)
    --once       Run once and exit (default: runs continuously every hour)
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.domain.publishing.engagement_tracker import get_engagement_tracker
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


async def update_metrics_once(hours_back: int = 24):
    """Update metrics for recent posts once"""
    tracker = get_engagement_tracker()
    result = await tracker.update_all_recent_posts(hours_back=hours_back)

    print(f"\n📊 Engagement Metrics Update Complete:")
    print(f"   ✅ Updated: {result['updated']}")
    print(f"   ❌ Failed: {result['failed']}")
    print(f"   ⏭️  Skipped: {result['skipped']}")
    print(f"   📝 Total: {result['total']}")

    if result.get("error"):
        print(f"   ⚠️  Error: {result['error']}")

    return result


async def run_continuous(hours_back: int = 24, interval_hours: int = 1):
    """Run metrics updates continuously"""
    import time

    logger.info(f"🔄 Starting continuous engagement metrics updater")
    logger.info(f"   Update interval: {interval_hours} hour(s)")
    logger.info(f"   Checking posts from last: {hours_back} hour(s)")

    while True:
        try:
            logger.info("🔄 Running engagement metrics update...")
            result = await update_metrics_once(hours_back=hours_back)

            if result["updated"] > 0:
                logger.info(f"✅ Updated {result['updated']} posts")

            # Wait for next interval
            wait_seconds = interval_hours * 3600
            logger.info(f"⏳ Next update in {interval_hours} hour(s)...")
            await asyncio.sleep(wait_seconds)

        except KeyboardInterrupt:
            logger.info("🛑 Stopping engagement metrics updater...")
            break
        except Exception as e:
            logger.error(f"❌ Error in metrics update loop: {e}")
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(300)


def main():
    parser = argparse.ArgumentParser(
        description="Update engagement metrics for published posts"
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Update posts from last N hours (default: 24)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (default: runs continuously)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1,
        help="Update interval in hours when running continuously (default: 1)",
    )

    args = parser.parse_args()

    if args.once:
        # Run once
        print(
            f"🔄 Updating engagement metrics for posts from last {args.hours} hour(s)..."
        )
        result = asyncio.run(update_metrics_once(hours_back=args.hours))
        sys.exit(0 if result["updated"] > 0 or result["total"] == 0 else 1)
    else:
        # Run continuously
        asyncio.run(run_continuous(hours_back=args.hours, interval_hours=args.interval))


if __name__ == "__main__":
    main()
