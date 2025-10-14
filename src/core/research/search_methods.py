#!/usr/bin/env python3
"""
Research Engine Search Methods
Handles different types of search operations
"""

import asyncio
from typing import Dict, List, Any, Optional
from .search_types import SearchFilter, SearchResult


class SearchMethods:
    """Handles different search method implementations"""
    
    def __init__(self, database_manager):
        self.database_manager = database_manager
    
    async def keyword_search(self, query: str, filters: SearchFilter) -> List[Dict]:
        """Perform keyword-based search"""
        try:
            # Split query into individual keywords
            keywords = [word.strip().lower() for word in query.split() if word.strip()]
            
            if not keywords:
                return []
            
            # Build SQL query for keyword search
            conditions = []
            params = []
            
            for keyword in keywords:
                conditions.append("""
                    (LOWER(content) LIKE ? OR 
                     LOWER(title) LIKE ? OR 
                     LOWER(key_concepts) LIKE ? OR
                     LOWER(tags) LIKE ?)
                """)
                keyword_param = f"%{keyword}%"
                params.extend([keyword_param, keyword_param, keyword_param, keyword_param])
            
            # Combine conditions with AND
            where_clause = " AND ".join(conditions)
            
            # Add platform filter if specified
            if filters.platform:
                where_clause += " AND platform = ?"
                params.append(filters.platform)
            
            # Add date filter if specified
            if filters.start_date:
                where_clause += " AND created_at >= ?"
                params.append(filters.start_date)
            
            if filters.end_date:
                where_clause += " AND created_at <= ?"
                params.append(filters.end_date)
            
            # Add limit
            limit_clause = f" LIMIT {filters.limit}"
            
            # Execute query
            query_sql = f"""
                SELECT * FROM posts 
                WHERE {where_clause}
                ORDER BY created_at DESC
                {limit_clause}
            """
            
            results = await self.database_manager.execute_query(query_sql, params)
            return results or []
            
        except Exception as e:
            print(f"❌ Keyword search error: {e}")
            return []
    
    async def semantic_search(self, query: str, filters: SearchFilter) -> List[Dict]:
        """Perform semantic search using embeddings"""
        try:
            # For now, fallback to keyword search
            # TODO: Implement proper semantic search with embeddings
            print("⚠️ Semantic search not fully implemented, using keyword search")
            return await self.keyword_search(query, filters)
            
        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []
    
    async def category_search(self, category: str, filters: SearchFilter) -> List[Dict]:
        """Search by category/folder"""
        try:
            if not category:
                return []
            
            # Build query for category search
            where_clause = "LOWER(folder_category) LIKE ?"
            params = [f"%{category.lower()}%"]
            
            # Add platform filter if specified
            if filters.platform:
                where_clause += " AND platform = ?"
                params.append(filters.platform)
            
            # Add date filter if specified
            if filters.start_date:
                where_clause += " AND created_at >= ?"
                params.append(filters.start_date)
            
            if filters.end_date:
                where_clause += " AND created_at <= ?"
                params.append(filters.end_date)
            
            # Add limit
            limit_clause = f" LIMIT {filters.limit}"
            
            # Execute query
            query_sql = f"""
                SELECT * FROM posts 
                WHERE {where_clause}
                ORDER BY created_at DESC
                {limit_clause}
            """
            
            results = await self.database_manager.execute_query(query_sql, params)
            return results or []
            
        except Exception as e:
            print(f"❌ Category search error: {e}")
            return []
    
    async def author_search(self, author: str, filters: SearchFilter) -> List[Dict]:
        """Search by author"""
        try:
            if not author:
                return []
            
            # Build query for author search
            where_clause = "LOWER(author) LIKE ? OR LOWER(author_handle) LIKE ?"
            author_param = f"%{author.lower()}%"
            params = [author_param, author_param]
            
            # Add platform filter if specified
            if filters.platform:
                where_clause += " AND platform = ?"
                params.append(filters.platform)
            
            # Add date filter if specified
            if filters.start_date:
                where_clause += " AND created_at >= ?"
                params.append(filters.start_date)
            
            if filters.end_date:
                where_clause += " AND created_at <= ?"
                params.append(filters.end_date)
            
            # Add limit
            limit_clause = f" LIMIT {filters.limit}"
            
            # Execute query
            query_sql = f"""
                SELECT * FROM posts 
                WHERE {where_clause}
                ORDER BY created_at DESC
                {limit_clause}
            """
            
            results = await self.database_manager.execute_query(query_sql, params)
            return results or []
            
        except Exception as e:
            print(f"❌ Author search error: {e}")
            return []
    
    async def platform_search(self, platform: str, filters: SearchFilter) -> List[Dict]:
        """Search by platform"""
        try:
            if not platform:
                return []
            
            # Build query for platform search
            where_clause = "platform = ?"
            params = [platform.lower()]
            
            # Add date filter if specified
            if filters.start_date:
                where_clause += " AND created_at >= ?"
                params.append(filters.start_date)
            
            if filters.end_date:
                where_clause += " AND created_at <= ?"
                params.append(filters.end_date)
            
            # Add limit
            limit_clause = f" LIMIT {filters.limit}"
            
            # Execute query
            query_sql = f"""
                SELECT * FROM posts 
                WHERE {where_clause}
                ORDER BY created_at DESC
                {limit_clause}
            """
            
            results = await self.database_manager.execute_query(query_sql, params)
            return results or []
            
        except Exception as e:
            print(f"❌ Platform search error: {e}")
            return []
    
    async def combined_search(self, query: str, filters: SearchFilter) -> List[Dict]:
        """Perform combined search using multiple methods"""
        try:
            # Run different search methods in parallel
            tasks = []
            
            # Always do keyword search
            tasks.append(self.keyword_search(query, filters))
            
            # Add semantic search if query is substantial
            if len(query.strip()) > 3:
                tasks.append(self.semantic_search(query, filters))
            
            # Run searches in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine and deduplicate results
            all_results = []
            seen_ids = set()
            
            for result_set in results:
                if isinstance(result_set, list):
                    for post in result_set:
                        post_id = post.get('post_id')
                        if post_id and post_id not in seen_ids:
                            all_results.append(post)
                            seen_ids.add(post_id)
            
            # Sort by relevance (simple: by created_at for now)
            all_results.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            # Apply limit
            return all_results[:filters.limit]
            
        except Exception as e:
            print(f"❌ Combined search error: {e}")
            return []
