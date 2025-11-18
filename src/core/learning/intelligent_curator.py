"""
Intelligent Content Curator
Learns user preferences and curates personalized content feed
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntelligentCurator:
    """
    Learns from user behavior to personalize content discovery

    Features:
    - Tracks save/dismiss/skip actions
    - Learns category preferences
    - Learns source quality
    - Adjusts quality scores
    - Filters dismissed items
    - Recommends similar content
    """

    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.preferences = self._load_preferences()

    def _load_preferences(self) -> Dict[str, Dict[str, float]]:
        """Load user preferences from database"""
        try:
            result = (
                self.supabase.table("user_preferences")
                .select("*")
                .eq("user_id", "default")
                .execute()
            )

            prefs = defaultdict(dict)
            for pref in result.data:
                pref_type = pref["preference_type"]
                pref_key = pref["preference_key"]
                pref_value = pref["preference_value"]
                prefs[pref_type][pref_key] = pref_value

            return prefs
        except Exception as e:
            logger.warning(f"Preferences table not yet created (run migration): {e}")
            # Return empty prefs - system will work without learning until migration runs
            return defaultdict(dict)

    def log_interaction(self, discovery_id: int, action: str):
        """Log user interaction for learning"""
        try:
            # Try to log to interactions table (if it exists)
            try:
                self.supabase.table("user_interactions").insert(
                    {
                        "user_id": "default",
                        "discovery_id": discovery_id,
                        "action": action,
                        "created_at": datetime.now().isoformat(),
                    }
                ).execute()
            except Exception as e:
                logger.warning(f"Interactions table not available yet: {e}")

            # Update discovery status (using existing fields that should be there)
            status_map = {
                "save": "saved",
                "dismiss": "dismissed",
                "skip": "skipped",
                "view": "shown",
            }

            updates = {}

            # Only update fields that exist
            try:
                updates["status"] = status_map.get(action, "shown")
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            try:
                if action == "dismiss":
                    updates["dismissed"] = True
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

            if updates:
                self.supabase.table("discoveries").update(updates).eq(
                    "id", discovery_id
                ).execute()

            logger.info(f"Logged {action} for discovery {discovery_id}")
        except Exception as e:
            logger.warning(f"Could not log interaction (migration needed): {e}")

    def learn_from_action(self, discovery: Dict[str, Any], action: str):
        """
        Learn from user action and update preferences

        Actions:
        - save: Boost preference (+0.1)
        - dismiss: Lower preference (-0.2)
        - skip: Small negative (-0.05)
        """
        try:
            # Determine preference weight
            weight_map = {"save": 0.1, "dismiss": -0.2, "skip": -0.05, "view": 0.01}
            weight = weight_map.get(action, 0)

            if weight == 0:
                return

            # Update category preference
            category = discovery.get("category") or discovery.get("topic")
            if category:
                self._update_preference("category", category, weight)

            # Update source preference
            source = discovery.get("source")
            if source:
                self._update_preference("source", source, weight)

            # Update topic preferences from keywords
            topics = discovery.get("matched_topics", [])
            if isinstance(topics, list):
                for topic in topics:
                    self._update_preference("topic", topic, weight * 0.5)

            logger.info(f"Learned from {action}: category={category}, source={source}")
        except Exception as e:
            logger.error(f"Error learning from action: {e}")

    def _update_preference(self, pref_type: str, pref_key: str, weight: float):
        """Update or create preference with decay"""
        try:
            # Check if preference exists
            result = (
                self.supabase.table("user_preferences")
                .select("*")
                .eq("user_id", "default")
                .eq("preference_type", pref_type)
                .eq("preference_key", pref_key)
                .execute()
            )

            if result.data:
                # Update existing
                pref = result.data[0]
                current_value = pref["preference_value"]
                interaction_count = pref["interaction_count"]

                # Calculate new value with decay (weighted average)
                new_value = (current_value * interaction_count + weight) / (
                    interaction_count + 1
                )
                new_value = max(-1.0, min(1.0, new_value))  # Clamp to [-1, 1]

                self.supabase.table("user_preferences").update(
                    {
                        "preference_value": new_value,
                        "interaction_count": interaction_count + 1,
                        "last_updated": datetime.now().isoformat(),
                    }
                ).eq("id", pref["id"]).execute()
            else:
                # Create new
                self.supabase.table("user_preferences").insert(
                    {
                        "user_id": "default",
                        "preference_type": pref_type,
                        "preference_key": pref_key,
                        "preference_value": weight,
                        "interaction_count": 1,
                    }
                ).execute()

            # Update local cache
            self.preferences[pref_type][pref_key] = weight

        except Exception as e:
            logger.warning(f"Preferences table not available (run migration): {e}")
            # Update local cache only
            self.preferences[pref_type][pref_key] = weight

    def calculate_personalized_score(self, discovery: Dict[str, Any]) -> float:
        """
        Calculate personalized relevance score based on learned preferences
        Returns: -1.0 to 1.0 (negative = dislike, positive = like)
        """
        score = 0.0
        weights = 0.0

        # Category preference
        category = discovery.get("category") or discovery.get("topic")
        if category and category in self.preferences.get("category", {}):
            pref = self.preferences["category"][category]
            score += pref * 0.4
            weights += 0.4

        # Source preference
        source = discovery.get("source")
        if source and source in self.preferences.get("source", {}):
            pref = self.preferences["source"][source]
            score += pref * 0.3
            weights += 0.3

        # Topic preferences
        topics = discovery.get("matched_topics", [])
        if isinstance(topics, list) and topics:
            topic_prefs = [self.preferences.get("topic", {}).get(t, 0) for t in topics]
            if topic_prefs:
                avg_topic_pref = sum(topic_prefs) / len(topic_prefs)
                score += avg_topic_pref * 0.3
                weights += 0.3

        # Normalize
        return score / weights if weights > 0 else 0.0

    def filter_and_rank_feed(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter dismissed items and rank by personalized score
        """
        # Filter out dismissed
        filtered = [item for item in items if not item.get("dismissed", False)]

        # Calculate personalized scores
        for item in filtered:
            base_score = item.get("score", 0)
            personal_score = self.calculate_personalized_score(item)

            # Combine base quality with personalization (70% base, 30% personal)
            combined_score = base_score * 0.7 + (personal_score * 5 + 5) * 0.3
            item["personalized_score"] = combined_score
            item["preference_boost"] = personal_score

        # Sort by personalized score
        filtered.sort(key=lambda x: x.get("personalized_score", 0), reverse=True)

        return filtered

    def get_preference_summary(self) -> Dict[str, Any]:
        """Get summary of learned preferences"""
        summary = {
            "categories": {},
            "sources": {},
            "topics": {},
            "total_interactions": 0,
        }

        try:
            # Get interaction count
            result = (
                self.supabase.table("user_interactions")
                .select("id", count="exact")
                .execute()
            )
            summary["total_interactions"] = result.count or 0

            # Top categories
            for cat, score in sorted(
                self.preferences.get("category", {}).items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]:
                summary["categories"][cat] = round(score, 3)

            # Top sources
            for src, score in sorted(
                self.preferences.get("source", {}).items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]:
                summary["sources"][src] = round(score, 3)

            # Top topics
            for topic, score in sorted(
                self.preferences.get("topic", {}).items(),
                key=lambda x: x[1],
                reverse=True,
            )[:10]:
                summary["topics"][topic] = round(score, 3)

        except Exception as e:
            logger.error(f"Error getting preference summary: {e}")

        return summary
