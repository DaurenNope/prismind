import logging

logger = logging.getLogger(__name__)
"""
BEYONDLINES Data Schemas - Standardized Types
===========================================

This module defines the standardized data structures used throughout BEYONDLINES.
These TypedDict classes create contracts between components, ensuring:
- Analyzer produces exactly what Rewriter needs
- Discovery Engine receives complete signals
- Learning System gets proper user profile data
- All components speak the same language

Author: BEYONDLINES AI System
"""

from typing import Dict, List, Literal, Optional, TypedDict

# ============================================================================
# REWRITE ANGLES - For Content Transformation
# ============================================================================


class RewriteAngle(TypedDict):
    """
    How content should be rewritten for a specific persona.

    Used by: Analyzer → Rewriter
    Purpose: Provides distinct angles for each of the 5 personas
    """

    persona: Literal["technical", "builder", "learner", "trendsetter", "thought_leader"]
    angle: str  # How to approach this content for this persona
    hook: str  # The most compelling opening line
    key_points: List[str]  # 3-5 main points to emphasize
    target_audience: str  # Who this angle targets
    estimated_engagement: Literal["high", "medium", "low"]
    tone: str  # Writing tone (technical, action-oriented, educational, excited, authoritative)
    call_to_action: str  # What action to suggest to readers
    platform_fit: str  # Best platform/format (twitter_thread, linkedin_post, short_tweet)


# ============================================================================
# DISCOVERY SIGNALS - For Autonomous Discovery
# ============================================================================


class DiscoverySignals(TypedDict):
    """
    Signals that help discover similar high-quality content.

    Used by: Analyzer → Discovery Engine
    Purpose: Determine content worth and discoverability patterns
    """

    author_authority: Literal["high", "medium", "low"]  # Credibility assessment
    trend_relevance: Literal["emerging", "mainstream", "declining"]  # Topic lifecycle
    viral_potential: int  # 0-100 score for shareability
    discussion_quality: Literal["high", "medium", "low"]  # Conversation value
    unique_perspective: Literal["yes", "no"]  # Is this original or repetitive


# ============================================================================
# CONTENT FRESHNESS - For Timing & Relevance
# ============================================================================


class ContentFreshness(TypedDict):
    """
    How timely and relevant content is right now.

    Used by: Analyzer → Scheduler, Publisher
    Purpose: Determine optimal timing for rewriting and publishing
    """

    publication_age: str  # "X hours/days/weeks"
    still_relevant: Literal["yes", "no"]  # Is this still useful
    time_sensitivity: Literal["urgent", "timely", "evergreen"]  # How time-dependent


# ============================================================================
# MEDIA INSIGHT - For Vision Analysis Results
# ============================================================================


class MediaInsight(TypedDict):
    """
    AI vision analysis of an image/video from a post.

    Used by: Analyzer (Vision Model) → Analysis Storage
    Purpose: Extract value from visual content
    """

    media_url: str
    content_type: Literal[
        "diagram", "code", "screenshot", "infographic", "photo", "chart", "other"
    ]
    description: str  # What's shown (2-3 sentences)
    key_elements: List[str]  # Notable elements in the image
    extracted_text: str  # OCR text (if applicable)
    technical_concepts: List[str]  # Concepts visible in image
    educational_value: Literal["high", "medium", "low"]
    practical_insights: List[str]  # What can be learned
    adds_value: Literal["yes", "no"]  # Does this enhance understanding
    analyzed_with: Literal["gemini-vision", "basic", "none"]


# ============================================================================
# COMPLETE ANALYSIS - Full Output from Analyzer
# ============================================================================


