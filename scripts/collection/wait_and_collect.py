#!/usr/bin/env python3
"""
Wait for rate limit to expire and then try collection
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.automation.orchestrator import get_orchestrator

async def wait_and_collect(minutes: int = 30):
    """Wait for specified minutes then try collection"""
    
    print("=" * 70)
    print(f"⏳ WAITING {minutes} MINUTES FOR RATE LIMIT TO EXPIRE")
    print("=" * 70)
    print()
    print("💡 Twitter/X may be rate limiting login attempts.")
    print(f"   Waiting {minutes} minutes before attempting collection...")
    print()
    print("   You can press Ctrl+C to cancel and try later.")
    print()
    
    # Wait with progress updates
    total_seconds = minutes * 60
    update_interval = 300  # Update every 5 minutes
    
    elapsed = 0
    while elapsed < total_seconds:
        remaining = total_seconds - elapsed
        remaining_minutes = remaining // 60
        remaining_seconds = remaining % 60
        
        if elapsed % update_interval == 0:
            print(f"⏳ {elapsed // 60} minutes elapsed, {remaining_minutes}m {remaining_seconds}s remaining...")
        
        await asyncio.sleep(60)  # Wait 1 minute at a time
        elapsed += 60
    
    print()
    print("✅ Wait complete! Attempting collection...")
    print()
    
    # Now try collection
    orchestrator = get_orchestrator()
    
    results = {}
    
    # Try Twitter
    print("🐦 Testing Twitter Collection...")
    try:
        twitter_count = await orchestrator.collect_platform("twitter")
        results["twitter"] = {"success": True, "count": twitter_count}
        print(f"✅ Twitter: Collected {twitter_count} posts")
    except Exception as e:
        results["twitter"] = {"success": False, "error": str(e)}
        print(f"❌ Twitter: {e}")
    
    # Try Threads
    print()
    print("🧵 Testing Threads Collection...")
    try:
        threads_count = await orchestrator.collect_platform("threads")
        results["threads"] = {"success": True, "count": threads_count}
        print(f"✅ Threads: Collected {threads_count} posts")
    except Exception as e:
        results["threads"] = {"success": False, "error": str(e)}
        print(f"❌ Threads: {e}")
    
    print()
    print("=" * 70)
    print("📊 RESULTS")
    print("=" * 70)
    for platform, result in results.items():
        if result["success"]:
            print(f"✅ {platform.capitalize()}: {result['count']} posts")
        else:
            print(f"❌ {platform.capitalize()}: {result['error']}")

if __name__ == "__main__":
    import sys
    minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    asyncio.run(wait_and_collect(minutes))

