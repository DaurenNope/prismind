"""
BEYONDLINES Analysis Components
===========================

Broken out components from IntelligentContentAnalyzer for better maintainability.
Each component handles a specific aspect of content analysis.

Author: BEYONDLINES AI System
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.core.extraction.social_extractor_base import SocialPost


class ContentAnalyzer:
    """Main content analyzer that orchestrates all analysis components"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.scorer = ContentScorer()
        self.processor = ContentProcessor()
        self.insight_generator = InsightGenerator()
        self.time_detector = TimeSensitivityDetector()

    def analyze_post(self, post: SocialPost) -> Dict[str, Any]:
        """Perform comprehensive analysis of a social media post"""
        try:
            # Extract keywords and process content
            keywords = self.processor.extract_keywords(post.content or "")
            content_type = self.processor.guess_type(post)
            language = self.processor.guess_language(post.content or "")

            # Calculate various scores
            intelligent_score = self.scorer.calculate_intelligent_value_score({}, post)
            quality_score = self.scorer.calculate_content_quality_score({}, post)

            # Generate insights and recommendations
            insights = self.insight_generator.generate_actionable_insights({}, post)
            learning = self.insight_generator.generate_learning_recommendations(
                {}, post
            )

            # Detect time sensitivity
            time_analysis = self.time_detector.detect_time_sensitivity(post, {})

            return {
                "keywords": keywords,
                "content_type": content_type,
                "language": language,
                "intelligent_value_score": intelligent_score,
                "content_quality_score": quality_score,
                "actionable_insights": insights,
                "learning_value": learning.get("next_steps", []),
                "time_sensitivity": time_analysis,
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "is_rewrite_candidate": self.scorer.determine_rewrite_candidate(
                    {}, post, quality_score
                ),
            }
        except Exception as e:
            logger.error(f"Error: {e}")
            return {
                "error": str(e),
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "intelligent_value_score": 0.0,
                "content_quality_score": 0.0,
                "is_rewrite_candidate": False,
            }


