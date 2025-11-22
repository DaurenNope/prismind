#!/usr/bin/env python3
"""
Run quality validation on all existing posts
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.new_database_manager import NewDatabaseManager
from src.utils.post_validator import PostValidator
from src.database.database_agent import DatabaseAgent
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

def validate_all_posts(limit: int = None, platform: str = None):
    """Validate all posts and report quality metrics"""
    print("🔍 Starting quality validation on all posts...")
    
    db = NewDatabaseManager()
    validator = PostValidator(strict=True)
    agent = DatabaseAgent()
    
    # Get all posts
    print(f"📥 Fetching posts...")
    if limit:
        posts = db.get_posts(limit=limit, platforms=[platform] if platform else None)
    else:
        posts = db.get_posts(limit=10000, platforms=[platform] if platform else None)
    
    print(f"📊 Found {len(posts)} posts to validate")
    
    # Validate posts
    valid_count = 0
    low_quality_count = 0
    invalid_count = 0
    invalid_posts = []
    low_quality_posts = []
    
    print(f"🔄 Validating posts...")
    for i, post in enumerate(posts, 1):
        if i % 100 == 0:
            print(f"   Progress: {i}/{len(posts)} ({i/len(posts)*100:.1f}%)")
        
        validation = validator.validate_post(post)
        
        if not validation.is_valid:
            invalid_count += 1
            invalid_posts.append({
                'post_id': post.get('post_id', 'unknown'),
                'platform': post.get('platform', 'unknown'),
                'author': post.get('author', 'unknown'),
                'errors': validation.errors,
                'warnings': validation.warnings
            })
        elif validation.warnings:
            low_quality_count += 1
            low_quality_posts.append({
                'post_id': post.get('post_id', 'unknown'),
                'platform': post.get('platform', 'unknown'),
                'warnings': validation.warnings
            })
        else:
            valid_count += 1
    
    # Report results
    print("\n" + "="*60)
    print("📊 VALIDATION RESULTS")
    print("="*60)
    print(f"✅ Valid: {valid_count} ({valid_count/len(posts)*100:.1f}%)")
    print(f"⚠️  Low Quality: {low_quality_count} ({low_quality_count/len(posts)*100:.1f}%)")
    print(f"❌ Invalid: {invalid_count} ({invalid_count/len(posts)*100:.1f}%)")
    print(f"📝 Total: {len(posts)}")
    
    # Show invalid posts
    if invalid_posts:
        print(f"\n❌ INVALID POSTS ({len(invalid_posts)}):")
        for invalid in invalid_posts[:20]:  # Show first 20
            print(f"   - {invalid['post_id']} ({invalid['platform']}) - {invalid['author']}")
            print(f"     Errors: {', '.join(invalid['errors'][:2])}")
        if len(invalid_posts) > 20:
            print(f"   ... and {len(invalid_posts) - 20} more")
    
    # Show low quality posts
    if low_quality_posts:
        print(f"\n⚠️  LOW QUALITY POSTS ({len(low_quality_posts)}):")
        for low in low_quality_posts[:10]:  # Show first 10
            print(f"   - {low['post_id']} ({low['platform']})")
            print(f"     Warnings: {', '.join(low['warnings'][:2])}")
        if len(low_quality_posts) > 10:
            print(f"   ... and {len(low_quality_posts) - 10} more")
    
    # Get quality metrics
    print("\n📈 QUALITY METRICS:")
    try:
        metrics = agent.get_quality_metrics(hours=24)
        print(f"   Avg Quality (24h): {metrics.get('avg_quality', 0):.2f}/10")
        print(f"   Avg Value (24h): {metrics.get('avg_value', 0):.2f}/10")
        print(f"   Low Quality %: {metrics.get('low_quality_percentage', 0):.1f}%")
    except Exception as e:
        print(f"   ⚠️ Could not fetch quality metrics: {e}")
    
    print("\n✅ Validation complete!")
    
    return {
        'total': len(posts),
        'valid': valid_count,
        'low_quality': low_quality_count,
        'invalid': invalid_count,
        'invalid_posts': invalid_posts,
        'low_quality_posts': low_quality_posts
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Validate all posts for quality")
    parser.add_argument("--limit", type=int, help="Limit number of posts to validate")
    parser.add_argument("--platform", type=str, help="Filter by platform (twitter, reddit, threads)")
    args = parser.parse_args()
    
    validate_all_posts(limit=args.limit, platform=args.platform)



