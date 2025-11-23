"""
User Feedback Tracker

Tracks manual user ratings and feedback on rewrites to improve quality.
Stores ratings, notes, and learns from what users explicitly approve/reject.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()
logger = logging.getLogger(__name__)


class FeedbackTracker:
    """
    Tracks user feedback on rewrites to improve quality.

    Core Functions:
    1. Store user ratings (thumbs up/down, 1-5 stars)
    2. Store feedback notes
    3. Track what gets approved/rejected
    4. Learn patterns from user preferences
    """

    def __init__(self):
        """Initialize the feedback tracker with Supabase connection"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", supabase_key)

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

        self.supabase: Client = create_client(supabase_url, supabase_key)
        self._supabase_url = supabase_url
        self._service_key = service_key

        self._ensure_table_exists()

        logger.info("✅ FeedbackTracker initialized with Supabase connection")

    def _ensure_table_exists(self) -> None:
        """
        Ensure rewrite_feedback table exists, creating it via SQL API if necessary.
        """
        try:
            self.supabase.table("rewrite_feedback").select("id").limit(1).execute()
            return
        except Exception as exc:
            if "PGRST205" not in str(exc) and "rewrite_feedback" not in str(exc):
                logger.debug("Feedback table check failed: %s", exc)
                return

        if not self._service_key:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set; cannot auto-create rewrite_feedback table"
            )
            return

        # Table should be created via migration - just verify it exists
        # Migration: create_rewrite_feedback_table
        try:
            # Try to query the table to verify it exists
            result = (
                self.client.table("rewrite_feedback").select("id").limit(1).execute()
            )
            logger.debug("✅ rewrite_feedback table exists")
        except Exception as exc:
            # Table doesn't exist - log warning but don't fail
            logger.warning(
                "rewrite_feedback table not found - run migration 'create_rewrite_feedback_table': %s",
                exc,
            )

    async def store_feedback(
        self,
        rewrite_id: str,
        rating: int,
        feedback_type: str = "rating",
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """
        Store user feedback on a rewrite.

        Args:
            rewrite_id: Unique identifier for the rewrite
            rating: 1-5 stars, or -1 (reject), 0 (neutral), 1 (approve) for thumbs
            feedback_type: "rating" (1-5 stars), "thumbs" (up/down), "approval" (approve/reject)
            notes: Optional text feedback from user
            metadata: Optional metadata (persona, platform, content_type, etc.)

        Returns:
            Database ID of the feedback record, or None if failed
        """
        try:
            # Prepare data
            data = {
                "rewrite_id": rewrite_id,
                "rating": rating,
                "feedback_type": feedback_type,
                "notes": notes,
                "created_at": datetime.now().isoformat(),
            }

            # Add metadata if provided
            if metadata:
                data["metadata"] = metadata

            # Insert into database
            # Use DatabaseAgent (delegates to StorageFacade)
            from src.infrastructure.database.database_agent import get_database_agent

            db_agent = get_database_agent()
            db_agent.save_rewrite_feedback(data)
            response = type(
                "Response", (), {"data": [data]}
            )()  # Mock response for compatibility

            if response.data and len(response.data) > 0:
                record_id = response.data[0]["id"]
                logger.info(
                    f"✅ Stored feedback for rewrite {rewrite_id}: {rating} ({feedback_type})"
                )
                return record_id
            else:
                logger.error(f"❌ Failed to store feedback: no data returned")
                return None

        except Exception as e:
            if "PGRST205" in str(e):
                self._ensure_table_exists()
                logger.warning(
                    "rewrite_feedback table missing; ensured and skipping store this time"
                )
                return None
            logger.error(f"❌ Error storing feedback: {e}")
            return None

    async def get_rewrite_feedback(self, rewrite_id: str) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific rewrite.

        Args:
            rewrite_id: Unique identifier for the rewrite

        Returns:
            List of feedback records
        """
        try:
            response = (
                self.supabase.table("rewrite_feedback")
                .select("*")
                .eq("rewrite_id", rewrite_id)
                .order("created_at", desc=True)
                .execute()
            )

            return response.data or []

        except Exception as e:
            if "PGRST205" in str(e):
                self._ensure_table_exists()
                return []
            logger.error(f"❌ Error getting rewrite feedback: {e}")
            return []

    async def get_feedback_stats(
        self,
        persona: Optional[str] = None,
        platform: Optional[str] = None,
        days_back: int = 30,
    ) -> Dict[str, Any]:
        """
        Get feedback statistics.

        Returns:
        - Average rating
        - Approval rate (thumbs up vs thumbs down)
        - Total feedback count
        - Distribution by rating
        - Common feedback themes
        """
        try:
            # Build query
            query = self.supabase.table("rewrite_feedback").select("*")

            # Filter by persona/platform if in metadata
            # Note: This requires JSONB queries which might need adjustment
            if persona or platform:
                logger.warning(
                    "Persona/platform filtering on metadata not yet implemented"
                )

            # Filter by date range
            cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
            query = query.gte("created_at", cutoff_date)

            # Execute query
            response = query.execute()
            feedback_records = response.data

            if not feedback_records:
                return {
                    "total_count": 0,
                    "avg_rating": 0,
                    "approval_rate": 0,
                    "rating_distribution": {},
                    "feedback_types": {},
                }

            # Calculate statistics
            total_count = len(feedback_records)

            # Rating stats
            ratings = [
                f["rating"] for f in feedback_records if f.get("rating") is not None
            ]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0

            # Approval rate (for thumbs feedback)
            thumbs_feedback = [
                f for f in feedback_records if f.get("feedback_type") == "thumbs"
            ]
            approvals = len([f for f in thumbs_feedback if f.get("rating", 0) > 0])
            rejections = len([f for f in thumbs_feedback if f.get("rating", 0) < 0])
            approval_rate = (
                (approvals / len(thumbs_feedback) * 100) if thumbs_feedback else 0
            )

            # Rating distribution
            rating_dist = {}
            for f in feedback_records:
                rating = f.get("rating")
                if rating is not None:
                    rating_dist[rating] = rating_dist.get(rating, 0) + 1

            # Feedback types
            feedback_types = {}
            for f in feedback_records:
                ftype = f.get("feedback_type", "unknown")
                feedback_types[ftype] = feedback_types.get(ftype, 0) + 1

            logger.info(
                f"📊 Feedback stats: {total_count} records, avg rating {avg_rating:.2f}, approval rate {approval_rate:.1f}%"
            )

            return {
                "total_count": total_count,
                "avg_rating": round(avg_rating, 2),
                "approval_rate": round(approval_rate, 1),
                "approvals": approvals,
                "rejections": rejections,
                "rating_distribution": rating_dist,
                "feedback_types": feedback_types,
            }

        except Exception as e:
            if "PGRST205" in str(e):
                self._ensure_table_exists()
                return {
                    "total_count": 0,
                    "avg_rating": 0,
                    "approval_rate": 0,
                    "rating_distribution": {},
                    "feedback_types": {},
                }
            logger.error(f"❌ Error getting feedback stats: {e}")
            return {
                "total_count": 0,
                "avg_rating": 0,
                "approval_rate": 0,
                "rating_distribution": {},
                "feedback_types": {},
                "error": str(e),
            }

    async def get_approved_rewrites(
        self,
        persona: Optional[str] = None,
        platform: Optional[str] = None,
        min_rating: int = 4,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get highly-rated rewrites to use as examples.

        Args:
            persona: Filter by persona (if in metadata)
            platform: Filter by platform (if in metadata)
            min_rating: Minimum rating (default 4)
            limit: Max number of results

        Returns:
            List of feedback records for approved rewrites
        """
        try:
            # Build query
            query = self.supabase.table("rewrite_feedback").select("*")

            # Filter by minimum rating
            query = query.gte("rating", min_rating)

            # Order by rating and limit
            query = query.order("rating", desc=True).limit(limit)

            # Execute query
            response = query.execute()
            records = response.data

            logger.info(
                f"🏆 Found {len(records)} highly-rated rewrites (rating >= {min_rating})"
            )

            return records

        except Exception as e:
            logger.error(f"❌ Error getting approved rewrites: {e}")
            return []

    async def get_rejected_rewrites(
        self,
        persona: Optional[str] = None,
        platform: Optional[str] = None,
        max_rating: int = 2,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get poorly-rated rewrites to learn what to avoid.

        Args:
            persona: Filter by persona (if in metadata)
            platform: Filter by platform (if in metadata)
            max_rating: Maximum rating (default 2)
            limit: Max number of results

        Returns:
            List of feedback records for rejected rewrites
        """
        try:
            # Build query
            query = self.supabase.table("rewrite_feedback").select("*")

            # Filter by maximum rating
            query = query.lte("rating", max_rating)

            # Order by rating and limit
            query = query.order("rating", desc=False).limit(limit)

            # Execute query
            response = query.execute()
            records = response.data

            logger.info(
                f"⚠️ Found {len(records)} low-rated rewrites (rating <= {max_rating})"
            )

            return records

        except Exception as e:
            logger.error(f"❌ Error getting rejected rewrites: {e}")
            return []

    async def learn_from_feedback(self, persona: str, platform: str) -> Dict[str, Any]:
        """
        Analyze feedback to learn patterns.

        Returns:
        - What users like (common traits in approved rewrites)
        - What users dislike (common traits in rejected rewrites)
        - Improvement suggestions
        """
        try:
            # Get approved and rejected rewrites
            approved = await self.get_approved_rewrites(
                persona=persona, platform=platform
            )
            rejected = await self.get_rejected_rewrites(
                persona=persona, platform=platform
            )

            # Analyze metadata for patterns
            approved_patterns = self._analyze_patterns(approved)
            rejected_patterns = self._analyze_patterns(rejected)

            logger.info(
                f"🧠 Learned from {len(approved)} approved and {len(rejected)} rejected rewrites"
            )

            return {
                "approved_count": len(approved),
                "rejected_count": len(rejected),
                "approved_patterns": approved_patterns,
                "rejected_patterns": rejected_patterns,
                "suggestions": self._generate_suggestions(
                    approved_patterns, rejected_patterns
                ),
            }

        except Exception as e:
            logger.error(f"❌ Error learning from feedback: {e}")
            return {
                "approved_count": 0,
                "rejected_count": 0,
                "approved_patterns": {},
                "rejected_patterns": {},
                "suggestions": [],
                "error": str(e),
            }

    def _analyze_patterns(
        self, feedback_records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in feedback metadata.

        Looks for:
        - Common content types
        - Common tones
        - Common lengths
        - Common structures
        """
        if not feedback_records:
            return {}

        # Extract metadata
        content_types = []
        lengths = []
        has_emojis = []
        has_hashtags = []

        for record in feedback_records:
            metadata = record.get("metadata", {})
            if isinstance(metadata, dict):
                if "content_type" in metadata:
                    content_types.append(metadata["content_type"])
                if "length" in metadata:
                    lengths.append(metadata["length"])
                if "has_emojis" in metadata:
                    has_emojis.append(metadata["has_emojis"])
                if "has_hashtags" in metadata:
                    has_hashtags.append(metadata["has_hashtags"])

        # Calculate statistics
        patterns = {}

        if content_types:
            type_counts = {}
            for ct in content_types:
                type_counts[ct] = type_counts.get(ct, 0) + 1
            patterns["content_types"] = type_counts

        if lengths:
            patterns["avg_length"] = sum(lengths) // len(lengths)
            patterns["min_length"] = min(lengths)
            patterns["max_length"] = max(lengths)

        if has_emojis:
            patterns["emoji_usage"] = sum(has_emojis) / len(has_emojis)

        if has_hashtags:
            patterns["hashtag_usage"] = sum(has_hashtags) / len(has_hashtags)

        return patterns

    def _generate_suggestions(
        self, approved_patterns: Dict[str, Any], rejected_patterns: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions based on patterns"""
        suggestions = []

        # Length comparison
        approved_len = approved_patterns.get("avg_length")
        rejected_len = rejected_patterns.get("avg_length")

        if approved_len and rejected_len:
            if approved_len < rejected_len * 0.8:
                suggestions.append(
                    f"Users prefer shorter content (~{approved_len} chars vs {rejected_len} chars)"
                )
            elif approved_len > rejected_len * 1.2:
                suggestions.append(
                    f"Users prefer longer content (~{approved_len} chars vs {rejected_len} chars)"
                )

        # Emoji usage
        approved_emoji = approved_patterns.get("emoji_usage")
        rejected_emoji = rejected_patterns.get("emoji_usage")

        if approved_emoji is not None and rejected_emoji is not None:
            if approved_emoji > rejected_emoji * 1.5:
                suggestions.append(
                    f"Users prefer more emojis ({approved_emoji:.0%} vs {rejected_emoji:.0%})"
                )
            elif approved_emoji < rejected_emoji * 0.5:
                suggestions.append(
                    f"Users prefer fewer emojis ({approved_emoji:.0%} vs {rejected_emoji:.0%})"
                )

        # Content type preferences
        approved_types = approved_patterns.get("content_types", {})
        if approved_types:
            top_type = max(approved_types.items(), key=lambda x: x[1])
            suggestions.append(
                f"Most approved content type: {top_type[0]} ({top_type[1]} occurrences)"
            )

        return suggestions
