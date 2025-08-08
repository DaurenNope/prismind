#!/usr/bin/env python3
"""
Fix categorization system by integrating AI analysis
"""

from scripts.database_manager import DatabaseManager
from core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
from core.extraction.social_extractor_base import SocialPost
import pandas as pd
import asyncio

def analyze_uncategorized_posts():
    """Analyze all uncategorized posts with AI"""
    print("🔍 Analyzing uncategorized posts with AI...")
    print("=" * 60)
    
    # Initialize systems
    db = DatabaseManager()
    analyzer = IntelligentContentAnalyzer()
    
    # Get all posts
    posts_df = db.get_all_posts()
    print(f"📊 Total posts: {len(posts_df)}")
    
    # Find uncategorized posts
    uncategorized = posts_df[
        posts_df['category'].isna() | 
        (posts_df['category'] == '') | 
        (posts_df['category'] == 'Unknown') |
        (posts_df['category'] == 'None')
    ]
    
    print(f"❓ Uncategorized posts: {len(uncategorized)}")
    
    if len(uncategorized) == 0:
        print("✅ All posts are already categorized!")
        return
    
    # Analyze each uncategorized post
    analyzed_count = 0
    for idx, post_data in uncategorized.iterrows():
        try:
            print(f"\n🔍 Analyzing post {idx + 1}/{len(uncategorized)}: {post_data['post_id']}")
            
            # Convert DataFrame row to SocialPost object
            from datetime import datetime
            
            # Parse created_at
            created_at = post_data.get('created_at', '')
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.now()
            elif not isinstance(created_at, datetime):
                created_at = datetime.now()
            
            # Parse saved_at
            saved_at = post_data.get('saved_at', '')
            if isinstance(saved_at, str) and saved_at:
                try:
                    saved_at = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                except:
                    saved_at = None
            elif not isinstance(saved_at, datetime):
                saved_at = None
            
            post = SocialPost(
                platform=post_data['platform'],
                post_id=post_data['post_id'],
                author=post_data.get('author', ''),
                author_handle=post_data.get('author_handle', post_data.get('author', '')),
                content=post_data.get('content', ''),
                created_at=created_at,
                url=post_data.get('url', ''),
                post_type=post_data.get('post_type', 'post'),
                media_urls=post_data.get('media_urls', []),
                hashtags=post_data.get('hashtags', []),
                mentions=post_data.get('mentions', []),
                engagement=post_data.get('engagement', {}),
                is_saved=post_data.get('is_saved', True),
                saved_at=saved_at,
                folder_category=post_data.get('folder_category', ''),
                analysis=post_data.get('analysis', None)
            )
            
            # Analyze with AI
            analysis_result = analyzer.analyze_bookmark(post)
            
            # Update database with analysis results
            update_data = {
                'category': analysis_result.get('category', 'uncertain'),
                'value_score': analysis_result.get('value_score', 0.0),
                'sentiment': analysis_result.get('sentiment', 'neutral'),
                'ai_summary': analysis_result.get('summary', ''),
                'key_concepts': str(analysis_result.get('key_concepts', [])),
                'smart_tags': str(analysis_result.get('smart_tags', [])),
                'intelligence_analysis': str(analysis_result.get('intelligence_analysis', {})),
                'actionable_insights': str(analysis_result.get('actionable_insights', []))
            }
            
            # Update the post in database
            success = db.update_post_smart_fields(post_data['post_id'], **update_data)
            
            if success:
                analyzed_count += 1
                print(f"✅ Analyzed and categorized: {update_data['category']} (Score: {update_data['value_score']})")
            else:
                print(f"❌ Failed to update post {post_data['post_id']}")
                
        except Exception as e:
            print(f"❌ Error analyzing post {post_data['post_id']}: {e}")
            continue
    
    print(f"\n🎉 Analysis complete!")
    print(f"✅ Successfully analyzed: {analyzed_count}/{len(uncategorized)} posts")
    
    # Show new category distribution
    updated_posts = db.get_all_posts()
    categorized = updated_posts[updated_posts['category'].notna() & (updated_posts['category'] != '')]
    print(f"\n📊 New category distribution:")
    category_counts = categorized['category'].value_counts()
    for category, count in category_counts.items():
        print(f"   {category}: {count} posts")

def integrate_ai_into_collection():
    """Show how to integrate AI analysis into the collection workflow"""
    print("\n🔧 INTEGRATION GUIDE")
    print("=" * 60)
    print("To fix categorization permanently, modify collect_multi_platform.py:")
    print()
    print("1. Import the analyzer:")
    print("   from core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer")
    print()
    print("2. Initialize in main():")
    print("   analyzer = IntelligentContentAnalyzer()")
    print()
    print("3. Analyze each new post before adding to database:")
    print("   # After extracting posts, before adding to database:")
    print("   for post in new_posts:")
    print("       analysis = analyzer.analyze_bookmark(post)")
    print("       post.update(analysis)  # Add analysis results to post")
    print("       db_manager.add_post(post)")
    print()
    print("4. This will ensure all new posts are categorized automatically!")

if __name__ == "__main__":
    # Fix existing uncategorized posts
    analyze_uncategorized_posts()
    
    # Show integration guide
    integrate_ai_into_collection()
