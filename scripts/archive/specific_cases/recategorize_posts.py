#!/usr/bin/env python3
"""
Recategorize Generic Posts
===========================

Recategorizes posts with generic categories like "Technology" or "General"
using the improved categorization system.

Usage:
    python recategorize_posts.py --limit 50
    python recategorize_posts.py --all
    python recategorize_posts.py --categories "Technology,General"
"""

import asyncio
import argparse
from datetime import datetime
from src.supabase_manager import SupabaseManager
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer


async def recategorize_posts(categories_to_fix=None, limit=None):
    """Recategorize posts with generic categories"""
    
    print("🔄 Starting recategorization process...")
    print("=" * 70)
    
    # Initialize services
    sm = SupabaseManager()
    analyzer = IntelligentContentAnalyzer()
    
    # Default categories to fix
    if not categories_to_fix:
        categories_to_fix = ['Technology', 'General', 'bookmark']
    
    print(f"📊 Target categories: {', '.join(categories_to_fix)}")
    
    # Fetch posts with generic categories
    query = sm.client.table('posts').select('*').in_('category', categories_to_fix)
    
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    posts = result.data
    
    if not posts:
        print("✅ No posts need recategorization!")
        return
    
    print(f"📊 Found {len(posts)} posts to recategorize")
    print()
    
    success_count = 0
    error_count = 0
    category_changes = {}
    
    for i, post in enumerate(posts, 1):
        post_id = post.get('post_id', 'unknown')
        old_category = post.get('category', 'Unknown')
        title = (post.get('title') or post.get('content', ''))[:50]
        
        print(f"[{i}/{len(posts)}] Processing: {post_id}")
        print(f"   Title: {title}...")
        print(f"   Old category: {old_category}")
        
        try:
            # Analyze with improved prompt
            analysis_content = {
                "post_id": post_id,
                "title": post.get("title", ""),
                "content": post.get("content", ""),
                "url": post.get("url", ""),
                "platform": post.get("platform", ""),
                "author": post.get("author", ""),
                "author_handle": post.get("author_handle", ""),
                "created_at": post.get("created_at", datetime.now().isoformat()),
                "hashtags": post.get("hashtags", []),
            }
            
            print(f"   🧠 Re-analyzing...")
            result = await analyzer.analyze_content(analysis_content)
            
            new_category = result.get('category', old_category)
            new_subcategory = result.get('subcategory', '')
            
            # Track category changes
            change_key = f"{old_category} → {new_category}"
            category_changes[change_key] = category_changes.get(change_key, 0) + 1
            
            # Update Supabase
            update_data = {
                'category': new_category,
                'subcategory': new_subcategory,
                'updated_at': datetime.now().isoformat()
            }
            
            sm.client.table('posts').update(update_data).eq('post_id', post_id).execute()
            
            success_count += 1
            print(f"   ✅ Updated: {old_category} → {new_category}")
            if new_subcategory:
                print(f"      Subcategory: {new_subcategory}")
            
        except Exception as e:
            error_count += 1
            print(f"   ❌ Error: {e}")
        
        print()
        
        # Rate limiting
        if i % 10 == 0:
            print(f"💤 Processed {i} posts, taking a short break...")
            await asyncio.sleep(2)
    
    print("=" * 70)
    print(f"🎉 Recategorization complete!")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Errors: {error_count}")
    print(f"   📊 Total: {len(posts)}")
    
    print()
    print("📊 Category Changes:")
    print("-" * 70)
    for change, count in sorted(category_changes.items(), key=lambda x: x[1], reverse=True):
        print(f"   {change:50} {count:3} posts")
    
    # Show final category distribution
    print()
    print("📊 Checking final category distribution...")
    final_result = sm.client.table('posts').select('category').not_.is_('category', 'null').execute()
    
    from collections import Counter
    final_cats = Counter([p.get('category') for p in final_result.data])
    
    print()
    print("Final Distribution:")
    print("-" * 70)
    for cat, count in final_cats.most_common(15):
        pct = count / len(final_result.data) * 100
        print(f"   {cat:40} {count:4} ({pct:5.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Recategorize posts with generic categories')
    parser.add_argument('--limit', type=int, help='Limit number of posts to process')
    parser.add_argument('--all', action='store_true', help='Process all generic posts')
    parser.add_argument('--categories', type=str, default='Technology,General,bookmark',
                       help='Comma-separated categories to recategorize')
    
    args = parser.parse_args()
    
    categories = args.categories.split(',')
    
    if args.all:
        limit = None
    elif args.limit:
        limit = args.limit
    else:
        # Default: process 10 posts
        limit = 10
        print(f"💡 Processing {limit} posts by default. Use --limit N or --all for more.")
        print()
    
    asyncio.run(recategorize_posts(categories_to_fix=categories, limit=limit))


if __name__ == '__main__':
    main()