class AnalyzedContent(TypedDict, total=False):
    """
    Complete analysis output from IntelligentContentAnalyzer.

    This is the COMPLETE contract - what Analyzer produces and what
    downstream components (Rewriter, Discovery, Scheduler) consume.

    Used by: Analyzer → All downstream components
    """

    # ===== CORE IDENTIFICATION =====
    post_id: str
    platform: Literal["twitter", "reddit", "threads", "other"]
    analyzed_at: str  # ISO timestamp
    analysis_version: str

    # ===== CONTENT CATEGORIZATION =====
    category: str  # Main category (e.g., "AI & Machine Learning")
    subcategory: str  # Specific subcategory (e.g., "AI Agents")
    content_type: str  # "Tutorial", "News", "Discussion", "Tool", etc.
    topics: List[str]  # 3-5 main topics
    key_concepts: List[str]  # Core concepts discussed

    # ===== CONTENT SUMMARY & VALUE =====
    ai_summary: str  # AI-generated summary (primary field, stored in DB)
    summary: Optional[str]  # Legacy field name (for backward compatibility)
    why_valuable: Optional[str]  # Why someone bookmarked this
    learning_value: Optional[str]  # What can be learned

    # ===== SENTIMENT & COMPLEXITY =====
    sentiment: Literal["Positive", "Negative", "Neutral", "Mixed"]
    sentiment_scores: Dict[str, float]  # VADER sentiment scores
    complexity_level: Literal["Beginner", "Intermediate", "Advanced", "Expert"]
    time_to_consume: str  # Estimated reading time

    # ===== ACTIONABLE CONTENT =====
    actionable_items: List[str]  # Specific actions to take
    practical_applications: List[str]  # How to apply this
    related_skills: List[str]  # Skills related to this content
    follow_up_research: List[str]  # What to research next

    # ===== QUALITY INDICATORS =====
    quality_indicators: List[str]  # Why this is high/low quality
    tags: List[str]  # Searchable keywords
    confidence_score: float  # 0.0-1.0 AI confidence

    # ===== AI SERVICE INFO =====
    ai_service: Literal["ollama", "mistral", "gemini", "basic", "deterministic"]

    # ===== SCORING =====
    value_score: float  # 0-10 overall value (standardized field name)
    quality_score: float  # 0-10 content quality (standardized field name)
    rewrite_score: Optional[float]  # 0-10 rewrite potential
    # Legacy field names (for backward compatibility)
    intelligent_value_score: Optional[float]  # Legacy: use value_score instead
    content_quality_score: Optional[float]  # Legacy: use quality_score instead
    is_rewrite_candidate: Optional[bool]  # Good for rewriting?

    # ===== NEW FIELDS (Week 1 Improvements) =====

    # For Content Rewriting
    rewrite_suggestions: Optional[List[Dict[str, Any]]]  # Creative rewrite suggestions (new format, preferred)
    rewrite_angles: Optional[List[RewriteAngle]]  # Legacy: 5 persona-specific angles (deprecated, use rewrite_suggestions)

    # For Discovery Engine
    discovery_signals: Optional[DiscoverySignals]  # Authority, trends, virality

    # For Timing & Publishing
    content_freshness: Optional[ContentFreshness]  # Age, relevance, urgency
    
    # For Persona/Profile Matching (NEW: Dynamic profile matching)
    profile_matches: Optional[Dict[str, float]]  # JSONB: profile_key -> score (0-100 scale)
    persona_fit_scores: Optional[Dict[str, float]]  # Legacy: persona_key -> score (0-10 scale)
    best_persona_key: Optional[str]  # Best matching persona/profile
    best_persona_score: Optional[float]  # Best match score (0-10)
    best_persona_reasons: Optional[List[str]]  # Reasons for best match

    # ===== OPTIONAL ENHANCEMENTS =====

    # Comment analysis (Reddit only)
    comment_insights: Optional[List[str]]

    # Media analysis (if post has images/videos)
    media_insights: Optional[Dict[str, any]]  # Contains MediaInsight objects

    # Visual content flags
    has_high_value_visuals: Optional[bool]  # Does this have great diagrams/code?
    visual_text_content: Optional[str]  # Text extracted from images

    # Learning recommendations
    actionable_insights: Optional[List[str]]
    learning_recommendations: Optional[Dict[str, any]]


# ============================================================================
# USER PROFILE - For Learning & Personalization
# ============================================================================


class UserInterest(TypedDict):
    """A single interest/topic the user cares about"""

    weight: float  # 0.0-1.0 strength of interest
    subtopics: List[str]  # Specific subtopics within this interest


class ContentPreferences(TypedDict):
    """What kinds of content the user prefers"""

    types: List[str]  # ["tutorial", "tool", "thread"]
    length: Literal["short", "medium", "long"]
    complexity: Literal["beginner", "intermediate", "advanced", "expert"]
    tone: Literal["technical", "casual", "formal", "conversational"]


class WritingStyle(TypedDict):
    """How the user writes/wants to write"""

    voice: Literal["authoritative", "friendly", "educational", "provocative"]
    structure: Literal["bullet-heavy", "paragraph-heavy", "mixed"]
    emoji_usage: Literal["none", "minimal", "moderate", "heavy"]
    technical_depth: Literal["high", "medium", "low"]


