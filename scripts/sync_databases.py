#!/usr/bin/env python3
"""
Database Synchronization Script

This script synchronizes posts between the local SQLite database and Supabase,
ensuring both databases contain the same set of posts.
"""

import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
from typing import List, Dict, Any, Set

# Load environment variables
load_dotenv()

def get_local_posts(db_path: str) -> List[Dict[str, Any]]:
    """Retrieve all posts from the local SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT post_id, content, url, created_at, platform, 
               author as author_handle, post_type, 
               media_urls, hashtags, mentions,
               upvote_ratio, num_comments, is_saved,
               saved_at, summary, intelligence_analysis,
               comment_analysis, media_analysis,
               category, subcategory, topic,
               content_type, complexity_level
        FROM posts
        WHERE is_deleted = 0
    ''')
    
    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return posts

def get_supabase_posts() -> List[Dict[str, Any]]:
    """Retrieve all posts from Supabase."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        raise ValueError("Missing Supabase URL or Service Role Key")
    
    supabase = create_client(url, key)
    
    try:
        # Fetch all posts from Supabase with pagination
        all_posts = []
        page = 0
        page_size = 100
        
        while True:
            offset = page * page_size
            response = supabase.table('posts') \
                .select('*') \
                .range(offset, offset + page_size - 1) \
                .execute()
                
            if not response.data or len(response.data) == 0:
                break
                
            all_posts.extend(response.data)
            page += 1
            
            # If we got fewer posts than requested, we've reached the end
            if len(response.data) < page_size:
                break
        
        # Map Supabase fields to our local schema
        mapped_posts = []
        for post in all_posts:
            mapped_post = {
                'post_id': str(post.get('id')),  # Using Supabase's id as post_id
                'content': post.get('content', ''),
                'url': post.get('url', ''),
                'platform': post.get('platform', 'unknown'),
                'author_handle': post.get('author_handle') or post.get('author', ''),
                'created_at': post.get('created_at', ''),
                'summary': post.get('summary', ''),
                'ai_summary': post.get('ai_summary', ''),
                'category': post.get('category', ''),
                'folder_category': post.get('folder_category', '')
            }
            mapped_posts.append(mapped_post)
            
        return mapped_posts
        
    except Exception as e:
        print(f"❌ Error fetching posts from Supabase: {str(e)}")
        return []

from typing import List, Dict, Any, Set
from datetime import datetime
import json
import os
import sqlite3
from dotenv import load_dotenv
from supabase import create_client

def analyze_and_sync_post(supabase, post_data: Dict[str, Any], existing_urls: Set[str]) -> Dict[str, Any]:
    """
    Analyze a post and sync it to Supabase.
    
    Args:
        supabase: Supabase client instance
        post_data: Dictionary containing post data
        existing_urls: Set of existing post URLs in Supabase
        
    Returns:
        Dictionary with sync results
    """
    # Make a copy to avoid modifying the original
    data = post_data.copy()
    post_id = data.get('post_id', 'unknown')
    
    try:
        # Check if we should analyze this post
        if should_analyze_post(data):
            print(f"🔍 Analyzing post: {post_id}")
            analysis = analyze_post(data)
            if analysis:
                # Update post data with analysis results
                data.update({
                    'ai_summary': analysis.get('ai_summary', ''),
                    'key_concepts': analysis.get('key_concepts', ''),
                    'sentiment': analysis.get('sentiment', 'neutral'),
                    'category': analysis.get('category', data.get('category', 'general')),
                    'analyzed_at': datetime.utcnow().isoformat()
                })
        
        # Sync to Supabase
        result = supabase.insert_post(data, upsert=True)
        
        if result and 'id' in result:
            return {
                'status': 'success',
                'action': 'updated' if any(p.get('url') == data.get('url') for p in supabase_posts if 'url' in p) else 'created',
                'post_id': post_id,
                'supabase_id': result['id']
            }
        else:
            return {
                'status': 'error',
                'message': f"Failed to sync post {post_id}",
                'post_id': post_id
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'post_id': post_id
        }

