#!/usr/bin/env python3
"""
Full Automated Loop Orchestrator

Complete automated pipeline:
1. COLLECTION → Collect posts from platforms
2. ANALYSIS → Analyze posts (with persona matching built-in)
3. TRANSFORMATION → Transform matched posts for personas
4. SCHEDULING → Schedule transformed posts
5. POSTING → Automatic via PublisherWorker
6. LEARNING → Track performance and update matching weights

Everything is automated - this orchestrates the entire flow.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.unified_collection_service import UnifiedCollectionService
from src.services.new_database_manager import NewDatabaseManager
from src.services.analysis.post_analyzer import analyze_and_store_post
from src.services.persona_matcher import get_persona_matcher
from src.publishing.services.transformer import PersonaGenerator, SimpleTransformer
from src.database.manager import SupabaseManager
from src.database.database_agent import DatabaseAgent
from src.services.analysis_lock import acquire_analysis_lock, release_analysis_lock
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class FullAutomationLoop:
    """Orchestrates the complete automated loop"""
    
    def __init__(self):
        self.db = NewDatabaseManager()
        self.collection_service = UnifiedCollectionService()
        self.persona_matcher = get_persona_matcher()
        
        # Initialize Supabase if available
        try:
            self.supabase = SupabaseManager()
            logger.info("✅ Supabase available")
        except Exception as e:
            logger.warning(f"⚠️ Supabase not available: {e}")
            self.supabase = None
        
        # Initialize transformer and persona generator
        self.transformer = SimpleTransformer()
        self.persona_generator = PersonaGenerator(
            sb=self.supabase,
            transformer=self.transformer
        )
    
    async def run_collection(self, platforms: Optional[List[str]] = None) -> Dict[str, int]:
        """Step 1: Collect posts from platforms
        
        If platforms is None, collects from all platforms (twitter, reddit, threads).
        If platforms is specified, only collects from those platforms.
        """
        logger.info("="*70)
        logger.info("📥 STEP 1: COLLECTION")
        logger.info("="*70)
        
        try:
            if platforms:
                logger.info(f"Collecting from: {', '.join(platforms)}")
                results = {}
                for platform in platforms:
                    try:
                        result = await self.collection_service.collect(platform)
                        results[platform] = result.posts_collected
                        logger.info(f"✅ {platform}: {result.posts_collected} posts collected")
                    except Exception as e:
                        logger.error(f"❌ {platform}: Failed - {e}")
                        results[platform] = 0
                total_collected = sum(results.values())
            else:
                # Default to all bookmark platforms (twitter, reddit, threads)
                logger.info("Collecting from all platforms (twitter, reddit, threads)...")
                default_platforms = ["twitter", "reddit", "threads"]
                results = {}
                for platform in default_platforms:
                    try:
                        result = await self.collection_service.collect(platform)
                        results[platform] = result.posts_collected
                        logger.info(f"✅ {platform}: {result.posts_collected} posts collected")
                    except Exception as e:
                        logger.error(f"❌ {platform}: Failed - {e}")
                        results[platform] = 0
                total_collected = sum(results.values())
            
            logger.info(f"📊 Collection Summary: {total_collected} total posts collected")
            return results if isinstance(results, dict) else {k: v.posts_collected for k, v in results.items()}
            
        except Exception as e:
            logger.error(f"❌ Collection failed: {e}")
            return {}
    
    async def run_analysis(self, limit: Optional[int] = None, resume: bool = True) -> Dict[str, Any]:
        """Step 2: Analyze unanalyzed posts (with persona matching built-in)
        
        Args:
            limit: Maximum number of posts to analyze (None = all)
            resume: If True, skip already analyzed posts (analyzed_at IS NOT NULL)
        """
        logger.info("\n" + "="*70)
        logger.info("🤖 STEP 2: ANALYSIS (with Persona Matching)")
        logger.info("="*70)

        if not acquire_analysis_lock():
            logger.info("Analysis skipped: an analysis run is already in progress")
            return {"analyzed": 0, "failed": 0, "skipped": True}

        try:
            # Opportunistic platform normalization (once per interval)
            try:
                agent = DatabaseAgent()
                agent.fix_invalid_platforms(limit=2000, dry_run=False, auto=True)
            except Exception as cleanup_err:
                logger.debug(f"Platform normalization skipped: {cleanup_err}")
        
            # Get unanalyzed posts (prefer Supabase as primary source)
            unanalyzed: List[Dict[str, Any]] = []
            effective_limit = int(limit) if isinstance(limit, int) and limit > 0 else 100
            if self.supabase is not None:
                try:
                    # Prefer 'analyzed_at' (present in Supabase schema)
                    query = (
                        self.supabase.client
                        .table("posts")
                        .select("*")
                    )
                    if resume:
                        query = query.is_("analyzed_at", "null")
                    query = query.order("created_at", desc=True).limit(effective_limit)
                    r = query.execute()
                    data = getattr(r, "data", []) or []
                    # If empty, fallback to value_score null/zero heuristic
                    if not data:
                        r2 = (
                            self.supabase.client
                            .table("posts")
                            .select("*")
                            .or_("value_score.is.null,value_score.eq.0")
                            .order("created_at", desc=True)
                            .limit(effective_limit)
                            .execute()
                        )
                        data = getattr(r2, "data", []) or []
                    unanalyzed = data
                except Exception as e:
                    logger.warning(f"Supabase unanalyzed fetch failed, falling back to SQLite: {e}")
                    pass
            if not unanalyzed:
                unanalyzed = self.db.get_unanalyzed_posts(limit=effective_limit)
            logger.info(f"Found {len(unanalyzed)} unanalyzed posts")
            
            if not unanalyzed:
                logger.info("✅ All posts are analyzed!")
                return {"analyzed": 0, "failed": 0}
            
            successful = 0
            failed = 0
            
            for i, post in enumerate(unanalyzed, 1):
                post_id = post.get('post_id', 'unknown')
                platform = post.get('platform', 'unknown')
                author = post.get('author', 'Unknown')[:30]
                
                logger.info(f"\n[{i}/{len(unanalyzed)}] Analyzing: {platform} - {author}")
                
                try:
                    result = await analyze_and_store_post(self.db, post, self.supabase)
                    if result:
                        successful += 1
                        logger.info(f"  ✅ Successfully analyzed")
                    else:
                        failed += 1
                        logger.warning(f"  ❌ Analysis returned False")
                except Exception as e:
                    failed += 1
                    logger.error(f"  ❌ Error: {str(e)[:100]}")
            
            logger.info(f"\n📊 Analysis Summary: {successful} successful, {failed} failed")
            return {"analyzed": successful, "failed": failed}
        finally:
            release_analysis_lock()
    
    async def run_transformation_and_scheduling(
        self,
        min_match_score: float = 0.65,
        schedule_minutes: int = 60
    ) -> Dict[str, Any]:
        """Step 3: Transform matched posts and schedule them"""
        logger.info("\n" + "="*70)
        logger.info("🎭 STEP 3: TRANSFORMATION & SCHEDULING")
        logger.info("="*70)
        
        # Get analyzed posts with persona recommendations
        all_posts = self.db.get_all_posts()
        
        # Filter posts with persona recommendations
        # Handle JSON strings that might be stored in database
        import json
        posts_with_personas = []
        for p in all_posts:
            recommended_personas = p.get('recommended_personas')
            persona_match_scores = p.get('persona_match_scores')
            
            # Handle JSON strings
            if isinstance(recommended_personas, str):
                try:
                    recommended_personas = json.loads(recommended_personas)
                except:
                    recommended_personas = None
            
            if isinstance(persona_match_scores, str):
                try:
                    persona_match_scores = json.loads(persona_match_scores)
                except:
                    persona_match_scores = None
            
            # Check if we have valid persona recommendations
            if recommended_personas and (
                (isinstance(recommended_personas, list) and len(recommended_personas) > 0) or
                (isinstance(recommended_personas, str) and recommended_personas != '[]' and recommended_personas != 'null')
            ):
                posts_with_personas.append(p)
            elif persona_match_scores and (
                (isinstance(persona_match_scores, dict) and len(persona_match_scores) > 0) or
                (isinstance(persona_match_scores, str) and persona_match_scores != '{}' and persona_match_scores != 'null')
            ):
                posts_with_personas.append(p)
        
        logger.info(f"Found {len(posts_with_personas)} posts with persona recommendations")
        
        if not posts_with_personas:
            logger.info("⚠️ No posts with persona matches found")
            return {"transformed": 0, "scheduled": 0}
        
        transformed = 0
        scheduled = 0
        
        for post in posts_with_personas:
            # Parse JSON strings if needed (sophisticated approach)
            recommended_personas = post.get('recommended_personas', [])
            persona_match_scores = post.get('persona_match_scores', {})
            
            # Handle JSON string format (from database storage)
            if isinstance(recommended_personas, str):
                try:
                    import json
                    recommended_personas = json.loads(recommended_personas)
                except (json.JSONDecodeError, ValueError):
                    recommended_personas = []
            
            if isinstance(persona_match_scores, str):
                try:
                    import json
                    persona_match_scores = json.loads(persona_match_scores)
                except (json.JSONDecodeError, ValueError):
                    persona_match_scores = {}
            
            # Check if we have valid persona recommendations
            if not recommended_personas:
                continue
            
            # Ensure recommended_personas is a list with content
            if isinstance(recommended_personas, list):
                if len(recommended_personas) == 0:
                    continue
            elif isinstance(recommended_personas, str):
                # Handle edge case where it's still a string after parsing
                if recommended_personas in ['[]', 'null', 'None', '']:
                    continue
            
            post_id = post.get('post_id')
            logger.info(f"\n📝 Post: {post_id} ({post.get('platform', 'unknown')})")
            logger.info(f"   Recommended personas: {', '.join(recommended_personas[:3])}")
            
            # Transform and schedule for each matched persona
            for persona_key in recommended_personas:
                match_score = persona_match_scores.get(persona_key, 0.0)
                
                if match_score < min_match_score:
                    logger.debug(f"   ⏭️  {persona_key}: score {match_score:.2f} < {min_match_score}")
                    continue
                
                try:
                    # Transform post for persona
                    transformed_content = self.transformer.transform(persona_key, post)
                    
                    # Get persona's platform
                    import json
                    from pathlib import Path
                    persona_file = Path(f"config/personas/{persona_key}.json")
                    persona = None
                    if persona_file.exists():
                        with open(persona_file, 'r') as f:
                            persona = json.load(f)
                    
                    if not persona:
                        logger.warning(f"   ⚠️  Persona {persona_key} not found")
                        continue
                    
                    platform = persona.get('platform', 'twitter')
                    
                    # Schedule post
                    scheduled_posts = self.persona_generator.generate_and_schedule(
                        persona_key=persona_key,
                        platform=platform,
                        sources=[post],
                        schedule_in_minutes=schedule_minutes
                    )
                    
                    if scheduled_posts:
                        transformed += 1
                        scheduled += len(scheduled_posts)
                        logger.info(f"   ✅ {persona_key}: Transformed and scheduled (score: {match_score:.2f})")
                    else:
                        logger.warning(f"   ⚠️  {persona_key}: Failed to schedule")
                        
                except Exception as e:
                    logger.error(f"   ❌ {persona_key}: Transformation failed - {e}")
        
        logger.info(f"\n📊 Transformation Summary: {transformed} posts transformed, {scheduled} posts scheduled")
        return {"transformed": transformed, "scheduled": scheduled}
    
    async def run_full_loop(
        self,
        platforms: Optional[List[str]] = None,
        analyze_limit: Optional[int] = None,
        min_match_score: float = 0.65,
        schedule_minutes: int = 60
    ) -> Dict[str, Any]:
        """
        Run the complete automated loop
        
        Args:
            platforms: List of platforms to collect from (None = all)
            analyze_limit: Max posts to analyze (None = all unanalyzed)
            min_match_score: Minimum persona match score threshold
            schedule_minutes: Minutes to schedule posts in the future
        """
        logger.info("\n" + "="*70)
        logger.info("🔄 FULL AUTOMATED LOOP - STARTING")
        logger.info("="*70)
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        
        results = {
            "collection": {},
            "analysis": {},
            "transformation": {},
            "started_at": datetime.now().isoformat()
        }
        
        # Step 1: Collection
        collection_results = await self.run_collection(platforms=platforms)
        results["collection"] = collection_results
        
        # Step 2: Analysis (with persona matching built-in)
        analysis_results = await self.run_analysis(limit=analyze_limit)
        results["analysis"] = analysis_results
        
        # Step 3: Transformation & Scheduling
        transformation_results = await self.run_transformation_and_scheduling(
            min_match_score=min_match_score,
            schedule_minutes=schedule_minutes
        )
        results["transformation"] = transformation_results
        
        results["completed_at"] = datetime.now().isoformat()
        
        logger.info("\n" + "="*70)
        logger.info("✅ FULL AUTOMATED LOOP - COMPLETE")
        logger.info("="*70)
        logger.info(f"Collection: {sum(results['collection'].values())} posts collected")
        logger.info(f"Analysis: {results['analysis'].get('analyzed', 0)} posts analyzed")
        logger.info(f"Transformation: {results['transformation'].get('scheduled', 0)} posts scheduled")
        logger.info("\n📤 Posting: Automatic via PublisherWorker (check scheduled_posts table)")
        
        return results


async def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run full automated loop')
    parser.add_argument('--platforms', nargs='+', help='Platforms to collect from (twitter, threads, reddit)')
    parser.add_argument('--analyze-limit', type=int, help='Max posts to analyze (default: all unanalyzed)')
    parser.add_argument('--min-match-score', type=float, default=0.65, help='Minimum persona match score (0.0-1.0)')
    parser.add_argument('--schedule-minutes', type=int, default=60, help='Minutes to schedule posts in future')
    
    args = parser.parse_args()
    
    loop = FullAutomationLoop()
    results = await loop.run_full_loop(
        platforms=args.platforms,
        analyze_limit=args.analyze_limit,
        min_match_score=args.min_match_score,
        schedule_minutes=args.schedule_minutes
    )
    
    logger.info("\n✅ Full loop complete!")
    logger.info(f"Results: {results}")


if __name__ == "__main__":
    asyncio.run(main())

