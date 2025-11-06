#!/usr/bin/env python3
"""
Supabase Manager for PrisMind
Handles all Supabase database operations
"""

import os
import json
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()

try:
    from supabase import create_client, Client
except ImportError:
    logger.warning("Warning: supabase-py not installed. Install with: pip install supabase")
    create_client = None
    Client = None


class SupabaseManager:
    """Manager for Supabase database operations"""

    def __init__(self):
        """Initialize Supabase manager with credentials from environment"""
        self.client = None
        self.table_name = "posts"

        # Get credentials from environment
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        # Store credentials as attributes for test compatibility
        self.supabase_url = url
        self.supabase_key = key

        if not url or not key:
            raise ValueError("Missing Supabase credentials in .env file")

        if create_client is None:
            raise ImportError(
                "supabase-py not installed. Install with: pip install supabase"
            )

        try:
            self.client = create_client(url, key)
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {e}")

    def check_duplicate_by_url(self, url: str) -> bool:
        """
        Check if a post with this URL already exists

        Args:
            url: Post URL to check

        Returns:
            True if duplicate exists, False otherwise
        """
        if not url:
            return False

        try:
            result = (
                self.client.table(self.table_name)
                .select("id")
                .eq("url", url)
                .limit(1)
                .execute()
            )

            is_duplicate = len(result.data) > 0
            # Don't log here - let insert_post handle logging to avoid duplicates
            return is_duplicate
        except Exception as e:
            logger.warning(f"   ⚠️  Error checking duplicate: {e}")
            return False

    def check_duplicate_post(
        self,
        content: str,
        author: str,
        platform: str = None,
        category: str = None,
        url: str = None,
    ) -> bool:
        """
        Check if a post with similar content, author, or URL already exists

        Args:
            content: Post content to check
            author: Post author to check
            platform: Platform to check (optional)
            category: Category to check within (optional) - if provided, only checks within same category
            url: Post URL to check for duplicates

        Returns:
            bool: True if duplicate exists, False otherwise
        """
        try:
            # First check for URL duplicates (most reliable)
            if url:
                url_query = (
                    self.client.table(self.table_name)
                    .select("id, url, author")
                    .eq("url", url)
                    .limit(1)
                )
                url_response = url_query.execute()
                if url_response.data:
                    logger.info(f"🔍 URL duplicate found: {url}")
                    return True

            if not content or not author:
                return False

            # Build query to check for duplicates (category dropped from schema)
            query = self.client.table(self.table_name).select(
                "id, created_at, url"
            )

            # Check for exact content match and same author
            query = query.eq("content", content).eq("author", author)

            # Add platform filter if provided
            if platform:
                query = query.eq("platform", platform)

            # Category column dropped; ignore category-based duplicate scoping

            response = query.limit(5).execute()  # Get more results to see categories

            # For ZERO IKA posts, check if duplicates have different timestamps or URLs
            if author.upper() == "ZERO IKA" and len(response.data) > 0:
                logger.debug(f"🔍 ZERO IKA duplicate check: {content[:50]}...")
                for existing_post in response.data:
                    logger.debug(f"    Existing post ID: {existing_post.get('id')}")
                    logger.debug(f"    Created at: {existing_post.get('created_at')}")
                    logger.debug(f"    URL: {existing_post.get('url')}")

                # Allow ZERO IKA posts if they have different URLs (different tweets)
                # This handles retweets or similar content posted at different times
                return (
                    False  # Don't mark as duplicate for ZERO IKA to preserve all posts
                )

            # Debug logging for duplicate detection
            if len(response.data) > 0:
                logger.info(f"🔍 Duplicate found: {author} - {content[:50]}...")
            else:
                logger.debug(f"✅ New content: {author} - {content[:50]}...")

            # Return True if any matching posts found
            return len(response.data) > 0

        except Exception as e:
            logger.error(f"Error checking for duplicates: {e}")
            return False  # If error, assume not duplicate to avoid blocking new posts

    def insert_post(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert a new post into Supabase

        Args:
            post_data: Dictionary containing post data

        Returns:
            Dict containing the inserted post data, or empty dict on error/duplicate
        """
        try:
            if not post_data:
                logger.error(f"❌ Supabase insert_post: Empty post_data provided")
                return {}

            # Ensure we have required fields
            if not post_data.get("title") and not post_data.get("content"):
                logger.error(f"❌ Supabase insert_post: Missing both title and content")
                logger.error(f"   Post ID: {post_data.get('post_id', 'unknown')}")
                logger.error(f"   Keys present: {list(post_data.keys())}")
                return {}

            # Debug: Check if embedding exists in incoming data
            has_emb_input = 'embedding' in post_data and post_data['embedding'] is not None
            if has_emb_input:
                logger.debug(f"🔍 insert_post: Received embedding ({len(post_data['embedding'])} dims)")
            else:
                logger.debug(f"⚠️  insert_post: NO embedding in post_data")
            
            # Check for duplicates before inserting
            content = post_data.get("content", "")
            author = post_data.get("author", "")
            platform = post_data.get("platform", "")
            url = post_data.get("url", "")

            logger.debug(
                f"🔍 Supabase: Checking duplicates for post {post_data.get('post_id', 'unknown')}"
            )

            # Check if this is an update (has embedding) or initial insert
            is_enriched_update = has_emb_input

            # First check by URL (most reliable)
            if url and self.check_duplicate_by_url(url):
                if is_enriched_update:
                    logger.info(f"   🔄 Duplicate URL found, will UPDATE with enriched data: {url}")
                    # Don't return, proceed to update
                else:
                    logger.debug(f"   ⏭️  Duplicate URL detected: {url[:60]}...")
                    return {}  # Return empty dict to indicate duplicate

            # Then check by content/author
            elif self.check_duplicate_post(content, author, platform, url=url):
                if is_enriched_update:
                    logger.info(f"   🔄 Duplicate found, will UPDATE with enriched data")
                    # Don't return, proceed to update
                else:
                    logger.debug(f"   ⏭️  Duplicate detected: {author} - {content[:50]}...")
                    return {}  # Return empty dict to indicate duplicate
            else:
                logger.debug(
                    f"✅ Supabase: No duplicate found, inserting post {post_data.get('post_id', 'unknown')}"
                )

            # ONLY SEND FIELDS THAT EXIST IN SUPABASE SCHEMA
            # Based on your exact schema definition
            supabase_schema_fields = {
                'post_id','title','content','url','platform','author','author_handle',
                'created_at','ai_summary','topic','content_type','post_type','media_urls',
                'hashtags','mentions','is_saved','analyzed_at','sentiment','key_concepts',
                'tags','analysis_model','value_score','quality_score','embedding',
                'embedding_model','language'
            }
            
            # First apply field mappings (currently identity; schema uses quality_score)
            mapped_data = {}
            field_mappings = {}
            
            for key, value in post_data.items():
                if value is not None:
                    # Apply field mapping if needed
                    target_key = field_mappings.get(key, key)
                    mapped_data[target_key] = value
            
            # Clean the data - only include fields that exist in Supabase schema
            clean_data = {}
            for key, value in mapped_data.items():
                # Only include fields that exist in our Supabase schema
                if key in supabase_schema_fields:
                    # Embedding vector: keep as list of floats for pgvector
                    if key == 'embedding':
                        clean_data[key] = value  # pgvector handles list of floats
                    # Convert datetime objects to ISO format strings
                    elif hasattr(value, "isoformat"):
                        clean_data[key] = value.isoformat()
                    # Convert lists to JSON strings if needed
                    elif isinstance(value, list):
                        clean_data[key] = (
                            json.dumps(value)
                            if key in ["smart_tags", "media_urls"]
                            else value
                        )
                    else:
                        clean_data[key] = value

            # Final guard: strip deprecated/removed columns
            if 'content_quality_score' in clean_data:
                clean_data.pop('content_quality_score', None)

            # Debug logging for schema filtering
            original_count = len(post_data)
            filtered_count = len(clean_data)
            if original_count != filtered_count:
                filtered_fields = set(post_data.keys()) - set(clean_data.keys())
                logger.debug(f"🧹 Schema filter: {filtered_count}/{original_count} fields kept")
                logger.debug(f"   Removed fields: {sorted(filtered_fields)}")

            # Debug: Check if embedding is present
            has_embedding = 'embedding' in clean_data and clean_data['embedding'] is not None
            emb_preview = f" (embedding: {len(clean_data['embedding'])} dims)" if has_embedding else ""

            action = "Upserting" if is_enriched_update else "Inserting"
            logger.debug(f"📤 Supabase: {action} with {len(clean_data)} fields{emb_preview}")

            # Use upsert to handle both insert and update
            # This allows enriched data (with embeddings) to update existing posts
            try:
                response = self.client.table(self.table_name).upsert(
                    clean_data,
                    on_conflict='url'  # Use URL as unique key for upsert
                ).execute()
            except Exception as api_error:
                # Handle schema mismatch errors specifically
                error_str = str(api_error)
                if "schema cache" in error_str or "column" in error_str.lower():
                    logger.error(f"❌ Supabase insert_post ERROR: Schema mismatch - {api_error}")
                    logger.error(f"   Post ID: {post_data.get('post_id', 'unknown')}")
                    logger.error(f"   Platform: {post_data.get('platform', 'unknown')}")
                    logger.error(f"   URL: {post_data.get('url', 'unknown')}")
                    logger.error(f"   Post data keys: {list(post_data.keys())}")
                    logger.error(f"   This indicates the Supabase table schema needs to be updated")
                    logger.error(f"   Run the schema update script at supabase_schema_update.sql")
                    return {}
                else:
                    raise api_error

            if response.data:
                logger.debug(
                    f"✅ Supabase: Insert successful for post {post_data.get('post_id', 'unknown')}"
                )
                return (
                    response.data[0]
                    if isinstance(response.data, list)
                    else response.data
                )
            else:
                logger.warning(
                    f"⚠️ Supabase: Insert returned no data for post {post_data.get('post_id', 'unknown')}"
                )
            return {}

        except Exception as e:
            logger.exception(f"❌ Supabase insert_post ERROR: {e}")
            logger.error(f"   Post ID: {post_data.get('post_id', 'unknown')}")
            logger.error(f"   Platform: {post_data.get('platform', 'unknown')}")
            logger.error(f"   URL: {post_data.get('url', 'no url')}")
            return {}

    def add_post(self, post_data: Dict[str, Any]) -> bool:
        """
        Add a new post to Supabase (compatibility method)

        Args:
            post_data: Dictionary containing post data

        Returns:
            bool: True if successful, False otherwise
        """
        result = self.insert_post(post_data)
        return bool(result)

    def get_posts(
        self,
        limit: int = 10,
        platform: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get posts from Supabase with optional filtering

        Args:
            limit: Maximum number of posts to return
            platform: Filter by platform (optional)
            category: Filter by category (optional)

        Returns:
            List of post dictionaries
        """
        try:
            query = self.client.table(self.table_name).select("*")

            # Apply filters
            if platform:
                query = query.eq("platform", platform)
            if category:
                query = query.eq("category", category)

            # Apply limit and ordering
            query = query.limit(limit).order("created_at", desc=True)

            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting posts: {e}")
            return []

    def get_post_by_id(self, post_id: int) -> Dict[str, Any]:
        """
        Get a specific post by ID

        Args:
            post_id: The post ID to retrieve

        Returns:
            Post dictionary or empty dict if not found
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("id", post_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return {}

        except Exception as e:
            logger.error(f"Error getting post by ID: {e}")
            return {}

    def update_post(self, post_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a post in Supabase

        Args:
            post_id: The post ID to update
            update_data: Dictionary containing fields to update

        Returns:
            Updated post dictionary or empty dict on error
        """
        try:
            if not update_data:
                return {}

            # Clean the update data
            clean_data = {}
            for key, value in update_data.items():
                if value is not None:
                    # Convert lists to JSON strings if needed
                    if isinstance(value, list):
                        clean_data[key] = (
                            json.dumps(value)
                            if key in ["smart_tags", "media_urls"]
                            else value
                        )
                    else:
                        clean_data[key] = value

            response = (
                self.client.table(self.table_name)
                .update(clean_data)
                .eq("id", post_id)
                .execute()
            )

            if response.data and len(response.data) > 0:
                return response.data[0]
            return {}

        except Exception as e:
            logger.error(f"Error updating post: {e}")
            return {}

    def delete_post(self, post_id: int) -> bool:
        """
        Delete a post from Supabase

        Args:
            post_id: The post ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            response = (
                self.client.table(self.table_name).delete().eq("id", post_id).execute()
            )
            return len(response.data) > 0 if response.data else False

        except Exception as e:
            logger.error(f"Error deleting post: {e}")
            return False

    def get_all_posts(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get all posts from Supabase

        Args:
            include_deleted: Whether to include deleted posts (not implemented in Supabase schema)

        Returns:
            List of all post dictionaries
        """
        try:
            query = (
                self.client.table(self.table_name)
                .select("*")
                .order("created_at", desc=True)
            )
            response = query.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting all posts: {e}")
            return []

    def insert_post_v2(self, post_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alternative insert method for compatibility

        Args:
            post_data: Dictionary containing post data

        Returns:
            Dict containing the inserted post data, or empty dict on error
        """
        return self.insert_post(post_data)

    def search_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search posts by title or content

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching post dictionaries
        """
        try:
            # Use Supabase's text search functionality
            response = (
                self.client.table(self.table_name)
                .select("*")
                .or_(f"title.ilike.%{query}%,content.ilike.%{query}%")
                .limit(limit)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error searching posts: {e}")
            return []

    def advanced_search(
        self,
        query: Optional[str] = None,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        author: Optional[str] = None,
        min_value_score: Optional[int] = None,
        max_value_score: Optional[int] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Advanced search with multiple filters

        Args:
            query: Text search query
            platform: Filter by platform
            category: Filter by category
            author: Filter by author
            min_value_score: Minimum value score
            max_value_score: Maximum value score
            date_from: Start date (ISO format)
            date_to: End date (ISO format)
            tags: List of tags to search for
            limit: Maximum number of results

        Returns:
            List of matching post dictionaries
        """
        try:
            # Start with base query
            query_builder = self.client.table(self.table_name).select("*")

            # Apply text search
            if query:
                query_builder = query_builder.or_(
                    f"title.ilike.%{query}%,content.ilike.%{query}%,ai_summary.ilike.%{query}%"
                )

            # Apply filters
            if platform:
                query_builder = query_builder.eq("platform", platform)

            if category:
                query_builder = query_builder.eq("category", category)

            if author:
                query_builder = query_builder.or_(
                    f"author.ilike.%{author}%,author_handle.ilike.%{author}%"
                )

            if min_value_score is not None:
                query_builder = query_builder.gte("value_score", min_value_score)

            if max_value_score is not None:
                query_builder = query_builder.lte("value_score", max_value_score)

            if date_from:
                query_builder = query_builder.gte("created_at", date_from)

            if date_to:
                query_builder = query_builder.lte("created_at", date_to)

            if tags:
                # Search in smart_tags field (assuming it's JSON)
                for tag in tags:
                    query_builder = query_builder.ilike("smart_tags", f"%{tag}%")

            # Apply ordering and limit
            query_builder = query_builder.order("created_at", desc=True).limit(limit)

            response = query_builder.execute()
            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error in advanced search: {e}")
            return []

    def get_search_suggestions(
        self, partial_query: str, limit: int = 10
    ) -> Dict[str, List[str]]:
        """
        Get search suggestions based on partial query

        Args:
            partial_query: Partial search query
            limit: Maximum suggestions per category

        Returns:
            Dictionary with suggestion categories
        """
        try:
            suggestions = {
                "titles": [],
                "authors": [],
                "categories": [],
                "platforms": [],
            }

            # Get title suggestions
            title_response = (
                self.client.table(self.table_name)
                .select("title")
                .ilike("title", f"%{partial_query}%")
                .limit(limit)
                .execute()
            )

            if title_response.data:
                suggestions["titles"] = [
                    item["title"] for item in title_response.data if item["title"]
                ]

            # Get author suggestions
            author_response = (
                self.client.table(self.table_name)
                .select("author")
                .ilike("author", f"%{partial_query}%")
                .limit(limit)
                .execute()
            )

            if author_response.data:
                suggestions["authors"] = list(
                    set(
                        [
                            item["author"]
                            for item in author_response.data
                            if item["author"]
                        ]
                    )
                )

            # Category column dropped; skip category suggestions
            suggestions["categories"] = []

            # Get platform suggestions
            platform_response = (
                self.client.table(self.table_name)
                .select("platform")
                .ilike("platform", f"%{partial_query}%")
                .limit(limit)
                .execute()
            )

            if platform_response.data:
                suggestions["platforms"] = list(
                    set(
                        [
                            item["platform"]
                            for item in platform_response.data
                            if item["platform"]
                        ]
                    )
                )

            return suggestions

        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return {"titles": [], "authors": [], "categories": [], "platforms": []}

    def get_posts_by_category(
        self, category: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get posts filtered by category

        Args:
            category: Category to filter by
            limit: Maximum number of posts to return

        Returns:
            List of post dictionaries in the specified category
        """
        # Category column dropped; keep method for compatibility returning empty
        return []

    def get_top_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top posts ordered by value score

        Args:
            limit: Maximum number of posts to return

        Returns:
            List of top-rated post dictionaries
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .order("value_score", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(f"Error getting top posts: {e}")
            return []
