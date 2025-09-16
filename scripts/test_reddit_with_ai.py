#!/usr/bin/env python3
"""
Test script for Reddit collection with AI-powered summaries and tags
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.absolute())
sys.path.insert(0, project_root)

# Now import the module
from src.core.extraction.working_reddit_extractor import WorkingRedditExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_reddit_collection():
    """Test Reddit collection with AI-powered analysis"""
    try:
        # Initialize the Reddit extractor
        logger.info("🚀 Initializing Reddit extractor...")
        extractor = WorkingRedditExtractor()
        
        # Fetch saved posts with AI analysis
        logger.info("🔍 Fetching saved posts with AI analysis...")
        posts = extractor.get_saved_posts(limit=3)  # Only get 3 posts for testing
        
        # Print the results
        print("\n" + "="*80)
        print(f"🎉 Successfully processed {len(posts)} posts")
        print("="*80 + "\n")
        
        for i, post in enumerate(posts, 1):
            print(f"📌 Post #{i}")
            print(f"   Title: {post.get('title')}")
            print(f"   Subreddit: r/{post.get('subreddit')}")
            print(f"   URL: {post.get('url')}")
            print(f"   Posted: {post.get('created_timestamp')}")
            print(f"   Score: {post.get('score')} (Upvote ratio: {post.get('upvote_ratio')*100:.1f}%)")
            print(f"   Comments: {post.get('num_comments')}")
            print(f"   Category: {post.get('category', 'N/A')}")
            print(f"   Tags: {', '.join(post.get('tags', [])) or 'None'}")
            print("\n💡 Summary:")
            print(f"   {post.get('summary', 'No summary available')}")
            print("\n" + "-"*80 + "\n")
        
        # Save results to a JSON file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"reddit_analysis_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(posts, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"❌ Error during Reddit collection test: {str(e)}", exc_info=True)
        return False
    
    return True

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    success = test_reddit_collection()
    
    if success:
        logger.info("✅ Test completed successfully!")
    else:
        logger.error("❌ Test failed!")
        exit(1)
