#!/usr/bin/env python3
"""
Re-analyze posts to verify analysis pipeline fix

This script re-analyzes posts to verify that all required fields
(ai_summary, key_concepts, tags, action_items) are now being populated.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.new_database_manager import get_database_manager
from src.domain.analysis.services.post_analyzer import analyze_and_store_post
from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


async def re_analyze_posts(limit: int = 10, force: bool = False):
    """
    Re-analyze posts to verify the fix works.
    
    Args:
        limit: Number of posts to re-analyze
        force: If True, re-analyze even posts that already have analyzed_at set
    """
    logger.info("=" * 70)
    logger.info("🔍 RE-ANALYZING POSTS TO VERIFY FIX")
    logger.info("=" * 70)
    
    db_manager = get_database_manager()
    
    # Get posts to re-analyze
    all_posts = db_manager.get_posts(limit=limit * 2)
    
    if force:
        # Re-analyze all posts regardless of analyzed_at
        posts_to_analyze = all_posts[:limit]
        logger.info(f"🔄 Force mode: Re-analyzing {len(posts_to_analyze)} posts")
    else:
        # Only re-analyze posts missing ai_summary or key fields
        posts_to_analyze = []
        for post in all_posts:
            ai_summary = post.get("ai_summary")
            key_concepts = post.get("key_concepts")
            tags = post.get("tags") or post.get("suggested_tags")
            action_items = post.get("action_items")
            
            # Check if any required field is missing
            if not ai_summary or not key_concepts or not tags or not action_items:
                posts_to_analyze.append(post)
                if len(posts_to_analyze) >= limit:
                    break
        
        logger.info(f"📊 Found {len(posts_to_analyze)} posts with missing fields")
    
    if not posts_to_analyze:
        logger.info("✅ No posts need re-analysis (all have required fields)")
        return {"re_analyzed": 0, "success": 0, "failed": 0, "results": []}
    
    results = []
    success_count = 0
    failed_count = 0
    
    for i, post in enumerate(posts_to_analyze, 1):
        post_id = post.get("post_id", "unknown")
        logger.info(f"\n{'='*70}")
        logger.info(f"📝 Post {i}/{len(posts_to_analyze)}: {post_id[:30]}...")
        logger.info(f"{'='*70}")
        
        # Show current state
        logger.info("Current state:")
        logger.info(f"  ai_summary: {'✅' if post.get('ai_summary') else '❌'} ({len(post.get('ai_summary', '') or '')} chars)")
        logger.info(f"  key_concepts: {'✅' if post.get('key_concepts') else '❌'} ({len(post.get('key_concepts', []) or [])} items)")
        logger.info(f"  tags: {'✅' if (post.get('tags') or post.get('suggested_tags')) else '❌'} ({len(post.get('tags', []) or post.get('suggested_tags', []) or [])} items)")
        logger.info(f"  action_items: {'✅' if post.get('action_items') else '❌'} ({len(post.get('action_items', []) or [])} items)")
        
        try:
            # Force re-analysis by clearing analyzed_at
            if force:
                # Clear analyzed_at to force re-analysis
                post_copy = dict(post)
                post_copy.pop("analyzed_at", None)
                post_copy.pop("analysis_model", None)
                # Also clear the analysis fields we want to re-populate
                post_copy.pop("ai_summary", None)
                post_copy.pop("key_concepts", None)
                post_copy.pop("tags", None)
                post_copy.pop("suggested_tags", None)
                post_copy.pop("action_items", None)
                post = post_copy
            
            # Re-analyze the post
            logger.info(f"\n🔄 Re-analyzing post...")
            success = await analyze_and_store_post(
                db_manager, 
                post, 
                supabase_manager=None  # Will use default
            )
            
            if success:
                # Fetch updated post
                updated_post = db_manager.get_post_by_id(post_id)
                if updated_post:
                    # Check updated state
                    logger.info("\n✅ Re-analysis complete. Updated state:")
                    logger.info(f"  ai_summary: {'✅' if updated_post.get('ai_summary') else '❌'} ({len(updated_post.get('ai_summary', '') or '')} chars)")
                    logger.info(f"  key_concepts: {'✅' if updated_post.get('key_concepts') else '❌'} ({len(updated_post.get('key_concepts', []) or [])} items)")
                    logger.info(f"  tags: {'✅' if (updated_post.get('tags') or updated_post.get('suggested_tags')) else '❌'} ({len(updated_post.get('tags', []) or updated_post.get('suggested_tags', []) or [])} items)")
                    logger.info(f"  action_items: {'✅' if updated_post.get('action_items') else '❌'} ({len(updated_post.get('action_items', []) or [])} items)")
                    
                    # Verify all fields are populated
                    all_populated = (
                        updated_post.get("ai_summary") and 
                        updated_post.get("key_concepts") and 
                        len(updated_post.get("key_concepts", [])) > 0 and
                        (updated_post.get("tags") or updated_post.get("suggested_tags")) and
                        len(updated_post.get("tags", []) or updated_post.get("suggested_tags", []) or []) > 0 and
                        updated_post.get("action_items") and
                        len(updated_post.get("action_items", [])) > 0
                    )
                    
                    if all_populated:
                        logger.info("✅ All required fields are now populated!")
                        success_count += 1
                        results.append({"post_id": post_id, "status": "success", "all_fields_populated": True})
                    else:
                        logger.warning("⚠️ Some fields are still missing")
                        failed_count += 1
                        results.append({"post_id": post_id, "status": "partial", "all_fields_populated": False})
                else:
                    logger.warning("⚠️ Could not fetch updated post")
                    failed_count += 1
                    results.append({"post_id": post_id, "status": "error", "error": "Could not fetch updated post"})
            else:
                logger.error("❌ Re-analysis failed")
                failed_count += 1
                results.append({"post_id": post_id, "status": "error", "error": "Analysis failed"})
                
        except Exception as e:
            logger.error(f"❌ Error re-analyzing post {post_id}: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1
            results.append({"post_id": post_id, "status": "error", "error": str(e)})
    
    # Summary
    logger.info(f"\n{'='*70}")
    logger.info("📊 RE-ANALYSIS SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total posts re-analyzed: {len(posts_to_analyze)}")
    logger.info(f"✅ Success: {success_count}")
    logger.info(f"❌ Failed/Partial: {failed_count}")
    logger.info(f"{'='*70}")
    
    return {
        "re_analyzed": len(posts_to_analyze),
        "success": success_count,
        "failed": failed_count,
        "results": results
    }


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Re-analyze posts to verify fix")
    parser.add_argument("--limit", type=int, default=10, help="Number of posts to re-analyze")
    parser.add_argument("--force", action="store_true", help="Force re-analysis of all posts (even if already analyzed)")
    
    args = parser.parse_args()
    
    result = await re_analyze_posts(limit=args.limit, force=args.force)
    
    # Return exit code based on results
    if result["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

