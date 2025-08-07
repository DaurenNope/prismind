#!/usr/bin/env python3
"""
Media Analysis - Analyze images and videos in social media posts using AI
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from scripts.database_manager import DatabaseManager
from core.analysis.media_analyzer import MediaAnalyzer

def main():
    print("🖼️ Starting media analysis...")
    print("=" * 50)
    
    # Initialize systems
    db_manager = DatabaseManager(db_path=str(project_root / "data" / "prismind.db"))
    media_analyzer = MediaAnalyzer()
    
    # Get all posts that have media URLs
    posts = db_manager.get_all_posts(include_deleted=False)
    
    if posts.empty:
        print("❌ No posts found in database")
        return
    
    # Filter posts that have media (either in media_urls or mentioned in content) but no media analysis
    posts_with_media = posts[
        (
            # Has actual media URLs
            (
                (posts['media_urls'].notna()) & 
                (posts['media_urls'] != '') &
                (posts['media_urls'] != '[]')
            ) |
            # Or mentions media in content (pic.twitter.com, video, image, photo)
            (posts['content'].str.contains(r'pic\.twitter\.com|video|image|photo|gif|youtube\.com|youtu\.be', case=False, na=False))
        ) &
        (
            (posts['media_analysis'].isna()) | 
            (posts['media_analysis'] == '') |
            (posts['media_analysis'] == '{}')
        )
    ]
    
    print(f"📊 Found {len(posts_with_media)} posts with media needing analysis")
    
    if posts_with_media.empty:
        print("✅ All media posts already analyzed or no media posts found")
        return
    
    analyzed_count = 0
    error_count = 0
    
    for idx, (_, post) in enumerate(posts_with_media.iterrows()):
        post_id = post['post_id']
        platform = post['platform']
        
        # Parse media URLs or extract from content
        media_urls = []
        try:
            if post['media_urls'] and post['media_urls'] != '[]':
                media_urls = json.loads(post['media_urls']) if isinstance(post['media_urls'], str) else post['media_urls']
        except:
            pass
        
        # If no direct media URLs, extract from content
        if not media_urls:
            import re
            content = post['content']
            # Extract Twitter pic links, YouTube links, etc.
            url_patterns = [
                r'pic\.twitter\.com/\w+',
                r'youtube\.com/watch\?v=[\w-]+',
                r'youtu\.be/[\w-]+',
                r'https?://[^\s]+\.(jpg|jpeg|png|gif|mp4|webm)',
            ]
            
            for pattern in url_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                media_urls.extend(['https://' + match if not match.startswith('http') else match for match in matches])
        
        if not media_urls:
            # Still analyze posts that mention media even without direct URLs
            media_urls = ['content_mentions_media']
        
        print(f"\n🖼️ Analyzing {idx+1}/{len(posts_with_media)}: {post_id}")
        print(f"   Media files: {len(media_urls)}")
        
        try:
            # Analyze media for this post using the correct method
            media_analysis = media_analyzer.analyze_media_urls(
                media_urls=media_urls,
                post_context=post['content']
            )
            
            if media_analysis:
                # Update database with media analysis
                db_manager.update_post_analysis(
                    post_id=post_id,
                    analysis_data={
                        'media_analysis': media_analysis,
                        'media_analysis_date': datetime.now().isoformat()
                    }
                )
                print(f"   ✅ Media analysis completed")
                analyzed_count += 1
            else:
                print(f"   ⚠️ No media analysis generated")
                
        except Exception as e:
            print(f"   ❌ Error analyzing media: {str(e)}")
            error_count += 1
    
    print("\n" + "=" * 50)
    print("🎉 Media analysis completed!")
    print(f"📊 Results:")
    print(f"   ✅ Successfully analyzed: {analyzed_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📊 Total processed: {len(posts_with_media)}")
    
    if analyzed_count > 0:
        print("💡 Check the dashboard to see media insights!")

if __name__ == "__main__":
    main()