class ContentScorer:
    """Handles various scoring algorithms for content analysis"""

    @staticmethod
    def calculate_intelligent_value_score(analysis: Dict, post: SocialPost) -> float:
        """Calculate sophisticated value score based on multiple factors with wider distribution"""

        # Safety check - ensure analysis is a dict
        if not isinstance(analysis, dict):
            return 0.0

        score = 3.0  # Lower base score for more contrast

        # Content quality indicators (0-3 points)
        if isinstance(analysis.get("quality_indicators"), list):
            quality_count = len(analysis["quality_indicators"])
            score += min(quality_count * 0.6, 3.0)

        # Actionable content bonus (0-2 points)
        if isinstance(analysis.get("actionable_items"), list):
            actionable_count = len(analysis["actionable_items"])
            score += min(actionable_count * 0.4, 2.0)

        # Learning value bonus (0-2 points)
        learning_value = analysis.get("learning_value")
        if learning_value and isinstance(learning_value, str):
            if len(learning_value) > 50:
                score += 2.0
            else:
                score += 1.0

        # Engagement quality with exponential scaling (0-2 points)
        if isinstance(post.engagement, dict):
            likes = (
                post.engagement.get("likes", 0)
                or post.engagement.get("score", 0)
                or post.engagement.get("favorite_count", 0)
            )
            comments = (
                post.engagement.get("comments", 0)
                or post.engagement.get("replies", 0)
                or post.engagement.get("num_comments", 0)
            )

            # Exponential scaling for viral content
            if likes > 1000 or comments > 100:
                score += 2.0
            elif likes > 500 or comments > 50:
                score += 1.5
            elif likes > 100 or comments > 20:
                score += 1.0
            elif likes > 20 or comments > 5:
                score += 0.5

        # Platform-specific adjustments (0-1 points)
        if post.platform == "reddit":
            score += 0.5
        elif post.platform == "twitter" and post.post_type == "thread":
            score += 1.0

        # Content complexity and depth (0-1.5 points)
        if "complexity_level" in analysis:
            complexity = analysis["complexity_level"]
            if complexity == "Expert":
                score += 1.5
            elif complexity == "Advanced":
                score += 1.0
            elif complexity == "Intermediate":
                score += 0.5

        # Practical applications bonus (0-1.5 points)
        if "practical_applications" in analysis:
            app_count = len(analysis["practical_applications"])
            score += min(app_count * 0.5, 1.5)

        # Penalize low quality
        if (
            "quality_indicators" in analysis
            and len(analysis["quality_indicators"]) == 0
        ):
            score -= 1.0

        return max(1.0, min(score, 10.0))

    @staticmethod
    def calculate_content_quality_score(analysis: Dict, post: SocialPost) -> float:
        """Calculate content quality score for social media reposting (0-10 scale)"""

        if not isinstance(analysis, dict):
            return 0.0

        if not post.content or not isinstance(post.content, str):
            return 0.0

        quality_score = 0.0
        content = post.content.lower()
        original_content = post.content

        # Base content value (0-3 points)
        content_length = len(original_content)
        if 50 <= content_length <= 280:
            quality_score += 3.0
        elif 280 < content_length <= 500:
            quality_score += 2.5
        elif content_length > 500:
            quality_score += 2.0
        elif content_length < 50:
            quality_score += 0.5

        # Engagement indicators (0-2 points)
        engagement_words = [
            "tip",
            "hack",
            "secret",
            "amazing",
            "incredible",
            "must-know",
            "game-changer",
            "breakthrough",
            "revolutionary",
            "insider",
        ]
        engagement_count = sum(1 for word in engagement_words if word in content)
        quality_score += min(engagement_count * 0.5, 2.0)

        # Technical value (0-2 points)
        tech_value_terms = [
            "ai",
            "ml",
            "python",
            "javascript",
            "react",
            "api",
            "database",
            "algorithm",
            "framework",
            "tool",
            "software",
            "code",
            "dev",
        ]
        tech_count = sum(1 for term in tech_value_terms if term in content)
        quality_score += min(tech_count * 0.3, 2.0)

        # Structure and readability (0-1.5 points)
        if any(
            indicator in content
            for indicator in ["1.", "2.", "3.", "•", "-", "first", "second"]
        ):
            quality_score += 1.0
        if "\n" in original_content:
            quality_score += 0.5

        # Social media friendly elements (0-1.5 points)
        if any(indicator in content for indicator in ["#", "@", "http", "link"]):
            quality_score += 0.5
        if any(indicator in content for indicator in ["?", "!", "what", "how", "why"]):
            quality_score += 0.5
        if any(
            emoji_indicator in original_content
            for emoji_indicator in ["🚀", "💡", "🔥", "✨", "⚡"]
        ):
            quality_score += 0.5

        # Actual engagement metrics (0-1 point)
        if hasattr(post, "engagement") and post.engagement:
            likes = (
                post.engagement.get("likes", 0)
                or post.engagement.get("score", 0)
                or post.engagement.get("favorite_count", 0)
            )
            comments = (
                post.engagement.get("replies", 0)
                or post.engagement.get("num_comments", 0)
                or post.engagement.get("reply_count", 0)
            )

            if likes > 100 or comments > 20:
                quality_score += 1.0
            elif likes > 20 or comments > 5:
                quality_score += 0.5

        return min(quality_score, 10.0)

    @staticmethod
    def determine_rewrite_candidate(
        analysis: Dict, post: SocialPost, quality_score: float
    ) -> bool:
        """Determine if content is a good candidate for rewriting and reposting"""

        if not isinstance(analysis, dict):
            return False

        if not post.content or not isinstance(post.content, str):
            return False

        if not isinstance(quality_score, (int, float)):
            quality_score = 0.0

        content = post.content
        content_lower = content.lower()
        content_length = len(content)

        # High-quality content that's too long for social media
        if quality_score >= 6.0 and content_length > 500:
            return True

        # Good technical content but lacks social media engagement elements
        tech_terms = [
            "ai",
            "ml",
            "python",
            "javascript",
            "react",
            "api",
            "database",
            "algorithm",
            "framework",
            "tool",
            "software",
            "code",
            "dev",
        ]
        has_tech_content = sum(1 for term in tech_terms if term in content_lower) >= 2

        engagement_elements = ["#", "@", "?", "!", "🚀", "💡", "🔥", "✨", "⚡"]
        has_engagement_elements = any(
            element in content for element in engagement_elements
        )

        if has_tech_content and not has_engagement_elements and quality_score >= 4.0:
            return True

        # Content with good structure but could be more engaging
        has_structure = any(
            indicator in content_lower
            for indicator in ["1.", "2.", "3.", "•", "-", "first", "second"]
        )
        engagement_words = [
            "tip",
            "hack",
            "secret",
            "amazing",
            "incredible",
            "must-know",
            "game-changer",
            "breakthrough",
            "revolutionary",
            "insider",
        ]
        has_engagement_words = any(word in content_lower for word in engagement_words)

        if has_structure and not has_engagement_words and quality_score >= 5.0:
            return True

        # Long posts with good content but poor social media optimization
        if content_length > 800 and quality_score >= 5.0:
            return True

        # Posts with valuable information but suboptimal length for social media
        if content_length < 50 and quality_score >= 6.0:
            return True

        # Posts with good engagement potential but missing key elements
        if quality_score >= 7.0 and not has_engagement_elements:
            return True

        # Check for posts that performed well but could be optimized further
        if hasattr(post, "engagement") and post.engagement:
            likes = (
                post.engagement.get("likes", 0)
                or post.engagement.get("score", 0)
                or post.engagement.get("favorite_count", 0)
            )
            comments = (
                post.engagement.get("replies", 0)
                or post.engagement.get("num_comments", 0)
                or post.engagement.get("reply_count", 0)
            )

            if (
                (likes > 50 or comments > 10)
                and quality_score >= 6.0
                and not has_engagement_elements
            ):
                return True

        return False


