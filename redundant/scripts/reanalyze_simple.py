#!/usr/bin/env python3
"""
Simple re-analysis using the analyzer's built-in fallback logic
"""

import os
import sys
import time
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
from core.extraction.social_extractor_base import SocialPost
from scripts.supabase_manager import SupabaseManager

def reanalyze_simple():
    """Simple re-analysis using analyzer's built-in fallback logic"""
    
    print("🎯 Simple Re-analysis (Using Built-in Fallback Logic)")
    print("=" * 50)
    
    # Initialize database manager
    db_manager = SupabaseManager()
    
    # Get all posts
    print("📊 Fetching all posts from database...")
    all_posts = db_manager.get_posts(limit=1000)
    
    if not all_posts:
        print("❌ No posts found in database")
        return
    
    print(f"📊 Found {len(all_posts)} posts")
    
    # Initialize AI analyzer (will automatically try services in order)
    print("🧠 Initializing AI analyzer...")
    analyzer = IntelligentContentAnalyzer()
    
    # Track statistics
    total_posts = len(all_posts)
    analyzed_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"\n🔍 Starting analysis for {total_posts} posts...")
    print("-" * 50)
    
    for idx, post_data in enumerate(all_posts, 1):
        try:
            # Check if post already has AI analysis (check multiple fields)
            has_ai_analysis = (
                # Check ai_summary field
                (post_data.get('ai_summary') and str(post_data.get('ai_summary')).strip() and str(post_data.get('ai_summary')) != 'None') or
                # Check summary field
                (post_data.get('summary') and str(post_data.get('summary')).strip() and str(post_data.get('summary')) != 'None') or
                # Check if it has category and value_score (indicating previous analysis)
                (post_data.get('category') and post_data.get('value_score') and post_data.get('value_score') > 0)
            )
            
            if has_ai_analysis:
                print(f"⏭️  [{idx}/{total_posts}] Skipping - already has AI analysis")
                skipped_count += 1
                continue
            
            # Create SocialPost object with safe defaults
            try:
                # Handle None values more robustly
                platform = str(post_data.get('platform', 'unknown') or 'unknown')
                author = str(post_data.get('author', 'Unknown') or 'Unknown')
                content = str(post_data.get('content', '') or '')
                url = str(post_data.get('url', '') or '')
                post_type = str(post_data.get('post_type', 'post') or 'post')
                
                # Handle lists safely
                hashtags = post_data.get('hashtags') or []
                if hashtags is None:
                    hashtags = []
                elif isinstance(hashtags, str):
                    hashtags = [hashtags]
                
                mentions = post_data.get('mentions') or []
                if mentions is None:
                    mentions = []
                elif isinstance(mentions, str):
                    mentions = [mentions]
                
                engagement = post_data.get('engagement') or {}
                if engagement is None:
                    engagement = {}
                
                media_urls = post_data.get('media_urls') or []
                if media_urls is None:
                    media_urls = []
                elif isinstance(media_urls, str):
                    media_urls = [media_urls]
                
                post_id = post_data.get('post_id') or post_data.get('id') or str(idx)
                
                post = SocialPost(
                    platform=platform,
                    author=author,
                    author_handle=author,
                    content=content,
                    created_at=datetime.now(),
                    url=url,
                    post_type=post_type,
                    hashtags=hashtags,
                    mentions=mentions,
                    engagement=engagement,
                    media_urls=media_urls,
                    post_id=str(post_id)
                )
            except Exception as e:
                print(f"❌ [{idx}/{total_posts}] Error creating SocialPost: {e}")
                continue
            
            # Get title safely
            title = post_data.get('title')
            if title is None:
                title = 'No title'
            elif not isinstance(title, str):
                title = str(title)
            
            print(f"🤖 [{idx}/{total_posts}] Analyzing: {title[:50]}...")
            
            # Let the analyzer handle all the fallback logic automatically
            try:
                analysis_result = analyzer.analyze_bookmark(post)
                
                # Update post data with AI analysis
                value_score = analysis_result.get('intelligent_value_score', analysis_result.get('value_score', None))
                # Convert to integer for database
                if value_score is not None:
                    try:
                        value_score = int(float(value_score))
                    except:
                        value_score = None
                
                updated_post = {
                    'category': analysis_result.get('category', 'uncertain'),
                    'value_score': value_score,
                    'ai_summary': analysis_result.get('summary', ''),
                    'summary': analysis_result.get('summary', '')
                }
                
                # Update in database
                db_manager.update_post(post_data.get('id'), updated_post)
                print(f"✅ [{idx}/{total_posts}] Analyzed - Category: {analysis_result.get('category', 'Unknown')}, Score: {analysis_result.get('intelligent_value_score', 'Unknown')}")
                analyzed_count += 1
                
            except Exception as e:
                print(f"❌ [{idx}/{total_posts}] Analysis failed: {e}")
                error_count += 1
            
            # Small delay
            time.sleep(1)
            
            # Show progress every 10 posts
            if idx % 10 == 0:
                print(f"📊 Progress: {idx}/{total_posts} ({idx/total_posts*100:.1f}%) - Analyzed: {analyzed_count}, Errors: {error_count}")
            
        except Exception as e:
            print(f"❌ [{idx}/{total_posts}] Error: {e}")
            error_count += 1
            continue
    
    print("\n" + "=" * 50)
    print("📊 Analysis Complete!")
    print(f"✅ Analyzed: {analyzed_count} posts")
    print(f"⏭️  Skipped: {skipped_count} posts (already had AI analysis)")
    print(f"❌ Errors: {error_count} posts")
    print(f"📈 Success rate: {analyzed_count/(analyzed_count+error_count)*100:.1f}%" if (analyzed_count+error_count) > 0 else "📈 No posts processed")
    
    if analyzed_count > 0:
        print(f"\n🎉 Successfully added AI analysis to {analyzed_count} posts!")
        print("💡 You can now view the AI summaries in the Browse Posts tab")

if __name__ == "__main__":
    reanalyze_simple()
