#!/usr/bin/env python3
"""
Backfill AI Analysis for Existing Posts

This script:
1. Finds posts without embeddings/analysis
2. Runs comprehensive AI analysis
3. Updates Supabase with enriched data

Run: python scripts/backfill_ai_analysis.py [--limit 10] [--dry-run]
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.auto_analyzer import AnalyzerQueue
from src.infrastructure.database.manager import SupabaseManager


async def main():
    dry_run = '--dry-run' in sys.argv
    limit = None
    
    # Parse limit argument
    for i, arg in enumerate(sys.argv):
        if arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
    
    print("="*80)
    print("AI ANALYSIS BACKFILL SCRIPT")
    print("="*80)
    
    if dry_run:
        print("🔍 DRY RUN MODE - Will analyze but not save\n")
    
    # Check how many posts need analysis
    sm = SupabaseManager()
    
    query = sm.client.table('posts').select('post_id, platform', count='exact').is_('embedding', 'null')
    result = query.execute()
    
    total_unanalyzed = result.count
    print(f"📊 Found {total_unanalyzed} posts without embeddings")
    
    if limit:
        print(f"🎯 Limiting to {limit} posts")
        total_to_process = min(limit, total_unanalyzed)
    else:
        total_to_process = total_unanalyzed
    
    if total_to_process == 0:
        print("\n✅ All posts already analyzed!")
        return
    
    if not dry_run:
        print(f"\n⚠️  This will analyze {total_to_process} posts using OpenAI API")
        print(f"    Estimated cost: ~${total_to_process * 0.001:.2f} (embeddings)")
        print(f"    Estimated cost: ~${total_to_process * 0.01:.2f} (analysis)")
        print(f"    Total estimated: ~${total_to_process * 0.011:.2f}")
        
        response = input("\nContinue? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            return
    
    # Run backfill
    queue = AnalyzerQueue(batch_size=5)  # Process 5 at a time to avoid rate limits
    
    if dry_run:
        # Just analyze a few posts to test
        result = sm.client.table('posts').select('*').is_('embedding', 'null').limit(3).execute()
        posts = result.data
        
        print(f"\n🧪 Testing analysis on {len(posts)} posts...\n")
        analyzed = await queue.analyze_batch(posts)
        
        print("\n" + "="*80)
        print("DRY RUN RESULTS:")
        print("="*80)
        
        for post in analyzed:
            print(f"\nPost: {post.get('post_id')}")
            print(f"  Topics: {post.get('topics')}")
            print(f"  Tags: {post.get('tags', [])[:5]}...")
            print(f"  Summary: {post.get('ai_summary', '')[:100]}...")
            print(f"  Value: {post.get('value_score')}/10")
            print(f"  Has embedding: {bool(post.get('embedding'))}")
    else:
        # Actual backfill
        await queue.backfill_from_supabase(limit=limit)
    
    print("\n" + "="*80)
    print("✅ BACKFILL COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
