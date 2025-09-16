#!/usr/bin/env python3
"""
Scheduled Reddit Collector

This script runs the Reddit extractor on a schedule and handles logging and error reporting.
It's designed to be run as a cron job or scheduled task.
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
project_root = Path(__file__).parent.parent
load_dotenv(project_root / '.env')

# Add project root to Python path
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Import the test_reddit_extractor module to reuse its functionality
from scripts.test_reddit_extractor import (
    RedditExtractor, 
    DatabaseManager, 
    save_posts_to_db,
    SocialPost
)

# Configure logging
LOG_FILE = 'logs/reddit_collector.log'
os.makedirs('logs', exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('reddit_collector')


def setup_argparse() -> argparse.Namespace:
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description='Run the Reddit collector')
    parser.add_argument(
        '--limit', 
        type=int, 
        default=25,
        help='Maximum number of posts to fetch (default: 25)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without saving to database'
    )
    return parser.parse_args()


def get_existing_posts(db: DatabaseManager) -> set:
    """Get a set of existing post IDs from the database."""
    import sqlite3
    existing_posts = set()
    conn = None
    cursor = None
    
    try:
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT post_id FROM posts WHERE platform = 'reddit'")
        existing_posts = {row[0] for row in cursor.fetchall() if row[0] is not None}
        logger.info(f"Found {len(existing_posts)} existing Reddit posts in database")
    except Exception as e:
        logger.warning(f"Error fetching existing posts: {e}")
        logger.info("Continuing with empty set of existing posts")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return existing_posts


def main():
    """Main function to run the Reddit collector."""
    args = setup_argparse()
    start_time = datetime.utcnow()
    
    # Initialize counters
    stats = {
        'total_posts_fetched': 0,
        'new_posts': 0,
        'duplicate_posts': 0,
        'saved_posts': 0,
        'errors': 0,
        'start_time': start_time
    }
    
    logger.info("=" * 80)
    logger.info(f"Starting Reddit collector at {start_time.isoformat()}")
    logger.info(f"Limit: {args.limit} posts")
    logger.info(f"Dry run: {args.dry_run}")
    
    try:
        # Initialize database
        db = DatabaseManager()
        logger.info(f"Connected to database at {db.db_path}")
        
        # Get existing posts for deduplication
        existing_posts = get_existing_posts(db)
        logger.info(f"Found {len(existing_posts)} existing posts in database")
        
        # Initialize extractor
        extractor = RedditExtractor(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'prismind/1.0'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD')
        )
        
        # Authenticate
        logger.info("Authenticating with Reddit...")
        if not extractor.authenticate():
            logger.error("❌ Authentication failed")
            stats['errors'] += 1
            return 1
        
        # Fetch saved posts
        logger.info(f"Fetching up to {args.limit} new posts...")
        posts, next_after = extractor.get_saved_posts(
            limit=args.limit,
            existing_ids=existing_posts
        )
        
        stats['total_posts_fetched'] = len(posts) if posts else 0
        stats['duplicate_posts'] = len(existing_posts)
        
        if not posts:
            logger.warning("⚠️ No new posts found")
            # Return 2 to indicate no new posts (but no error)
            return 2
            
        stats['new_posts'] = len(posts)
        logger.info(f"✅ Retrieved {len(posts)} new posts from Reddit")
        
        # Save to database if not in dry run mode
        if not args.dry_run:
            saved_count = save_posts_to_db(db, posts)
            stats['saved_posts'] = saved_count
            if saved_count > 0:
                logger.info(f"💾 Successfully saved {saved_count}/{len(posts)} posts to database")
            else:
                logger.warning("⚠️ No posts were saved to the database")
        else:
            logger.info(f"🔍 Dry run: Would have saved {len(posts)} posts to database")
            
        return 0 if stats['new_posts'] > 0 else 2
        
    except Exception as e:
        logger.exception("❌ An error occurred during Reddit collection")
        stats['errors'] += 1
        return 1
    finally:
        # Log completion
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info("\n" + "=" * 40 + " COLLECTION SUMMARY " + "=" * 40)
        logger.info(f"{'Total posts fetched:':<25} {stats['total_posts_fetched']}")
        logger.info(f"{'New posts found:':<25} {stats['new_posts']}")
        logger.info(f"{'Duplicate posts:':<25} {stats['duplicate_posts']}")
        if not args.dry_run:
            logger.info(f"{'Posts saved to DB:':<25} {stats['saved_posts']}")
        logger.info(f"{'Errors:':<25} {stats['errors']}")
        logger.info(f"{'Duration:':<25} {duration:.2f} seconds")
        logger.info("=" * 100)
        logger.info("Reddit collector finished")
        logger.info("=" * 100)


if __name__ == "__main__":
    import sys
    sys.exit(main())
