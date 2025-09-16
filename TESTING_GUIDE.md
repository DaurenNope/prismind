# PrisMind Collection Testing Guide

This guide helps you test the Reddit collection functionality locally and diagnose GitHub Actions issues.

## Prerequisites

1. Python 3.8+
2. Required packages: `pip install -r requirements.txt`
3. `.env` file with Reddit API credentials

## Test Files

### 1. Test Reddit OAuth2 Connection

Create `test_reddit_auth.py`:

```python
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
```

### 2. Test Collection Service

Create `test_collection_service.py`:

```python
import os
import logging
from dotenv import load_dotenv
from src.services.collection_service import CollectionService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_collection_service():
    """Test the collection service with all platforms"""
    try:
        logger.info("🚀 Testing Collection Service...")
        
        # Initialize collection service
        service = CollectionService()
        
        # Test Reddit collection
        logger.info("\n🔴 Testing Reddit collection...")
        reddit_posts = service.collect_reddit_posts(limit=3)
        logger.info(f"✅ Retrieved {len(reddit_posts)} Reddit posts")
        
        # Test Twitter collection
        logger.info("\n🔵 Testing Twitter collection...")
        twitter_posts = service.collect_twitter_posts(limit=3)
        logger.info(f"✅ Retrieved {len(twitter_posts)} Twitter posts")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    test_collection_service()
```

## Running Tests

1. Test Reddit Authentication:
   ```bash
   python test_reddit_auth.py
   ```

2. Test Collection Service:
   ```bash
   python test_collection_service.py
   ```

## GitHub Actions Alternatives

If GitHub Actions continues to be problematic, consider these free alternatives:

1. **GitLab CI/CD**
   - Free for public repositories
   - 2,000 CI/CD minutes per month for private repos
   - Similar YAML configuration to GitHub Actions

2. **CircleCI**
   - Free tier: 6,000 build minutes/month (Linux)
   - 3 concurrent jobs
   - Good Docker support

3. **Travis CI**
   - Free for open source projects
   - Easy GitHub integration
   - Limited build minutes for private repos

4. **Drone CI**
   - Open source
   - Self-hosted option available
   - Simple YAML configuration

5. **AppVeyor**
   - Good for Windows builds
   - Free for open source
   - 1 concurrent job

## Debugging GitHub Actions

If you want to continue with GitHub Actions, try these steps:

1. **Enable Debug Logging**:
   ```yaml
   env:
     ACTIONS_STEP_DEBUG: true
     ACTIONS_RUNNER_DEBUG: true
   ```

2. **Check Secrets**:
   Ensure all required secrets are set in GitHub repository settings:
   - REDDIT_CLIENT_ID
   - REDDIT_CLIENT_SECRET
   - REDDIT_USERNAME
   - REDDIT_PASSWORD
   - REDDIT_USER_AGENT

3. **Add Debug Steps**:
   ```yaml
   - name: Debug environment
     run: |
       echo "Current directory: $(pwd)"
       echo "Python version: $(python --version)"
       echo "Environment variables:"
       env | sort
   ```

4. **Test with Manual Trigger**:
   Add a `workflow_dispatch` trigger to manually run the workflow:
   ```yaml
   on:
     schedule:
       - cron: '0 */6 * * *'  # Every 6 hours
     workflow_dispatch:  # Allows manual trigger
   ```

## Next Steps

1. Run the test files locally to verify functionality
2. Check the logs for any authentication or API errors
3. Consider setting up a simple CI/CD pipeline with one of the alternative services
4. Monitor the first few automated runs closely to catch any issues

For persistent issues, you may want to:
- Check Reddit API rate limits
- Verify OAuth2 app settings on Reddit
- Consider using a different Reddit account for testing
- Review GitHub Actions logs for network timeouts or permission issues
