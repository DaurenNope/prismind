#!/usr/bin/env python3
"""
Backfill script to fix missing essential analysis fields in recent posts.

This script identifies posts that are missing required analysis fields and
re-analyzes them using the current analyzer to fill in the gaps.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from src.services.new_database_manager import NewDatabaseManager
from src.database.manager import SupabaseManager
from src.services.analysis.post_analyzer import analyze_and_store_post
from urllib.parse import urlparse

# Essential fields that should be present after analysis
ESSENTIAL_FIELDS = [
    'ai_summary',
    'value_score',
    'quality_score',
    'tags',
    'key_concepts',
    'topic',
    'content_type',
    'language',
    'analyzed_at',
    'analysis_model',
    'rewrite_score',
    'rewrite_readiness',
    'rewrite_reasons',
    'rewrite_risks',
    'analysis_confidence',
    'analysis_depth',
    'needs_deep_analysis',
    'persona_fit_scores',
    'persona_fit_reasons',
    'best_persona_key',
    'best_persona_score',
    'best_persona_reasons',
]


def find_posts_with_missing_fields(db, supabase, limit=100):
    """Find posts that are missing essential analysis fields"""
    missing = []
    
    try:
        # Query Supabase for posts missing essential fields
        if supabase:
            posts = supabase.client.table("posts").select("*").limit(limit).execute().data
            for post in posts:
                missing_count = sum(1 for field in ESSENTIAL_FIELDS if not post.get(field))
                if missing_count > 5:  # If more than 5 fields are missing
                    missing.append({
                        'post': post,
                        'missing_fields': [f for f in ESSENTIAL_FIELDS if not post.get(f)],
                        'missing_count': missing_count
                    })
    except Exception as e:
        print(f"⚠️ Supabase query failed: {e}")
        # Fallback to SQLite
        posts = db.get_all_posts()
        for post in posts[:limit]:
            missing_count = sum(1 for field in ESSENTIAL_FIELDS if not post.get(field))
            if missing_count > 5:
                missing.append({
                    'post': post,
                    'missing_fields': [f for f in ESSENTIAL_FIELDS if not post.get(f)],
                    'missing_count': missing_count
                })
    
    return missing


async def backfill_post(post_dict, db, supabase):
    """Re-analyze a single post to fill missing fields"""
    post_id = post_dict.get('post_id', 'unknown')
    print(f"📝 Backfilling: {post_id}")
    
    try:
        # Fix author_handle for Twitter if missing or contains '@'
        if (post_dict.get('platform') == 'twitter'):
            ah = post_dict.get('author_handle') or ''
            if (not ah) or ('@' in ah) or (ah == 'unknown'):
                url = post_dict.get('url') or ''
                try:
                    path = urlparse(url).path.strip('/')
                    username = path.split('/')[0] if path else ''
                    if username and username not in ('i','home','explore','notifications'):
                        post_dict['author_handle'] = username
                except Exception:
                    pass

        result = await analyze_and_store_post(db, post_dict, supabase)
        if result:
            print(f"✅ Backfilled: {post_id}")
            return True
        else:
            print(f"❌ Backfill failed: {post_id}")
            return False
    except Exception as e:
        print(f"❌ Error backfilling {post_id}: {e}")
        return False


async def main():
    """Main backfill routine"""
    print("🔧 Starting analysis backfill...")
    
    db = NewDatabaseManager()
    try:
        supabase = SupabaseManager()
        print("✅ Supabase available")
    except Exception:
        supabase = None
        print("⚠️ Supabase not available, using SQLite only")
    
    # Find posts with missing fields
    print("\n🔍 Finding posts with missing analysis fields...")
    missing = find_posts_with_missing_fields(db, supabase, limit=500)
    
    if not missing:
        print("✅ No posts found with missing essential fields!")
        return
    
    print(f"📊 Found {len(missing)} posts with missing fields")
    
    # Show summary
    missing_by_count = {}
    for item in missing:
        count = item['missing_count']
        missing_by_count[count] = missing_by_count.get(count, 0) + 1
    
    print("\n📈 Missing fields distribution:")
    for count in sorted(missing_by_count.keys(), reverse=True):
        print(f"  {count} missing fields: {missing_by_count[count]} posts")
    
    # Confirm before proceeding
    print(f"\n⚠️  About to re-analyze {len(missing)} posts")
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return
    
    # Backfill posts
    print("\n🔄 Backfilling posts...")
    successful = 0
    failed = 0
    
    for i, item in enumerate(missing, 1):
        print(f"\n[{i}/{len(missing)}] Processing...")
        result = await backfill_post(item['post'], db, supabase)
        if result:
            successful += 1
        else:
            failed += 1
    
    print(f"\n✅ Backfill complete!")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())


