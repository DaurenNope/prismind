#!/usr/bin/env python3
"""
Multi-Platform Bookmark Collection - Extract from Twitter, Reddit, and Threads
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Import after setting up paths
from core.extraction.social_extractor_base import SocialPost

from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
# Optional local media analyzer (OCR); safe to skip if deps unavailable in CI
try:
    from src.core.analysis.local_media_analyzer import LocalMediaAnalyzer
    _LOCAL_MEDIA_AVAILABLE = True
except Exception:
    _LOCAL_MEDIA_AVAILABLE = False
from src.core.extraction.reddit_extractor import RedditExtractor
from src.core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright
from src.scrape_state_manager import state_manager
from scripts.supabase_manager import SupabaseManager
from src.services.new_database_manager import get_database_manager


async def analyze_and_store_post(db_manager, post_dict, supabase_manager=None):
    """
    Analyze post with AI and store with analysis results.
    
    Args:
        db_manager: Database manager instance
        post_dict: Dictionary containing post data
        supabase_manager: Optional SupabaseManager instance for cloud sync
        
    Returns:
        bool: True if post was successfully stored, False otherwise
    """
    import os
    from datetime import datetime, timezone
    import json
    import traceback
    from typing import Dict, Any, Optional, Union, List
    
    # Initialize logging
    def log(message: str, level: str = "info"):
        """Helper function for consistent logging"""
        prefix = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }.get(level, "ℹ️")
        print(f"{prefix} {message}")
    
    try:
        # Log start of processing
        post_id = post_dict.get('post_id') or post_dict.get('id', 'unknown')
        log(f"Starting analyze_and_store_post for post: {post_id}")
        log(f"Platform: {post_dict.get('platform', 'unknown')}")
        log(f"Title: {post_dict.get('title', 'No title')}")
        
        # --- Data Preparation ---
        # Parse created_at
        created_at = None
        created_at_str = post_dict.get('created_at')
        if created_at_str:
            if isinstance(created_at_str, str):
                try:
                    # Handle different datetime formats
                    if 'T' in created_at_str:
                        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    elif created_at_str.replace('.', '').isdigit():
                        created_at = datetime.fromtimestamp(float(created_at_str), tz=timezone.utc)
                    else:
                        # Try parsing with common formats
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                            try:
                                created_at = datetime.strptime(created_at_str, fmt).replace(tzinfo=timezone.utc)
                                break
                            except ValueError:
                                continue
                    
                    if created_at:
                        log(f"Parsed created_at: {created_at.isoformat()}")
                    else:
                        log(f"Could not parse created_at: {created_at_str}", "warning")
                        created_at = datetime.now(timezone.utc)
                        
                except Exception as e:
                    log(f"Error parsing created_at {created_at_str}: {e}", "warning")
                    created_at = datetime.now(timezone.utc)
            elif isinstance(created_at_str, (int, float)):
                created_at = datetime.fromtimestamp(created_at_str, tz=timezone.utc)
            elif isinstance(created_at_str, datetime):
                created_at = created_at_str
        
        if not created_at:
            created_at = datetime.now(timezone.utc)
            log("Using current time for created_at", "warning")
        
        # Ensure post_id exists with fallback
        post_id = str(post_id or post_dict.get('url', '').split('/')[-1] or f"temp_{int(datetime.now().timestamp())}")
        if not post_id or post_id.startswith('temp_'):
            log(f"Generated temporary post_id: {post_id}", "warning")
        
        # Prepare engagement data
        engagement = post_dict.get('engagement', {})
        if hasattr(engagement, 'to_dict'):
            engagement = engagement.to_dict()
        elif not isinstance(engagement, dict):
            engagement = {}
        
        # Ensure media_urls is a list of strings
        media_urls = post_dict.get('media_urls', [])
        if not isinstance(media_urls, list):
            media_urls = [media_urls] if media_urls else []
        media_urls = [str(url) for url in media_urls if url]
        
        # Prepare hashtags and mentions
        def prepare_list_field(field: Any) -> List[str]:
            """Convert field to list of strings"""
            if not field:
                return []
            if isinstance(field, str):
                return [s.strip() for s in field.split(',') if s.strip()]
            if isinstance(field, (list, tuple, set)):
                return [str(item).strip() for item in field if item]
            return [str(field)]
        
        hashtags = prepare_list_field(post_dict.get('hashtags', []))
        mentions = prepare_list_field(post_dict.get('mentions', []))
        
        # Prepare the post data for storage
        post_data = {
            'platform': str(post_dict.get('platform', 'unknown')),
            'post_id': post_id,
            'author': str(post_dict.get('author', '')),
            'author_handle': str(post_dict.get('author_handle', post_dict.get('author', ''))),
            'content': str(post_dict.get('content', '')),
            'created_at': created_at.isoformat(),
            'url': str(post_dict.get('url', '')),
            'post_type': str(post_dict.get('post_type', 'post')),
            'media_urls': media_urls,
            'hashtags': hashtags,
            'mentions': mentions,
            'engagement': engagement,
            'is_saved': bool(post_dict.get('is_saved', True)),
            'saved_at': datetime.now(timezone.utc).isoformat(),
            'subreddit': str(post_dict.get('subreddit', '')),
            'title': str(post_dict.get('title', '')),
            'folder_category': str(post_dict.get('folder_category', '')),
            'processed': False,
            'deleted': False,
            'metadata': json.dumps({
                'source': post_dict.get('platform', 'unknown'),
                'original_data': {k: v for k, v in post_dict.items() 
                               if k not in ['content', 'media_urls', 'hashtags', 'mentions', 
                                          'engagement', 'folder_category', 'analysis', 'metadata']}
            }, default=str, ensure_ascii=False)
        }
        
        # Add AI analysis if available
        if 'analysis' in post_dict and post_dict['analysis']:
            analysis = post_dict['analysis']
            if isinstance(analysis, dict):
                post_data.update({
                    'category': str(analysis.get('category', 'uncertain')),
                    'value_score': float(analysis.get('value_score', 0.0)) if 'value_score' in analysis else None,
                    'sentiment': str(analysis.get('sentiment', 'neutral')),
                    'ai_summary': str(analysis.get('summary', '')),
                    'key_concepts': str(analysis.get('key_concepts', [])),
                    'smart_tags': str(analysis.get('smart_tags', [])),
                    'intelligence_analysis': str(analysis.get('intelligence_analysis', {})),
                    'actionable_insights': str(analysis.get('actionable_insights', []))
                })
        
        # --- Store in Local Database ---
        log(f"Storing post {post_id} in local database...")
        local_result = db_manager.add_post(post_data)
        
        if not local_result:
            log(f"Failed to store post {post_id} in local database (add_post returned False)", "error")
            return False
        
        log(f"Successfully stored post {post_id} in local database", "success")
        
        # --- Store in Supabase if available ---
        if supabase_manager:
            try:
                log(f"Syncing post {post_id} to Supabase...")
                # Prepare data for Supabase (ensure all values are JSON serializable)
                supabase_data = post_data.copy()
                
                # Convert datetime strings to ISO format if needed
                for date_field in ['created_at', 'saved_at']:
                    if date_field in supabase_data and supabase_data[date_field]:
                        if hasattr(supabase_data[date_field], 'isoformat'):
                            supabase_data[date_field] = supabase_data[date_field].isoformat()
                
                # Ensure media_urls is a list of strings
                if 'media_urls' in supabase_data and not isinstance(supabase_data['media_urls'], list):
                    supabase_data['media_urls'] = [supabase_data['media_urls']] if supabase_data['media_urls'] else []
                
                # Insert into Supabase
                result = supabase_manager.insert_post(supabase_data)
                
                if result:
                    log(f"Successfully synced post {post_id} to Supabase", "success")
                else:
                    log(f"Failed to sync post {post_id} to Supabase", "error")
                    # Don't fail the whole operation if Supabase sync fails
                    
            except Exception as e:
                log(f"Error syncing to Supabase: {str(e)}", "error")
                import traceback
                log(traceback.format_exc(), "error")
                # Continue with local storage even if Supabase fails
        
        # Verify the post was stored
        try:
            stored_posts = db_manager.get_posts(limit=1, filters={'post_id': post_id})
            if stored_posts and len(stored_posts) > 0:
                log(f"Verified post {post_id} is in the database (ID: {stored_posts[0].get('id', 'unknown')})", "success")
            else:
                log(f"Post {post_id} was not found in the database after storage", "error")
        except Exception as e:
            log(f"Error verifying post storage: {e}", "error")
        
        return True
        
    except Exception as e:
        log(f"Unexpected error in analyze_and_store_post: {e}", "error")
        traceback.print_exc()
        return False

async def collect_twitter_bookmarks(db_manager, existing_ids, existing_urls=None, supabase_manager=None):
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
        return 0
        
    try:
        # Get Twitter credentials from environment
        twitter_username = os.getenv('TWITTER_USERNAME')
        twitter_password = os.getenv('TWITTER_PASSWORD')
        
        if not twitter_username or not twitter_password:
            print("❌ Twitter credentials not found in environment variables")
            return 0
        
        # Initialize Twitter extractor with credentials
        extractor = TwitterExtractorPlaywright(
            username=twitter_username,
            password=twitter_password,
            headless=True
        )
        
        # Authenticate
        print("🔑 Logging into Twitter...")
        if not await extractor.authenticate():
            print("❌ Failed to authenticate with Twitter")
            return 0
            
        print("🔍 Extracting Twitter SAVED posts (bookmarks only)...")
        # Get limit from environment variable or use default
        twitter_limit = int(os.getenv('TWITTER_LIMIT', '200'))
        
        # Log existing IDs for debugging
        print(f"🔍 Will skip {len(existing_ids)} existing post IDs")
        if existing_ids:
            print(f"   Sample existing IDs: {list(existing_ids)[:5]}...")
        
        # Pass existing_ids to skip already processed tweets during extraction
        saved_posts = await extractor.get_saved_posts(
            limit=twitter_limit, 
            skip_cached_ids=existing_ids
        )
        
        if saved_posts:
            print(f"🔍 Found {len(saved_posts)} Twitter posts")
            
            new_posts = []
            duplicate_count = 0
            
            for post in saved_posts:
                try:
                    if not post:
                        print("⚠️ Empty post object, skipping...")
                        continue
                        
                    # Convert SocialPost to dict for processing
                    post_dict = {
                        'post_id': post.post_id or f"twitter_{post.id}" if hasattr(post, 'id') else None,
                        'platform': post.platform,
                        'content': post.content,
                        'created_at': post.created_at.isoformat() if hasattr(post, 'created_at') and post.created_at else datetime.now(timezone.utc).isoformat(),
                        'url': post.url,
                        'author': post.author,
                        'author_handle': post.author_handle,
                        'post_type': getattr(post, 'post_type', 'tweet'),
                        'metadata': {
                            'tweet_id': getattr(post, 'id', None),
                            'tweet_url': getattr(post, 'url', ''),
                            'media_urls': getattr(post, 'media_urls', []),
                            'hashtags': getattr(post, 'hashtags', []),
                            'mentions': getattr(post, 'mentions', []),
                            'engagement': getattr(post, 'engagement', {})
                        }
                    }
                    
                    # Skip if no post_id or URL
                    if not post_dict['post_id'] and not post_dict['url']:
                        print("⚠️ Post missing both ID and URL, skipping...")
                        continue
                    
                    # Get post_id and normalize it
                    post_id = post_dict['post_id']
                    normalized_id = post_id.replace('twitter_', '') if post_id and post_id.startswith('twitter_') else post_id
                    
                    # Check for duplicates by both original and normalized post_id
                    is_duplicate = False
                    if not post_id:
                        print("⚠️ Post has no ID, skipping...")
                        duplicate_count += 1
                        continue
                        
                    if post_id in existing_ids or normalized_id in existing_ids:
                        print(f"   ⚠️ Post ID {post_id} already exists in database, skipping...")
                        duplicate_count += 1
                        continue
                    
                    # Check URL duplicates
                    post_url = post_dict.get('url', '')
                    if post_url and existing_urls and post_url in existing_urls:
                        print(f"   ⚠️ URL {post_url} already exists in database, skipping...")
                        duplicate_count += 1
                        continue
                    
                    # If we get here, it's a new post
                    new_posts.append(post_dict)
                    
                    # Add both original and normalized IDs to prevent future duplicates
                    existing_ids.add(post_id)
                    if normalized_id != post_id:
                        existing_ids.add(normalized_id)
                        
                    if post_url and existing_urls is not None:
                        existing_urls.add(post_url)
                        
                    print(f"✅ Added new post: {post_id} - {post_dict.get('content', '')[:50]}...")
                        
                except Exception as e:
                    print(f"❌ Error processing Twitter post: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # Update scrape state if we have new posts
            if new_posts:
                # Get the most recent post's ID and URL
                latest_post = max(new_posts, key=lambda x: x.get('created_at', ''))
                last_post_id = latest_post.get('post_id', '')
                last_post_url = latest_post.get('url', '')
                
                state_manager.update_scrape_state(
                    platform='twitter',
                    last_post_id=last_post_id,
                    last_post_url=last_post_url,
                    posts_scraped=len(new_posts),
                    success=True
                )

            print(f"✅ Twitter: {len(new_posts)} new bookmarks added")
            return int(len(new_posts)) if len(new_posts) is not None else 0
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

async def collect_reddit_bookmarks(db_manager, existing_ids, existing_urls=None, supabase_manager=None):
    """Collect Reddit posts using working public API approach"""
    print("\n🤖 REDDIT COLLECTION")
    print("-" * 30)

    # Get last scrape info
    last_scrape = state_manager.get_last_scrape_info('reddit')
    last_post_id = None
    if last_scrape and last_scrape.get('last_post_id'):
        last_post_id = last_scrape['last_post_id']
        print(f"📅 Last scraped: {last_scrape.get('last_scraped_at', 'Never')}")
        print(f"📊 Total posts scraped: {last_scrape.get('total_posts_scraped', 0)}")
        print(f"🔗 Last post ID: {last_post_id}")
    else:
        print("🆕 First time scraping Reddit")

    # Get existing post IDs from database to avoid re-processing
    try:
        existing_posts_df = db_manager.get_all_posts()
        if not existing_posts_df.empty and 'post_id' in existing_posts_df.columns:
            # Drop rows where post_id is None or NaN before converting to string
            valid_post_ids = existing_posts_df['post_id'].dropna()
            existing_ids.update(valid_post_ids.astype(str).tolist())
        print(f"🔍 Found {len(existing_ids)} existing posts in database")
    except Exception as e:
        print(f"⚠️ Could not fetch existing posts: {e}")

    # Track processed posts to avoid duplicates in this run
    processed_ids = set(existing_ids)

    # Check for Reddit credentials
    reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_username = os.getenv('REDDIT_USERNAME')
    reddit_password = os.getenv('REDDIT_PASSWORD')
    reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'PrisMind:1.0 (by /u/YourUsername)')

    if not (reddit_client_id and reddit_client_secret and reddit_username and reddit_password):
        # Allow tests to monkeypatch RedditExtractor without real creds
        if os.getenv('ALLOW_REDDIT_TESTS_WITHOUT_CREDS', '0') != '1':
            print("❌ Reddit credentials not found. Please set:")
            print("   REDDIT_CLIENT_ID")
            print("   REDDIT_CLIENT_SECRET")
            print("   REDDIT_USERNAME")
            print("   REDDIT_PASSWORD")
            print("   REDDIT_USER_AGENT (optional)")
            return 0

    try:
        from src.core.extraction.reddit_extractor import RedditExtractor

        extractor = RedditExtractor(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent,
            username=reddit_username,
            password=reddit_password
        )

        print("🔍 Extracting Reddit saved posts...")
        # Get limit from environment variable or use default
        reddit_limit = int(os.getenv('REDDIT_LIMIT', '25'))
        max_posts = 100  # Maximum total posts to process in one run

        total_new_posts = 0
        after = None  # Start from the beginning, let the Reddit API handle pagination
        has_more = True

        # If we have a last_post_id, we'll use the Reddit API's 'after' parameter to start from there
        if last_post_id:
            print(f"🔄 Resuming from last saved post ID: {last_post_id}")
            # The Reddit API doesn't support starting from a specific post_id directly,
            # so we'll use the 'after' parameter from the last successful scrape
            after = last_scrape.get('after_parameter')
            if after:
                print(f"↩️  Resuming from after parameter: {after}")
            else:
                print("ℹ️  No 'after' parameter found, will start from the beginning")
                after = None

        # Now fetch and process new posts
        while has_more and total_new_posts < max_posts:
            try:
                # Get next page of posts - this is a synchronous call
                result = extractor.get_saved_posts(
                    limit=reddit_limit,
                    after=after,
                    existing_ids=existing_ids
                )
                posts = result[0] if result and len(result) > 0 else []
                next_after = result[1] if result and len(result) > 1 else None

                if not posts:
                    print("ℹ️ No more new posts to fetch")
                    break

                print(f"📥 Fetched {len(posts)} new posts")

                # Update the after cursor for the next page before processing posts
                after = next_after
                if not after:
                    print("ℹ️ No more pages to fetch after this one")
                    has_more = False

                # Process each post in the current page
                for post in posts:
                    try:
                        # Handle both dict-like and object-like access
                        post_id = getattr(post, 'post_id', None) or getattr(post, 'id', None)
                        if not post_id:
                            print("⚠️ Skipping post with no ID")
                            continue
                            
                        post_id = str(post_id)

                        # Skip if we've already processed this post in this run or it exists in the database
                        if post_id in processed_ids or post_id in existing_ids:
                            print(f"⏭️  Skipping duplicate post: {post_id}")
                            continue

                        # Add to processed set
                        processed_ids.add(post_id)

                        # Convert SocialPost to dict with proper field mapping
                        post_dict = {
                            'platform': 'reddit',
                            'post_id': post_id,
                            'title': getattr(post, 'title', getattr(post, 'link_title', '')),
                            'content': getattr(post, 'content', getattr(post, 'selftext', '')),
                            'url': getattr(post, 'url', getattr(post, 'permalink', '')),
                            'created_at': getattr(post, 'created_utc', None),
                            'author': str(getattr(post, 'author', '')),
                            'author_handle': f"u/{getattr(post, 'author', '')}",
                            'subreddit': getattr(post, 'subreddit', ''),
                            'post_type': 'post',
                            'media_urls': getattr(post, 'media_urls', []),
                            'hashtags': [],
                            'mentions': [],
                            'engagement': {
                                'score': getattr(post, 'score', 0),
                                'num_comments': getattr(post, 'num_comments', 0),
                                'upvote_ratio': getattr(post, 'upvote_ratio', 1.0)
                            },
                            'is_saved': True,
                            'saved_at': datetime.now().isoformat(),
                            'folder_category': f"r/{getattr(post, 'subreddit', 'unknown')}"
                        }
                        
                        # If this is a SocialPost object, it might have additional fields
                        if hasattr(post, 'to_dict'):
                            post_dict.update(post.to_dict())
                        elif hasattr(post, '__dict__'):
                            post_dict.update({k: v for k, v in vars(post).items() if not k.startswith('_')})
                            
                        # Ensure URL is properly formatted
                        if 'url' in post_dict and post_dict['url'] and not post_dict['url'].startswith('http'):
                            post_dict['url'] = f"https://reddit.com{post_dict['url']}"
                            
                        print(f"\n📝 Processing post: {post_dict.get('title', 'No title')}")
                        print(f"   ID: {post_dict.get('post_id', 'unknown')}")
                        print(f"   URL: {post_dict.get('url', 'No URL')}")
                        print(f"   Content length: {len(post_dict.get('content', ''))} chars")
                        print(f"   Created: {post_dict.get('created_at')}")
                        print(f"   Author: {post_dict.get('author', 'Unknown')}")

                        # Ensure required fields are present
                        if 'id' not in post_dict:
                            post_dict['id'] = post_dict.get('post_id', '')
                        if 'platform' not in post_dict:
                            post_dict['platform'] = 'reddit'

                        # Process and store the post
                        try:
                            # Convert post to dict if it's an object
                            if hasattr(post, 'to_dict'):
                                post_dict = post.to_dict()
                            elif isinstance(post, dict):
                                post_dict = post
                            else:
                                print(f"⚠️ Skipping post with unknown type: {type(post)}")
                                continue
                                
                            # Add platform and ensure post_id is set
                            post_dict['platform'] = 'reddit'
                            if 'post_id' not in post_dict:
                                post_dict['post_id'] = getattr(post, 'id', None) or f"reddit_{post_dict.get('id', '')}"
                            
                            # Store the post
                            success = await analyze_and_store_post(
                                db_manager=db_manager, 
                                post_dict=post_dict,
                                supabase_manager=supabase_manager
                            )
                            if success:
                                total_new_posts += 1
                                
                                # Update the last scraped post ID
                                state_manager.update_last_scrape_info(
                                    platform='reddit',
                                    last_post_id=post_dict.get('post_id', ''),
                                    after=after
                                )
                                
                                # Print progress
                                if total_new_posts % 10 == 0:
                                    print(f"📥 Processed {total_new_posts} new posts")
                        
                        except Exception as e:
                            post_id = post_dict.get('post_id', 'unknown')
                            print(f"⚠️ Error processing post {post_id}: {e}")
                            import traceback
                            traceback.print_exc()
                            continue
                
                # Small delay to avoid hitting rate limits
                import time
                time.sleep(2)
                        
            except Exception as e:
                print(f"⚠️ Error fetching Reddit posts: {e}")
                import traceback
                traceback.print_exc()
                has_more = False

    except Exception as e:
        print(f"❌ Reddit collection failed: {e}")
        return 0

async def main():
    """Main collection function"""
    print("📥 Starting MULTI-PLATFORM bookmark collection...")
    print("=" * 60)

    # Initialize database manager
    db_manager = get_database_manager()
    
    # Initialize Supabase manager if credentials are available
    supabase_manager = None
    try:
        supabase_manager = SupabaseManager()
        print("✅ Supabase manager initialized successfully")
    except Exception as e:
        print(f"⚠️ Could not initialize Supabase manager: {e}")
        print("⚠️ Continuing with local storage only")
    
    # Get existing post IDs to avoid duplicates
    existing_posts = db_manager.get_all_posts(include_deleted=False)
    existing_ids = set()
    existing_urls = set()
    
    for post in existing_posts:
        if 'post_id' in post and post['post_id']:
            existing_ids.add(str(post['post_id']))
        if 'url' in post and post['url']:
            existing_urls.add(str(post['url']))

    print(f"📊 Database contains {len(existing_ids)} existing posts")
    print(f"🔍 Existing post IDs: {list(existing_ids)[:5]}...")  # Show first 5 IDs
    print(f"🔗 Existing URLs: {len(existing_urls)} unique URLs")

    total_new = 0

    # Collect from all platforms
    try:
        # Twitter
        twitter_count = await collect_twitter_bookmarks(
            db_manager=db_manager, 
            existing_ids=existing_ids, 
            existing_urls=existing_urls,
            supabase_manager=supabase_manager
        )
        total_new += twitter_count

        # Run Reddit collection
        print("\n📱 Running Reddit collection...")
        try:
            reddit_count = await collect_reddit_bookmarks(
                db_manager=db_manager, 
                existing_ids=existing_ids, 
                existing_urls=existing_urls,
                supabase_manager=supabase_manager
            )
            reddit_count = reddit_count or 0  # Handle None return value
            print(f"✅ Reddit collection complete: {reddit_count} new posts")
            total_new += reddit_count
        except Exception as e:
            print(f"❌ Error during Reddit collection: {e}")
            import traceback
            traceback.print_exc()
            reddit_count = 0
            
        # Threads collection is disabled for now
        print("\n⏭️ Skipping Threads collection (temporarily disabled)")
        threads_count = 0

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
