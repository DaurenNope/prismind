#!/usr/bin/env python3
"""
Database Operations for BEYONDLINES - Modular Implementation
Handles basic CRUD operations for posts
"""

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.database.queries import DatabaseQueries
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseOperations:
    """Handles basic database operations"""

    def __init__(self, db_path: str = "beyondlines.db"):
        self.db_path = db_path
        self.queries = DatabaseQueries(db_path)
        self._init_database()

        # Initialize Supabase for cloud sync (optional)
        self.supabase = None
        try:
            import os

            from src.database.manager import SupabaseManager

            # Only initialize if credentials are properly set
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

            if url and key and url != "your-project-url" and key != "your-api-key":
                self.supabase = SupabaseManager()
                logger.debug("✅ Supabase sync enabled")
            else:
                logger.debug("ℹ️  Supabase sync disabled (no valid credentials)")
        except Exception as e:
            # Don't show error if it's just missing credentials
            if "Invalid API key" in str(e) or "Missing" in str(e):
                logger.debug("ℹ️  Supabase sync disabled (credentials not configured)")
            else:
                logger.debug(f"⚠️  Supabase sync disabled: {e}")

        # Initialize AI summarizer
        self.summarizer = None
        try:
            from src.services.summarizer import get_summarizer

            self.summarizer = get_summarizer()
            logger.debug("✅ AI summarizer enabled")
        except Exception as e:
            logger.debug(f"⚠️  AI summarizer disabled: {e}")

    def _init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Create posts table
                cursor.execute(
                    """
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
                        updated_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                           embedding TEXT,
                           embedding_model TEXT,
                           ai_summary TEXT,
                           key_concepts TEXT,
                           tags TEXT,
                           category TEXT,
                           analyzed_at TIMESTAMP,
                           recommended_personas TEXT,
                           persona_match_scores TEXT,
                           persona_candidacy TEXT
                       )
                """
                )

                # Add new columns if they don't exist (migration for existing databases)
                # SQLite doesn't support IF NOT EXISTS for ALTER TABLE, so check first
                cursor.execute("PRAGMA table_info(posts)")
                existing_columns = [row[1] for row in cursor.fetchall()]

                columns_to_add = {
                    "embedding": "TEXT",
                    "embedding_model": "TEXT",
                    "ai_summary": "TEXT",
                    "key_concepts": "TEXT",
                    "tags": "TEXT",
                    "category": "TEXT",
                    "analyzed_at": "TIMESTAMP",
                    "recommended_personas": "TEXT",
                    "persona_match_scores": "TEXT",
                    "persona_candidacy": "TEXT",
                    "analysis_model": "TEXT",
                }

                for col_name, col_type in columns_to_add.items():
                    if col_name not in existing_columns:
                        try:
                            cursor.execute(
                                f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}"
                            )
                        except sqlite3.OperationalError as e:
                            # Column might already exist from concurrent access
                            if "duplicate column" not in str(e).lower():
                                logger.error(f"⚠️ Failed to add column {col_name}: {e}")

                conn.commit()

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
                logger.debug("✅ Database initialized successfully")

                # Ensure schema for existing databases (add missing columns)
                self._ensure_posts_schema(conn)

        except Exception as e:
            logger.error(f"❌ Error initializing database: {e}", exc_info=True)

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
                ("analyzed_at", "TIMESTAMP"),
                ("analysis_model", "TEXT"),
                ("ai_summary", "TEXT"),
                ("language", "TEXT"),
                ("embedding", "TEXT"),
                ("embedding_model", "TEXT"),
                ("rewrite_score", "REAL"),
                ("rewrite_readiness", "TEXT"),
                ("rewrite_reasons", "TEXT"),
                ("rewrite_risks", "TEXT"),
                ("analysis_confidence", "REAL"),
                ("analysis_depth", "TEXT"),
                ("needs_deep_analysis", "BOOLEAN"),
                ("persona_fit_scores", "TEXT"),
                ("persona_fit_reasons", "TEXT"),
                ("best_persona_key", "TEXT"),
                ("best_persona_score", "REAL"),
                ("best_persona_reasons", "TEXT"),
                ("time_sensitive", "BOOLEAN"),
                ("urgency_score", "REAL"),
                ("relevance_window", "TEXT"),
                ("time_sensitive_reasons", "TEXT"),
            ]

            added_column = False
            for col, col_type in column_definitions:
                if col not in existing_cols:
                    cursor.execute(f"ALTER TABLE posts ADD COLUMN {col} {col_type}")
                    added_column = True

            # Apply sensible defaults where needed
            cursor.execute(
                """
                UPDATE posts
                SET rewrite_status = COALESCE(rewrite_status, 'none')
            """
            )
            cursor.execute(
                """
                UPDATE posts
                SET is_rewrite_candidate = COALESCE(is_rewrite_candidate, 0)
            """
            )

            conn.commit()
        except Exception as e:
            logger.error(f"⚠️ Schema ensure failed: {e}")

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
                logger.error(
                    f"❌ Post validation failed: {', '.join(validation.errors)}"
                )
                logger.info(f"   Post ID: {post_data.get('post_id')}")
                logger.info(f"   Author: {post_data.get('author')}")
                logger.info(
                    f"   Content preview: {post_data.get('content', '')[:50]}..."
                )
                return False

            # Show warnings if any
            if validation.warnings:
                logger.warning(
                    f"⚠️  Post validation warnings: {', '.join(validation.warnings)}"
                )

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

                # Handle embedding - serialize if it's a list/array
                embedding = post_data.get("embedding")
                embedding_model = post_data.get("embedding_model")
                embedding_str = self._serialize_json(embedding) if embedding else None

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
                    "embedding",
                    "embedding_model",
                    "ai_summary",
                    "category",
                    "analyzed_at",
                    "recommended_personas",
                    "persona_match_scores",
                    "persona_candidacy",
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
                    embedding_str,
                    embedding_model,
                    content_summary or post_data.get("ai_summary"),
                    post_data.get("category"),
                    post_data.get("analyzed_at") or post_data.get("analysis_timestamp"),
                    self._serialize_json(post_data.get("recommended_personas", [])),
                    self._serialize_json(post_data.get("persona_match_scores", {})),
                    self._serialize_json(post_data.get("persona_candidacy", {})),
                ]

                # P2: Fix SQL injection risk - validate column names are whitelisted
                # Column names are hardcoded above, but validate for safety
                valid_columns = set(columns)  # All columns are from hardcoded list above
                if not all(col in valid_columns for col in columns):
                    raise ValueError("Invalid column name detected")
                
                placeholders = ", ".join(["?"] * len(columns))
                # Safe: columns are from hardcoded whitelist, values are parameterized
                query = f"INSERT OR REPLACE INTO posts ({', '.join(columns)}) VALUES ({placeholders})"
                cursor.execute(query, values)

                conn.commit()
                logger.info(f"✅ Added post to SQLite: {post_id}")

                # SYNC TO SUPABASE
                if self.supabase:
                    try:
                        # Generate AI summary if available
                        summarize_enabled = os.getenv(
                            "ANALYZE_DURING_COLLECTION", "false"
                        ).lower() in ("true", "1", "yes")
                        if (
                            summarize_enabled
                            and self.summarizer
                            and content
                            and not content_summary
                        ):
                            content_summary = self.summarizer.summarize(content, url)
                            if content_summary:
                                logger.info(f"   🤖 Generated AI summary")

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
                            logger.info(f"   ☁️  Synced to Supabase")
                        else:
                            logger.warning(f"   ⚠️  Supabase sync returned no result")

                    except Exception as e:
                        logger.error(f"   ⚠️  Supabase sync failed: {e}")
                        # Don't fail the entire operation if Supabase sync fails
                        # The data is still safely stored in SQLite

                return True

        except Exception as e:
            logger.error(f"❌ Error adding post: {e}")
            return False

    def update_post(self, post_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing post"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Ensure schema is up to date before updating
                self._ensure_posts_schema(conn)

                cursor = conn.cursor()

                # Build update query dynamically
                set_clauses = []
                values = []

                # Determine existing columns to avoid unknown-column errors
                cursor.execute("PRAGMA table_info(posts)")
                existing_columns = {row[1] for row in cursor.fetchall()}

                # Fields that should be JSON-serialized (explicit list + catch-all for list/dict types)
                json_fields = [
                    "media_urls",
                    "hashtags",
                    "mentions",
                    "engagement",
                    "embedding",
                    "key_concepts",
                    "tags",
                    "sentiment_analysis",
                    "recommended_personas",
                    "persona_match_scores",
                    "persona_candidacy",
                    "insights",
                    "action_items",
                    "recommendations",
                    "rewrite_reasons",
                    "rewrite_risks",
                    "persona_fit_scores",
                    "persona_fit_reasons",
                    "best_persona_reasons",
                    "time_sensitive_reasons",
                ]

                for key, value in update_data.items():
                    # P2: Fix SQL injection risk - validate column names
                    # Skip fields not present in SQLite schema (e.g., legacy subcategory)
                    if key not in existing_columns:
                        continue
                    
                    # Additional validation: ensure key is a valid identifier
                    if not key.replace("_", "").isalnum():
                        logger.warning(f"⚠️ Skipping invalid column name: {key}")
                        continue

                    # Handle None values - convert to NULL
                    if value is None:
                        set_clauses.append(f"{key} = NULL")
                        continue

                    # Normalize JSON-like fields to TEXT for SQLite
                    if key in json_fields or isinstance(value, (list, dict)):
                        value = self._serialize_json(value)
                    # Ensure numeric fields are actually numeric
                    elif key in [
                        "value_score",
                        "quality_score",
                        "rewrite_score",
                        "analysis_confidence",
                        "best_persona_score",
                        "urgency_score",
                    ]:
                        try:
                            value = float(value) if value is not None else None
                        except (ValueError, TypeError):
                            value = None
                    # Ensure boolean fields are 0/1
                    elif key in [
                        "needs_deep_analysis",
                        "is_saved",
                        "deleted",
                        "is_rewrite_candidate",
                        "time_sensitive",
                    ]:
                        value = 1 if value else 0

                    set_clauses.append(f"{key} = ?")
                    values.append(value)

                if not set_clauses:
                    return False

                set_clauses.append("updated_timestamp = CURRENT_TIMESTAMP")
                values.append(post_id)

                # P2: Safe - column names validated above, values are parameterized
                query = f"UPDATE posts SET {', '.join(set_clauses)} WHERE post_id = ?"
                try:
                    cursor.execute(query, values)
                except sqlite3.Error as e:
                    # Fallback: try field-by-field to skip problematic bindings
                    logger.error(
                        f"⚠️ SQLite update failed ({e}), attempting field-by-field fallback"
                    )
                    safe_set = []
                    safe_vals = []
                    # Build column->value pairs
                    pairs = [
                        (clause.split("=")[0].strip(), val)
                        for clause, val in zip(set_clauses, values[:-1])
                    ]  # exclude post_id
                    for col, val in pairs:
                        try:
                            test_query = f"UPDATE posts SET {col} = ? WHERE post_id = ?"
                            cursor.execute(test_query, [val, post_id])
                            safe_set.append(f"{col} = ?")
                            safe_vals.append(val)
                        except sqlite3.Error:
                            logger.error(f"Error: {e}")
                            # Skip this bad field
                            continue
                    if safe_set:
                        fallback_query = f"UPDATE posts SET {', '.join(safe_set)}, updated_timestamp = CURRENT_TIMESTAMP WHERE post_id = ?"
                        cursor.execute(fallback_query, safe_vals + [post_id])
                    else:
                        raise

                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"✅ Updated post: {post_id}")
                    return True
                else:
                    logger.warning(f"⚠️ Post not found: {post_id}")
                    return False

        except Exception as e:
            logger.error(f"❌ Error updating post: {e}")
            # Log the problematic update_data for debugging
            if update_data:
                logger.info(f"   Update data keys: {list(update_data.keys())}")
                logger.info(
                    f"   Update data sample: {dict(list(update_data.items())[:3])}"
                )
            import traceback

            traceback.print_exc()
            return False

    def delete_post(self, post_id: str) -> bool:
        """Soft delete a post"""
        return self.update_post(post_id, {"deleted": True})

    def _serialize_json(self, obj: Any) -> str:
        """Serialize object to JSON string"""
        try:
            return json.dumps(obj) if obj is not None else "null"
        except (TypeError, ValueError) as e:
            logger.error(f"⚠️ JSON serialization failed: {e}")
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