class ContentProcessor:
    """Handles content processing and normalization"""

    @staticmethod
    def extract_keywords(text: str) -> List[str]:
        """Extract keywords from text using frequency analysis"""
        if not text:
            return []
        words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_+-]{3,}", text)]
        freq: Dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        return [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:10]]

    @staticmethod
    def listize_field(value: Any) -> List[str]:
        """Convert various field types to consistent list format"""
        if value is None:
            return []
        if isinstance(value, list):
            return [str(i).strip() for i in value if str(i).strip()]
        if isinstance(value, str):
            parts = [p.strip(" #") for p in re.split(r"[#,;]|\n", value) if p.strip()]
            return parts[:8]
        return []

    @staticmethod
    def guess_topic(tags: List[str], concepts: List[str]) -> str:
        """Guess main topic from tags and concepts"""
        pool = (tags or []) + (concepts or [])
        if not pool:
            return "General"
        return pool[0][:50]

    @staticmethod
    def guess_type(post: SocialPost) -> str:
        """Guess content type from post metadata"""
        if post.post_type and post.post_type.lower() in ("thread", "tweet", "post"):
            return "thread" if post.platform in ("threads", "twitter") else "post"
        if post.title and len(post.content or "") > 600:
            return "how_to"
        return "opinion"

    @staticmethod
    def guess_language(text: str) -> str:
        """Detect language from text content"""
        try:
            if re.search(r"[А-Яа-я]", text):
                return "ru"
            if re.search(r"[\u0600-\u06FF]", text):
                return "ar"
            return "en"
        except Exception as e:
            logger.error(f"Error: {e}")
            return "en"


class InsightGenerator:
    """Generates actionable insights and learning recommendations"""

    @staticmethod
    def generate_actionable_insights(analysis: Dict, post: SocialPost) -> List[str]:
        """Generate specific actionable insights from the analysis"""

        insights = []

        # Extract from analysis
        if "actionable_items" in analysis:
            insights.extend(analysis["actionable_items"])

        # Add platform-specific insights
        if post.platform == "reddit":
            insights.append(
                f"Explore discussion thread for community insights: {post.url}"
            )

        if "follow_up_research" in analysis:
            for research in analysis["follow_up_research"]:
                insights.append(f"Research: {research}")

        return insights[:5]  # Return top 5 insights

    @staticmethod
    def generate_learning_recommendations(
        analysis: Dict, post: SocialPost
    ) -> Dict[str, Any]:
        """Generate personalized learning recommendations"""

        return {
            "next_steps": analysis.get("follow_up_research", []),
            "related_skills": analysis.get("related_skills", []),
            "difficulty_level": analysis.get("complexity_level", "Unknown"),
            "estimated_time": analysis.get("time_to_consume", "Unknown"),
            "prerequisites": [],
            "learning_path": [],
        }


