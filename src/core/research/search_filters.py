#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Search Filters for Research Engine
Handles filtering and result processing
"""

from typing import Any, Dict, List

from .search_types import SearchFilter, SearchResult


class SearchFilters:
    """Handles search result filtering and processing"""

    def __init__(self):
        pass

    def apply_filters(self, posts: List[Dict], filters: SearchFilter) -> List[Dict]:
        """Apply filters to search results"""
        if not posts:
            return []

        filtered_posts = []

        for post in posts:
            # Apply quality score filter
            if filters.min_quality_score is not None:
                quality_score = post.get("quality_score", 0)
                if quality_score < filters.min_quality_score:
                    continue

            # Apply value score filter
            if filters.min_value_score is not None:
                value_score = post.get("value_score", 0)
                if value_score < filters.min_value_score:
                    continue

            # Apply media filter
            if not filters.include_media and post.get("media_urls"):
                continue

            filtered_posts.append(post)

        return filtered_posts

    def post_to_search_result(
        self, post: Dict, query: str, match_type: str
    ) -> SearchResult:
        """Convert post data to SearchResult object"""
        try:
            # Extract basic information
            post_id = post.get("post_id", "")
            platform = post.get("platform", "")
            author = post.get("author", "")
            content = post.get("content", "")
            title = post.get("title")
            url = post.get("url", "")

            # Parse dates
            created_at = post.get("created_at")
            if isinstance(created_at, str):
                from datetime import datetime

                try:
                    created_at = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                except Exception as e:
                    logger.error(f"Error: {e}")
                    created_at = None

            # Extract scores
            quality_score = float(post.get("quality_score", 0))
            value_score = float(post.get("value_score", 0))

            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(post, query, match_type)

            # Extract lists
            key_concepts = post.get("key_concepts", [])
            if isinstance(key_concepts, str):
                # Try to parse as JSON array
                try:
                    import json

                    key_concepts = json.loads(key_concepts)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    key_concepts = []

            tags = post.get("tags", [])
            if isinstance(tags, str):
                try:
                    import json

                    tags = json.loads(tags)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    tags = []

            media_urls = post.get("media_urls", [])
            if isinstance(media_urls, str):
                try:
                    import json

                    media_urls = json.loads(media_urls)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    media_urls = []

            return SearchResult(
                post_id=post_id,
                platform=platform,
                author=author,
                content=content,
                title=title,
                url=url,
                created_at=created_at,
                quality_score=quality_score,
                value_score=value_score,
                match_type=match_type,
                relevance_score=relevance_score,
                key_concepts=key_concepts,
                tags=tags,
                media_urls=media_urls,
            )

        except Exception as e:
            logger.error(f"⚠️ Error converting post to search result: {e}")
            # Return minimal SearchResult
            return SearchResult(
                post_id=post.get("post_id", ""),
                platform=post.get("platform", ""),
                author=post.get("author", ""),
                content=post.get("content", ""),
                title=post.get("title"),
                url=post.get("url", ""),
                created_at=None,
                quality_score=0,
                value_score=0,
                match_type=match_type,
                relevance_score=0,
                key_concepts=[],
                tags=[],
                media_urls=[],
            )

    def _calculate_relevance_score(
        self, post: Dict, query: str, match_type: str
    ) -> float:
        """Calculate relevance score for a post"""
        try:
            score = 0.0

            # Base score by match type
            match_type_scores = {
                "exact": 1.0,
                "keyword": 0.8,
                "semantic": 0.7,
                "category": 0.6,
                "author": 0.5,
                "platform": 0.3,
            }
            score += match_type_scores.get(match_type, 0.5)

            # Content relevance
            content = post.get("content", "").lower()
            title = post.get("title", "").lower()
            query_lower = query.lower()

            if query_lower in content:
                score += 0.2
            if query_lower in title:
                score += 0.3

            # Quality bonus
            quality_score = post.get("quality_score", 0)
            if quality_score > 7:
                score += 0.1
            elif quality_score > 5:
                score += 0.05

            # Value bonus
            value_score = post.get("value_score", 0)
            if value_score > 7:
                score += 0.1
            elif value_score > 5:
                score += 0.05

            return min(1.0, score)

        except Exception as e:
            logger.error(f"⚠️ Error calculating relevance score: {e}")
            return 0.5
