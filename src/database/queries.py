#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Database Queries for BEYONDLINES
Handles database query operations
"""

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional


class DatabaseQueries:
    """Handles database query operations"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _deserialize_post(self, row: sqlite3.Row) -> Dict:
        post = dict(row)
        json_fields = [
            "engagement",
            "media_urls",
            "hashtags",
            "mentions",
            "key_concepts",
            "tags",
            "sentiment_analysis",
            "insights",
            "action_items",
            "recommendations",
        ]

        for field in json_fields:
            value = post.get(field)
            if isinstance(value, str) and value not in ("", "null"):
                try:
                    post[field] = json.loads(value)
                except (TypeError, json.JSONDecodeError):
                    pass

        if "is_rewrite_candidate" in post and post["is_rewrite_candidate"] is not None:
            post["is_rewrite_candidate"] = bool(post["is_rewrite_candidate"])

        return post

    def get_all_posts(self, include_deleted: bool = False) -> List[Dict]:
        """Get all posts from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if include_deleted:
                    query = (
                        "SELECT * FROM posts "
                        "ORDER BY COALESCE(saved_at, created_at, updated_timestamp, created_timestamp) DESC"
                    )
                else:
                    query = (
                        "SELECT * FROM posts WHERE deleted = 0 "
                        "ORDER BY COALESCE(saved_at, created_at, updated_timestamp, created_timestamp) DESC"
                    )

                cursor.execute(query)
                rows = cursor.fetchall()

                return [self._deserialize_post(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting all posts: {e}")
            return []

    def get_posts(
        self,
        limit: int = 100,
        offset: int = 0,
        platforms: List[str] = None,
        min_score: float = None,
        search_query: str = None,
    ) -> List[Dict]:
        """Get posts with pagination and filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Build query with filters
                query = "SELECT * FROM posts WHERE deleted = 0"
                params = []

                if platforms:
                    placeholders = ",".join(["?" for _ in platforms])
                    query += f" AND platform IN ({placeholders})"
                    params.extend(platforms)

                if min_score is not None:
                    query += " AND value_score >= ?"
                    params.append(min_score)

                if search_query:
                    query += " AND (title LIKE ? OR content LIKE ?)"
                    search_term = f"%{search_query}%"
                    params.extend([search_term, search_term])

                query += " ORDER BY COALESCE(saved_at, created_at, updated_timestamp, created_timestamp) DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor.execute(query, params)
                rows = cursor.fetchall()

                return [self._deserialize_post(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting posts: {e}")
            return []

    def get_post_by_id(self, post_id: str) -> Optional[Dict]:
        """Get a specific post by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = "SELECT * FROM posts WHERE post_id = ? AND deleted = 0"
                cursor.execute(query, (post_id,))
                row = cursor.fetchone()

                if row:
                    return self._deserialize_post(row)

                return None
        except Exception as e:
            logger.error(f"Error getting post by ID: {e}")
            return None

    def get_posts_by_platform(self, platform: str, limit: int = 100) -> List[Dict]:
        """Get posts by platform"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                query = (
                    "SELECT * FROM posts "
                    "WHERE platform = ? AND deleted = 0 "
                    "ORDER BY COALESCE(saved_at, created_at, updated_timestamp, created_timestamp) DESC "
                    "LIMIT ?"
                )

                cursor.execute(query, (platform, limit))
                rows = cursor.fetchall()

                return [self._deserialize_post(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting posts by platform: {e}")
            return []

    def get_post_count(self) -> int:
        """Get total number of posts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                query = "SELECT COUNT(*) FROM posts WHERE deleted = 0"
                cursor.execute(query)
                count = cursor.fetchone()[0]

                return count
        except Exception as e:
            logger.error(f"Error getting post count: {e}")
            return 0

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Total posts
                cursor.execute("SELECT COUNT(*) FROM posts WHERE deleted = 0")
                total_posts = cursor.fetchone()[0]

                # Posts by platform
                cursor.execute(
                    """
                    SELECT platform, COUNT(*)
                    FROM posts
                    WHERE deleted = 0
                    GROUP BY platform
                """
                )
                platform_counts = dict(cursor.fetchall())

                # Recent posts (last 7 days)
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM posts
                    WHERE deleted = 0
                    AND created_at >= datetime('now', '-7 days')
                """
                )
                recent_posts = cursor.fetchone()[0]

                # Average value score
                cursor.execute(
                    """
                    SELECT AVG(value_score)
                    FROM posts
                    WHERE deleted = 0 AND value_score IS NOT NULL
                """
                )
                avg_value_score = cursor.fetchone()[0] or 0.0

                return {
                    "total_posts": total_posts,
                    "platform_counts": platform_counts,
                    "recent_posts": recent_posts,
                    "average_value_score": avg_value_score,
                }
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}

    def get_platforms(self) -> List[str]:
        """Get list of unique platforms from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT platform FROM posts WHERE deleted = 0")
                platforms = [row[0] for row in cursor.fetchall()]
                return platforms
        except Exception as e:
            logger.error(f"Error getting platforms: {e}")
            return []

    def get_analytics(self, days: int = 14) -> Dict[str, Any]:
        """Get aggregated analytics data for dashboard views"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM posts WHERE deleted = 0")
                total_posts = cursor.fetchone()[0] or 0

                cursor.execute(
                    """
                    SELECT AVG(value_score) FROM posts
                    WHERE deleted = 0 AND value_score IS NOT NULL
                """
                )
                average_value_score = cursor.fetchone()[0] or 0.0

                cursor.execute(
                    "SELECT COUNT(DISTINCT author) FROM posts WHERE deleted = 0 AND author IS NOT NULL"
                )
                unique_authors = cursor.fetchone()[0] or 0

                cursor.execute(
                    "SELECT COUNT(DISTINCT platform) FROM posts WHERE deleted = 0"
                )
                unique_platforms = cursor.fetchone()[0] or 0

                cursor.execute(
                    """
                    SELECT platform, COUNT(*) as count
                    FROM posts
                    WHERE deleted = 0
                    GROUP BY platform
                """
                )
                platform_rows = cursor.fetchall()
                platform_distribution = {}
                for row in platform_rows:
                    count = row[1] or 0
                    platform_distribution[row[0] or "unknown"] = {
                        "count": count,
                        "percentage": (count / total_posts * 100) if total_posts else 0,
                    }

                cursor.execute(
                    """
                    SELECT author, COUNT(*) as post_count,
                           AVG(value_score) as average_score,
                           SUM(value_score) as total_score
                    FROM posts
                    WHERE deleted = 0 AND author IS NOT NULL AND author != ''
                    GROUP BY author
                    ORDER BY post_count DESC, total_score DESC
                    LIMIT 10
                """
                )
                top_authors = []
                for author, post_count, average_score, total_score in cursor.fetchall():
                    top_authors.append(
                        {
                            "author": author,
                            "post_count": post_count or 0,
                            "average_score": (average_score or 0.0),
                            "total_score": (total_score or 0.0),
                        }
                    )

                cursor.execute(
                    """
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM posts
                    WHERE deleted = 0 AND created_at IS NOT NULL
                      AND DATE(created_at) >= DATE('now', ?)
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at)
                """,
                    (f"-{max(days, 1)} day",),
                )
                daily_posts = [
                    {"date": row[0], "count": row[1]} for row in cursor.fetchall()
                ]

                cursor.execute(
                    """
                    SELECT DATE(created_at) as date, AVG(value_score) as average_score
                    FROM posts
                    WHERE deleted = 0 AND created_at IS NOT NULL AND value_score IS NOT NULL
                      AND DATE(created_at) >= DATE('now', ?)
                    GROUP BY DATE(created_at)
                    ORDER BY DATE(created_at)
                """,
                    (f"-{max(days, 1)} day",),
                )
                score_trends = [
                    {"date": row[0], "average_score": row[1] or 0.0}
                    for row in cursor.fetchall()
                ]

                cursor.execute(
                    """
                    SELECT
                        SUM(CASE WHEN value_score >= 0.7 THEN 1 ELSE 0 END) AS high,
                        SUM(CASE WHEN value_score >= 0.4 AND value_score < 0.7 THEN 1 ELSE 0 END) AS medium,
                        SUM(CASE WHEN value_score < 0.4 THEN 1 ELSE 0 END) AS low
                    FROM posts
                    WHERE deleted = 0 AND value_score IS NOT NULL
                """
                )
                high, medium, low = cursor.fetchone()
                score_distribution = {
                    "High (0.7-1.0)": high or 0,
                    "Medium (0.4-0.7)": medium or 0,
                    "Low (0.0-0.4)": low or 0,
                }

                insights = []
                if total_posts == 0:
                    insights.append(
                        "No posts collected yet — run a collection to populate the dashboard."
                    )
                else:
                    leading_platform = (
                        max(
                            platform_distribution.items(),
                            key=lambda item: item[1]["count"],
                        )[0]
                        if platform_distribution
                        else None
                    )
                    if leading_platform:
                        insights.append(
                            f"{leading_platform.title()} currently has the most saved posts."
                        )
                    if average_value_score:
                        insights.append(
                            f"Average value score across posts is {average_value_score:.2f}."
                        )
                    if top_authors:
                        top_author = top_authors[0]
                        insights.append(
                            f"Top contributor: {top_author['author']} with {top_author['post_count']} posts."
                        )

                return {
                    "total_posts": total_posts,
                    "average_value_score": float(average_value_score or 0.0),
                    "unique_authors": unique_authors,
                    "unique_platforms": unique_platforms,
                    "platform_distribution": platform_distribution,
                    "top_authors": top_authors,
                    "trends": {
                        "daily_posts": daily_posts,
                        "score_trends": score_trends,
                    },
                    "score_distribution": score_distribution,
                    "insights": insights,
                }
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return {}
