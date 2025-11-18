#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Research Engine Search Methods
Handles different types of search operations
"""

import asyncio
from typing import Any, Dict, List, Optional

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
                conditions.append(
                    """
                    (LOWER(content) LIKE ? OR
                     LOWER(title) LIKE ? OR
                     LOWER(key_concepts) LIKE ? OR
                     LOWER(tags) LIKE ?)
                """
                )
                keyword_param = f"%{keyword}%"
                params.extend(
                    [keyword_param, keyword_param, keyword_param, keyword_param]
                )

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
            logger.error(f"❌ Keyword search error: {e}")
            return []

    async def semantic_search(self, query: str, filters: SearchFilter) -> List[Dict]:
        """Perform semantic search using embeddings"""
        try:
            import os

            import numpy as np
            from sentence_transformers import SentenceTransformer

            # Check if embeddings are available
            if not self.embeddings:
                logger.warning(
                    "⚠️ No embeddings loaded, falling back to keyword search"
                )
                return await self.keyword_search(query, filters)

            # Load sentence transformer model (cached after first load)
            if not hasattr(self, "_semantic_model"):
                try:
                    # Use a lightweight model for semantic search
                    self._semantic_model = SentenceTransformer("all-MiniLM-L6-v2")
                    logger.info("✅ Semantic search model loaded")
                except Exception as model_error:
                    logger.error(f"⚠️ Could not load semantic model: {model_error}")
                    return await self.keyword_search(query, filters)

            # Create query embedding
            query_embedding = self._semantic_model.encode([query])[0]

            # Calculate cosine similarity with all documents
            similarities = []
            for doc_id, doc_embedding in self.embeddings.items():
                # Compute cosine similarity
                similarity = np.dot(query_embedding, doc_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
                )
                similarities.append((doc_id, float(similarity)))

            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Get top results (adjust threshold and limit as needed)
            threshold = 0.3  # Minimum similarity threshold
            max_results = 50

            semantic_results = []
            for doc_id, similarity in similarities[:max_results]:
                if similarity >= threshold:
                    # Find the corresponding document in our index
                    for doc in self.index:
                        if doc.get("id") == doc_id:
                            # Add similarity score to document
                            doc_copy = doc.copy()
                            doc_copy["semantic_similarity"] = similarity
                            semantic_results.append(doc_copy)
                            break

            # Apply additional filters
            if filters.category and filters.category != "all":
                semantic_results = [
                    doc
                    for doc in semantic_results
                    if doc.get("category") == filters.category
                ]

            if filters.tag and filters.tag != "all":
                semantic_results = [
                    doc
                    for doc in semantic_results
                    if filters.tag in doc.get("tags", [])
                ]

            logger.info(
                f"✅ Semantic search found {len(semantic_results)} similar documents"
            )
            return semantic_results

        except ImportError:
            logger.warning(
                "⚠️ Sentence transformers not available, falling back to keyword search"
            )
            return await self.keyword_search(query, filters)
        except Exception as e:
            logger.error(f"❌ Semantic search error: {e}")
            return await self.keyword_search(query, filters)

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
            logger.error(f"❌ Category search error: {e}")
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
            logger.error(f"❌ Author search error: {e}")
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
            logger.error(f"❌ Platform search error: {e}")
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
                        post_id = post.get("post_id")
                        if post_id and post_id not in seen_ids:
                            all_results.append(post)
                            seen_ids.add(post_id)

            # Sort by relevance (simple: by created_at for now)
            all_results.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            # Apply limit
            return all_results[: filters.limit]

        except Exception as e:
            logger.error(f"❌ Combined search error: {e}")
            return []
