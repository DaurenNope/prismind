#!/usr/bin/env python3
"""
New Database Manager (Simplified)
=================================

Main orchestrator for database operations using modular components.
"""

from typing import Dict, List, Any, Optional
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

from src.database.operations import DatabaseOperations
from src.database.analysis import DatabaseAnalysis


class NewDatabaseManager:
    """Main database manager using modular components"""

    def __init__(self, db_path: str = "prismind.db"):
        self.db_operations = DatabaseOperations(db_path)
        self.db_analysis = DatabaseAnalysis(db_path)
        self.db_path = db_path
        logger.debug("🗄️ Database Manager initialized")

    # Basic Operations
    def get_all_posts(self, include_deleted: bool = False) -> List[Dict]:
        """Get all posts from database"""
        return self.db_operations.get_all_posts(include_deleted)

    def get_posts(
        self,
        limit: int = 100,
        platforms: List[str] = None,
        min_score: float = None,
        search_query: str = None,
        offset: int = 0,
    ) -> List[Dict]:
        """Get posts with pagination and filtering"""
        return self.db_operations.get_posts(
            limit=limit,
            offset=offset,
            platforms=platforms,
            min_score=min_score,
            search_query=search_query,
        )

    def get_post_by_id(self, post_id: str) -> Optional[Dict]:
        """Get a specific post by ID"""
        return self.db_operations.get_post_by_id(post_id)

    def get_posts_by_platform(self, platform: str, limit: int = 100) -> List[Dict]:
        """Get posts by platform"""
        return self.db_operations.get_posts_by_platform(platform, limit)

    def add_post(self, post_data: Dict[str, Any]) -> bool:
        """Add a new post to the database"""
        return self.db_operations.add_post(post_data)

    def update_post(self, post_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing post"""
        return self.db_operations.update_post(post_id, update_data)

    def delete_post(self, post_id: str) -> bool:
        """Delete a post (soft delete)"""
        return self.db_operations.delete_post(post_id)

    def get_post_count(self) -> int:
        """Get total number of posts"""
        return self.db_operations.get_post_count()

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.db_operations.get_database_stats()

    def get_platforms(self) -> List[str]:
        """Get list of platforms from database"""
        return self.db_operations.get_platforms()

    # Analysis Operations
    def update_post_analysis(self, post_id: str, analysis: dict) -> bool:
        """Update post with analysis results"""
        return self.db_analysis.update_post_analysis(post_id, analysis)

    def update_rewrite_status(
        self,
        post_id: str,
        status: str,
        rewritten_content: str = None,
        rewrite_notes: str = None,
    ) -> bool:
        """Update rewrite status for a post"""
        return self.db_analysis.update_rewrite_status(
            post_id, status, rewritten_content, rewrite_notes
        )

    def get_rewrite_candidates(self, limit: int = 50) -> List[Dict]:
        """Get posts that are candidates for rewriting"""
        return self.db_analysis.get_rewrite_candidates(limit)

    def get_high_quality_posts(
        self, min_quality: float = 7.0, limit: int = 50
    ) -> List[Dict]:
        """Get high quality posts"""
        return self.db_analysis.get_high_quality_posts(min_quality, limit)

    def get_low_quality_posts(
        self, max_quality: float = 5.0, limit: int = 50
    ) -> List[Dict]:
        """Get low quality posts for improvement"""
        return self.db_analysis.get_low_quality_posts(max_quality, limit)

    def get_unanalyzed_posts(
        self, limit: int = 100, platforms: Optional[List[str]] = None
    ) -> List[Dict]:
        """Get posts that haven't been analyzed yet"""
        return self.db_analysis.get_unanalyzed_posts(limit, platforms)

    def get_posts_by_score_range(
        self, min_score: float, max_score: float, limit: int = 100
    ) -> List[Dict]:
        """Get posts within a score range"""
        return self.db_analysis.get_posts_by_score_range(min_score, max_score, limit)

    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        return self.db_analysis.get_analysis_stats()

    # Convenience Methods
    def get_recent_posts(self, limit: int = 20) -> List[Dict]:
        """Get recent posts"""
        return self.get_posts(limit)

    def get_twitter_posts(self, limit: int = 50) -> List[Dict]:
        """Get Twitter posts"""
        return self.get_posts_by_platform("twitter", limit)

    def get_reddit_posts(self, limit: int = 50) -> List[Dict]:
        """Get Reddit posts"""
        return self.get_posts_by_platform("reddit", limit)

    def get_threads_posts(self, limit: int = 50) -> List[Dict]:
        """Get Threads posts"""
        return self.get_posts_by_platform("threads", limit)

    def get_analytics(self, days: int = 14) -> Dict[str, Any]:
        """Get aggregated analytics data for dashboards"""
        return self.db_operations.get_analytics(days)

    def bulk_update_analysis(self, analysis_updates: List[Dict[str, Any]]) -> int:
        """Bulk update analysis for multiple posts"""
        success_count = 0
        for update in analysis_updates:
            post_id = update.get("post_id")
            analysis = update.get("analysis")
            if post_id and analysis:
                if self.update_post_analysis(post_id, analysis):
                    success_count += 1
        return success_count

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        db_stats = self.get_database_stats()
        analysis_stats = self.get_analysis_stats()

        return {
            "database_stats": db_stats,
            "analysis_stats": analysis_stats,
            "summary": {
                "total_posts": db_stats.get("total_posts", 0),
                "analyzed_posts": analysis_stats.get("analyzed_posts", 0),
                "unanalyzed_posts": analysis_stats.get("unanalyzed_posts", 0),
                "rewrite_candidates": analysis_stats.get("rewrite_candidates", 0),
            },
        }


# Global instance for backward compatibility
_database_manager_instance = None


def get_database_manager(db_path: str = "prismind.db") -> NewDatabaseManager:
    """Get global database manager instance"""
    global _database_manager_instance
    if _database_manager_instance is None:
        _database_manager_instance = NewDatabaseManager(db_path)
    return _database_manager_instance

    # GitHub and Telegram methods for unified collection
    def get_github_trending_repos(self, limit: int = 100) -> List[Dict]:
        """Get GitHub trending repositories"""
        try:
            from src.storage.db import get_storage
            storage = get_storage()
            return storage.get_github_trending_repos(limit)
        except Exception as e:
            logger.error(f"Failed to get GitHub repos: {e}")
            return []

    def get_telegram_messages(self, limit: int = 100) -> List[Dict]:
        """Get Telegram messages"""
        try:
            from src.storage.db import get_storage
            storage = get_storage()
            return storage.get_telegram_messages(limit)
        except Exception as e:
            logger.error(f"Failed to get Telegram messages: {e}")
            return []
