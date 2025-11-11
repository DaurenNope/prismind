#!/usr/bin/env python3
"""
Production Rewrite & Schedule System
Processes database posts, rewrites with language routing, and schedules for publishing
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv(override=True)

from src.storage.db import StorageFacade
from src.publishing.rewriter import ContentRewriter
from src.publishing.scheduler import PublishingScheduler
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProductionPublisher:
    """
    Production publishing system with language routing:

    Threads → Russian (Qronoya persona)
    Twitter → English (Qronoya persona)
    Telegram → Russian (Qronoya persona)
    """

    def __init__(self):
        self.db = StorageFacade()
        self.rewriter = ContentRewriter()
        self.scheduler = PublishingScheduler()
        self.analyzer = IntelligentContentAnalyzer()

        # Language routing
        self.language_map = {
            'threads': 'russian',
            'twitter': 'english',
            'telegram': 'russian',
            'reddit': 'english'  # Default to English for Reddit
        }

        # Platform routing for scheduled posts
        self.output_platforms = {
            'threads': 'threads',     # Rewrite for Threads
            'twitter': 'twitter',     # Rewrite for Twitter
            'reddit': 'threads',      # Reddit content → Threads (Russian)
            'telegram': 'telegram'    # Future: Telegram channel
        }

        # Storage for scheduled posts
        self.schedule_dir = Path("scheduled_posts")
        self.schedule_dir.mkdir(exist_ok=True)

    async def process_batch(
        self,
        limit: int = 20,
        platform_filter: str = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Process a batch of posts from database.

        Args:
            limit: Number of posts to process
            platform_filter: Filter by platform ('threads', 'twitter', 'reddit')
            dry_run: If True, don't save scheduled posts

        Returns:
            Processing statistics
        """

        logger.info(f"\n{'='*100}")
        logger.info(f"🚀 PRODUCTION REWRITE & SCHEDULE - BATCH PROCESSING")
        logger.info(f"{'='*100}")
        logger.info(f"Limit: {limit} posts")
        logger.info(f"Platform filter: {platform_filter or 'All'}")
        logger.info(f"Dry run: {dry_run}")

        # Fetch posts from database
        logger.info(f"\n📂 Fetching posts from database...")
        all_posts = self.db.get_posts(limit=limit * 3)  # Get more to account for filtering

        # Filter posts
        posts = []
        for post in all_posts:
            if post is None:
                continue

            # Platform filter
            if platform_filter and post.get('platform') != platform_filter:
                continue

            posts.append(post)

            if len(posts) >= limit:
                break

        logger.info(f"✅ Found {len(posts)} posts to process")

        # Process each post
        results = {
            'total': len(posts),
            'processed': 0,
            'scheduled': 0,
            'errors': 0,
            'by_platform': {},
            'scheduled_posts': []
        }

        for idx, post in enumerate(posts, 1):
            try:
                logger.info(f"\n{'='*100}")
                logger.info(f"POST {idx}/{len(posts)}")
                logger.info(f"{'='*100}")

                # Process post
                scheduled_post = await self.process_single_post(post, dry_run=dry_run)

                if scheduled_post:
                    results['processed'] += 1
                    results['scheduled'] += 1
                    results['scheduled_posts'].append(scheduled_post)

                    platform = scheduled_post['platform']
                    results['by_platform'][platform] = results['by_platform'].get(platform, 0) + 1
                else:
                    results['errors'] += 1

            except Exception as e:
                logger.error(f"❌ Error processing post {idx}: {e}")
                results['errors'] += 1

        # Summary
        logger.info(f"\n{'='*100}")
        logger.info(f"📊 BATCH PROCESSING SUMMARY")
        logger.info(f"{'='*100}")
        logger.info(f"Total posts: {results['total']}")
        logger.info(f"Successfully processed: {results['processed']}")
        logger.info(f"Scheduled: {results['scheduled']}")
        logger.info(f"Errors: {results['errors']}")
        logger.info(f"\nBy platform:")
        for platform, count in results['by_platform'].items():
            logger.info(f"  {platform}: {count}")

        return results

    async def process_single_post(
        self,
        post: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Process a single post: analyze, rewrite with language routing, schedule.

        Returns:
            Scheduled post data or None if failed
        """

        # Extract post data
        title = post.get('title', '')
        content = post.get('content', '')
        source_platform = post.get('platform', 'unknown')
        url = post.get('url', '')

        logger.info(f"📝 Title: {title[:60]}...")
        logger.info(f"   Source: {source_platform}")
        logger.info(f"   URL: {url[:60]}...")

        # Determine output platform and language
        output_platform = self.output_platforms.get(source_platform, 'threads')
        language = self.language_map.get(output_platform, 'russian')

        logger.info(f"   Output: {output_platform} ({language})")

        # Analyze content
        logger.info(f"\n🔍 Analyzing content...")
        analyzed = await self.analyzer.analyze_for_rewriting(
            content=content,
            category='Technology',  # Default category
            metadata={
                'platform': source_platform,
                'url': url,
                'title': title
            }
        )

        if not analyzed or 'error' in analyzed:
            logger.error(f"❌ Analysis failed: {analyzed.get('error', 'Unknown error')}")
            return None

        logger.info(f"✅ Analysis complete:")
        logger.info(f"   Viral potential: {analyzed.get('viral_potential', 0)}/100")
        logger.info(f"   Time sensitivity: {analyzed.get('time_sensitivity', 'unknown')}")

        # Rewrite for platform with language routing
        logger.info(f"\n✍️  Rewriting for {output_platform} ({language})...")
        rewritten = await self.rewriter.rewrite_analyzed_post(
            analyzed_content=analyzed,
            persona='qronoya',
            platform=output_platform,
            language=language  # Pass language explicitly
        )

        if 'error' in rewritten:
            logger.error(f"❌ Rewrite failed: {rewritten['error']}")
            return None

        rewritten_content = rewritten.get('rewritten_content', '')
        logger.info(f"✅ Rewrite complete ({len(rewritten_content)} chars)")
        logger.info(f"\n📄 Preview:")
        logger.info(f"{'-'*100}")
        # Show first 300 chars
        preview = rewritten_content[:300]
        if len(rewritten_content) > 300:
            preview += "..."
        logger.info(preview)
        logger.info(f"{'-'*100}")

        # Schedule post
        logger.info(f"\n📅 Scheduling post...")
        decision = self.scheduler.schedule_rewritten_post(
            rewritten_content=rewritten,
            platform_override=output_platform
        )

        # Prepare scheduled post data
        scheduled_post = {
            'id': f"{output_platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'source_post': {
                'title': title,
                'url': url,
                'platform': source_platform
            },
            'rewritten_content': rewritten_content,
            'platform': output_platform,
            'language': language,
            'persona': 'qronoya',
            'scheduled_for': decision.when.isoformat(),
            'priority': decision.priority,
            'reason': decision.reason,
            'metadata': {
                'viral_potential': analyzed.get('viral_potential', 0),
                'time_sensitivity': analyzed.get('time_sensitivity', 'unknown'),
                'created_at': datetime.now().isoformat()
            }
        }

        logger.info(f"✅ Scheduled for: {decision.when.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"   Priority: {decision.priority}/100")
        logger.info(f"   Reason: {decision.reason}")

        # Save to file (unless dry run)
        if not dry_run:
            filename = f"{scheduled_post['id']}.json"
            filepath = self.schedule_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(scheduled_post, f, ensure_ascii=False, indent=2)

            logger.info(f"💾 Saved to: {filepath}")
        else:
            logger.info(f"💾 [DRY RUN] Would save to: {self.schedule_dir}/{scheduled_post['id']}.json")

        return scheduled_post

    def get_scheduled_posts(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get all scheduled posts, sorted by scheduled_for"""

        posts = []
        for filepath in self.schedule_dir.glob("*.json"):
            with open(filepath, 'r', encoding='utf-8') as f:
                post = json.load(f)
                posts.append(post)

        # Sort by scheduled_for
        posts.sort(key=lambda p: p['scheduled_for'])

        if limit:
            posts = posts[:limit]

        return posts

    def show_schedule_overview(self):
        """Show overview of scheduled posts"""

        posts = self.get_scheduled_posts()

        print(f"\n{'='*100}")
        print(f"📅 SCHEDULED POSTS OVERVIEW")
        print(f"{'='*100}")
        print(f"Total scheduled: {len(posts)}")

        # Group by platform
        by_platform = {}
        by_language = {}

        for post in posts:
            platform = post['platform']
            language = post['language']

            by_platform[platform] = by_platform.get(platform, 0) + 1
            by_language[language] = by_language.get(language, 0) + 1

        print(f"\nBy platform:")
        for platform, count in by_platform.items():
            print(f"  {platform}: {count}")

        print(f"\nBy language:")
        for language, count in by_language.items():
            print(f"  {language}: {count}")

        # Show next 10 posts
        print(f"\n{'='*100}")
        print(f"📋 NEXT 10 POSTS")
        print(f"{'='*100}")

        for idx, post in enumerate(posts[:10], 1):
            scheduled_for = datetime.fromisoformat(post['scheduled_for'])
            print(f"\n{idx}. [{post['platform'].upper()}] [{post['language'].upper()}] Priority: {post['priority']}")
            print(f"   Scheduled: {scheduled_for.strftime('%Y-%m-%d %H:%M')}")
            print(f"   Content: {post['rewritten_content'][:100]}...")
            print(f"   Reason: {post['reason']}")


async def main():
    """Main entry point for production publishing"""

    import argparse

    parser = argparse.ArgumentParser(description='Production Rewrite & Schedule System')
    parser.add_argument('--limit', type=int, default=10, help='Number of posts to process')
    parser.add_argument('--platform', choices=['threads', 'twitter', 'reddit', 'telegram'], help='Filter by platform')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (don\'t save files)')
    parser.add_argument('--show-schedule', action='store_true', help='Show scheduled posts overview')

    args = parser.parse_args()

    publisher = ProductionPublisher()

    if args.show_schedule:
        publisher.show_schedule_overview()
        return

    # Process batch
    results = await publisher.process_batch(
        limit=args.limit,
        platform_filter=args.platform,
        dry_run=args.dry_run
    )

    # Show schedule overview
    if not args.dry_run and results['scheduled'] > 0:
        print("\n")
        publisher.show_schedule_overview()


if __name__ == "__main__":
    asyncio.run(main())
