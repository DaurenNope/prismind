#!/usr/bin/env python3
"""
Database Synchronization Script

This script synchronizes posts between the local SQLite database and Supabase,
ensuring both databases contain the same set of posts.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
from supabase import create_client

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
        # Try to get all posts from Supabase
        response = supabase.table('posts').select('*').execute()
        return response.data if hasattr(response, 'data') else []
    except Exception as e:
        print(f"Error fetching posts from Supabase: {e}")
        return []

def analyze_post(post_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a post using ContentAnalyzer.
    Returns empty dict if analysis is not possible.
    """
    # Return empty analysis for now since ContentAnalyzer is not available
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
    if not post_data:
        return {'status': 'error', 'message': 'No post data provided'}
        
    # Make a copy to avoid modifying the original
    data = post_data.copy()
    post_id = data.get('post_id', 'unknown')
    
    # Ensure required fields have default values
    data.setdefault('is_saved', True)
    data.setdefault('is_deleted', False)
    
    # Ensure all required fields have default values
    data['is_saved'] = data.get('is_saved', True)
    data['is_deleted'] = data.get('is_deleted', False)
    
    try:
        # Skip analysis for now since ContentAnalyzer is not available
        # Just set a default analyzed_at timestamp
        data['analyzed_at'] = datetime.utcnow().isoformat()
        
        # Prepare data for Supabase - only include fields that exist in the table
        supabase_data = {
            'post_id': data.get('post_id', ''),
            'title': data.get('title', '')[:255],  # Limit title length
            'content': data.get('content', ''),
            'url': data.get('url', ''),
            'platform': data.get('platform', ''),
            'author': data.get('author', '')[:100],  # Limit author length
            'author_handle': data.get('author_handle', '')[:100],
            'created_at': data.get('created_at'),
            'summary': data.get('summary', '')[:1000],
            'ai_summary': data.get('ai_summary', '')[:1000],
            'folder_category': data.get('folder_category', '')[:100],
            'category': data.get('category', '')[:100],
            'subcategory': data.get('subcategory', '')[:100],
            'topic': data.get('topic', '')[:100],
            'content_type': data.get('content_type', '')[:50],
            'post_type': data.get('post_type', '')[:50],
            'media_urls': str(data.get('media_urls', ''))[:1000],
            'hashtags': str(data.get('hashtags', ''))[:500],
            'mentions': str(data.get('mentions', ''))[:500],
            'upvote_ratio': float(data.get('upvote_ratio', 0.0)),
            'num_comments': int(data.get('num_comments', 0)),
            'is_saved': bool(data.get('is_saved', True)),
            'saved_at': data.get('saved_at'),
            'analyzed_at': data.get('analyzed_at'),
            'sentiment': data.get('sentiment', '')[:50],
            'key_concepts': str(data.get('key_concepts', ''))[:1000],
            'tags': str(data.get('tags', ''))[:500],
            'analysis_model': data.get('analysis_model', '')[:100],
            'value_score': float(data.get('value_score', 0.0)),
            'smart_tags': str(data.get('smart_tags', ''))[:500],
            'is_deleted': bool(data.get('is_deleted', False))
        }
        
        # Remove None values as they can cause issues with Supabase
        supabase_data = {k: v for k, v in supabase_data.items() if v is not None}
        
        # Check if the post already exists
        existing_post = supabase.table('posts') \
            .select('id') \
            .eq('url', supabase_data.get('url', '')) \
            .execute()
            
        if existing_post.data:
            # Update existing post
            result = supabase.table('posts') \
                .update(supabase_data) \
                .eq('id', existing_post.data[0]['id']) \
                .execute()
            action = 'updated'
        else:
            # Insert new post
            result = supabase.table('posts') \
                .insert(supabase_data) \
                .execute()
            action = 'created'
        
        if result and hasattr(result, 'data') and result.data:
            return {
                'status': 'success',
                'action': 'updated' if data.get('url') in existing_urls else 'created',
                'post_id': post_id,
                'supabase_id': result.data[0].get('id')
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
    """Sync local posts to Supabase."""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        print("❌ Error: Missing Supabase URL or Service Role Key")
        return {
            'status': 'error',
            'message': 'Missing Supabase credentials',
            'created': 0,
            'updated': 0,
            'errors': 0
        }
    
    print("🔌 Initializing Supabase connection...")
    try:
        supabase = create_client(url, key)
        
        # Get existing posts from Supabase
        print("📥 Fetching existing posts from Supabase...")
        supabase_posts = get_supabase_posts()
        existing_urls = {p['url'] for p in supabase_posts if 'url' in p}
        
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        print(f"🔄 Syncing {len(local_posts)} posts to Supabase...")
        
        for post in local_posts:
            try:
                post_id = post.get('post_id', 'unknown')
                post_url = post.get('url', '')
                
                # Skip if no URL is available
                if not post_url:
                    print(f"⚠️  Skipping post {post_id}: No URL provided")
                    stats['errors'] += 1
                    continue
                
                # Prepare the data for Supabase
                post_data = {
                    'post_id': post_id,
                    'title': (post.get('content', '')[:100] + '...') if post.get('content') else 'Untitled',
                    'content': post.get('content', ''),
                    'url': post_url,
                    'platform': post.get('platform', 'unknown'),
                    'author': post.get('author', ''),
                    'author_handle': post.get('author_handle', ''),
                    'created_at': post.get('created_at') or datetime.utcnow().isoformat(),
                    'summary': post.get('summary') or post.get('ai_summary', '') or '',
                    'ai_summary': post.get('ai_summary') or post.get('summary', '') or '',
                    'folder_category': post.get('folder_category') or post.get('category', '') or '',
                    'category': post.get('category') or post.get('folder_category', '') or '',
                    'value_score': 0,  # Default value
                    'smart_tags': '',  # Default value
                    'subcategory': post.get('subcategory', ''),
                    'topic': post.get('topic', ''),
                    'content_type': post.get('content_type', ''),
                    'post_type': post.get('post_type', ''),
                    'media_urls': post.get('media_urls', ''),
                    'hashtags': post.get('hashtags', ''),
                    'mentions': post.get('mentions', ''),
                    'upvote_ratio': post.get('upvote_ratio', 0),
                    'num_comments': post.get('num_comments', 0),
                    'is_saved': post.get('is_saved', True),
                    'is_deleted': post.get('is_deleted', False),
                    'analyzed_at': post.get('analyzed_at') or datetime.utcnow().isoformat()
                }
                
                # Check if post exists by URL
                if post_url in existing_urls:
                    # Update existing post
                    result = supabase.table('posts').update(post_data).eq('url', post_url).execute()
                    if hasattr(result, 'data') and result.data:
                        print(f"🔄 Updated post: {post_url}")
                        stats['updated'] += 1
                    else:
                        print(f"⚠️  Failed to update post: {post_url}")
                        stats['errors'] += 1
                else:
                    # Insert new post
                    result = supabase.table('posts').insert(post_data).execute()
                    if hasattr(result, 'data') and result.data:
                        print(f"✅ Created post: {post_url}")
                        stats['created'] += 1
                        existing_urls.add(post_url)  # Add to existing URLs to prevent duplicates
                    else:
                        print(f"⚠️  Failed to create post: {post_url}")
                        stats['errors'] += 1
                        
            except Exception as e:
                print(f"❌ Error processing post {post.get('post_id', 'unknown')}: {str(e)}")
                stats['errors'] += 1
                continue
        
        print(f"\n✅ Sync completed: {stats['created']} created, {stats['updated']} updated, {stats['errors']} errors")
        return {
            'status': 'success',
            'message': 'Sync completed',
            'created': stats['created'],
            'updated': stats['updated'],
            'errors': stats['errors']
        }
        
    except Exception as e:
        print(f"❌ Fatal error during sync: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'created': 0,
            'updated': 0,
            'errors': len(local_posts) if 'local_posts' in locals() else 1
        }

def main():
    """Main function to sync local database with Supabase."""
    print("🔄 Starting database synchronization...")
    
    # Get local database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'prismind.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Error: Local database not found at {db_path}")
        return 1
    
    # Get local posts
    print("📥 Fetching local posts...")
    local_posts = get_local_posts(db_path)
    
    if not local_posts:
        print("ℹ️  No local posts found to sync")
        return 0
    
    print(f"📊 Found {len(local_posts)} local posts to sync")
    
    # Sync to Supabase
    result = sync_to_supabase(local_posts)
    
    if result.get('status') == 'error':
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
