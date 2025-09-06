#!/usr/bin/env python3
"""
Multi-Platform Bookmark Collection - Extract from Twitter, Reddit, and Threads
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
# Optional local media analyzer (OCR); safe to skip if deps unavailable in CI
try:
    from core.analysis.local_media_analyzer import LocalMediaAnalyzer
    _LOCAL_MEDIA_AVAILABLE = True
except Exception:
    _LOCAL_MEDIA_AVAILABLE = False
from core.extraction.reddit_extractor import RedditExtractor
from core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright
from scrape_state_manager import state_manager
from scripts.supabase_manager import SupabaseManager
from services.database import DatabaseManager


def analyze_and_store_post(db_manager, post_dict):
    """Analyze post with AI and store with analysis results"""
    try:
        # Convert dict to SocialPost for AI analysis
        from datetime import datetime

        from core.extraction.social_extractor_base import SocialPost
        
        # Parse created_at
        created_at = post_dict.get('created_at', '')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except:
                created_at = datetime.now()
        elif not isinstance(created_at, datetime):
            created_at = datetime.now()
        
        # Parse saved_at
        saved_at = post_dict.get('saved_at', '')
        if isinstance(saved_at, str) and saved_at:
            try:
                saved_at = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
            except:
                saved_at = None
        elif not isinstance(saved_at, datetime):
            saved_at = None
        
        # Ensure post_id exists with fallback
        post_id = post_dict.get('post_id') or post_dict.get('id') or post_dict.get('url', '').split('/')[-1]
        if not post_id:
            print(f"⚠️ Skipping post without ID in analysis: {post_dict.get('title', 'Unknown')}")
            return
            
        post = SocialPost(
            platform=post_dict['platform'],
            post_id=post_id,
            author=post_dict.get('author', ''),
            author_handle=post_dict.get('author_handle', post_dict.get('author', '')),
            content=post_dict.get('content', ''),
            created_at=created_at,
            url=post_dict.get('url', ''),
            post_type=post_dict.get('post_type', 'post'),
            media_urls=post_dict.get('media_urls', []),
            hashtags=post_dict.get('hashtags', []),
            mentions=post_dict.get('mentions', []),
            engagement=post_dict.get('engagement', {}),
            is_saved=post_dict.get('is_saved', True),
            saved_at=saved_at,
            folder_category=post_dict.get('folder_category', ''),
            analysis=post_dict.get('analysis', None)
        )
        
        # Analyze with AI
        analyzer = IntelligentContentAnalyzer()
        analysis_result = analyzer.analyze_bookmark(post)

        # Integrate media analysis (optional)
        if _LOCAL_MEDIA_AVAILABLE and post.media_urls:
            try:
                media_analyzer = LocalMediaAnalyzer()
                media_enhanced = media_analyzer.analyze_post_media({
                    'post_id': post.post_id,
                    'media_urls': post.media_urls,
                    'value_score': analysis_result.get('value_score', 5)
                })
                # Merge media analysis into AI result
                analysis_result['media_analysis'] = media_enhanced.get('media_analysis')
                # Update value score with media boost if present
                if media_enhanced.get('value_score'):
                    analysis_result['value_score'] = media_enhanced['value_score']
            except Exception as _:
                pass
        
        # Add analysis results to post_dict
        post_dict.update({
            'post_id': post_id,  # Ensure post_id is set correctly
            'category': analysis_result.get('category', 'uncertain'),
            # Optionally reduce or disable value scoring for ranking only
            'value_score': analysis_result.get('intelligent_value_score', analysis_result.get('value_score', None)) if os.getenv('USE_VALUE_SCORER', '0') == '1' else None,
            'sentiment': analysis_result.get('sentiment', 'neutral'),
            'ai_summary': analysis_result.get('summary', ''),
            'key_concepts': str(analysis_result.get('key_concepts', [])),
            'smart_tags': str(analysis_result.get('smart_tags', [])),
            'intelligence_analysis': str(analysis_result.get('intelligence_analysis', {})),
            'actionable_insights': str(analysis_result.get('actionable_insights', []))
        })
        
        # Store with AI analysis in local SQLite
        db_manager.add_post(post_dict)

        # Optional: sync to Supabase if enabled (Supabase is source of truth)
        if os.getenv('SAVE_TO_SUPABASE', '0') == '1':
            try:
                if not hasattr(analyze_and_store_post, '_supabase'):
                    analyze_and_store_post._supabase = SupabaseManager()
                supa = analyze_and_store_post._supabase
                # Ensure numeric score or null
                value_score = post_dict.get('value_score')
                if isinstance(value_score, str):
                    try:
                        value_score = float(value_score)
                    except:
                        value_score = None
                supa.insert_post({
                    **post_dict,
                    # Ensure JSONable
                    'media_urls': json.dumps(post_dict.get('media_urls', [])),
                    'hashtags': json.dumps(post_dict.get('hashtags', [])),
                    'mentions': json.dumps(post_dict.get('mentions', [])),
                    'key_concepts': post_dict.get('key_concepts'),
                    'value_score': value_score,
                })
            except Exception as _:
                pass
        print(f"🤖 AI analyzed: {post_dict['post_id']} -> {analysis_result.get('category', 'uncertain')} (Score: {analysis_result.get('value_score', 0.0)})")
        
    except Exception as e:
        print(f"❌ AI analysis failed for {post_dict.get('post_id', 'unknown')}: {e}")
        # Store without AI analysis as fallback
        db_manager.add_post(post_dict)

async def collect_twitter_bookmarks(db_manager, existing_ids, existing_urls=None):
    """Collect Twitter bookmarks"""
    print("\n🐦 TWITTER COLLECTION")
    print("-" * 30)
    
    # Get last scrape info
    last_scrape = state_manager.get_last_scrape_info('twitter')
    if last_scrape:
        print(f"📅 Last scraped: {last_scrape['last_scraped_at']}")
        print(f"📊 Total posts scraped: {last_scrape['total_posts_scraped']}")
        if last_scrape['last_post_id']:
            print(f"🔗 Last post ID: {last_scrape['last_post_id']}")
    else:
        print("🆕 First time scraping Twitter")
    
    # Get Twitter credentials
    twitter_username = os.getenv('TWITTER_USERNAME')
    if not twitter_username:
        config_dir = project_root / "config"
        if config_dir.exists():
            cookie_files = list(config_dir.glob("twitter_cookies_*.json"))
            if cookie_files:
                cookie_file = cookie_files[0]
                twitter_username = cookie_file.stem.replace("twitter_cookies_", "")
                print(f"🔍 Found existing session for: {twitter_username}")
    
    if not twitter_username:
        print("❌ No Twitter username found. Please set TWITTER_USERNAME environment variable.")
        return 0
    
    try:
        # Get Twitter password from environment
        twitter_password = os.getenv('TWITTER_PASSWORD')
        
        extractor = TwitterExtractorPlaywright(
            username=twitter_username,
            password=twitter_password,
            headless=True,
            cookie_file=str(project_root / "config" / f"twitter_cookies_{twitter_username}.json")
        )
        
        print("🔍 Extracting Twitter SAVED posts (bookmarks only)...")
        # Get limit from environment variable or use default
        twitter_limit = int(os.getenv('TWITTER_LIMIT', '200'))
        saved_posts = await extractor.get_saved_posts(limit=twitter_limit)
        
        if saved_posts:
            print(f"🔍 Found {len(saved_posts)} Twitter posts")
            new_posts = []
            for post in saved_posts:
                post_dict = post.__dict__ if hasattr(post, '__dict__') else post
                post_id = post_dict.get('post_id') or post_dict.get('id') or post_dict.get('url', '').split('/')[-1]
                
                if not post_id:
                    print(f"   ⚠️ Skipping post without ID: {post_dict.get('title', 'Unknown')}")
                    continue
                    
                # Check for duplicates by both post_id and URL
                is_duplicate = False
                if post_id in existing_ids:
                    print(f"   ⚠️ Post ID {post_id} already exists, skipping...")
                    is_duplicate = True
                
                if not is_duplicate and existing_urls and post_dict.get('url') in existing_urls:
                    print(f"   ⚠️ URL {post_dict.get('url')} already exists, skipping...")
                    is_duplicate = True
                
                if not is_duplicate:
                    new_posts.append(post_dict)
                    existing_ids.add(post_id)
                    if post_dict.get('url') and existing_urls:
                        existing_urls.add(post_dict.get('url'))
            
            # Add new posts to database with AI analysis
            last_post_id = None
            last_post_url = None
            
            for post_dict in new_posts:
                analyze_and_store_post(db_manager, post_dict)
                
                # Mark as scraped in state manager
                post_id = post_dict.get('post_id')
                if post_id:
                    state_manager.mark_post_scraped(
                        post_id=post_id,
                        platform='twitter',
                        url=post_dict.get('url'),
                        title=post_dict.get('title'),
                        author=post_dict.get('author')
                    )
                    last_post_id = post_id
                    last_post_url = post_dict.get('url')
            
            # Update scrape state
            state_manager.update_scrape_state(
                platform='twitter',
                last_post_id=last_post_id,
                last_post_url=last_post_url,
                posts_scraped=len(new_posts),
                success=True
            )
            
            print(f"✅ Twitter: {len(new_posts)} new bookmarks added")
            return len(new_posts)
        else:
            print("📭 No Twitter bookmarks found")
            return 0
            
    except Exception as e:
        print(f"❌ Twitter collection error: {e}")
        # Update scrape state with failure
        state_manager.update_scrape_state(
            platform='twitter',
            posts_scraped=0,
            success=False
        )
        return 0
    finally:
        try:
            await extractor.close()
        except:
            pass

def collect_reddit_bookmarks(db_manager, existing_ids, existing_urls=None):
    """Collect Reddit posts using working public API approach"""
    print("\n🤖 REDDIT COLLECTION")
    print("-" * 30)
    
    # Get last scrape info
    last_scrape = state_manager.get_last_scrape_info('reddit')
    if last_scrape:
        print(f"📅 Last scraped: {last_scrape['last_scraped_at']}")
        print(f"📊 Total posts scraped: {last_scrape['total_posts_scraped']}")
        if last_scrape['last_post_id']:
            print(f"🔗 Last post ID: {last_scrape['last_post_id']}")
    else:
        print("🆕 First time scraping Reddit")
    
    try:
        # Use the automatic Reddit collector
        from automatic_reddit_collector import AutomaticRedditBookmarksCollector
        
        collector = AutomaticRedditBookmarksCollector()
        posts = collector.collect_bookmarks()
        
        if not posts:
            print("📭 No Reddit posts found")
            return 0
        
        print(f"📊 Found {len(posts)} Reddit posts")
        
        # Store posts in database
        stored_count = 0
        for post in posts:
            post_id = post['url'].split('/')[-1] if '/' in post['url'] else post['url']
            
            if post_id not in existing_ids:
                try:
                    # Convert to the format expected by analyze_and_store_post
                    post_dict = {
                        'platform': 'reddit',
                        'post_id': post_id,
                        'title': post['title'],
                        'content': post['content'],
                        'author': post['author'],
                        'author_handle': f"u/{post['author']}",
                        'url': post['url'],
                        'created_at': post['created_timestamp'],
                        'post_type': 'post',
                        'media_urls': [],
                        'hashtags': [],
                        'mentions': [],
                        'engagement': {
                            'score': post['score'],
                            'num_comments': post.get('num_comments', 0)
                        },
                        'is_saved': True,
                        'saved_at': datetime.now().isoformat(),
                        'folder_category': f"r/{post['subreddit']}"
                    }
                    
                    analyze_and_store_post(db_manager, post_dict)
                    stored_count += 1
                    
                except Exception as e:
                    print(f"⚠️ Error storing Reddit post: {e}")
                    continue
        
        print(f"✅ Reddit: {stored_count} new posts stored")
        
        # Update scrape state
        state_manager.update_scrape_state('reddit', stored_count, posts[0]['url'] if posts else None)
        
        return stored_count
        
    except Exception as e:
        print(f"❌ Reddit collection failed: {e}")
        return 0
def collect_twitter_bookmarks_sync(db_manager, existing_ids, existing_urls=None):
    """Synchronous wrapper for Twitter collection"""
    import asyncio
    try:
        return asyncio.run(collect_twitter_bookmarks(db_manager, existing_ids, existing_urls))
    except Exception as e:
        print(f"❌ Twitter collection error: {e}")
        return 0

async def collect_threads_bookmarks(db_manager, existing_ids):
    """Collect Threads saved posts (DISABLED - authentication issues)"""
    print("\n🧵 THREADS COLLECTION (DISABLED)")
    print("-" * 30)
    print("❌ Threads collection is currently disabled")
    print("💡 Reason: Authentication issues with Instagram/Threads")
    print("💡 To re-enable Threads collection:")
    print("   1. Export fresh cookies from browser")
    print("   2. Update config/threads_cookies_qronoya.json")
    print("   3. Test authentication manually")
    print("   4. Remove this disabled message")
    return 0

async def main():
    """Main collection function"""
    print("📥 Starting MULTI-PLATFORM bookmark collection...")
    print("=" * 60)
    
    # Initialize systems
    db_manager = DatabaseManager(db_path=str(project_root / "data" / "prismind.db"))
    
    # Get existing post IDs to avoid duplicates
    existing_posts = db_manager.get_all_posts(include_deleted=False)
    existing_ids = set(existing_posts['post_id'].tolist()) if not existing_posts.empty else set()
    
    # Also get URLs for additional duplicate checking
    existing_urls = set()
    if not existing_posts.empty and 'url' in existing_posts.columns:
        existing_urls = set(existing_posts['url'].dropna().tolist())
    
    print(f"📊 Database contains {len(existing_ids)} existing posts")
    print(f"🔍 Existing post IDs: {list(existing_ids)[:5]}...")  # Show first 5 IDs
    print(f"🔗 Existing URLs: {len(existing_urls)} unique URLs")
    
    total_new = 0
    
    # Collect from all platforms
    try:
        # Twitter
        twitter_count = await collect_twitter_bookmarks(db_manager, existing_ids, existing_urls)
        total_new += twitter_count
        
        # Reddit  
        reddit_count = collect_reddit_bookmarks(db_manager, existing_ids, existing_urls)
        total_new += reddit_count
        
        # Threads (disabled due to authentication issues)
        threads_count = await collect_threads_bookmarks(db_manager, existing_ids)
        total_new += threads_count
        
    except KeyboardInterrupt:
        print("\n⚠️ Collection interrupted by user")
        return
    
    print("\n" + "=" * 60)
    print("🎉 MULTI-PLATFORM collection completed!")
    print(f"📊 Total new bookmarks collected: {total_new}")
    
    # Show scraping stats
    stats = state_manager.get_scraping_stats()
    print("\n📈 SCRAPING STATISTICS:")
    print(f"📊 Total posts tracked: {stats['total_posts']}")
    for platform_stat in stats['platform_stats']:
        print(f"   {platform_stat['platform']}: {platform_stat['total_posts_scraped']} posts")
    
    if total_new > 0:
        print("💡 Tip: Use the dashboard's AI enhancement to analyze new content")
    else:
        print("💡 No new bookmarks found - you're up to date!")

if __name__ == "__main__":
    asyncio.run(main())
