#!/usr/bin/env python3
"""Verify content posting is working"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.domain.publishing.worker import get_publisher_worker
from src.infrastructure.database.publishing.bridge import MimesisDB
from datetime import datetime, timedelta

async def verify():
    """Verify posting system status"""
    print("📊 Prismind Posting Verification Report")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    # Check worker
    worker = get_publisher_worker()
    worker_status = "✅ RUNNING" if worker._started else "❌ STOPPED"
    print(f"Publisher Worker: {worker_status}")
    
    if not worker._started:
        print("⚠️  WARNING: Publisher worker is not running!")
        print("   Start it with: python main.py integrated")
        print()
    
    # Check database
    try:
        db = MimesisDB()
        
        # Check scheduled posts
        due = db.list_due_posts()
        print(f"Scheduled Posts (Due): {len(due)}")
        
        # Check recent posts
        recent = db.get_recent_posts(hours=24)
        print(f"Posted (Last 24h): {len(recent)}")
        
        # Check last 7 days
        recent_7d = db.get_recent_posts(hours=168)
        print(f"Posted (Last 7 days): {len(recent_7d)}")
        
        print()
        
        # Show next 5 scheduled posts
        if due:
            print("Next 5 Scheduled Posts:")
            for i, post in enumerate(due[:5], 1):
                scheduled_at = post.get("scheduled_at", "Unknown")
                content_preview = post.get("content", "")[:50]
                platform = post.get("platform", "unknown")
                print(f"  {i}. [{platform}] {scheduled_at}: {content_preview}...")
            print()
        
        # Show recent posts
        if recent:
            print("Recent Posts (Last 24h):")
            for i, post in enumerate(recent[:5], 1):
                posted_at = post.get("posted_at", "Unknown")
                content_preview = post.get("content", "")[:50]
                platform = post.get("platform", "unknown")
                print(f"  {i}. [{platform}] {posted_at}: {content_preview}...")
            print()
        
        # Overall status
        if len(recent) > 0:
            print("✅ POSTING IS WORKING!")
            print(f"   Successfully posted {len(recent)} posts in the last 24 hours")
        elif len(due) > 0:
            print("⚠️  Posts are scheduled but not yet posted")
            print("   Check that publisher worker is running")
        else:
            print("⚠️  No posts scheduled or posted")
            print("   Run collection and analysis to create content")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())

