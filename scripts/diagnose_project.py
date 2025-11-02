#!/usr/bin/env python3
"""
Diagnose project health: unanalyzed posts, duplicates, truncation
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.new_database_manager import NewDatabaseManager
from src.utils.duplicate_detector import DuplicateDetector
import re

def check_unanalyzed_posts(db):
    """Check for posts without analysis"""
    print("\n" + "="*70)
    print("📊 CHECKING UNANALYZED POSTS")
    print("="*70)
    
    try:
        unanalyzed = db.get_unanalyzed_posts(limit=10000)
        print(f"Found {len(unanalyzed)} unanalyzed posts")
        
        if unanalyzed:
            # Group by platform
            by_platform = {}
            for post in unanalyzed:
                platform = post.get('platform', 'unknown')
                by_platform[platform] = by_platform.get(platform, 0) + 1
            
            print("\nBreakdown by platform:")
            for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
                print(f"  {platform}: {count}")
        else:
            print("✅ All posts are analyzed!")
        
        return len(unanalyzed)
    except Exception as e:
        print(f"❌ Error checking unanalyzed posts: {e}")
        return 0

def check_truncation(db):
    """Check for truncated posts"""
    print("\n" + "="*70)
    print("⚠️  CHECKING FOR TRUNCATED POSTS")
    print("="*70)
    
    try:
        all_posts = db.get_posts(limit=1000)
        truncated = []
        
        for post in all_posts:
            content = post.get('content', '')
            if not content:
                continue
            
            length = len(content)
            # Truncation patterns:
            # 1. Content length between 200-500 chars (suspicious range)
            # 2. Doesn't end with proper punctuation
            # 3. Doesn't end with ellipsis
            if 200 < length < 500:
                last_char = content[-1] if content else ''
                if last_char not in '.!?")\'' and not content.endswith('...') and not content.endswith('…'):
                    truncated.append({
                        'post_id': post.get('post_id', 'unknown'),
                        'platform': post.get('platform', 'unknown'),
                        'author': post.get('author', 'unknown')[:30],
                        'length': length,
                        'url': post.get('url', ''),
                        'content_preview': content[:100] + '...'
                    })
        
        print(f"Found {len(truncated)} potentially truncated posts")
        
        if truncated:
            # Group by platform
            by_platform = {}
            for post in truncated:
                platform = post['platform']
                by_platform[platform] = by_platform.get(platform, 0) + 1
            
            print("\nBreakdown by platform:")
            for platform, count in sorted(by_platform.items(), key=lambda x: -x[1]):
                print(f"  {platform}: {count}")
            
            print("\nSample truncated posts:")
            for i, post in enumerate(truncated[:5], 1):
                print(f"\n  {i}. {post['platform']} - {post['author']}")
                print(f"     Length: {post['length']} chars")
                print(f"     Preview: {post['content_preview']}")
                print(f"     URL: {post['url']}")
        else:
            print("✅ No truncated posts found!")
        
        return len(truncated)
    except Exception as e:
        print(f"❌ Error checking truncation: {e}")
        return 0

def check_duplicates(db):
    """Check for duplicate posts"""
    print("\n" + "="*70)
    print("🔄 CHECKING FOR DUPLICATES")
    print("="*70)
    
    try:
        detector = DuplicateDetector(db_manager=db)
        
        # Sample check - get recent posts and check for duplicates
        recent_posts = db.get_posts(limit=500)
        duplicates_found = []
        
        seen_urls = {}
        seen_content_hashes = {}
        
        for post in recent_posts:
            url = post.get('url', '')
            content = post.get('content', '')
            post_id = post.get('post_id', 'unknown')
            platform = post.get('platform', 'unknown')
            
            if url:
                normalized_url = detector.normalize_url(url)
                if normalized_url in seen_urls:
                    duplicates_found.append({
                        'type': 'url',
                        'post_id': post_id,
                        'platform': platform,
                        'url': url,
                        'duplicate_of': seen_urls[normalized_url]
                    })
                else:
                    seen_urls[normalized_url] = post_id
            
            if content:
                content_hash = detector.hash_content(content)
                if content_hash in seen_content_hashes:
                    duplicates_found.append({
                        'type': 'content',
                        'post_id': post_id,
                        'platform': platform,
                        'content_preview': content[:50] + '...',
                        'duplicate_of': seen_content_hashes[content_hash]
                    })
                else:
                    seen_content_hashes[content_hash] = post_id
        
        print(f"Found {len(duplicates_found)} duplicate posts in sample")
        
        if duplicates_found:
            by_type = {}
            for dup in duplicates_found:
                dup_type = dup['type']
                by_type[dup_type] = by_type.get(dup_type, 0) + 1
            
            print("\nBreakdown by type:")
            for dup_type, count in by_type.items():
                print(f"  {dup_type}: {count}")
            
            print("\nSample duplicates:")
            for i, dup in enumerate(duplicates_found[:5], 1):
                print(f"\n  {i}. {dup['type']} duplicate - {dup['platform']}")
                print(f"     Post ID: {dup['post_id']}")
                if 'url' in dup:
                    print(f"     URL: {dup['url']}")
                if 'content_preview' in dup:
                    print(f"     Content: {dup['content_preview']}")
                print(f"     Duplicate of: {dup['duplicate_of']}")
        else:
            print("✅ No duplicates found in sample!")
        
        return len(duplicates_found)
    except Exception as e:
        print(f"❌ Error checking duplicates: {e}")
        import traceback
        traceback.print_exc()
        return 0

def get_db_stats(db):
    """Get database statistics"""
    print("\n" + "="*70)
    print("📈 DATABASE STATISTICS")
    print("="*70)
    
    try:
        stats = db.get_database_stats()
        print(f"Total posts: {stats.get('total_posts', 0)}")
        print(f"Platforms: {', '.join(stats.get('platforms', []))}")
        
        # Get breakdown by platform
        platforms = db.get_platforms()
        print("\nPosts by platform:")
        for platform in platforms:
            posts = db.get_posts_by_platform(platform, limit=10000)
            print(f"  {platform}: {len(posts)}")
    except Exception as e:
        print(f"❌ Error getting stats: {e}")

def main():
    print("\n" + "="*70)
    print("🔍 PRISMIND PROJECT DIAGNOSTIC")
    print("="*70)
    
    try:
        db = NewDatabaseManager()
        
        # Get database stats
        get_db_stats(db)
        
        # Check unanalyzed posts
        unanalyzed_count = check_unanalyzed_posts(db)
        
        # Check truncation
        truncated_count = check_truncation(db)
        
        # Check duplicates
        duplicates_count = check_duplicates(db)
        
        # Summary
        print("\n" + "="*70)
        print("📊 SUMMARY")
        print("="*70)
        print(f"Unanalyzed posts: {unanalyzed_count}")
        print(f"Truncated posts: {truncated_count}")
        print(f"Duplicate posts: {duplicates_count}")
        
        if unanalyzed_count > 0:
            print("\n⚠️  ACTION: Run analysis batch on unanalyzed posts")
        if truncated_count > 0:
            print("⚠️  ACTION: Fix truncated content extraction")
        if duplicates_count > 0:
            print("⚠️  ACTION: Clean up duplicate posts")
        
        if unanalyzed_count == 0 and truncated_count == 0 and duplicates_count == 0:
            print("\n✅ All checks passed! Project is healthy.")
        
    except Exception as e:
        print(f"\n❌ Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()

