import os
import sys
import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Set, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('reddit_extractor.log')
    ]
)
logger = logging.getLogger(__name__)

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.core.extraction.reddit_extractor import RedditExtractor
from src.core.extraction.social_extractor_base import SocialPost
from src.services.database import DatabaseManager


def save_posts_to_db(db: DatabaseManager, posts: List[SocialPost]) -> int:
    """Save a list of SocialPost objects to the database.
    
    Args:
        db: DatabaseManager instance
        posts: List of SocialPost objects to save
        
    Returns:
        int: Number of posts successfully saved
    """
    saved_count = 0
    
    for post in posts:
        try:
            # Get a database connection
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO posts (
                        post_id, platform, author, author_handle, content, 
                        created_at, url, post_type, is_saved, saved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        post.post_id,
                        post.platform,
                        post.author,
                        post.author_handle,
                        post.content,
                        post.created_at,
                        post.url,
                        post.post_type,
                        post.is_saved,
                        datetime.utcnow().isoformat() if post.is_saved else None
                    )
                )
                
                # Commit the transaction
                conn.commit()
                
                # If this is a new post, save media URLs
                if cursor.rowcount > 0 and hasattr(post, 'media_urls') and post.media_urls:
                    # In a real implementation, you'd save media URLs to a separate table
                    logger.info(f"Saved {len(post.media_urls)} media URLs for post {post.post_id}")
                
                saved_count += 1
                logger.info(f"Saved post {post.post_id} to database")
                
            except Exception as e:
                conn.rollback()
                raise e
                
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            logger.error(f"Error saving post {getattr(post, 'post_id', 'unknown')}: {e}")
    
    return saved_count

def main():
    # Load environment variables
    load_dotenv()
    logger.info("Starting Reddit extractor test script")
    
    # Initialize database
    try:
        db = DatabaseManager()
        logger.info(f"Connected to database at {db.db_path}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    # Initialize extractor with environment variables
    try:
        extractor = RedditExtractor(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT', 'prismind/1.0'),
            username=os.getenv('REDDIT_USERNAME'),
            password=os.getenv('REDDIT_PASSWORD')
        )
        logger.info("Reddit extractor initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Reddit extractor: {e}")
        return
    
    # Get existing post IDs from database
    existing_posts = set()
    conn = None
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
        if conn:
            conn.close()
    
    # Test authentication
    logger.info("Testing authentication...")
    try:
        if not extractor.authenticate():
            logger.error("Authentication failed")
            return
        logger.info("Successfully authenticated with Reddit")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        logger.error("Please check your Reddit API credentials in the .env file")
        return
    
    # Fetch saved posts
    logger.info(f"Fetching up to 5 new posts (skipping {len(existing_posts)} existing ones)...")
    try:
        posts, next_after = extractor.get_saved_posts(
            limit=5,
            existing_ids=existing_posts
        )
        logger.info(f"Retrieved {len(posts)} new posts from Reddit")
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        return
    
    # Display and save the posts
    if not posts:
        logger.info("No new posts found")
        return
    
    # Save posts to database
    try:
        saved_count = save_posts_to_db(db, posts)
        logger.info(f"Successfully saved {saved_count}/{len(posts)} posts to database")
    except Exception as e:
        logger.error(f"Error saving posts to database: {e}")
    
    # Display the posts
    logger.info("\n=== New Posts ===")
    for i, post in enumerate(posts, 1):
        logger.info(f"\n📝 Post {i}:")
        logger.info(f"   ID: {post.post_id}")
        logger.info(f"   Author: {post.author} ({post.author_handle})")
        logger.info(f"   Type: {post.post_type}")
        logger.info(f"   Created: {post.created_at}")
        logger.info(f"   URL: {post.url}")
        logger.info(f"   Platform: {post.platform}")
        if post.content:
            logger.info(f"   Content: {post.content[:200]}...")
        if hasattr(post, 'media_urls') and post.media_urls:
            logger.info(f"   Media: {len(post.media_urls)} attachments")
        if hasattr(post, 'hashtags') and post.hashtags:
            logger.info(f"   Hashtags: {', '.join(post.hashtags)}")
        if hasattr(post, 'mentions') and post.mentions:
            logger.info(f"   Mentions: {', '.join(post.mentions)}")
        if hasattr(post, 'analysis') and post.analysis:
            logger.info(f"   Analysis: {post.analysis}")
    
    # Log completion
    logger.info("\n=== Reddit extraction completed successfully ===\n")

if __name__ == "__main__":
    main()
