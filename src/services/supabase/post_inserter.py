"""
Supabase Post Inserter for BEYONDLINES
Handles post insertion and data mapping
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class PostInserter:
    """Handles post insertion and data mapping"""

    def __init__(self, client, duplicate_checker):
        """Initialize with Supabase client and duplicate checker"""
        self.client = client
        self.duplicate_checker = duplicate_checker
        self.table_name = "posts"
        self.supports_collected_at = True

        # Detect whether the Supabase 'posts' table already has collected_at
        try:
            self.client.table(self.table_name).select("collected_at").limit(1).execute()
        except Exception as exc:  # pragma: no cover - depends on Supabase schema
            if "collected_at" in str(exc):
                logger.warning(
                    "Supabase table 'posts' missing collected_at column; falling back without it."
                )
                self.supports_collected_at = False
            else:
                logger.debug(f"Supabase schema probe failed (ignored): {exc}")

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
                return {}

            # FILTER OUT FIELDS THAT DON'T EXIST IN SUPABASE SCHEMA
            # Based on actual Supabase schema - only keep fields that exist
            supabase_schema_fields = {
                # Core identification
                "id",
                "post_id",
                "title",
                "content",
                "url",
                "platform",
                "author",
                "author_handle",
                "created_at",
                "post_type",
                # Content
                "media_urls",
                "hashtags",
                "mentions",
                # Analysis
                "ai_summary",
                "topic",
                "content_type",
                "analyzed_at",
                "sentiment",
                "key_concepts",
                "tags",
                "action_items",
                "analysis_model",
                "value_score",
                "quality_score",
                "language",
                "time_sensitive",
                "urgency_score",
                "relevance_window",
                "time_sensitive_reasons",
                "analysis_confidence",
                "analysis_depth",
                "needs_deep_analysis",
                "persona_fit_scores",
                "persona_fit_reasons",
                "best_persona_key",
                "best_persona_score",
                "best_persona_reasons",
                "profile_matches",
                # Embedding
                "embedding",
                "embedding_model",
                # Rewrite-related fields (kept for pipeline compatibility)
                "rewrite_score",
                "rewrite_readiness",
                "rewrite_reasons",
                "rewrite_risks",
                # Status
                "is_saved",
                "updated_at",
            }

            if self.supports_collected_at:
                supabase_schema_fields.add("collected_at")

            # Create clean post data with ONLY fields that exist in Supabase schema
            clean_post_data = {
                k: v for k, v in post_data.items() if k in supabase_schema_fields
            }

            filtered_count = len(post_data) - len(clean_post_data)
            logger.debug(
                f"🧹 Schema filter: kept {len(clean_post_data)}/{len(post_data)} fields"
            )
            if filtered_count > 0:
                filtered_fields = set(post_data.keys()) - supabase_schema_fields
                logger.debug(f"   Removed fields: {sorted(filtered_fields)}")

            # Ensure we have required fields
            if not clean_post_data.get("title") and not clean_post_data.get("content"):
                return {}

            url = clean_post_data.get("url", "")

            # Generate post_id using deterministic ID generator (NO random UUIDs)
            post_id = clean_post_data.get("post_id")
            if not post_id:
                from src.infrastructure.database.storage.id_generator import PostIDGenerator

                post_id = PostIDGenerator.generate_post_id(clean_post_data)
            else:
                # Normalize existing post_id
                from src.infrastructure.database.storage.id_generator import PostIDGenerator

                platform = clean_post_data.get("platform", "")
                post_id = PostIDGenerator._normalize_id(str(post_id), platform)

            # Check for duplicates before inserting (skip for same-ID upserts)
            if not clean_post_data.get("post_id"):
                content = clean_post_data.get("content", "")
                author = clean_post_data.get("author", "")
                platform = clean_post_data.get("platform", "")
                url = clean_post_data.get("url", "")

                if self.duplicate_checker.check_duplicate_post(
                    content, author, platform, url=url
                ):
                    logger.info(f"Duplicate detected: {author} - {content[:50]}...")
                    return {}  # Return empty dict to indicate duplicate

            # Map fields to match the actual Supabase table schema
            mapped_data = self._map_post_data(clean_post_data, post_id)
            conflict_target = self._determine_conflict_target(mapped_data)
            # Final guard: drop deprecated fields if present
            if "content_quality_score" in mapped_data:
                mapped_data.pop("content_quality_score", None)
            # Ensure JSON-serializable values (convert datetimes to isoformat)
            for k, v in list(mapped_data.items()):
                if isinstance(v, datetime):
                    mapped_data[k] = v.isoformat()

            # Make an UPSERT on post_id and update key fields to backfill missing data
            # Protected with circuit breaker
            from src.shared.utils.circuit_breaker_wrapper import get_circuit_breaker

            supabase_breaker = get_circuit_breaker(
                "supabase", failure_threshold=5, recovery_timeout=60.0
            )

            @supabase_breaker.protect
            def _execute_upsert():
                """Execute Supabase upsert with circuit breaker protection and retry logic"""
                import time

                attempts = 0
                max_attempts = 3
                last_error = None
                
                # P0-3: Exponential backoff retry logic
                while attempts < max_attempts:
                    try:
                        # P1-3: Explicit existence check before upsert (for better error handling)
                        # Note: upsert() is atomic, but we check first for better logging
                        post_id = mapped_data.get("post_id")
                        platform = mapped_data.get("platform")
                        url = mapped_data.get("url")
                        
                        existing = None
                        if post_id and platform:
                            try:
                                existing = (
                                    self.client.table(self.table_name)
                                    .select("post_id")
                                    .eq("post_id", post_id)
                                    .eq("platform", platform)
                                    .limit(1)
                                    .execute()
                                )
                            except Exception:
                                pass  # Ignore check errors, proceed with upsert
                        
                        # Upsert and update important analysis fields on conflict
                        # P0-3: Idempotency key = post_id + platform (already in conflict_target)
                        response = (
                            self.client.table(self.table_name)
                            .upsert(
                                mapped_data, on_conflict=conflict_target or "post_id"
                            )
                            .execute()
                        )
                        
                        # Log whether this was an insert or update
                        if existing and existing.data:
                            logger.debug(f"✅ Updated existing post: {post_id} ({platform})")
                        else:
                            logger.debug(f"✅ Inserted new post: {post_id} ({platform})")
                        
                        return response
                    except Exception as e:
                        msg = str(e)
                        if self._is_duplicate_supabase_error(msg):
                            logger.debug(
                                "Supabase duplicate inside upsert; treating as success"
                            )
                            return {"success": True}
                        last_error = e
                        
                        # P0-3: Exponential backoff for transient errors
                        if any(code in msg for code in [" 520 ", " 502 ", " 503 ", " 504 "]):
                            wait = (1.5 ** attempts) * 1.0  # Exponential: 1.0s, 1.5s, 2.25s
                            logger.warning(
                                f"Supabase transient error ({msg.strip()}), retrying in {wait:.2f}s... (attempt {attempts + 1}/{max_attempts})"
                            )
                            time.sleep(wait)
                            attempts += 1
                            continue
                        
                        # P0-3: For non-transient errors, log and fail
                        logger.error(f"Supabase upsert failed (non-retryable): {msg[:200]}")
                        raise
                
                # P0-3: All retries exhausted
                if last_error:
                    logger.error(f"Supabase upsert failed after {max_attempts} attempts")
                    raise last_error
                raise Exception("Unexpected: no error but upsert failed")

            response = _execute_upsert()

            # Dict responses indicate duplicate/short-circuit success
            if isinstance(response, dict):
                return response

            # Handle the response
            if response and response.data:
                return (
                    response.data[0]
                    if isinstance(response.data, list)
                    else response.data
                )

            return {"success": True}

        except Exception as e:
            # Silent fail - local DB is primary, Supabase is optional sync
            error_msg = str(e)
            # Treat duplicate key errors as success (idempotent insert) - don't log as error
            if self._is_duplicate_supabase_error(error_msg):
                logger.debug("Supabase duplicate on insert; treating as success")
                return {"success": True}
            if "row-level security" not in error_msg.lower():
                # Only log non-RLS errors (RLS means not configured, expected)
                logger.warning(f"Supabase insert failed: {error_msg[:100]}")
            return {}

    def _determine_conflict_target(self, mapped_data: Dict[str, Any]) -> str:
        """
        Choose the most reliable conflict target for Supabase upserts.
        Prefer unique URL constraint when present so legacy post_id formats get updated.
        """
        url = (mapped_data.get("url") or "").strip()
        if url:
            return "url"
        platform = (mapped_data.get("platform") or "").strip()
        post_id = (mapped_data.get("post_id") or "").strip()
        if platform and post_id:
            return "platform,post_id"
        if post_id:
            return "post_id"
        return "id"

    def _map_post_data(self, post_data: Dict[str, Any], post_id: str) -> Dict[str, Any]:
        """Map post data to Supabase schema"""

        # Helper to convert list to PostgreSQL array format
        # Supabase Python client accepts Python lists directly - no need for string conversion
        def to_pg_array(value):
            if not value or value == []:
                return []  # Return empty array instead of None for array fields
            if isinstance(value, list):
                # Return list directly - Supabase client will convert to PostgreSQL array
                return [str(item) for item in value if item]  # Filter out None/empty items
            return value

        # Helper to normalize timestamps to ISO format
        def normalize_timestamp(value, fallback=None):
            """Normalize timestamp to ISO format string"""
            if not value:
                return fallback or datetime.now().isoformat()

            # If already a datetime object, convert to ISO
            if isinstance(value, datetime):
                return value.isoformat()

            # If it's a string, try to parse it
            if isinstance(value, str):
                # Skip if it looks like text content (not a timestamp)
                if len(value) > 50 or not any(c.isdigit() for c in value[:10]):
                    return fallback or datetime.now().isoformat()

                # Try various timestamp formats
                formats = [
                    "%Y-%m-%dT%H:%M:%S.%f",  # ISO with microseconds
                    "%Y-%m-%dT%H:%M:%S",  # ISO without microseconds
                    "%Y-%m-%d %H:%M:%S",  # Space-separated
                    "%Y-%m-%d %H:%M:%S.%f",  # Space-separated with microseconds
                    "%Y-%m-%d",  # Date only
                ]

                for fmt in formats:
                    try:
                        dt = datetime.strptime(value[: len(fmt) + 10], fmt)
                        return dt.isoformat()
                    except (ValueError, TypeError):
                        continue

                # If all parsing fails, use fallback
                return fallback or datetime.now().isoformat()

            return fallback or datetime.now().isoformat()

        # Extract author_handle from various possible fields
        author_handle = (
            post_data.get("username")
            or post_data.get("author_handle")
            or post_data.get("author", "").split()[
                0
            ]  # Fallback: use first word of author
        )

        # Normalize created_at - try multiple sources
        created_at_raw = (
            post_data.get("created_at")
            or post_data.get("created_timestamp")
            or post_data.get("saved_at")
        )
        created_at = normalize_timestamp(created_at_raw)

        # Helper function to normalize boolean values
        def normalize_boolean(value, default=True):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                value_stripped = value.strip()
                # Check if it looks like JSON (array or object) - invalid for boolean
                if value_stripped.startswith(("{", "[")):
                    logger.warning(
                        f"Invalid boolean value appears to be JSON: {value_stripped[:50]}..., using default {default}"
                    )
                    return default
                value_lower = value_stripped.lower()
                if value_lower in ("true", "1", "yes", "on", "t"):
                    return True
                elif value_lower in ("false", "0", "no", "off", "f", ""):
                    return False
                # Unknown string value - use default
                logger.warning(
                    f"Unknown boolean string value: {value_stripped[:50]}..., using default {default}"
                )
                return default
            # Unknown type - use default
            logger.warning(
                f"Unknown boolean type: {type(value)}, using default {default}"
            )
            return default

        # ESSENTIAL FIELDS ONLY - no more bloated schema issues!
        # Get title - ensure it's not truncated content
        title = post_data.get("title") or ""
        # If title looks like truncated content (ends with ... or is very long), try to extract a proper title
        if title and (title.endswith("...") or title.endswith("…") or len(title) > 200):
            # Title might be corrupted - try to get a better one from content
            content = post_data.get("content") or ""
            if content:
                # Use first sentence or first 100 chars as title
                first_sentence = content.split(".")[0].strip()
                if first_sentence and len(first_sentence) <= 200:
                    title = first_sentence
                else:
                    title = content[:100].strip()

        mapped_data = {
            "post_id": post_id,
            "title": title,  # Add title field
            "content": post_data.get("content") or "",
            "url": post_data.get("url") or "",
            "platform": post_data.get("platform") or "",
            "author": post_data.get("author") or "",
            "author_handle": author_handle,
            "created_at": created_at,
            "language": post_data.get("language", "en"),
            "is_saved": normalize_boolean(post_data.get("is_saved"), True),
        }

        # ALWAYS set collected_at - this is critical for sorting/filtering
        if getattr(self, "supports_collected_at", True):
            # If collected_at is missing or None, ALWAYS set it to now
            collected_at = post_data.get("collected_at")
            if not collected_at:
                mapped_data["collected_at"] = datetime.now(timezone.utc).isoformat()
            else:
                mapped_data["collected_at"] = normalize_timestamp(
                    collected_at,
                    fallback=datetime.now(timezone.utc).isoformat(),
                )

        # Add analysis fields that exist in Supabase schema
        analysis_fields_mapping = {
            "ai_summary": "ai_summary",
            "value_score": "value_score",
            "quality_score": "quality_score",
            "sentiment": "sentiment",
            "key_concepts": "key_concepts",
            "tags": "tags",
            "action_items": "action_items",
            "category": "category",
            # Note: fit_categories column not yet in Supabase schema.
            # To enable: Add TEXT[] column 'fit_categories' to posts table via migration.
            # "fit_categories": "fit_categories",
            "analysis_model": "analysis_model",
            "embedding": "embedding",
            "embedding_model": "embedding_model",
            "analyzed_at": "analyzed_at",
            "time_sensitive": "time_sensitive",
            "urgency_score": "urgency_score",
            "relevance_window": "relevance_window",
            "time_sensitive_reasons": "time_sensitive_reasons",
            # Rewrite-focused fields
            "rewrite_score": "rewrite_score",
            "rewrite_readiness": "rewrite_readiness",
            "rewrite_reasons": "rewrite_reasons",
            "rewrite_risks": "rewrite_risks",
            "analysis_confidence": "analysis_confidence",
            "analysis_depth": "analysis_depth",
            "needs_deep_analysis": "needs_deep_analysis",
            # Persona fit fields
            "persona_fit_scores": "persona_fit_scores",
            "persona_fit_reasons": "persona_fit_reasons",
            "profile_matches": "profile_matches",
            "best_persona_key": "best_persona_key",
            "best_persona_score": "best_persona_score",
            "best_persona_reasons": "best_persona_reasons",
        }

        for source_field, target_field in analysis_fields_mapping.items():
            value = post_data.get(source_field)
            
            # Debug logging for action_items
            if source_field == "action_items":
                logger.debug(f"🔍 Mapping action_items: value={value}, type={type(value)}")

            # Apply defaults for important fields that should never be None
            if value is None:
                if target_field in [
                    "rewrite_score",
                    "analysis_confidence",
                    "best_persona_score",
                ]:
                    value = 0.0
                elif target_field in ["rewrite_readiness", "analysis_depth"]:
                    value = "fast"
                elif target_field in ["needs_deep_analysis"]:
                    value = False
                elif target_field in [
                    "rewrite_reasons",
                    "rewrite_risks",
                    "best_persona_reasons",
                ]:
                    value = []
                elif target_field in ["persona_fit_scores", "persona_fit_reasons"]:
                    value = {}
                elif target_field in ["best_persona_key"]:
                    value = None  # Keep None for optional fields
                elif target_field in ["action_items", "key_concepts", "tags", "rewrite_reasons", "rewrite_risks", "best_persona_reasons"]:
                    # Array fields should default to empty array, not None
                    value = []
                else:
                    # Skip other None values
                    continue

            # Normalize timestamp fields
            if target_field in ["analyzed_at"]:
                mapped_data[target_field] = normalize_timestamp(value)
            # Convert lists to PG arrays for array fields
            elif target_field in [
                "key_concepts",
                "tags",
                "action_items",
                "rewrite_reasons",
                "rewrite_risks",
                "best_persona_reasons",
                "time_sensitive_reasons",
            ]:
                # Handle JSON strings - parse them first
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            mapped_data[target_field] = to_pg_array(parsed)
                        else:
                            # Not a list after parsing - use empty array
                            mapped_data[target_field] = to_pg_array([])
                    except (json.JSONDecodeError, ValueError, TypeError):
                        # Invalid JSON - use empty array
                        logger.warning(
                            f"Invalid JSON for {target_field} in post {post_data.get('post_id')}: {value[:50]}..., using empty array"
                        )
                        mapped_data[target_field] = to_pg_array([])
                elif isinstance(value, list):
                    mapped_value = to_pg_array(value)
                    mapped_data[target_field] = mapped_value
                    # Debug logging for action_items
                    if target_field == "action_items":
                        logger.debug(f"🔍 action_items mapped: {mapped_value}, type={type(mapped_value)}")
                elif isinstance(value, (int, float)):
                    # Single number instead of list - convert to list with that number
                    logger.warning(
                        f"Number instead of list for {target_field} in post {post_data.get('post_id')}, using empty array"
                    )
                    mapped_data[target_field] = to_pg_array([])
                elif value is None:
                    # For array fields, use empty array instead of None
                    mapped_data[target_field] = []
                else:
                    # Unknown type - use empty array
                    logger.warning(
                        f"Unexpected type for {target_field} in post {post_data.get('post_id')}: {type(value)}, using empty array"
                    )
                    mapped_data[target_field] = to_pg_array([])
            # Convert dicts to JSONB for JSONB fields
            elif target_field in [
                "persona_fit_scores",
                "persona_fit_reasons",
                "profile_matches",
            ]:
                # Handle JSON strings - parse them first
                if isinstance(value, str):
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, dict):
                            mapped_data[target_field] = parsed
                        elif isinstance(parsed, list):
                            # List instead of dict - convert to empty dict (can't convert list to dict meaningfully)
                            logger.warning(
                                f"List instead of dict for {target_field} in post {post_data.get('post_id')}, using empty dict"
                            )
                            mapped_data[target_field] = {}
                        else:
                            # Not a dict after parsing - use empty dict
                            mapped_data[target_field] = {}
                    except (json.JSONDecodeError, ValueError, TypeError):
                        # Invalid JSON - use empty dict
                        logger.warning(
                            f"Invalid JSON for {target_field} in post {post_data.get('post_id')}: {value[:50]}..., using empty dict"
                        )
                        mapped_data[target_field] = {}
                elif isinstance(value, dict):
                    mapped_data[target_field] = value
                elif isinstance(value, list):
                    # List instead of dict - convert to empty dict (can't convert list to dict meaningfully)
                    logger.warning(
                        f"List instead of dict for {target_field} in post {post_data.get('post_id')}, using empty dict"
                    )
                    mapped_data[target_field] = {}
                elif value is None:
                    mapped_data[target_field] = {}
                else:
                    # Unknown type - use empty dict
                    logger.warning(
                        f"Unexpected type for {target_field} in post {post_data.get('post_id')}: {type(value)}, using empty dict"
                    )
                    mapped_data[target_field] = {}
            # Coerce boolean fields to proper booleans
            elif target_field in ["is_saved", "time_sensitive", "needs_deep_analysis"]:
                # Apply defaults based on field
                default = True if target_field == "is_saved" else False
                try:
                    mapped_data[target_field] = normalize_boolean(value, default)
                except Exception as e:
                    logger.warning(
                        f"Failed to normalize boolean {target_field} for post {post_data.get('post_id')}: {e}, using default {default}"
                    )
                    mapped_data[target_field] = default
            # Coerce numeric fields to floats
            elif target_field in [
                "rewrite_score",
                "analysis_confidence",
                "best_persona_score",
                "value_score",
                "quality_score",
                "urgency_score",
            ]:
                try:
                    mapped_data[target_field] = (
                        float(value) if value is not None else 0.0
                    )
                except (ValueError, TypeError):
                    mapped_data[target_field] = 0.0
            # Validate embedding vector format (must be a valid Postgres vector)
            elif target_field == "embedding":
                if value is None or value == "":
                    # Skip null/empty embeddings
                    continue
                elif isinstance(value, str):
                    # Check if it's a valid vector format (should start with "[" and be parseable as JSON array)
                    value_stripped = value.strip()
                    if not value_stripped.startswith("["):
                        # Invalid vector format - skip it to avoid Postgres errors
                        logger.warning(
                            f"Invalid embedding format for post {post_data.get('post_id')}: does not start with '['"
                        )
                        continue
                    try:
                        # Try to parse as JSON to validate
                        parsed = json.loads(value_stripped)
                        if isinstance(parsed, list) and all(
                            isinstance(x, (int, float)) for x in parsed
                        ):
                            mapped_data[target_field] = value_stripped
                        else:
                            logger.warning(
                                f"Invalid embedding format for post {post_data.get('post_id')}: not a valid array of numbers"
                            )
                            continue
                    except (json.JSONDecodeError, ValueError, TypeError):
                        logger.warning(
                            f"Invalid embedding format for post {post_data.get('post_id')}: not valid JSON"
                        )
                        continue
                elif isinstance(value, list):
                    # Convert list to JSON string format
                    try:
                        mapped_data[target_field] = json.dumps(value)
                    except (TypeError, ValueError):
                        logger.warning(
                            f"Invalid embedding list for post {post_data.get('post_id')}: cannot serialize"
                        )
                        continue
                else:
                    # Unknown type - skip it
                    logger.warning(
                        f"Invalid embedding type for post {post_data.get('post_id')}: {type(value)}"
                    )
                    continue
            # Skip empty strings for non-required fields
            elif value == "" and target_field not in [
                "rewrite_readiness",
                "analysis_depth",
                "best_persona_key",
            ]:
                continue
            else:
                mapped_data[target_field] = value

        return mapped_data

    @staticmethod
    def _is_duplicate_supabase_error(message: str) -> bool:
        if not message:
            return False
        msg = message.lower()
        return "23505" in msg or "duplicate key value" in msg or "posts_url_key" in msg

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
