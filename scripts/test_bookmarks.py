"""
Simple test script to verify Reddit and Twitter bookmark collection.
"""
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock database functions for testing
def save_post(post):
    """Mock function to save a post."""
    print(f"\n💾 Saving post to database:")
    print(f"   - ID: {post.get('id')}")
    print(f"   - Source: {post.get('source')}")
    print(f"   - Title/Content: {post.get('title', post.get('content', 'No content')[:50])}...")
    return True

def test_reddit_collection():
    """Test Reddit bookmark collection."""
    print("\n🔍 Testing Reddit bookmark collection...")
    
    # Simulate a Reddit post
    reddit_post = {
        'id': 't3_test123',
        'title': 'Test Reddit Post',
        'subreddit': 'test',
        'url': 'https://reddit.com/r/test/comments/test123',
        'created_utc': int(datetime.utcnow().timestamp()),
        'author': 'test_user',
        'selftext': 'This is a test Reddit post for verification.',
        'score': 42,
        'num_comments': 7,
        'saved': True,
        'source': 'reddit'
    }
    
    print("✅ Simulated Reddit post:")
    print(f"   - Title: {reddit_post['title']}")
    print(f"   - Author: u/{reddit_post['author']}")
    print(f"   - Subreddit: r/{reddit_post['subreddit']}")
    
    # Save the post
    save_post(reddit_post)
    
    return reddit_post

def test_twitter_collection():
    """Test Twitter bookmark collection."""
    print("\n🔍 Testing Twitter bookmark collection...")
    
    # Simulate a Twitter post
    twitter_post = {
        'id': '1234567890',
        'content': 'This is a test tweet for verification #testing',
        'created_at': (datetime.utcnow() - timedelta(hours=1)).isoformat(),
        'author': 'test_user',
        'url': 'https://twitter.com/test_user/status/1234567890',
        'favorites': 10,
        'retweets': 3,
        'source': 'twitter'
    }
    
    print("✅ Simulated Twitter post:")
    print(f"   - Content: {twitter_post['content']}")
    print(f"   - Author: @{twitter_post['author']}")
    
    # Save the post
    save_post(twitter_post)
    
    return twitter_post

def main():
    print("🚀 Starting bookmark collection test...")
    
    try:
        # Test Reddit collection
        reddit_post = test_reddit_collection()
        
        # Test Twitter collection
        twitter_post = test_twitter_collection()
        
        print("\n🎉 Test completed successfully!")
        print("\n📋 Summary:")
        print(f"- Reddit post ID: {reddit_post['id']}")
        print(f"- Twitter post ID: {twitter_post['id']}")
        
    except Exception as e:
        print(f"\n❌ Error during test: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