class TimeSensitivityDetector:
    """Detects time-sensitive content and estimates urgency"""

    @staticmethod
    def detect_time_sensitivity(
        post: SocialPost, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Heuristically detect if content is time-sensitive and estimate urgency"""

        reasons: List[str] = []
        content = (post.content or "") + "\n" + (analysis.get("ai_summary") or "")
        content_lower = content.lower()
        urgency = 0.0

        # Keyword cues
        urgent_terms = [
            "breaking",
            "just in",
            "urgent",
            "deadline",
            "today",
            "tonight",
            "hours",
            "minutes",
            "now",
            "alert",
            "update",
            "live",
            "launch",
            "announced",
            "vote",
            "earnings",
            "patch",
            "vulnerability",
            "security update",
        ]
        if any(t in content_lower for t in urgent_terms):
            reasons.append("Urgent language detected")
            urgency += 0.4

        # Category/type cues
        type_hint = (analysis.get("content_type") or "").lower()
        topic_hint = (analysis.get("topic") or "").lower()
        if any(
            k in (type_hint + " " + topic_hint)
            for k in [
                "news",
                "release",
                "incident",
                "vulnerability",
                "earnings",
                "announcement",
            ]
        ):
            reasons.append("News/incident category")
            urgency += 0.3

        # Recency
        try:
            created_at = (
                post.created_at
                if isinstance(post.created_at, datetime)
                else datetime.fromisoformat(str(post.created_at).replace("Z", "+00:00"))
            )
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            age_hours = (
                datetime.now(timezone.utc) - created_at
            ).total_seconds() / 3600.0
            if age_hours <= 6:
                reasons.append("Very recent (<6h)")
                urgency += 0.3
            elif age_hours <= 24:
                reasons.append("Recent (<24h)")
                urgency += 0.15
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Platform hints
        if post.platform in ("twitter", "threads"):
            urgency += 0.1

        urgency = max(0.0, min(1.0, urgency))
        is_time_sensitive = urgency >= 0.35

        # Relevance window suggestion
        if urgency >= 0.7:
            window = "same-day"
        elif urgency >= 0.45:
            window = "24-72h"
        elif urgency >= 0.35:
            window = "this-week"
        else:
            window = "evergreen"

        return {
            "time_sensitive": bool(is_time_sensitive),
            "urgency_score": float(urgency),
            "relevance_window": window,
            "time_sensitive_reasons": reasons,
        }


class RewriteGenerator:
    """Generates content rewrites for different personas"""

    @staticmethod
    def generate_rewrite(content: str, persona: str, target_platform: str) -> str:
        """Generate a persona-based rewrite of content"""

        # Basic rewrite logic - this would be enhanced with AI models
        rewrite_strategies = {
            "technical": {
                "twitter": f"🔥 {content[:240]} #tech #dev",
                "threads": f"{content}\n\n💡 Technical breakdown: [Detailed analysis would go here]",
                "reddit": f"**Technical Analysis:** {content}\n\n**Key Points:** [Extracted points]",
            },
            "builder": {
                "twitter": f"🚀 Building this: {content[:240]} #building #sideproject",
                "threads": f"{content}\n\n🛠️ Implementation notes: [Builder's perspective]",
                "reddit": f"**Builder's Take:** {content}\n\n**Build Status:** [Status update]",
            },
            "thought_leader": {
                "twitter": f"💭 Industry insight: {content[:240]} #leadership",
                "threads": f"{content}\n\n📈 Market impact: [Thought leader analysis]",
                "reddit": f"**Strategic Analysis:** {content}\n\n**Future Outlook:** [Predictions]",
            },
        }

        # Determine strategy based on persona
        if "technical" in persona.lower() or "developer" in persona.lower():
            strategy = rewrite_strategies["technical"]
        elif "builder" in persona.lower():
            strategy = rewrite_strategies["builder"]
        elif "leader" in persona.lower() or "thought" in persona.lower():
            strategy = rewrite_strategies["thought_leader"]
        else:
            strategy = rewrite_strategies["technical"]  # Default

        return strategy.get(target_platform, content)

    @staticmethod
    def adapt_for_platform(content: str, platform: str) -> str:
        """Adapt content for specific platform characteristics"""

        adaptations = {
            "twitter": {
                "max_length": 280,
                "hashtags": True,
                "emojis": True,
                "mentions": False,
            },
            "threads": {
                "max_length": 500,
                "hashtags": True,
                "emojis": True,
                "mentions": True,
            },
            "reddit": {
                "max_length": 10000,
                "hashtags": False,
                "emojis": False,
                "mentions": True,
                "markdown": True,
            },
        }

        rules = adaptations.get(platform, adaptations["twitter"])

        adapted = content

        # Truncate if too long
        if len(adapted) > rules["max_length"]:
            adapted = adapted[: rules["max_length"] - 3] + "..."

        # Add platform-specific elements
        if rules.get("hashtags") and "#" not in adapted:
            relevant_tags = ["#pris", "#tech", "#building", "#dev"]
            adapted += " " + " ".join(relevant_tags[:2])

        if rules.get("emojis"):
            if "🚀" not in adapted and len(adapted) > 100:
                adapted = "🚀 " + adapted
            elif "💡" not in adapted and "tech" in adapted.lower():
                adapted = "💡 " + adapted

        return adapted
