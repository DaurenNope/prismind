"""
Pipeline Status Service
Tracks and aggregates pipeline metrics for real-time dashboard
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class PipelineStatusService:
    """Service for aggregating pipeline status and metrics"""
    
    def __init__(self, supabase=None):
        """Initialize with optional Supabase client"""
        self.supabase = supabase
        if not self.supabase:
            try:
                from src.infrastructure.database.manager import SupabaseManager
                manager = SupabaseManager()
                self.supabase = manager.client
            except Exception as e:
                logger.warning(f"Could not initialize Supabase client: {e}")
                self.supabase = None
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status"""
        if not self.supabase:
            return self._empty_status()
        
        try:
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            
            # Count by stage
            collected = await self._count_collected_since(one_hour_ago)
            analyzed = await self._count_analyzed_since(one_hour_ago)
            rewritten = await self._count_rewritten_since(one_hour_ago)
            scheduled = await self._count_scheduled_pending()
            posted = await self._count_posted_since(one_hour_ago)
            
            # Calculate rates (per hour)
            collection_rate = collected / 1.0
            analysis_rate = analyzed / 1.0
            posting_rate = posted / 1.0
            
            # Detect bottlenecks
            bottlenecks = self._detect_bottlenecks({
                "collected": collected,
                "analyzed": analyzed,
                "rewritten": rewritten,
                "scheduled": scheduled,
                "posted": posted
            })
            
            # Calculate health
            health = self._calculate_health({
                "collected": collected,
                "analyzed": analyzed,
                "rewritten": rewritten,
                "scheduled": scheduled,
                "posted": posted
            }, bottlenecks)
            
            return {
                "stages": {
                    "collected": collected,
                    "analyzed": analyzed,
                    "rewritten": rewritten,
                    "scheduled": scheduled,
                    "posted": posted
                },
                "rates": {
                    "collection": round(collection_rate, 2),
                    "analysis": round(analysis_rate, 2),
                    "posting": round(posting_rate, 2)
                },
                "bottlenecks": bottlenecks,
                "health": health,
                "timestamp": now.isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}", exc_info=True)
            return self._empty_status()
    
    async def _count_collected_since(self, since: datetime) -> int:
        """Count posts collected since timestamp"""
        try:
            result = (
                self.supabase.table("posts")
                .select("id", count="exact")
                .gte("created_at", since.isoformat())
                .execute()
            )
            return getattr(result, "count", 0) or 0
        except Exception as e:
            logger.error(f"Error counting collected posts: {e}")
            return 0
    
    async def _count_analyzed_since(self, since: datetime) -> int:
        """Count posts analyzed since timestamp"""
        try:
            result = (
                self.supabase.table("posts")
                .select("id", count="exact")
                .gte("analyzed_at", since.isoformat())
                .not_.is_("analyzed_at", "null")
                .execute()
            )
            return getattr(result, "count", 0) or 0
        except Exception as e:
            logger.error(f"Error counting analyzed posts: {e}")
            return 0
    
    async def _count_rewritten_since(self, since: datetime) -> int:
        """Count rewrites created since timestamp"""
        try:
            result = (
                self.supabase.table("persona_transformations")
                .select("id", count="exact")
                .gte("created_at", since.isoformat())
                .execute()
            )
            return getattr(result, "count", 0) or 0
        except Exception as e:
            logger.error(f"Error counting rewritten posts: {e}")
            return 0
    
    async def _count_scheduled_pending(self) -> int:
        """Count posts scheduled but not yet posted"""
        try:
            result = (
                self.supabase.table("scheduled_posts")
                .select("id", count="exact")
                .in_("status", ["pending", "scheduled"])
                .execute()
            )
            return getattr(result, "count", 0) or 0
        except Exception as e:
            logger.error(f"Error counting scheduled posts: {e}")
            return 0
    
    async def _count_posted_since(self, since: datetime) -> int:
        """Count posts posted since timestamp"""
        try:
            result = (
                self.supabase.table("posted_content")
                .select("id", count="exact")
                .gte("posted_at", since.isoformat())
                .execute()
            )
            return getattr(result, "count", 0) or 0
        except Exception as e:
            logger.error(f"Error counting posted content: {e}")
            return 0
    
    def _detect_bottlenecks(self, counts: Dict[str, int]) -> List[str]:
        """Detect pipeline bottlenecks based on counts"""
        bottlenecks = []
        
        # Bottleneck thresholds
        if counts.get("scheduled", 0) > 50:
            bottlenecks.append("posting")
        if counts.get("rewritten", 0) > 100:
            bottlenecks.append("scheduling")
        if counts.get("analyzed", 0) > 200:
            bottlenecks.append("rewriting")
        if counts.get("collected", 0) > 500:
            bottlenecks.append("analysis")
        
        # Check for stage imbalances
        collected = counts.get("collected", 0)
        analyzed = counts.get("analyzed", 0)
        rewritten = counts.get("rewritten", 0)
        
        # If collected >> analyzed, analysis is bottleneck
        if collected > 0 and analyzed > 0:
            ratio = collected / analyzed
            if ratio > 2.0:
                bottlenecks.append("analysis")
        
        # If analyzed >> rewritten, rewriting is bottleneck
        if analyzed > 0 and rewritten > 0:
            ratio = analyzed / rewritten
            if ratio > 2.0:
                bottlenecks.append("rewriting")
        
        return list(set(bottlenecks))  # Remove duplicates
    
    def _calculate_health(self, counts: Dict[str, int], bottlenecks: List[str]) -> str:
        """Calculate overall pipeline health"""
        if bottlenecks:
            if len(bottlenecks) >= 2:
                return "critical"
            return "degraded"
        
        # Check if pipeline is active
        total_activity = sum(counts.values())
        if total_activity == 0:
            return "idle"
        
        return "healthy"
    
    def _empty_status(self) -> Dict[str, Any]:
        """Return empty status when service unavailable"""
        return {
            "stages": {
                "collected": 0,
                "analyzed": 0,
                "rewritten": 0,
                "scheduled": 0,
                "posted": 0
            },
            "rates": {
                "collection": 0.0,
                "analysis": 0.0,
                "posting": 0.0
            },
            "bottlenecks": [],
            "health": "unknown",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_activity_feed(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent pipeline activity"""
        if not self.supabase:
            return []
        
        try:
            activities = []
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            
            # Recent collections (from posts table)
            try:
                recent_posts = (
                    self.supabase.table("posts")
                    .select("post_id, platform, created_at")
                    .gte("created_at", one_hour_ago.isoformat())
                    .order("created_at", desc=True)
                    .limit(10)
                    .execute()
                )
                
                if recent_posts.data:
                    # Group by platform
                    by_platform = defaultdict(int)
                    for post in recent_posts.data:
                        platform = post.get("platform", "unknown")
                        by_platform[platform] += 1
                    
                    for platform, count in by_platform.items():
                        activities.append({
                            "type": "collection",
                            "message": f"Collected {count} posts from {platform}",
                            "timestamp": now.isoformat(),
                            "metadata": {"platform": platform, "count": count}
                        })
            except Exception as e:
                logger.debug(f"Error getting collection activity: {e}")
            
            # Recent analyses
            try:
                recent_analyses = (
                    self.supabase.table("posts")
                    .select("post_id, analyzed_at")
                    .gte("analyzed_at", one_hour_ago.isoformat())
                    .not_.is_("analyzed_at", "null")
                    .order("analyzed_at", desc=True)
                    .limit(10)
                    .execute()
                )
                
                if recent_analyses.data:
                    for analysis in recent_analyses.data[:5]:
                        post_id = analysis.get("post_id", "unknown")
                        activities.append({
                            "type": "analysis",
                            "message": f"Analyzed post: {post_id[:8]}...",
                            "timestamp": analysis.get("analyzed_at", now.isoformat()),
                            "metadata": {"post_id": post_id}
                        })
            except Exception as e:
                logger.debug(f"Error getting analysis activity: {e}")
            
            # Recent rewrites
            try:
                recent_rewrites = (
                    self.supabase.table("persona_transformations")
                    .select("id, persona_key, created_at")
                    .gte("created_at", one_hour_ago.isoformat())
                    .order("created_at", desc=True)
                    .limit(10)
                    .execute()
                )
                
                if recent_rewrites.data:
                    for rewrite in recent_rewrites.data[:5]:
                        persona = rewrite.get("persona_key", "unknown")
                        activities.append({
                            "type": "rewrite",
                            "message": f"Created rewrite for {persona} persona",
                            "timestamp": rewrite.get("created_at", now.isoformat()),
                            "metadata": {"persona": persona, "id": rewrite.get("id")}
                        })
            except Exception as e:
                logger.debug(f"Error getting rewrite activity: {e}")
            
            # Recent posts
            try:
                recent_posts = (
                    self.supabase.table("posted_content")
                    .select("id, platform, posted_at")
                    .gte("posted_at", one_hour_ago.isoformat())
                    .order("posted_at", desc=True)
                    .limit(10)
                    .execute()
                )
                
                if recent_posts.data:
                    for post in recent_posts.data[:5]:
                        platform = post.get("platform", "unknown")
                        activities.append({
                            "type": "post",
                            "message": f"Posted to {platform}",
                            "timestamp": post.get("posted_at", now.isoformat()),
                            "metadata": {"platform": platform, "id": post.get("id")}
                        })
            except Exception as e:
                logger.debug(f"Error getting posting activity: {e}")
            
            # Sort by timestamp (most recent first)
            activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return activities[:limit]
            
        except Exception as e:
            logger.error(f"Error getting activity feed: {e}", exc_info=True)
            return []

