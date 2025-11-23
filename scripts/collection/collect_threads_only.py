#!/usr/bin/env python3
"""
Collect from Threads only (bypasses Twitter rate limiting)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.application.automation.orchestrator import get_orchestrator

async def collect_threads_only():
    """Collect from Threads only"""
    
    print("=" * 70)
    print("🧵 THREADS COLLECTION ONLY")
    print("=" * 70)
    print()
    print("💡 Skipping Twitter (likely rate limited)")
    print("   Focusing on Threads collection...")
    print()
    
    orchestrator = get_orchestrator()
    
    try:
        print("🚀 Starting Threads collection...")
        threads_count = await orchestrator.collect_platform("threads")
        
        if threads_count > 0:
            print(f"\n✅ SUCCESS: Collected {threads_count} posts from Threads")
        else:
            print(f"\n⚠️  No new posts collected from Threads (may already be up to date)")
        
        return threads_count
        
    except Exception as e:
        print(f"\n❌ FAILED: Threads collection failed")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    count = asyncio.run(collect_threads_only())
    sys.exit(0 if count >= 0 else 1)

