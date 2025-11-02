#!/usr/bin/env python3
"""
Database Operations for PrisMind - Modular Implementation
Handles basic CRUD operations for posts
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from src.database.queries import DatabaseQueries


class DatabaseOperations:
    """Handles basic database operations"""

    def __init__(self, db_path: str = "prismind.db"):
        self.db_path = db_path
        self.queries = DatabaseQueries(db_path)
        self._init_database()

        # Initialize Supabase for cloud sync (optional)
        self.supabase = None
        try:
            from src.database.manager import SupabaseManager
            import os

            # Only initialize if credentials are properly set
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

            if url and key and url != "your-project-url" and key != "your-api-key":
                self.supabase = SupabaseManager()
                print("✅ Supabase sync enabled")
            else:
                print("ℹ️  Supabase sync disabled (no valid credentials)")
        except Exception as e:
            # Don't show error if it's just missing credentials
            if "Invalid API key" in str(e) or "Missing" in str(e):
                print("ℹ️  Supabase sync disabled (credentials not configured)")
            else:
                print(f"⚠️  Supabase sync disabled: {e}")

        # Initialize AI summarizer
        self.summarizer = None
        try:
            from src.services.summarizer import get_summarizer

            self.summarizer = get_summarizer()
            print("✅ AI summarizer enabled")
        except Exception as e:
            print(f"⚠️  AI summarizer disabled: {e}")

    def _init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create posts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS posts (
                        post_id TEXT PRIMARY KEY,
                        platform TEXT NOT NULL,
                        author TEXT,
                        author_handle TEXT,
                        content TEXT,
                        title TEXT,
                        url TEXT,
                        created_at TIMESTAMP,
                        post_type TEXT,
                        media_urls TEXT,
                        hashtags TEXT,
                        mentions TEXT,
                        engagement TEXT,
                        value_score REAL,
                        quality_score REAL,
                        sentiment TEXT,
                        topic TEXT,
                        content_type TEXT,
                        is_saved BOOLEAN DEFAULT 0,
                        saved_at TIMESTAMP,
                        deleted BOOLEAN DEFAULT 0,
                        created_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Create indexes
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_platform ON posts(platform)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_author ON posts(author)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_created_at ON posts(created_at)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_value_score ON posts(value_score)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_deleted ON posts(deleted)"
                )

                conn.commit()
                print("✅ Database initialized successfully")

                # Ensure schema for existing databases (add missing columns)
                self._ensure_posts_schema(conn)

        except Exception as e:
            print(f"❌ Error initializing database: {e}")

    def _ensure_posts_schema(self, conn: sqlite3.Connection) -> None:
        """Add any missing columns to the posts table for backward compatibility."""
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(posts)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            # Column definitions we rely on throughout the codebase
            column_definitions = [
                ("value_score", "REAL"),
                ("quality_score", "REAL"),
                ("sentiment", "TEXT"),
                ("topic", "TEXT"),
                ("content_type", "TEXT"),
                ("is_saved", "BOOLEAN"),
                ("saved_at", "TIMESTAMP"),
                ("deleted", "BOOLEAN"),
                ("created_timestamp", "TIMESTAMP"),
                ("updated_timestamp", "TIMESTAMP"),
                ("analysis_timestamp", "TIMESTAMP"),
                ("ai_service_used", "TEXT"),
                ("key_concepts", "TEXT"),
                ("tags", "TEXT"),
                ("sentiment_analysis", "TEXT"),
                ("content_summary", "TEXT"),
                ("insights", "TEXT"),
                ("action_items", "TEXT"),
                ("recommendations", "TEXT"),
                ("educational_value", "TEXT"),
                ("is_rewrite_candidate", "BOOLEAN"),
                ("rewrite_status", "TEXT"),
                ("rewritten_content", "TEXT"),
                ("rewrite_notes", "TEXT"),
            ]

            added_column = False
            for col, col_type in column_definitions:
                if col not in existing_cols:
                    cursor.execute(f"ALTER TABLE posts ADD COLUMN {col} {col_type}")
                    added_column = True

            # Apply sensible defaults where needed
            cursor.execute("""
                UPDATE posts
                SET rewrite_status = COALESCE(rewrite_status, 'none')
            """)
            cursor.execute("""
                UPDATE posts
                SET is_rewrite_candidate = COALESCE(is_rewrite_candidate, 0)
            """)

            conn.commit()
        except Exception as e:
            print(f"⚠️ Schema ensure failed: {e}")

    def get_all_posts(self, include_deleted: bool = False) -> List[Dict]:
        """Get all posts from database"""
        return self.queries.get_all_posts(include_deleted)

    def get_posts(
        self,
        limit: int = 100,
        offset: int = 0,
        platforms: List[str] = None,
        min_score: float = None,
        search_query: str = None,
    ) -> List[Dict]:
        """Get posts with pagination and filtering"""
        return self.queries.get_posts(limit, offset, platforms, min_score, search_query)

    def get_post_by_id(self, post_id: str) -> Optional[Dict]:
        """Get a specific post by ID"""
        return self.queries.get_post_by_id(post_id)

    def get_posts_by_platform(self, platform: str, limit: int = 100) -> List[Dict]:
        """Get posts by platform"""
        return self.queries.get_posts_by_platform(platform, limit)

    def add_post(self, post_data: Dict[str, Any]) -> bool:
        """Add a new post to the database"""
        try:
            # VALIDATE POST BEFORE SAVING
            from src.utils.post_validator import validate_post

            validation = validate_post(post_data, strict=True)
            if not validation.is_valid:
                print(f"❌ Post validation failed: {', '.join(validation.errors)}")
                print(f"   Post ID: {post_data.get('post_id')}")
                print(f"   Author: {post_data.get('author')}")
                print(f"   Content preview: {post_data.get('content', '')[:50]}...")
                return False

            # Show warnings if any
            if validation.warnings:
                print(f"⚠️  Post validation warnings: {', '.join(validation.warnings)}")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Prepare data
                post_id = post_data.get("post_id", "")
                platform = post_data.get("platform", "")
                author = post_data.get("author", "")
                author_handle = post_data.get("author_handle", "")
                content = post_data.get("content", "")
                title = post_data.get("title", "")
                url = post_data.get("url", "")
                created_at = post_data.get("created_at", datetime.now().isoformat())
                post_type = post_data.get("post_type", "post")
                media_urls = self._serialize_json(post_data.get("media_urls", []))
                hashtags = self._serialize_json(post_data.get("hashtags", []))
                mentions = self._serialize_json(post_data.get("mentions", []))
                engagement = self._serialize_json(post_data.get("engagement", {}))
                value_score = post_data.get("value_score", 0.0)
                quality_score = post_data.get("quality_score", 0.0)
                sentiment = post_data.get("sentiment", "neutral")
                topic = post_data.get("topic", "general")
                content_type = post_data.get("content_type", "text")
                is_saved = post_data.get("is_saved", False)
                saved_at = post_data.get("saved_at", datetime.now().isoformat())
                analysis_timestamp = post_data.get("analysis_timestamp")
                ai_service_used = post_data.get("ai_service_used")
                key_concepts = self._serialize_json(post_data.get("key_concepts", []))
                tags_source = post_data.get("tags") or post_data.get(
                    "suggested_tags", []
                )
                tags = self._serialize_json(tags_source)
                sentiment_analysis = self._serialize_json(
                    post_data.get("sentiment_analysis", {})
                )
                content_summary = (
                    post_data.get("content_summary")
                    or post_data.get("ai_summary")
                    or post_data.get("summary")
                )
                insights = self._serialize_json(post_data.get("insights", []))
                action_items = self._serialize_json(post_data.get("action_items", []))
                recommendations = self._serialize_json(
                    post_data.get("recommendations", [])
                )
                educational_value = post_data.get("educational_value")
                is_rewrite_candidate = (
                    1 if post_data.get("is_rewrite_candidate", False) else 0
                )
                rewrite_status = post_data.get("rewrite_status", "none")
                rewritten_content = post_data.get("rewritten_content")
                rewrite_notes = post_data.get("rewrite_notes")
                updated_timestamp = datetime.now().isoformat()

                columns = [
                    "post_id",
                    "platform",
                    "author",
                    "author_handle",
                    "content",
                    "title",
                    "url",
                    "created_at",
                    "post_type",
                    "media_urls",
                    "hashtags",
                    "mentions",
                    "engagement",
                    "value_score",
                    "quality_score",
                    "sentiment",
                    "topic",
                    "content_type",
                    "is_saved",
                    "saved_at",
                    "analysis_timestamp",
                    "ai_service_used",
                    "key_concepts",
                    "tags",
                    "sentiment_analysis",
                    "content_summary",
                    "insights",
                    "action_items",
                    "recommendations",
                    "educational_value",
                    "is_rewrite_candidate",
                    "rewrite_status",
                    "rewritten_content",
                    "rewrite_notes",
                    "updated_timestamp",
                ]

                values = [
                    post_id,
                    platform,
                    author,
                    author_handle,
                    content,
                    title,
                    url,
                    created_at,
                    post_type,
                    media_urls,
                    hashtags,
                    mentions,
                    engagement,
                    value_score,
                    quality_score,
                    sentiment,
                    topic,
                    content_type,
                    is_saved,
                    saved_at,
                    analysis_timestamp,
                    ai_service_used,
                    key_concepts,
                    tags,
                    sentiment_analysis,
                    content_summary,
                    insights,
                    action_items,
                    recommendations,
                    educational_value,
                    is_rewrite_candidate,
                    rewrite_status,
                    rewritten_content,
                    rewrite_notes,
                    updated_timestamp,
                ]

                placeholders = ", ".join(["?"] * len(columns))
                query = f"INSERT OR REPLACE INTO posts ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(query, values)

                conn.commit()
                print(f"✅ Added post to SQLite: {post_id}")

                # SYNC TO SUPABASE
                if self.supabase:
                    try:
                        # Generate AI summary if available
                        if self.summarizer and content and not content_summary:
                            content_summary = self.summarizer.summarize(content, url)
                            if content_summary:
                                print(f"   🤖 Generated AI summary")

                        # Base fields that are required in Supabase schema
                        supabase_data = {
                            "post_id": post_id,
                            "platform": platform,
                            "author": author,
                            "author_handle": author_handle,
                            "content": content,
                            "title": title,
                            "url": url,
                            "created_at": created_at,
                            "post_type": post_type,
                        }

                        # Field mapping between app fields and Supabase columns
                        field_mapping = {
                            # Core fields
                            "value_score": "value_score",
                            "quality_score": "quality_score",
                            "sentiment": "sentiment",
                            "topic": "topic",
                            "content_type": "content_type",
                            "is_saved": "is_saved",
                            "saved_at": "saved_at",
                            # Categorization
                            "folder_category": "folder_category",
                            "category": "category",
                            "subcategory": "subcategory",
                            # Content analysis
                            "summary": "summary",
                            "ai_summary": "ai_summary",
                            "key_concepts": "key_concepts",
                            "tags": "tags",
                            "smart_tags": "smart_tags",
                            "analyzed_at": "analyzed_at",
                            "analysis_model": "analysis_model",
                            # Rewrite status
                            "is_rewrite_candidate": "is_rewrite_candidate",
                            "content_quality_score": "content_quality_score",
                        }

                        # Add mapped fields
                        for app_field, supabase_field in field_mapping.items():
                            if (
                                app_field in post_data
                                and post_data[app_field] is not None
                            ):
                                value = post_data[app_field]
                                # Handle special data types
                                if isinstance(value, (list, dict)):
                                    supabase_data[supabase_field] = json.dumps(value)
                                elif isinstance(value, datetime):
                                    supabase_data[supabase_field] = value.isoformat()
                                else:
                                    supabase_data[supabase_field] = value

                        # Handle array fields
                        array_fields = [
                            "media_urls",
                            "hashtags",
                            "mentions",
                            "target_social_media",
                            "topics",
                            "related_skills",
                            "suggested_tags",
                        ]
                        for field in array_fields:
                            if field in post_data and post_data[field]:
                                if isinstance(post_data[field], list):
                                    supabase_data[field] = json.dumps(post_data[field])
                                else:
                                    supabase_data[field] = post_data[field]

                        # Handle engagement data
                        if "engagement" in post_data and post_data["engagement"]:
                            supabase_data["engagement"] = json.dumps(
                                post_data["engagement"]
                            )

                        # Handle text fields that might be in the application but not in schema
                        text_fields = [
                            "content_summary",
                            "action_items",
                            "insights",
                            "recommendations",
                            "educational_value",
                            "intelligence_analysis",
                            "actionable_insights",
                            "sentiment_analysis",
                            "analysis_timestamp",
                            "ai_service_used",
                            "rewrite_status",
                            "rewritten_content",
                            "rewrite_notes",
                            "created_timestamp",
                            "updated_timestamp",
                            "analysis_version",
                            "why_valuable",
                            "complexity_level",
                            "time_to_consume",
                            "actionable_items",
                            "learning_value",
                            "practical_applications",
                            "follow_up_research",
                            "quality_indicators",
                            "confidence_score",
                            "ai_service",
                            "intelligent_value_score",
                            "learning_recommendations",
                        ]

                        # Add text fields only if they have values
                        for field in text_fields:
                            if field in post_data and post_data[field] is not None:
                                supabase_data[field] = str(post_data[field])

                        # Insert to Supabase
                        result = self.supabase.insert_post(supabase_data)
                        if result:
                            print(f"   ☁️  Synced to Supabase")
                        else:
                            print(f"   ⚠️  Supabase sync returned no result")

                    except Exception as e:
                        print(f"   ⚠️  Supabase sync failed: {e}")
                        # Don't fail the entire operation if Supabase sync fails
                        # The data is still safely stored in SQLite

                return True

        except Exception as e:
            print(f"❌ Error adding post: {e}")
            return False

    def update_post(self, post_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing post"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Build update query dynamically
                set_clauses = []
                values = []

                for key, value in update_data.items():
                    if key in ["media_urls", "hashtags", "mentions", "engagement"]:
                        value = self._serialize_json(value)
                    set_clauses.append(f"{key} = ?")
                    values.append(value)

                if not set_clauses:
                    return False

                set_clauses.append("updated_timestamp = CURRENT_TIMESTAMP")
                values.append(post_id)

                query = f"UPDATE posts SET {', '.join(set_clauses)} WHERE post_id = ?"
                cursor.execute(query, values)

                if cursor.rowcount > 0:
                    conn.commit()
                    print(f"✅ Updated post: {post_id}")
                    return True
                else:
                    print(f"⚠️ Post not found: {post_id}")
                    return False

        except Exception as e:
            print(f"❌ Error updating post: {e}")
            return False

    def delete_post(self, post_id: str) -> bool:
        """Soft delete a post"""
        return self.update_post(post_id, {"deleted": True})

    def _serialize_json(self, obj: Any) -> str:
        """Serialize object to JSON string"""
        try:
            return json.dumps(obj) if obj is not None else "null"
        except (TypeError, ValueError) as e:
            print(f"⚠️ JSON serialization failed: {e}")
            return "null"

    def get_post_count(self) -> int:
        """Get total number of posts"""
        return self.queries.get_post_count()

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        return self.queries.get_database_stats()

    def get_platforms(self) -> List[str]:
        """Get list of platforms from database"""
        return self.queries.get_platforms()

    def get_analytics(self, days: int = 14) -> Dict[str, Any]:
        """Get aggregated analytics data"""
        return self.queries.get_analytics(days)
