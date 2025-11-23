#!/usr/bin/env python3
"""
Fast Rule-Based Recategorization
=================================

Uses simple keyword matching to quickly categorize posts.
Much faster and more reliable than AI.

Usage:
    python fast_recategorize.py --all
    python fast_recategorize.py --limit 50
"""

import argparse
from datetime import datetime
from collections import Counter
from src.infrastructure.database.manager import SupabaseManager
from simple_categorizer import SimpleCategorizer


def recategorize_fast(limit=None, auto_yes=False):
    """Fast recategorization using keyword matching"""
    
    print("🚀 Fast Rule-Based Recategorization")
    print("=" * 70)
    
    sm = SupabaseManager()
    categorizer = SimpleCategorizer()
    
    # Get all posts (or limited)
    query = sm.client.table('posts').select('*')
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    posts = result.data
    
    print(f"📊 Processing {len(posts)} posts...")
    print()
    
    updates = []
    category_changes = {}
    
    for i, post in enumerate(posts, 1):
        post_id = post.get('post_id')
        old_category = post.get('category', 'Unknown')
        title = post.get('title', '')
        content = post.get('content', '')
        
        # Categorize
        new_category, confidence = categorizer.categorize(content, title)
        subcategory = categorizer.get_subcategory(new_category, content)
        
        # Only update if category changed or was generic
        if new_category != old_category or old_category in ['Technology', 'General', 'bookmark']:
            updates.append({
                'post_id': post_id,
                'old_category': old_category,
                'new_category': new_category,
                'subcategory': subcategory,
                'confidence': confidence
            })
            
            change_key = f"{old_category} → {new_category}"
            category_changes[change_key] = category_changes.get(change_key, 0) + 1
        
        if i % 50 == 0:
            print(f"   Processed {i}/{len(posts)}...")
    
    print(f"\n📊 Found {len(updates)} posts to update")
    
    if not updates:
        print("✅ All posts already have good categories!")
        return
    
    # Confirm before updating
    print(f"\n📊 Category Changes Preview:")
    print("-" * 70)
    for change, count in sorted(category_changes.items(), key=lambda x: x[1], reverse=True)[:20]:
        print(f"   {change:50} {count:4} posts")
    
    print()
    if not auto_yes:
        try:
            response = input("Update Supabase with these changes? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cancelled")
                return
        except EOFError:
            print("❌ No input available, use --yes flag to auto-confirm")
            return
    else:
        print("✅ Auto-confirming (--yes flag)")
    
    # Batch update
    print(f"\n🔄 Updating {len(updates)} posts...")
    success = 0
    errors = 0
    
    for update in updates:
        try:
            sm.client.table('posts').update({
                'category': update['new_category'],
                'subcategory': update['subcategory'],
                'updated_at': datetime.now().isoformat()
            }).eq('post_id', update['post_id']).execute()
            
            success += 1
            if success % 10 == 0:
                print(f"   Updated {success}/{len(updates)}...")
        except Exception as e:
            errors += 1
            print(f"   ❌ Error updating {update['post_id']}: {e}")
    
    print()
    print("=" * 70)
    print(f"🎉 Recategorization complete!")
    print(f"   ✅ Success: {success}")
    print(f"   ❌ Errors: {errors}")
    
    # Show final distribution
    print()
    print("📊 Final Category Distribution:")
    print("-" * 70)
    
    final = sm.client.table('posts').select('category').not_.is_('category', 'null').execute()
    final_cats = Counter([p.get('category') for p in final.data])
    
    for cat, count in final_cats.most_common(20):
        pct = count / len(final.data) * 100
        print(f"   {cat:45} {count:4} ({pct:5.1f}%)")


def main():
    parser = argparse.ArgumentParser(description='Fast rule-based recategorization')
    parser.add_argument('--limit', type=int, help='Limit number of posts')
    parser.add_argument('--all', action='store_true', help='Process all posts')
    parser.add_argument('--yes', action='store_true', help='Auto-confirm changes')
    
    args = parser.parse_args()
    
    limit = None if args.all else args.limit
    recategorize_fast(limit=limit, auto_yes=args.yes)


if __name__ == '__main__':
    main()
