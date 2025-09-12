#!/usr/bin/env python3
"""
Test script for Reddit collector with actual data.
This script tests the Reddit collector with real API calls.
"""
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Check for required environment variables
required_vars = [
    'REDDIT_CLIENT_ID',
    'REDDIT_CLIENT_SECRET',
    'REDDIT_USERNAME',
    'REDDIT_PASSWORD'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print("❌ Missing required environment variables:")
    for var in missing_vars:
        print(f"   - {var}")
    print("\nPlease set these variables in your .env file.")
    sys.exit(1)

# Import the Reddit collector
print("📦 Attempting to import WorkingRedditExtractor...")
print(f"📂 Current working directory: {os.getcwd()}")
print(f"🔍 Python path: {sys.path}")

# Print all directories in the current path
print("📂 Directories in current path:")
for directory in os.listdir(os.getcwd()):
    if os.path.isdir(os.path.join(os.getcwd(), directory)):
        print(f"  - {directory}")

# Print src directory structure if it exists
if os.path.exists(os.path.join(os.getcwd(), 'src')):
    print("📂 src directory structure:")
    for root, dirs, files in os.walk(os.path.join(os.getcwd(), 'src')):
        print(f"  - {root}")
        for file in files:
            if file.endswith('.py'):
                print(f"    - {file}")

try:
    print("🔄 Trying import from src.core.extraction...")
    from src.core.extraction import WorkingRedditExtractor
    print("✅ Successfully imported WorkingRedditExtractor")
except ImportError as e:
    print(f"❌ Error importing Reddit extractor: {e}")
    print("🔄 Trying alternative import path...")
    try:
        from src.core.extraction.working_reddit_extractor import WorkingRedditExtractor
        print("✅ Successfully imported WorkingRedditExtractor from direct path")
    except ImportError as e2:
        print(f"❌ Error with alternative import: {e2}")
        print("📋 Trying to debug import issues:")
        try:
            # Try to import the src module first
            print("🔍 Attempting to import src module...")
            import src
            print(f"✅ Successfully imported src module: {dir(src)}")
            
            # Try to import src.core
            print("🔍 Attempting to import src.core module...")
            import src.core
            print(f"✅ Successfully imported src.core module: {dir(src.core)}")
            
            # Try to import src.core.extraction
            print("🔍 Attempting to import src.core.extraction module...")
            import src.core.extraction
            print(f"✅ Successfully imported src.core.extraction module: {dir(src.core.extraction)}")
        except ImportError as e3:
            print(f"❌ Cannot import modules: {e3}")
            
        # List all available modules in Python path
        print("📋 Listing all modules in sys.path:")
        for path in sys.path:
            if os.path.exists(path) and os.path.isdir(path):
                print(f"  Modules in {path}:")
                for item in os.listdir(path):
                    if os.path.isdir(os.path.join(path, item)) and not item.startswith('__'):
                        print(f"    - {item}")
        
        # Try a fallback approach - direct import
        print("🔄 Trying fallback approach - direct import...")
        try:
            sys.path.insert(0, os.path.join(os.getcwd(), 'src', 'core', 'extraction'))
            print(f"🔍 Updated Python path: {sys.path}")
            from working_reddit_extractor import WorkingRedditExtractor
            print("✅ Successfully imported WorkingRedditExtractor using fallback")
        except ImportError as e4:
            print(f"❌ All import attempts failed: {e4}")
            sys.exit(1)

def main():
    print("🚀 Testing Reddit Collector with Real Data")
    print("=" * 50)
    
    try:
        # Initialize the Reddit extractor
        print("\n🔌 Initializing Reddit extractor...")
        extractor = WorkingRedditExtractor()
        
        # Test getting posts from subreddits
        print("\n📥 Fetching hot posts from popular subreddits...")
        posts = extractor.get_reddit_posts_from_subreddits()
        
        if not posts:
            print("\n❌ No posts found or error occurred.")
            return
            
        print(f"\n✅ Successfully fetched {len(posts)} high-quality posts:")
        for i, post in enumerate(posts[:5], 1):  # Show first 5 posts
            print(f"\n📌 Post {i}:")
            print(f"   - Title: {post.get('title', 'No title')}")
            print(f"   - Author: u/{post.get('author', 'unknown')}")
            print(f"   - Subreddit: r/{post.get('subreddit', 'unknown')}")
            print(f"   - Score: {post.get('score', 0)}")
            print(f"   - URL: {post.get('url', 'No URL')}")
            
    except Exception as e:
        print(f"\n❌ Error during Reddit collection test: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