def analyze_post(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a post using ContentAnalyzer.
    
    Args:
        post_data: Dictionary containing post data
        
    Returns:
        Dictionary with analysis results
    """
    try:
        # Import here to avoid circular imports
        from src.core.analysis.content_analyzer import ContentAnalyzer
        
        # Initialize the analyzer
        analyzer = ContentAnalyzer()
        
        # Determine content type based on platform
        platform = post_data.get('platform', '').lower()
        content_type = platform if platform in ['reddit', 'twitter'] else 'generic'
        
        # Extract content fields
        content = {
            'title': post_data.get('title', ''),
            'content': post_data.get('content', ''),
            'url': post_data.get('url', ''),
            'platform': platform,
            'author': post_data.get('author', '')
        }
        
        # Add platform-specific fields
        if platform == 'reddit':
            content.update({
                'selftext': post_data.get('content', ''),
                'subreddit': post_data.get('subcategory', '')
            })
        
        # Perform analysis
        analysis = analyzer.analyze_content(content_type, content)
        
        # Map analysis results to our database fields
        result = {
            'ai_summary': analysis.get('summary', ''),
            'key_concepts': json.dumps(analysis.get('key_topics', [])),
            'sentiment': analysis.get('sentiment', 'neutral'),
            'category': analysis.get('category', 'general'),
            'tags': json.dumps(analysis.get('tags', [])),
            'analyzed_at': datetime.utcnow().isoformat(),
            'analysis_model': analysis.get('model_used', 'unknown')
        }
        
        return result
        
    except ImportError as e:
        print(f"Warning: Could not import ContentAnalyzer: {e}")
        return {}
    except Exception as e:
        print(f"Error analyzing post: {e}")
        return {}

def should_analyze_post(post_data: Dict[str, Any]) -> bool:
    """Determine if a post should be analyzed."""
    # Skip if already analyzed recently
    if post_data.get('analyzed_at'):
        try:
            analyzed_at = datetime.fromisoformat(post_data['analyzed_at'])
            if (datetime.utcnow() - analyzed_at).days < 30:  # Re-analyze after 30 days
                return False
        except (ValueError, TypeError):
            pass
    
    # Skip if content is too short
    content = post_data.get('content', '')
    if len(content) < 50:  # Minimum 50 characters for meaningful analysis
        return False
        
    return True
    
    try:
        # Check if we should analyze this post
        if should_analyze_post(data):
            print(f"🔍 Analyzing post: {post_id}")
            analysis = analyze_post(data)
            if analysis:
                # Update post data with analysis results
                data.update({
                    'ai_summary': analysis.get('ai_summary', ''),
                    'key_concepts': analysis.get('key_concepts', ''),
                    'sentiment': analysis.get('sentiment', 'neutral'),
                    'category': analysis.get('category', data.get('category', 'general')),
                    'analyzed_at': datetime.utcnow().isoformat()
                })
        
        # Sync to Supabase
        result = supabase.insert_post(data, upsert=True)
        
        if result and 'id' in result:
            return {
                'status': 'success',
                'action': 'updated' if data.get('url') in existing_urls else 'created',
                'post_id': post_id,
                'supabase_id': result['id']
            }
        else:
            return {
                'status': 'error',
                'message': f"Failed to sync post {post_id}",
                'post_id': post_id
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e),
            'post_id': post_id
        }

def sync_to_supabase(local_posts: List[Dict[str, Any]]):
    """Sync local posts to Supabase using SupabaseManager."""
    import sys
    import os
    # Add the parent directory to the path to allow imports from the scripts directory
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scripts.supabase_manager import SupabaseManager
    
    print("🔌 Initializing Supabase connection...")
    try:
        supabase = SupabaseManager()
    except Exception as e:
        print(f"❌ Failed to initialize Supabase: {e}")
        return
    
    # Get existing posts from Supabase (for comparison)
    print("🔍 Fetching existing posts from Supabase...")
    try:
        supabase_posts = get_supabase_posts()
        existing_urls = {post['url'] for post in supabase_posts if 'url' in post}
        print(f"✅ Found {len(supabase_posts)} existing posts in Supabase")
    except Exception as e:
        print(f"❌ Error fetching posts from Supabase: {e}")
        return
    
    # Initialize stats
    stats = {
        'total_processed': 0,
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    for post in local_posts:
        try:
            stats['total_processed'] += 1
            post_id = post['post_id']
            post_url = post.get('url', '')
            
            if not post_url:
                print(f"⚠️  Skipping post {post_id}: Missing URL")
                stats['skipped'] += 1
                continue
                
            # Prepare post data for Supabase
            content = post.get('content', '')
            title = (content[:100] + '...') if content else 'Untitled'
            created_at = post.get('created_at') or datetime.utcnow().isoformat()
            summary = post.get('summary') or post.get('ai_summary', '') or ''
            ai_summary = post.get('ai_summary') or post.get('summary', '') or ''
            folder_category = post.get('folder_category') or post.get('category', '') or ''
            category = post.get('category') or post.get('folder_category', '') or ''
            
            # Prepare the data for Supabase
            post_data = {
                'post_id': post_id,
                'title': title,
                'content': content,
                'url': post_url,
                'platform': post.get('platform', 'unknown'),
                'author': post.get('author', ''),
                'author_handle': post.get('author_handle', ''),
                'created_at': created_at,
                'summary': summary,
                'ai_summary': ai_summary,
                'folder_category': folder_category,
                'category': category,
                'value_score': 0,  # Default value
                'smart_tags': '',  # Default value
                'subcategory': post.get('subcategory', ''),
                'topic': post.get('topic', ''),
                'content_type': post.get('content_type', ''),
                'complexity_level': post.get('complexity_level', ''),
                'post_type': post.get('post_type', ''),
                'media_urls': post.get('media_urls', ''),
                'hashtags': post.get('hashtags', ''),
                'mentions': post.get('mentions', ''),
                'upvote_ratio': post.get('upvote_ratio', 0),
                'num_comments': post.get('num_comments', 0),
                'is_saved': post.get('is_saved', 1),
                'saved_at': post.get('saved_at', '')
            }
            
            # Get existing URLs for reference
            existing_urls = {p['url'] for p in supabase_posts if 'url' in p}
            
            # Analyze and sync the post
            result = analyze_and_sync_post(supabase, post_data, existing_urls)
            
            # Update stats based on the result
            if result['status'] == 'success':
                action = result.get('action', 'unknown')
                if action == 'updated':
                    stats['updated'] += 1
                    print(f"✅ Updated post: {post_id} (Supabase ID: {result.get('supabase_id', 'N/A')})")
                else:
                    stats['created'] += 1
                    print(f"✅ Created post: {post_id} (Supabase ID: {result.get('supabase_id', 'N/A')})")
            else:
                stats['errors'] += 1
                print(f"❌ Error processing post {post_id}: {result.get('message', 'Unknown error')}")
                    
        except Exception as e:
            print(f"❌ Error processing post {post.get('post_id', 'unknown')}: {str(e)}")
            stats['errors'] += 1
    
    return stats

def main():
    """Main function to sync local database with Supabase."""
    print("🔄 Starting database synchronization...")
    
    # Path to local database
    local_db_path = os.path.join(os.getcwd(), 'data', 'prismind.db')
    
    if not os.path.exists(local_db_path):
        print(f"❌ Local database not found at {local_db_path}")
        return
    
    try:
        # Get posts from both databases
        print("📥 Fetching posts from local database...")
        local_posts = get_local_posts(local_db_path)
        print(f"📊 Found {len(local_posts)} posts in local database")
        
        print("📥 Fetching posts from Supabase...")
        supabase_posts = get_supabase_posts()
        print(f"📊 Found {len(supabase_posts)} posts in Supabase")
        
        # Sync local posts to Supabase
        print("\n🔄 Syncing local posts to Supabase...")
        stats = sync_to_supabase(local_posts)
        
        # Print sync statistics
        print("\n📊 Sync Complete!")
        print(f"   Total processed: {stats['total_processed']}")
        print(f"   Created: {stats['created']}")
        print(f"   Updated: {stats['updated']}")
        print(f"   Skipped: {stats['skipped']}")
        print(f"   Errors: {stats['errors']}")
        
    except Exception as e:
        print(f"❌ Error during synchronization: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
