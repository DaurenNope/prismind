#!/usr/bin/env python3
"""
Cleanup wrongly collected posts using DatabaseAgent
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.database_agent import DatabaseAgent
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

def main():
    """Main cleanup function"""
    print("🔍 Database Cleanup - Finding and Removing Bad Posts")
    print("=" * 60)
    
    agent = DatabaseAgent()
    
    # First, run dry-run to see what we'll delete
    print("\n1️⃣ Running dry-run to identify bad posts...")
    dry_run_results = agent.cleanup_bad_posts(
        limit=1000,
        platforms=None,  # All platforms
        min_issues=2,
        dry_run=True
    )
    
    print(f"\n📊 Results:")
    print(f"   Posts checked: {dry_run_results['posts_checked']}")
    print(f"   Bad posts found: {dry_run_results['bad_posts_found']}")
    
    if dry_run_results['bad_posts']:
        print(f"\n❌ Bad Posts Found ({len(dry_run_results['bad_posts'])}):")
        for i, post in enumerate(dry_run_results['bad_posts'][:20], 1):
            print(f"\n{i}. {post['post_id']} ({post['platform']})")
            print(f"   Author: {post.get('author', 'N/A')}")
            print(f"   Content: {post['content_preview'][:80]}...")
            print(f"   Issues: {len(post['issues'])} issues")
            if post['critical_issues']:
                print(f"   Critical: {', '.join(post['critical_issues'][:2])}")
        
        if len(dry_run_results['bad_posts']) > 20:
            print(f"\n   ... and {len(dry_run_results['bad_posts']) - 20} more")
        
        # Ask for confirmation
        print(f"\n⚠️ About to delete {dry_run_results['bad_posts_found']} bad posts.")
        confirm = input("Continue? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            print("\n2️⃣ Deleting bad posts...")
            cleanup_results = agent.cleanup_bad_posts(
                limit=1000,
                platforms=None,
                min_issues=2,
                dry_run=False
            )
            
            print(f"\n✅ Cleanup complete!")
            print(f"   Posts checked: {cleanup_results['posts_checked']}")
            print(f"   Bad posts found: {cleanup_results['bad_posts_found']}")
            print(f"   Posts deleted: {cleanup_results['posts_deleted']}")
            print(f"   Failed deletions: {cleanup_results['posts_failed']}")
            
            if cleanup_results['errors']:
                print(f"\n⚠️ Errors:")
                for error in cleanup_results['errors'][:5]:
                    print(f"   - {error}")
        else:
            print("❌ Cancelled")
    else:
        print("\n✅ No bad posts found!")

if __name__ == "__main__":
    main()



