#!/usr/bin/env python3
"""
Collect then Analyze approach for PrisMind
First collect all data, then analyze it
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.pipeline.orchestrator import get_orchestrator
from src.services.new_database_manager import NewDatabaseManager
from src.services.analysis.post_analyzer import analyze_and_store_post

async def collect_only(platforms: List[str] = None) -> Dict[str, int]:
    """Collect data only, without AI analysis"""
    print("=== COLLECTION PHASE ===")
    
    if platforms is None:
        platforms = ["twitter", "reddit", "threads"]
    
    orch = get_orchestrator()
    
    # Temporarily disable AI analysis by setting environment variable
    original_skip_ai = os.environ.get("SKIP_AI_ANALYSIS", "")
    os.environ["SKIP_AI_ANALYSIS"] = "true"
    
    try:
        results = {}
        for platform in platforms:
            print(f"\nCollecting from {platform}...")
            try:
                count = await orch.collect_platform(platform)
                results[platform] = count
                print(f"✅ Collected {count} posts from {platform}")
            except Exception as e:
                print(f"❌ Failed to collect from {platform}: {e}")
                results[platform] = 0
        
        print(f"\nCollection Summary: {results}")
        return results
    finally:
        # Restore original setting
        if original_skip_ai:
            os.environ["SKIP_AI_ANALYSIS"] = original_skip_ai
        else:
            if "SKIP_AI_ANALYSIS" in os.environ:
                del os.environ["SKIP_AI_ANALYSIS"]

async def analyze_only(limit: int = None) -> int:
    """Analyze already collected posts only"""
    print("\n=== ANALYSIS PHASE ===")
    
    db_manager = NewDatabaseManager()
    
    # Get posts that haven't been analyzed yet
    # These are posts without value_score or with value_score = 0
    all_posts = db_manager.get_all_posts()
    
    # Filter for posts that need analysis (bookmark posts that are not RSS)
    posts_to_analyze = []
    for post in all_posts:
        # Check if post is from bookmark platforms
        if post.get("platform") in ["twitter", "reddit", "threads"]:
            # Check if post has been analyzed (has value_score)
            if not post.get("value_score") or post.get("value_score") == 0:
                posts_to_analyze.append(post)
    
    if limit:
        posts_to_analyze = posts_to_analyze[:limit]
    
    print(f"Found {len(posts_to_analyze)} posts to analyze")
    
    if not posts_to_analyze:
        print("No posts need analysis")
        return 0
    
    # Try to get supabase manager
    supabase_manager = None
    try:
        from src.supabase_manager import SupabaseManager
        supabase_manager = SupabaseManager()
    except Exception:
        pass
    
    # Analyze posts
    analyzed_count = 0
    for i, post in enumerate(posts_to_analyze, 1):
        post_id = post.get("post_id", "unknown")
        platform = post.get("platform", "unknown")
        title = post.get("title", "")[:50] + "..." if post.get("title") and len(post.get("title")) > 50 else post.get("title", "")
        print(f"\nAnalyzing post {i}/{len(posts_to_analyze)}: {post_id} ({platform}) - {title}")
        
        try:
            # Analyze and update the post
            if await analyze_and_store_post(db_manager, post, supabase_manager):
                analyzed_count += 1
                print(f"✅ Analyzed post {post_id}")
            else:
                print(f"❌ Failed to analyze post {post_id}")
        except Exception as e:
            print(f"❌ Error analyzing post {post_id}: {e}")
            continue
    
    print(f"\nAnalysis Summary: {analyzed_count}/{len(posts_to_analyze)} posts analyzed")
    return analyzed_count

async def collect_then_analyze(platforms: List[str] = None, analysis_limit: int = None):
    """First collect posts, then analyze them"""
    print("Starting Collect-then-Analyze process...")
    
    # Phase 1: Collect
    collection_results = await collect_only(platforms)
    
    # Phase 2: Analyze
    analysis_results = await analyze_only(analysis_limit)
    
    print("\n=== FINAL SUMMARY ===")
    print(f"Collection: {collection_results}")
    print(f"Analysis: {analysis_results} posts analyzed")
    
    return {
        "collection": collection_results,
        "analysis": analysis_results
    }

if __name__ == "__main__":
    # Parse arguments
    platforms = None
    analysis_limit = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--platforms" and len(sys.argv) > 2:
            platforms = sys.argv[2].split(",")
        elif sys.argv[1] == "--limit" and len(sys.argv) > 2:
            analysis_limit = int(sys.argv[2])
    
    results = asyncio.run(collect_then_analyze(platforms, analysis_limit))
    print(f"\nProcess completed: {results}")