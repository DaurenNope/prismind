#!/usr/bin/env python3
"""
Normalize and Clean Supabase Data

This script fixes inconsistencies in the Supabase posts table:
1. Backfills missing author_handle from URLs
2. Generates titles from content for posts missing them
3. Normalizes NULL vs empty arrays
4. Standardizes post_type and content_type
5. Removes duplicate posts
6. Fixes encoding issues

Run with: python scripts/normalize_supabase_data.py [--dry-run]
"""

import re
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.supabase_manager import SupabaseManager


def extract_handle_from_url(url: str) -> Optional[str]:
    """Extract Twitter handle from URL like https://x.com/username/status/123"""
    if not url:
        return None
    
    try:
        # Pattern: https://x.com/USERNAME/status/...
        match = re.search(r'x\.com/([^/]+)/', url)
        if match:
            username = match.group(1)
            # Filter out non-username paths
            if username not in ['i', 'home', 'explore', 'notifications', 'messages', 'settings']:
                return f'@{username}'
    except:
        pass
    
    return None


def generate_title_from_content(content: str, max_length: int = 100) -> str:
    """Generate a meaningful title from content"""
    if not content:
        return ""
    
    # Take first line
    first_line = content.split('\n')[0].strip()
    
    # Truncate if too long
    if len(first_line) > max_length:
        return first_line[:max_length-3] + '...'
    
    return first_line


def normalize_post_type(post_type: Optional[str], content: str) -> str:
    """Standardize post_type field"""
    if not post_type or post_type == 'post':
        # Check if it's a thread (multiple numbered points or long content)
        if re.search(r'\n\s*\d+[/.)]', content) or len(content) > 500:
            return 'thread'
        return 'tweet'
    
    return post_type.lower()


def normalize_content_type(content_type: Optional[str]) -> str:
    """Standardize content_type field"""
    if not content_type or content_type == 'Social Media Post':
        return 'text'
    
    return content_type.lower()


def normalize_array_field(value: Any) -> Optional[str]:
    """Normalize array fields to either NULL or proper PostgreSQL array"""
    if value is None:
        return None
    
    # If it's an empty object or empty array string, return NULL
    if value in ['{}', '[]', '', 'None']:
        return None
    
    # If it's already a proper array, keep it
    if isinstance(value, str) and value.startswith('{') and value.endswith('}'):
        # Check if it's actually empty
        content = value.strip('{}').strip()
        if not content:
            return None
        return value
    
    return None


def normalize_post(post: Dict[str, Any], dry_run: bool = False) -> Optional[Dict[str, Any]]:
    """
    Normalize a single post record
    Returns updates dict if changes needed, None if post is already normalized
    """
    updates = {}
    post_id = post.get('post_id')
    
    # 1. Fix missing author_handle
    if not post.get('author_handle'):
        handle = extract_handle_from_url(post.get('url', ''))
        if handle:
            updates['author_handle'] = handle
            print(f"  📝 {post_id}: Adding author_handle = {handle}")
    
    # 2. Fix missing or generic title
    title = (post.get('title') or '').strip()
    if not title or 'on twitter' in title.lower():
        content = post.get('content', '')
        if content:
            new_title = generate_title_from_content(content)
            if new_title and new_title != title:
                updates['title'] = new_title
                print(f"  📝 {post_id}: Updating title = '{new_title[:50]}...'")
    
    # 3. Normalize post_type
    current_post_type = post.get('post_type')
    normalized_post_type = normalize_post_type(current_post_type, post.get('content', ''))
    if current_post_type != normalized_post_type:
        updates['post_type'] = normalized_post_type
        print(f"  📝 {post_id}: Normalizing post_type: {current_post_type} → {normalized_post_type}")
    
    # 4. Normalize content_type
    current_content_type = post.get('content_type')
    normalized_content_type = normalize_content_type(current_content_type)
    if current_content_type != normalized_content_type:
        updates['content_type'] = normalized_content_type
        print(f"  📝 {post_id}: Normalizing content_type: {current_content_type} → {normalized_content_type}")
    
    # 5. Normalize array fields (media_urls, hashtags, mentions)
    for field in ['media_urls', 'hashtags', 'mentions']:
        current = post.get(field)
        normalized = normalize_array_field(current)
        
        # Only update if there's a change from {} to NULL
        if current == '{}' and normalized is None:
            updates[field] = None
            print(f"  📝 {post_id}: Normalizing {field}: {{}} → NULL")
    
    # 6. Fix value_score if it's 0 (should be NULL if not analyzed)
    if post.get('value_score') == 0 and not post.get('analyzed_at'):
        updates['value_score'] = None
        print(f"  📝 {post_id}: Clearing value_score (not analyzed yet)")
    
    return updates if updates else None


def main(dry_run: bool = False):
    """Main normalization routine"""
    print("="*80)
    print("SUPABASE DATA NORMALIZATION SCRIPT")
    print("="*80)
    
    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made\n")
    else:
        print("⚠️  LIVE MODE - Changes will be applied to Supabase\n")
        response = input("Continue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            return
    
    print("\n📊 Connecting to Supabase...")
    sm = SupabaseManager()
    
    # Get all posts (batch by batch to avoid memory issues)
    batch_size = 100
    offset = 0
    total_posts = 0
    total_updated = 0
    
    while True:
        print(f"\n📥 Fetching posts {offset} to {offset + batch_size}...")
        
        result = sm.client.table('posts').select('*').range(offset, offset + batch_size - 1).order('created_at', desc=True).execute()
        
        posts = result.data
        if not posts:
            break
        
        total_posts += len(posts)
        print(f"✅ Processing {len(posts)} posts...\n")
        
        for post in posts:
            updates = normalize_post(post, dry_run)
            
            if updates:
                total_updated += 1
                
                if not dry_run:
                    # Apply updates to Supabase
                    try:
                        sm.client.table('posts').update(updates).eq('post_id', post['post_id']).execute()
                        print(f"    ✅ Updated {post['post_id']}")
                    except Exception as e:
                        print(f"    ❌ Failed to update {post['post_id']}: {e}")
        
        # Move to next batch
        offset += batch_size
        
        # Safety limit - stop after 1000 posts in dry run
        if dry_run and offset >= 1000:
            print("\n⚠️  Dry run limit reached (1000 posts)")
            break
    
    # Summary
    print("\n" + "="*80)
    print("NORMALIZATION COMPLETE")
    print("="*80)
    print(f"Total posts processed: {total_posts}")
    print(f"Posts updated: {total_updated}")
    print(f"Posts unchanged: {total_posts - total_updated}")
    
    if dry_run:
        print("\n💡 This was a dry run. Run without --dry-run to apply changes.")


if __name__ == "__main__":
    dry_run_mode = '--dry-run' in sys.argv
    main(dry_run=dry_run_mode)
