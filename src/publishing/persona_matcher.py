#!/usr/bin/env python3
"""
Intelligent Persona Matcher
Dynamically loads profiles from config/personas/*.json and matches content
using AI analysis results (category, key_concepts, topics) instead of keyword matching.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class PersonaMatcher:
    """
    Intelligently matches content to personas based on AI analysis results:
    - Content category (from AI)
    - Key concepts (from AI - semantic)
    - Topics (from AI - semantic)
    - Complexity level
    - Uses AI summary (semantic, language-agnostic) instead of raw content
    """

    def __init__(self):
        # Dynamically load persona profiles from config/personas/*.json
        self.persona_profiles = self._load_personas()

        # Category to persona mapping (based on profile expertise)
        self._category_to_persona = self._build_category_mapping()

    def _load_personas(self) -> Dict[str, Dict[str, Any]]:
        """Dynamically load all personas from config/personas/*.json"""
        profiles = {}
        personas_dir = Path("config/personas")

        if not personas_dir.exists():
            logger.warning(f"Personas directory not found: {personas_dir}")
            return profiles

        for persona_file in personas_dir.glob("*.json"):
            # Skip example files
            if "example" in persona_file.name.lower():
                continue

            try:
                with open(persona_file, "r", encoding="utf-8") as f:
                    persona = json.load(f)
                    persona_key = persona.get("key") or persona_file.stem
                    profiles[persona_key] = persona
                    logger.debug(f"Loaded persona: {persona_key}")
            except Exception as e:
                logger.error(f"Failed to load persona {persona_file}: {e}")

        logger.info(f"Loaded {len(profiles)} personas: {list(profiles.keys())}")
        return profiles

    def _build_category_mapping(self) -> Dict[str, str]:
        """Build category to persona mapping from profile expertise"""
        category_map = {}

        for persona_key, profile in self.persona_profiles.items():
            expertise = profile.get("expertise", [])

            # Map expertise to categories
            for exp in expertise:
                exp_lower = exp.lower()
                if (
                    "crypto" in exp_lower
                    or "blockchain" in exp_lower
                    or "defi" in exp_lower
                ):
                    category_map["CRYPTO"] = persona_key
                elif (
                    "tech" in exp_lower
                    or "software" in exp_lower
                    or "startup" in exp_lower
                    or "business" in exp_lower
                ):
                    if "CRYPTO" not in category_map:  # Don't override crypto
                        category_map.setdefault("TECH", persona_key)
                        category_map.setdefault("BUSINESS", persona_key)
                        category_map.setdefault("LEARNING", persona_key)
                elif (
                    "dating" in exp_lower
                    or "relationship" in exp_lower
                    or "personal" in exp_lower
                ):
                    category_map["PERSONAL"] = persona_key
                    category_map["DATING"] = persona_key

        logger.debug(f"Category mapping: {category_map}")
        return category_map

    def match_personas(
        self,
        analyzed_content: Dict[str, Any],
        min_personas: int = 1,
        max_personas: int = 3,
    ) -> List[Tuple[str, float, str]]:
        """
        Match content to personas using AI analysis results (not keyword matching).

        Args:
            analyzed_content: Full analysis from IntelligentContentAnalyzer with:
                - category: Primary category from AI
                - fit_categories: Multiple categories content fits
                - key_concepts: Semantic concepts extracted by AI
                - topics: Topics extracted by AI
                - ai_summary: Semantic summary (always in English)
                - complexity: Complexity level
            min_personas: Minimum personas to return (default: 1)
            max_personas: Maximum personas to return (default: 3)

        Returns:
            List of (persona_id, match_score, reason) tuples, sorted by score
            Scores are in 0-100 format for profile_matches JSONB storage
        """

        # Extract AI analysis results (semantic, language-agnostic)
        category = analyzed_content.get("category", "").upper().strip()
        fit_categories = [
            c.upper().strip()
            for c in (analyzed_content.get("fit_categories", []) or [])
        ]
        key_concepts = [
            str(c).lower() for c in (analyzed_content.get("key_concepts", []) or [])
        ]
        topics = [str(t).lower() for t in (analyzed_content.get("topics", []) or [])]
        complexity = analyzed_content.get("complexity", "Intermediate")

        # Use AI summary (semantic, always in English) instead of raw content
        ai_summary = (
            analyzed_content.get("ai_summary", "")
            or analyzed_content.get("summary", "")
        ).lower()

        # Calculate match score for each dynamically loaded persona
        persona_scores = {}

        for persona_key, profile in self.persona_profiles.items():
            score = 0.0
            reasons = []

            # METHOD 1: Category-based matching (most reliable, from AI)
            # Check fit_categories first (more comprehensive than primary category)
            category_match = False
            matched_categories = []

            for fit_cat in fit_categories:
                if fit_cat in self._category_to_persona:
                    if self._category_to_persona[fit_cat] == persona_key:
                        category_match = True
                        matched_categories.append(fit_cat)

            # Also check primary category
            if category and category in self._category_to_persona:
                if self._category_to_persona[category] == persona_key:
                    category_match = True
                    if category not in matched_categories:
                        matched_categories.append(category)

            if category_match:
                score += 40
                reasons.append(f"Category match: {', '.join(matched_categories)}")

            # METHOD 2: Concept-based matching (semantic, from AI key_concepts)
            # Use expertise from profile to match concepts
            expertise = [str(e).lower() for e in (profile.get("expertise", []) or [])]

            concept_matches = 0
            for concept in key_concepts:
                # Check if concept matches any expertise area
                for exp in expertise:
                    if exp in concept or concept in exp:
                        concept_matches += 1
                        break

            if concept_matches > 0:
                score += min(concept_matches * 8, 30)
                reasons.append(f"Concept match: {concept_matches} concepts")

            # METHOD 3: Topic-based matching (semantic, from AI topics)
            topic_matches = 0
            for topic in topics:
                for exp in expertise:
                    if exp in topic or topic in exp:
                        topic_matches += 1
                        break

            if topic_matches > 0:
                score += min(topic_matches * 5, 20)
                reasons.append(f"Topic match: {topic_matches} topics")

            # METHOD 4: Complexity match
            complexity_pref = profile.get("complexity_preference", [])
            if complexity in complexity_pref:
                score += 10
                reasons.append(f"Complexity match: {complexity}")

            # KEYWORDS ONLY AS FALLBACK (when AI analysis is weak)
            # Use ai_summary (semantic, language-agnostic) instead of raw content
            if score < 30 and ai_summary:
                # Get keywords from profile config if available
                keywords = profile.get("filters", {}).get("keywords", []) or []
                keyword_matches = sum(1 for kw in keywords if kw.lower() in ai_summary)

                if keyword_matches > 0:
                    score += min(
                        keyword_matches * 3, 15
                    )  # Lower weight - less reliable
                    reasons.append(f"Keyword fallback: {keyword_matches}")

            # Special handling for crypto content
            # Qronoya can handle crypto business/trading, but claimzilla gets priority for technical crypto
            if persona_key == "qronoya" and category == "CRYPTO":
                # Check if it's business/trading crypto (qronoya is knowledgeable about this!)
                crypto_business = any(
                    cb in " ".join(key_concepts).lower()
                    for cb in ["trading", "markets", "investing", "business"]
                )
                if crypto_business:
                    score += 15
                    reasons.append("Crypto business/trading content")

            elif persona_key == "claimzilla" and category == "CRYPTO":
                # Deep crypto technical gets priority
                crypto_technical = any(
                    ct in " ".join(key_concepts).lower()
                    for ct in [
                        "defi",
                        "protocol",
                        "smart contract",
                        "blockchain tech",
                        "airdrop",
                        "tokenomics",
                        "staking",
                    ]
                )
                if crypto_technical:
                    score += 20
                    reasons.append("Crypto technical content")

            # Store score (0-100 format for JSONB storage)
            reason_text = ", ".join(reasons) if reasons else "low match"
            persona_scores[persona_key] = (score, reason_text)

        # Sort by score (descending)
        sorted_personas = sorted(
            persona_scores.items(), key=lambda x: x[1][0], reverse=True
        )

        # Return all personas with scores (not just above threshold)
        # Let the caller decide thresholds based on use case
        results = []
        for persona_key, (score, reason) in sorted_personas:
            # Return score in 0-100 format (for profile_matches JSONB)
            results.append((persona_key, round(score, 2), reason))

        # Cap at max_personas
        results = results[:max_personas]

        if len(results) > 0:
            logger.debug(f"🎯 Matched {len(results)} persona(s) for this content")
            for persona_id, score, reason in results:
                logger.debug(f"   • {persona_id}: {score:.1f}/100 ({reason})")
        else:
            logger.debug(f"❌ No personas matched for this content")

        return results


# Singleton
_matcher = None


def get_persona_matcher() -> PersonaMatcher:
    """Get global matcher instance"""
    global _matcher
    if _matcher is None:
        _matcher = PersonaMatcher()
    return _matcher


def demo_matcher():
    """Demo persona matching with different content types"""

    logger.info("🧪 Testing Persona Matcher\n")

    matcher = get_persona_matcher()

    # Test Case 1: Deep technical content
    test_cases = [
        {
            "name": "Deep Technical: Redis Architecture",
            "content": {
                "category": "TECH",
                "topics": ["redis", "architecture", "performance", "memory"],
                "key_concepts": ["data structures", "persistence", "replication"],
                "complexity": "Expert",
                "ai_summary": "Deep dive into Redis architecture: How Redis achieves microsecond latency with in-memory data structures. Implementation details of the event loop, persistence mechanisms, and replication protocol.",
                "fit_categories": ["TECH"],
            },
        },
        {
            "name": "Crypto Trading Content",
            "content": {
                "category": "CRYPTO",
                "topics": ["bitcoin", "trading", "markets"],
                "key_concepts": ["trading", "markets", "investing", "bitcoin"],
                "complexity": "Intermediate",
                "ai_summary": "Bitcoin trading analysis: Market trends and investment strategies for crypto trading.",
                "fit_categories": ["CRYPTO", "BUSINESS"],
            },
        },
        {
            "name": "Personal Growth Content",
            "content": {
                "category": "PERSONAL",
                "topics": ["mindfulness", "personal growth", "self-awareness"],
                "key_concepts": ["mindfulness", "present moment", "self-awareness"],
                "complexity": "Intermediate",
                "ai_summary": "Deep reflection on mindfulness and being present in the moment, exploring personal growth and self-awareness.",
                "fit_categories": ["PERSONAL"],
            },
        },
    ]

    logger.info("=" * 80)
    logger.info("PERSONA MATCHING RESULTS")
    logger.info("=" * 80)
    logger.info()

    for test_case in test_cases:
        logger.info(f"📄 {test_case['name']}")
        logger.info("-" * 80)

        matches = matcher.match_personas(
            test_case["content"], min_personas=1, max_personas=3
        )

        logger.info(f"   Matched {len(matches)} personas:\n")

        for i, (persona_id, score, reason) in enumerate(matches, 1):
            emoji = {"qronoya": "💡", "aspandead": "🖤", "claimzilla": "💎"}.get(
                persona_id, "❓"
            )

            logger.info(f"   {i}. {emoji} {persona_id.upper()}")
            logger.info(f"      Score: {score:.1f}/100")
            logger.info(f"      Reason: {reason}")
            logger.info()

        logger.info()

    logger.info("=" * 80)
    logger.info("✅ Persona matching working!")
    logger.info()
    logger.info(
        "Key Insight: Uses AI analysis results (category, key_concepts, topics) instead of keyword matching"
    )


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    demo_matcher()
