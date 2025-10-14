#!/usr/bin/env python3
"""
Bookmark Collection Pipeline
Runs only bookmark-based collectors: Reddit, Twitter, Threads
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path('.env'), override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_bookmark_collection():
    """Run bookmark-based collection pipeline"""
    
    print("=" * 70)
    print("🚀 BOOKMARK COLLECTION PIPELINE")
    print("=" * 70)
    print()
    
    start_time = datetime.now()
    results = {
        "twitter": 0,
        "reddit": 0,
        "threads": 0,
        "errors": []
    }
    
    # Import orchestrator
    from src.pipeline.orchestrator import get_orchestrator
    orch = get_orchestrator()
    
    # ==========================================
    # 1. Social Bookmarks Collection
    # ==========================================
    print("📱 COLLECTING SOCIAL BOOKMARKS")
    print("-" * 70)
    
    try:
        # Run only bookmark-based platforms
        bookmark_results = await orch.collect_all(["twitter", "reddit", "threads"])
        
        results['twitter'] = bookmark_results.get('twitter', 0)
        results['reddit'] = bookmark_results.get('reddit', 0)
        results['threads'] = bookmark_results.get('threads', 0)
        results['errors'] = bookmark_results.get('errors', [])
        
        print(f"   ✅ Twitter bookmarks: {results['twitter']} items")
        print(f"   ✅ Reddit bookmarks: {results['reddit']} items")
        print(f"   ✅ Threads bookmarks: {results['threads']} items")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results['errors'].append(f"Collection: {str(e)}")
    
    print()
    
    # ==========================================
    # 2. GitHub Trending (Optional)
    # ==========================================
    print("🐙 COLLECTING GITHUB TRENDING")
    print("-" * 70)
    
    try:
        github_results = await orch.collect_all(["github_trending"])
        github_count = github_results.get('github_trending', 0)
        results['github'] = github_count
        print(f"   ✅ GitHub trending: {github_count} items")
        
        if github_results.get('errors'):
            results['errors'].extend(github_results['errors'])
            
    except Exception as e:
        print(f"   ⚠️  GitHub trending skipped: {e}")
        results['errors'].append(f"GitHub: {str(e)}")
    
    print()
    
    # ==========================================
    # 3. Telegram Channels (Optional)
    # ==========================================
    print("🇷🇺 COLLECTING TELEGRAM CHANNELS")
    print("-" * 70)
    
    try:
        telegram_results = await orch.collect_all(["telegram_channels"])
        telegram_count = telegram_results.get('telegram_channels', 0)
        results['telegram'] = telegram_count
        print(f"   ✅ Telegram channels: {telegram_count} items")
        
        if telegram_results.get('errors'):
            results['errors'].extend(telegram_results['errors'])
            
    except Exception as e:
        print(f"   ⚠️  Telegram channels skipped: {e}")
        results['errors'].append(f"Telegram: {str(e)}")
    
    print()
    
    # ==========================================
    # SUMMARY
    # ==========================================
    duration = (datetime.now() - start_time).total_seconds()
    
    print("=" * 70)
    print("✅ BOOKMARK COLLECTION COMPLETE!")
    print("=" * 70)
    print()
    print(f"⏱️  Duration: {duration:.1f}s")
    print()
    print("📊 Results:")
    print(f"   Twitter bookmarks: {results['twitter']} items")
    print(f"   Reddit bookmarks: {results['reddit']} items")
    print(f"   Threads bookmarks: {results['threads']} items")
    print(f"   GitHub trending: {results.get('github', 0)} items")
    print(f"   Telegram channels: {results.get('telegram', 0)} items")
    print(f"   Total: {sum([results['twitter'], results['reddit'], results['threads'], results.get('github', 0), results.get('telegram', 0)])} items")
    print()
    
    if results['errors']:
        print(f"⚠️  Errors: {len(results['errors'])}")
        for err in results['errors']:
            print(f"   • {err}")
        print()
    
    print("🎯 View results in Web UI:")
    print("   • Posts tab → Your bookmarks")
    print("   • GitHub tab → Trending repositories")
    print("   • Telegram tab → Channel messages")
    print()
    
    return results


if __name__ == "__main__":
    asyncio.run(run_bookmark_collection())