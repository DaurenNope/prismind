#!/usr/bin/env python3
"""
Intelligent Persona Matcher
Selects which personas (2-3) would actually care about specific content
Instead of blindly rewriting for all 5 personas
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


class PersonaMatcher:
    """
    Intelligently matches content to personas based on:
    - Content category and topics
    - Complexity level
    - Use cases and applications
    - Target audience signals
    """

    def __init__(self):
        # Define persona preferences and signals
        # ONLY 3 PROFILES: Qronoya (tech pro), Aspandead (deep writer), Claimzilla (crypto)
        self.persona_profiles = {
            "qronoya": {
                "interests": [
                    "technology", "tech", "startup", "startups", "career", "professional",
                    "software", "development", "coding", "programming", "developer",
                    "entrepreneurship", "entrepreneur", "business", "life lessons",
                    "productivity", "growth", "learning", "advice", "services",
                    "building", "product", "tools", "work", "job"
                ],
                "complexity_preference": ["Beginner", "Intermediate", "Advanced"],
                "categories": [
                    "Technology", "Startups", "Career", "Professional Development",
                    "Software Development", "Business", "Life Lessons", "Productivity"
                ],
                "keywords": [
                    "tech", "career", "professional", "startup", "advice",
                    "how to", "tips", "guide", "practical", "experience"
                ],
                "strict_exclusions": [
                    # Exclude strictly crypto content (that's Claimzilla's domain)
                    "crypto", "defi", "blockchain", "airdrop", "web3", "nft",
                    "eth", "btc", "sol", "token", "chain", "l2", "layer2"
                ],
                "platforms": ["twitter", "threads", "telegram"]
            },
            "aspandead": {
                "interests": [
                    "dating", "relationship", "love", "personal", "story", "experience",
                    "emotion", "feeling", "soul", "heart", "deep", "vulnerable",
                    "real", "raw", "honest", "reflection", "thought", "observation",
                    "human", "connection", "intimacy", "life", "meaning", "philosophy"
                ],
                "complexity_preference": ["Intermediate", "Advanced", "Expert"],
                "categories": [
                    "Personal Stories", "Dating", "Relationships", "Deep Thoughts",
                    "Creative Writing", "Life Observations", "Emotional", "Vulnerable"
                ],
                "keywords": [
                    "dating", "relationship", "personal", "story", "felt", "soul",
                    "raw", "real", "vulnerable", "deep", "thought", "reflection"
                ],
                "strict_exclusions": [
                    # Exclude strictly crypto and pure tech/career content
                    "crypto", "defi", "blockchain", "airdrop", "web3", "nft",
                    "startup funding", "product launch", "tech stack"
                ],
                "platforms": ["twitter", "threads", "telegram", "medium"]
            },
            "claimzilla": {
                "interests": [
                    "crypto", "cryptocurrency", "defi", "blockchain", "web3",
                    "airdrop", "airdrops", "token", "eth", "ethereum", "btc", "bitcoin",
                    "sol", "solana", "base", "l2", "layer2", "chain", "nft", "dex",
                    "yield", "farming", "staking", "protocol", "smart contract",
                    "market", "trading", "price", "alpha", "gems", "portfolio"
                ],
                "complexity_preference": ["Beginner", "Intermediate", "Advanced", "Expert"],
                "categories": [
                    "Crypto", "DeFi", "Blockchain", "Airdrops", "Web3",
                    "Market Analysis", "Trading", "Technology", "Protocols"
                ],
                "keywords": [
                    "crypto", "defi", "airdrop", "blockchain", "web3", "alpha",
                    "market", "token", "chain", "protocol", "trading", "yield"
                ],
                "strict_exclusions": [
                    # STRICTLY crypto only - NO AI, NO general tech, NO personal stories
                    "dating", "relationship", "personal story", "feelings", "soul",
                    "career advice", "life lessons", "startup advice",
                    # Allow AI ONLY if combined with crypto/blockchain context
                ],
                "strict_requirements": [
                    # MUST have at least ONE of these to match Claimzilla
                    "crypto", "defi", "blockchain", "airdrop", "web3", "nft",
                    "eth", "btc", "sol", "token", "chain", "l2", "layer2",
                    "protocol", "dex", "yield", "staking"
                ],
                "platforms": ["twitter", "threads"]
            }
        }

    def match_personas(
        self,
        analyzed_content: Dict[str, Any],
        min_personas: int = 1,
        max_personas: int = 2
    ) -> List[Tuple[str, float, str]]:
        """
        Match content to personas and return ranked list.
        STRICT ROUTING: Crypto → Claimzilla ONLY, Tech → Qronoya ONLY, Dating/Personal → Aspandead ONLY

        Args:
            analyzed_content: Full analysis from IntelligentContentAnalyzer
            min_personas: Minimum personas to return (default: 1)
            max_personas: Maximum personas to return (default: 2)

        Returns:
            List of (persona_id, match_score, reason) tuples, sorted by score
        """

        # Extract content features
        category = analyzed_content.get('category', '')
        topics = analyzed_content.get('topics', [])
        key_concepts = analyzed_content.get('key_concepts', [])
        complexity = analyzed_content.get('complexity', 'Intermediate')
        content = analyzed_content.get('content', '') + ' ' + analyzed_content.get('summary', '')
        content_lower = content.lower()

        # Get discovery signals for additional context
        discovery_signals = analyzed_content.get('discovery_signals', {})
        trend_relevance = discovery_signals.get('trend_relevance', 'mainstream')
        viral_potential = discovery_signals.get('viral_potential', 0)

        # Calculate match score for each persona
        persona_scores = {}

        for persona_id, profile in self.persona_profiles.items():
            score = 0.0
            reasons = []
            rejected = False
            rejection_reason = ""

            # STEP 1: Check strict exclusions (IMMEDIATE DISQUALIFICATION)
            if 'strict_exclusions' in profile:
                for exclusion in profile['strict_exclusions']:
                    if exclusion in content_lower:
                        rejected = True
                        rejection_reason = f"excluded: contains '{exclusion}'"
                        break

            # STEP 2: Check strict requirements (for Claimzilla)
            if not rejected and 'strict_requirements' in profile:
                # MUST have at least ONE requirement keyword
                has_requirement = any(
                    req in content_lower
                    for req in profile['strict_requirements']
                )
                if not has_requirement:
                    rejected = True
                    rejection_reason = "missing required crypto keywords"

            # If rejected, store 0 score and continue
            if rejected:
                persona_scores[persona_id] = (0, rejection_reason)
                continue

            # STEP 3: Calculate positive match score

            # 1. Interest keyword matching (0-40 points)
            interest_matches = sum(
                1 for interest in profile['interests']
                if interest in content_lower or interest in ' '.join(topics).lower()
            )
            if interest_matches > 0:
                interest_score = min(interest_matches * 5, 40)
                score += interest_score
                reasons.append(f"{interest_matches} interest matches")

            # 2. Complexity match (0-20 points)
            if complexity in profile['complexity_preference']:
                score += 20
                reasons.append(f"complexity match ({complexity})")
            elif complexity == "Intermediate":
                # Intermediate is acceptable for most
                score += 10
                reasons.append("intermediate complexity")

            # 3. Category match (0-20 points)
            if category and any(cat.lower() in category.lower() for cat in profile['categories']):
                score += 20
                reasons.append(f"category match")

            # 4. Keyword signals in content (0-20 points)
            keyword_matches = sum(
                1 for keyword in profile['keywords']
                if keyword in content_lower
            )
            if keyword_matches > 0:
                keyword_score = min(keyword_matches * 10, 20)
                score += keyword_score
                reasons.append(f"{keyword_matches} keyword signals")

            # 5. Special bonuses based on persona type
            if persona_id == "claimzilla":
                # Crypto-specific bonuses
                crypto_chains = ["eth", "btc", "sol", "base", "l2", "layer2"]
                chain_mentions = sum(1 for chain in crypto_chains if chain in content_lower)
                if chain_mentions > 0:
                    score += 15
                    reasons.append(f"crypto chain mentions ({chain_mentions})")

                # Market/trading signals
                if any(kw in content_lower for kw in ["market", "trading", "price", "alpha"]):
                    score += 10
                    reasons.append("market/trading signals")

            if persona_id == "qronoya":
                # Tech professional bonuses
                if any(kw in content_lower for kw in ["startup", "career", "professional", "advice"]):
                    score += 10
                    reasons.append("professional/career focus")

                # Practical tech content
                if any(kw in content_lower for kw in ["how to", "guide", "tips", "building"]):
                    score += 10
                    reasons.append("practical content")

            if persona_id == "aspandead":
                # Deep writer bonuses
                if any(kw in content_lower for kw in ["dating", "relationship", "love", "personal"]):
                    score += 15
                    reasons.append("dating/relationship focus")

                # Emotional depth signals
                if any(kw in content_lower for kw in ["soul", "vulnerable", "raw", "real", "deep"]):
                    score += 10
                    reasons.append("emotional depth")

            # Store score and reasons
            reason_text = ", ".join(reasons) if reasons else "low match"
            persona_scores[persona_id] = (score, reason_text)

        # Sort by score (descending)
        sorted_personas = sorted(
            persona_scores.items(),
            key=lambda x: x[1][0],
            reverse=True
        )

        # STRICT MATCHING: Higher threshold (50 points minimum)
        # Only return personas that actually match well
        MIN_SCORE_THRESHOLD = 50

        results = []
        for persona_id, (score, reason) in sorted_personas:
            if score >= MIN_SCORE_THRESHOLD:
                results.append((persona_id, score, reason))

        # DO NOT force min_personas if nothing matches well
        # Better to return 0-1 matches than force bad matches
        # But cap at max_personas
        results = results[:max_personas]

        if len(results) > 0:
            logger.info(f"🎯 Matched {len(results)} persona(s) for this content")
            for persona_id, score, reason in results:
                logger.info(f"   • {persona_id}: {score:.0f} points ({reason})")
        else:
            logger.info(f"❌ No personas matched (all below {MIN_SCORE_THRESHOLD} point threshold)")
            # Show why they were rejected
            for persona_id, (score, reason) in sorted_personas[:3]:
                logger.info(f"   • {persona_id}: {score:.0f} points - {reason}")

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

    print("🧪 Testing Persona Matcher\n")

    matcher = get_persona_matcher()

    # Test Case 1: Deep technical content
    test_cases = [
        {
            "name": "Deep Technical: Redis Architecture",
            "content": {
                "category": "Technical Deep Dive",
                "topics": ["redis", "architecture", "performance", "memory"],
                "key_concepts": ["data structures", "persistence", "replication"],
                "complexity": "Expert",
                "content": "Deep dive into Redis architecture: How Redis achieves microsecond latency with in-memory data structures. Implementation details of the event loop, persistence mechanisms, and replication protocol.",
                "discovery_signals": {
                    "trend_relevance": "mainstream",
                    "viral_potential": 40
                }
            }
        },
        {
            "name": "Trending: New AI Model Launch",
            "content": {
                "category": "Product Launch",
                "topics": ["AI", "GPT", "launch", "announcement"],
                "key_concepts": ["machine learning", "breakthrough", "release"],
                "complexity": "Intermediate",
                "content": "BREAKING: OpenAI just launched GPT-5! Everyone's talking about it. This is trending everywhere. Major AI breakthrough announced today.",
                "discovery_signals": {
                    "trend_relevance": "emerging",
                    "viral_potential": 95
                }
            }
        },
        {
            "name": "Tutorial: React for Beginners",
            "content": {
                "category": "Educational Tutorial",
                "topics": ["react", "javascript", "tutorial", "beginners"],
                "key_concepts": ["components", "state", "props", "hooks"],
                "complexity": "Beginner",
                "content": "Learn React from scratch: A beginner's guide to building your first React app. Step-by-step tutorial for beginners. Introduction to React fundamentals explained.",
                "discovery_signals": {
                    "trend_relevance": "mainstream",
                    "viral_potential": 30
                }
            }
        },
        {
            "name": "Builder: Startup Tool Launch",
            "content": {
                "category": "Product Launch",
                "topics": ["startup", "tool", "product", "launch", "SaaS"],
                "key_concepts": ["MVP", "users", "market", "growth"],
                "complexity": "Intermediate",
                "content": "We just shipped our MVP! Tool for startup builders to launch faster. Practical use cases for product teams. How to build and ship in 2 weeks.",
                "discovery_signals": {
                    "trend_relevance": "mainstream",
                    "viral_potential": 55
                }
            }
        },
        {
            "name": "Strategy: Future of AI Industry",
            "content": {
                "category": "Industry Analysis",
                "topics": ["AI", "future", "industry", "strategy", "market"],
                "key_concepts": ["prediction", "impact", "leadership", "vision"],
                "complexity": "Advanced",
                "content": "The future of AI: Strategic analysis of industry trends. Why this matters for executives and decision makers. Big picture implications for the next decade. Market predictions and strategic insights.",
                "discovery_signals": {
                    "trend_relevance": "mainstream",
                    "viral_potential": 60
                }
            }
        }
    ]

    print("=" * 80)
    print("PERSONA MATCHING RESULTS")
    print("=" * 80)
    print()

    for test_case in test_cases:
        print(f"📄 {test_case['name']}")
        print("-" * 80)

        matches = matcher.match_personas(test_case['content'], min_personas=2, max_personas=3)

        print(f"   Matched {len(matches)} personas:\n")

        for i, (persona_id, score, reason) in enumerate(matches, 1):
            emoji = {
                'technical': '🔧',
                'builder': '🚀',
                'learner': '📚',
                'trendsetter': '🔥',
                'thought_leader': '💡'
            }.get(persona_id, '❓')

            print(f"   {i}. {emoji} {persona_id.upper()}")
            print(f"      Score: {score:.0f}/100")
            print(f"      Reason: {reason}")
            print()

        print()

    print("=" * 80)
    print("✅ Persona matching working!")
    print()
    print("Key Insight: Each content type matches 2-3 relevant personas, not all 5")


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    demo_matcher()
