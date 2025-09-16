import os
import logging
from dotenv import load_dotenv
from src.core.extraction.working_reddit_extractor import WorkingRedditExtractor, RedditOAuth2Error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_reddit_auth():
    """Test Reddit OAuth2 authentication"""
    try:
        logger.info("🔑 Testing Reddit OAuth2 authentication...")
        extractor = WorkingRedditExtractor()
        
        # Test getting a small number of saved posts
        posts = extractor.get_saved_posts(limit=2)
        
        if posts:
            logger.info("✅ Authentication successful!")
            logger.info(f"Retrieved {len(posts)} saved posts")
            for i, post in enumerate(posts, 1):
                logger.info(f"\n--- Post {i} ---")
                logger.info(f"Title: {post.get('title')}")
                logger.info(f"Subreddit: r/{post.get('subreddit')}")
                logger.info(f"URL: {post.get('url')}")
            return True
        else:
            logger.warning("⚠️ Authentication succeeded but no posts found")
            return False
            
    except RedditOAuth2Error as e:
        logger.error(f"❌ Authentication failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    test_reddit_auth()
