#!/usr/bin/env python3
"""
Extract Reddit Comments - Add valuable comments to existing Reddit posts
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from scripts.database_manager import DatabaseManager
from core.extraction.reddit_extractor import RedditExtractor

def extract_comments_for_existing_posts():
    """Extract comments for existing Reddit posts in database"""
    print("🤖 Extracting Reddit comments for existing posts...")
    print("=" * 60)
    
    # Initialize systems
    db_manager = DatabaseManager(db_path=str(project_root / "data" / "prismind.db"))
    
    # Check Reddit credentials
    reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_username = os.getenv('REDDIT_USERNAME')
    reddit_password = os.getenv('REDDIT_PASSWORD')
    reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'PrisMind:1.0')
    
    if not (reddit_client_id and reddit_client_secret and reddit_username and reddit_password):
        print("❌ Reddit credentials not found. Please set:")
        print("   REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD")
        return
    
    try:
        extractor = RedditExtractor(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent,
            username=reddit_username,
            password=reddit_password
        )
        
        # Get all Reddit posts
        posts = db_manager.get_all_posts(include_deleted=False)
        reddit_posts = posts[posts['platform'] == 'reddit']
        
        print(f"📊 Found {len(reddit_posts)} Reddit posts to enhance with comments")
        
        if reddit_posts.empty:
            print("❌ No Reddit posts found in database")
            return
        
        enhanced_count = 0
        error_count = 0
        
        for idx, (_, post) in enumerate(reddit_posts.iterrows()):
            post_id = post['post_id']
            current_content = post['content']
            
            print(f"\n🤖 Processing {idx+1}/{len(reddit_posts)}: {post_id}")
            
            # Check if already has comments
            if "=== TOP VALUABLE COMMENTS ===" in current_content:
                print(f"   ⚠️ Already has comments, skipping")
                continue
            
            try:
                # Extract top comments for this post
                top_comments = extractor.get_top_comments(post_id, limit=5)
                
                if top_comments:
                    # Build enhanced content
                    enhanced_content = current_content
                    enhanced_content += "\n\n=== TOP VALUABLE COMMENTS ===\n"
                    
                    for i, comment in enumerate(top_comments, 1):
                        enhanced_content += f"\n💬 Comment {i} (Score: {comment['score']}) by {comment['author']}:\n"
                        enhanced_content += f"{comment['content']}\n"
                    
                    # Update the post with enhanced content
                    success = db_manager.update_post_content(post_id, enhanced_content)
                    if success:
                        print(f"   ✅ Added {len(top_comments)} comments to database")
                        enhanced_count += 1
                    else:
                        print(f"   ❌ Failed to update database")
                        error_count += 1
                else:
                    print(f"   ⚠️ No valuable comments found")
                    
            except Exception as e:
                print(f"   ❌ Error extracting comments: {str(e)}")
                error_count += 1
        
        print("\n" + "=" * 60)
        print("🎉 Reddit comment extraction completed!")
        print(f"📊 Results:")
        print(f"   ✅ Successfully enhanced: {enhanced_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📊 Total processed: {len(reddit_posts)}")
        
        if enhanced_count > 0:
            print("💡 Next: Run AI enhancement to analyze posts + comments together!")
            
    except Exception as e:
        print(f"❌ Reddit extractor error: {e}")

if __name__ == "__main__":
    extract_comments_for_existing_posts()
