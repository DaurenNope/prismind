"""
Content Organizer for BEYONDLINES
Handles content organization and categorization
"""

import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

import pandas as pd


class ContentOrganizer:
    """Handles content organization and categorization"""

    def __init__(self, db_path="data/beyondlines.db"):
        self.db_path = Path(db_path)

    def get_tools_by_category(self) -> Dict[str, List[Dict]]:
        """Organize tools by category"""
        with sqlite3.connect(self.db_path) as conn:
            tools_df = pd.read_sql_query(
                """
                SELECT post_id, author, smart_title, content, smart_tags, value_score, url, category, topic
                FROM posts
                WHERE (content_type LIKE '%Tool%' OR content_type LIKE '%App%' OR content_type LIKE '%Software%')
                AND is_deleted = 0
                ORDER BY value_score DESC
            """,
                conn,
            )

        if tools_df.empty:
            return {}

        # Categorize tools
        categorized_tools = defaultdict(list)
        for _, row in tools_df.iterrows():
            category = self._categorize_tool(
                row["content"], row["smart_tags"], row["topic"]
            )
            tool_data = {
                "post_id": row["post_id"],
                "author": row["author"],
                "title": row["smart_title"],
                "content": row["content"],
                "tags": row["smart_tags"],
                "value_score": row["value_score"],
                "url": row["url"],
                "topic": row["topic"],
            }
            categorized_tools[category].append(tool_data)

        return dict(categorized_tools)

    def get_opinions_by_topic(self) -> Dict[str, List[Dict]]:
        """Organize opinions by topic"""
        with sqlite3.connect(self.db_path) as conn:
            opinions_df = pd.read_sql_query(
                """
                SELECT post_id, author, smart_title, content, smart_tags, value_score, url, topic
                FROM posts
                WHERE content_type LIKE '%Opinion%' AND is_deleted = 0
                ORDER BY value_score DESC
            """,
                conn,
            )

        if opinions_df.empty:
            return {}

        # Group by topic
        opinions_by_topic = defaultdict(list)
        for _, row in opinions_df.iterrows():
            topic = row["topic"] or self._infer_topic(row["content"])
            opinion_data = {
                "post_id": row["post_id"],
                "author": row["author"],
                "title": row["smart_title"],
                "content": row["content"],
                "tags": row["smart_tags"],
                "value_score": row["value_score"],
                "url": row["url"],
            }
            opinions_by_topic[topic].append(opinion_data)

        return dict(opinions_by_topic)

    def get_learning_resources_by_level(self) -> Dict[str, List[Dict]]:
        """Organize learning resources by complexity level"""
        with sqlite3.connect(self.db_path) as conn:
            resources_df = pd.read_sql_query(
                """
                SELECT post_id, author, smart_title, content, smart_tags, value_score, url, topic
                FROM posts
                WHERE (content_type LIKE '%Tutorial%' OR content_type LIKE '%Guide%' OR content_type LIKE '%Resource%')
                AND is_deleted = 0
                ORDER BY value_score DESC
            """,
                conn,
            )

        if resources_df.empty:
            return {}

        # Categorize by complexity
        resources_by_level = defaultdict(list)
        for _, row in resources_df.iterrows():
            complexity = self._infer_complexity(row["content"])
            resource_data = {
                "post_id": row["post_id"],
                "author": row["author"],
                "title": row["smart_title"],
                "content": row["content"],
                "tags": row["smart_tags"],
                "value_score": row["value_score"],
                "url": row["url"],
                "topic": row["topic"],
            }
            resources_by_level[complexity].append(resource_data)

        return dict(resources_by_level)

    def get_author_collections(self, min_posts=3) -> Dict[str, List[Dict]]:
        """Get collections of posts by author"""
        with sqlite3.connect(self.db_path) as conn:
            authors_df = pd.read_sql_query(
                """
                SELECT author, COUNT(*) as post_count, AVG(value_score) as avg_score
                FROM posts
                WHERE is_deleted = 0
                GROUP BY author
                HAVING post_count >= ?
                ORDER BY avg_score DESC
            """,
                conn,
                params=(min_posts,),
            )

        if authors_df.empty:
            return {}

        # Get posts for each author
        author_collections = {}
        for _, author_row in authors_df.iterrows():
            author = author_row["author"]
            with sqlite3.connect(self.db_path) as conn:
                posts_df = pd.read_sql_query(
                    """
                    SELECT post_id, smart_title, content, smart_tags, value_score, url, topic, content_type
                    FROM posts
                    WHERE author = ? AND is_deleted = 0
                    ORDER BY value_score DESC
                """,
                    conn,
                    params=(author,),
                )

            posts = []
            for _, post_row in posts_df.iterrows():
                post_data = {
                    "post_id": post_row["post_id"],
                    "title": post_row["smart_title"],
                    "content": post_row["content"],
                    "tags": post_row["smart_tags"],
                    "value_score": post_row["value_score"],
                    "url": post_row["url"],
                    "topic": post_row["topic"],
                    "content_type": post_row["content_type"],
                }
                posts.append(post_data)

            author_collections[author] = {
                "post_count": len(posts),
                "avg_score": author_row["avg_score"],
                "posts": posts,
            }

        return author_collections

    def get_trending_topics(self, days=30) -> List[Dict]:
        """Get trending topics based on recent activity"""
        with sqlite3.connect(self.db_path) as conn:
            trending_df = pd.read_sql_query(
                """
                SELECT topic, COUNT(*) as post_count, AVG(value_score) as avg_score
                FROM posts
                WHERE created_at >= datetime('now', '-{} days') AND is_deleted = 0
                GROUP BY topic
                HAVING post_count >= 2
                ORDER BY post_count DESC, avg_score DESC
                LIMIT 20
            """.format(
                    days
                ),
                conn,
            )

        if trending_df.empty:
            return []

        trending_topics = []
        for _, row in trending_df.iterrows():
            topic_data = {
                "topic": row["topic"],
                "post_count": row["post_count"],
                "avg_score": row["avg_score"],
            }
            trending_topics.append(topic_data)

        return trending_topics

    def _categorize_tool(self, content: str, tags: List[str], topic: str) -> str:
        """Categorize a tool based on content and tags"""
        content_lower = content.lower()
        tags_lower = [tag.lower() for tag in tags] if tags else []

        # Development tools
        if any(
            keyword in content_lower
            for keyword in ["code", "programming", "development", "api", "framework"]
        ):
            return "Development Tools"

        # AI/ML tools
        if any(
            keyword in content_lower
            for keyword in ["ai", "machine learning", "neural", "model", "algorithm"]
        ):
            return "AI/ML Tools"

        # Design tools
        if any(
            keyword in content_lower
            for keyword in ["design", "ui", "ux", "graphic", "visual"]
        ):
            return "Design Tools"

        # Productivity tools
        if any(
            keyword in content_lower
            for keyword in ["productivity", "task", "project", "management", "organize"]
        ):
            return "Productivity Tools"

        # Data tools
        if any(
            keyword in content_lower
            for keyword in ["data", "analytics", "database", "visualization"]
        ):
            return "Data Tools"

        # Security tools
        if any(
            keyword in content_lower
            for keyword in ["security", "privacy", "encryption", "vulnerability"]
        ):
            return "Security Tools"

        return "Other Tools"

    def _infer_topic(self, content: str) -> str:
        """Infer topic from content"""
        content_lower = content.lower()

        # Technology topics
        if any(
            keyword in content_lower
            for keyword in ["python", "javascript", "react", "node"]
        ):
            return "Programming"
        elif any(
            keyword in content_lower for keyword in ["ai", "machine learning", "neural"]
        ):
            return "Artificial Intelligence"
        elif any(
            keyword in content_lower
            for keyword in ["web", "frontend", "backend", "fullstack"]
        ):
            return "Web Development"
        elif any(
            keyword in content_lower for keyword in ["mobile", "ios", "android", "app"]
        ):
            return "Mobile Development"
        elif any(
            keyword in content_lower for keyword in ["data", "analytics", "database"]
        ):
            return "Data Science"
        elif any(
            keyword in content_lower for keyword in ["devops", "cloud", "aws", "docker"]
        ):
            return "DevOps"
        elif any(
            keyword in content_lower
            for keyword in ["security", "cybersecurity", "privacy"]
        ):
            return "Security"
        elif any(
            keyword in content_lower for keyword in ["blockchain", "crypto", "bitcoin"]
        ):
            return "Blockchain"
        elif any(
            keyword in content_lower
            for keyword in ["startup", "business", "entrepreneur"]
        ):
            return "Business"
        elif any(
            keyword in content_lower for keyword in ["design", "ui", "ux", "graphic"]
        ):
            return "Design"

        return "General"

    def _infer_complexity(self, content: str) -> str:
        """Infer complexity level from content"""
        content_lower = content.lower()

        # Beginner indicators
        if any(
            keyword in content_lower
            for keyword in ["beginner", "intro", "getting started", "basics", "simple"]
        ):
            return "Beginner"

        # Advanced indicators
        if any(
            keyword in content_lower
            for keyword in [
                "advanced",
                "expert",
                "complex",
                "sophisticated",
                "optimization",
            ]
        ):
            return "Advanced"

        # Intermediate indicators
        if any(
            keyword in content_lower
            for keyword in ["intermediate", "medium", "moderate", "step by step"]
        ):
            return "Intermediate"

        # Default to intermediate
        return "Intermediate"
