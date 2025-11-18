#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Research Engine (Simplified)
============================

Main orchestrator for research operations using modular components.
"""

import asyncio
from typing import Any, Dict, List, Optional

from src.core.research.search_filters import SearchFilters
from src.core.research.search_methods import SearchMethods
from src.core.research.search_types import SearchFilter, SearchResult


class ResearchEngine:
    """Main research engine using modular components"""

    def __init__(self, database_manager):
        self.database_manager = database_manager
        self.search_methods = SearchMethods(database_manager)
        self.search_filters = SearchFilters()
        logger.debug("🔍 Research Engine initialized")

    async def search(
        self,
        query: str,
        filters: Optional[SearchFilter] = None,
        search_type: str = "combined",
    ) -> List[SearchResult]:
        """
        Perform comprehensive search across all content

        Args:
            query: Search query
            filters: Search filters
            search_type: Type of search (combined, keyword, semantic, category, author, platform)

        Returns:
            List of SearchResult objects
        """
        if not query or not query.strip():
            return []

        # Default filters
        if filters is None:
            filters = SearchFilter()

        logger.debug(f"🔍 Searching for: '{query}' (type: {search_type})")

        try:
            # Perform search based on type
            if search_type == "keyword":
                posts = await self.search_methods.keyword_search(query, filters)
            elif search_type == "semantic":
                posts = await self.search_methods.semantic_search(query, filters)
            elif search_type == "category":
                posts = await self.search_methods.category_search(query, filters)
            elif search_type == "author":
                posts = await self.search_methods.author_search(query, filters)
            elif search_type == "platform":
                posts = await self.search_methods.platform_search(query, filters)
            else:  # combined
                posts = await self.search_methods.combined_search(query, filters)

            # Apply filters
            filtered_posts = self.search_filters.apply_filters(posts, filters)

            # Convert to SearchResult objects
            search_results = []
            for post in filtered_posts:
                result = self.search_filters.post_to_search_result(
                    post, query, search_type
                )
                search_results.append(result)

            # Sort by relevance score
            search_results.sort(key=lambda x: x.relevance_score, reverse=True)

            logger.info(f"✅ Found {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []

    async def quick_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Quick search returning simple dictionaries"""
        try:
            filters = SearchFilter(limit=limit)
            results = await self.search(query, filters, "keyword")

            # Convert to simple dictionaries
            return [result.to_dict() for result in results]

        except Exception as e:
            logger.error(f"❌ Quick search error: {e}")
            return []

    async def get_recent_posts(
        self, platform: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent posts from database"""
        try:
            # Build query
            where_clause = "1=1"
            params = []

            if platform:
                where_clause += " AND platform = ?"
                params.append(platform.lower())

            query_sql = f"""
                SELECT * FROM posts
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit}
            """

            results = await self.database_manager.execute_query(query_sql, params)
            return results or []

        except Exception as e:
            logger.error(f"❌ Error getting recent posts: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            # Get total posts
            total_query = "SELECT COUNT(*) as count FROM posts"
            total_result = await self.database_manager.execute_query(total_query)
            total_posts = total_result[0]["count"] if total_result else 0

            # Get posts by platform
            platform_query = """
                SELECT platform, COUNT(*) as count
                FROM posts
                GROUP BY platform
            """
            platform_results = await self.database_manager.execute_query(platform_query)
            platform_stats = (
                {row["platform"]: row["count"] for row in platform_results}
                if platform_results
                else {}
            )

            return {
                "total_posts": total_posts,
                "platform_stats": platform_stats,
                "last_updated": "now",
            }

        except Exception as e:
            logger.error(f"❌ Error getting stats: {e}")
            return {"total_posts": 0, "platform_stats": {}, "last_updated": "error"}