class UserProfile(TypedDict):
    """
    Complete user profile for personalization.

    Used by: Learning System → Analyzer, Discovery, Rewriter
    Purpose: Personalize everything to the user's preferences
    """

    user_id: str
    created_at: str
    last_updated: str

    # What they care about
    interests: Dict[str, UserInterest]  # {"ai": {weight: 0.9, subtopics: [...]}}

    # Content preferences
    content_preferences: ContentPreferences

    # Writing style
    writing_style: WritingStyle

    # Quality standards
    quality_threshold: float  # 0.0-1.0 minimum quality score

    # Personalized categories (not generic)
    categories: List[str]

    # Behavior stats
    total_bookmarks: int
    total_dismissals: int
    avg_engagement_time: float  # minutes


# ============================================================================
# CONCEPT GRAPH - For Knowledge Connections
# ============================================================================


class Concept(TypedDict):
    """A single concept extracted from content"""

    concept: str
    related_concepts: List[str]
    posts_count: int  # How many posts mention this
    first_seen: str  # ISO timestamp
    trending: bool  # Is this trending up
    user_interest_score: float  # 0.0-1.0 user's interest


class ConceptConnection(TypedDict):
    """A connection between two concepts"""

    concept_a: str
    concept_b: str
    connection_type: Literal["requires", "relates_to", "implements", "is_type_of"]
    strength: float  # 0.0-1.0
    posts_linking: int  # How many posts link these


# ============================================================================
# PUBLISHED CONTENT - For Tracking Published Posts
# ============================================================================


class PublishedPost(TypedDict):
    """A post that was published to social media"""

    published_id: str
    original_post_id: str  # Source post
    platform: Literal["twitter", "threads", "telegram"]
    persona: Literal["technical", "builder", "learner", "trendsetter", "thought_leader"]
    content: str  # The actual published content
    published_at: str  # ISO timestamp
    platform_post_id: Optional[str]  # ID from platform
    success: bool  # Did it publish successfully
    engagement: Optional[Dict[str, int]]  # Likes, comments, etc.


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def validate_analyzed_content(data: dict) -> bool:
    """
    Validate that analysis output has all required fields.

    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "post_id",
        "platform",
        "category",
        "ai_summary",  # Updated to match actual storage
    ]
    # Optional but recommended fields
    recommended_fields = [
        "value_score",
        "quality_score",
        "rewrite_suggestions",  # New format (preferred over rewrite_angles)
    ]

    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False

    # Validate rewrite_suggestions or rewrite_angles structure (if present)
    if "rewrite_suggestions" in data:
        if not isinstance(data["rewrite_suggestions"], list):
            logger.warning("rewrite_suggestions must be a list")
            return False
    elif "rewrite_angles" in data:
        # Legacy format validation
        if not isinstance(data["rewrite_angles"], list):
            logger.warning("rewrite_angles must be a list")
            return False

    return True


def get_rewrite_angle(
    analysis: AnalyzedContent, persona: str
) -> Optional[RewriteAngle]:
    """
    Extract the rewrite angle for a specific persona.

    Args:
        analysis: Complete analysis output
        persona: One of ["technical", "builder", "learner", "trendsetter", "thought_leader"]

    Returns:
        RewriteAngle for that persona or None
    """
    rewrite_angles = analysis.get("rewrite_angles", [])

    for angle in rewrite_angles:
        if angle.get("persona") == persona:
            return angle

    return None


# Example usage
if __name__ == "__main__":
    logger.info("BEYONDLINES Data Schemas")
    logger.info("=====================")
    logger.info()
    logger.info("Available schemas:")
    logger.info("  - RewriteAngle: Content transformation for each persona")
    logger.info("  - DiscoverySignals: Signals for discovering similar content")
    logger.info("  - ContentFreshness: Timing and relevance metrics")
    logger.info("  - MediaInsight: Vision AI analysis of images")
    logger.info("  - AnalyzedContent: Complete analysis output (main contract)")
    logger.info("  - UserProfile: User preferences and personalization")
    logger.info("  - Concept: Knowledge graph concepts")
    logger.info("  - ConceptConnection: Relationships between concepts")
    logger.info("  - PublishedPost: Tracking published content")
    logger.info()
    logger.info("These schemas ensure all BEYONDLINES components communicate with")
    logger.info("standardized, type-checked data structures.")
