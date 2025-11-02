"""
PrisMind Data Schemas - Standardized Types
===========================================

This module defines the standardized data structures used throughout PrisMind.
These TypedDict classes create contracts between components, ensuring:
- Analyzer produces exactly what Rewriter needs
- Discovery Engine receives complete signals
- Learning System gets proper user profile data
- All components speak the same language

Author: PrisMind AI System
"""

from typing import TypedDict, List, Dict, Optional, Literal


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
    content_type: Literal["diagram", "code", "screenshot", "infographic", "photo", "chart", "other"]
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
    summary: str  # 2-3 sentence summary
    why_valuable: str  # Why someone bookmarked this
    learning_value: str  # What can be learned

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
    intelligent_value_score: float  # 0-10 overall value
    content_quality_score: float  # 0-10 content quality
    is_rewrite_candidate: bool  # Good for rewriting?

    # ===== NEW FIELDS (Week 1 Improvements) =====

    # For Content Rewriting
    rewrite_angles: List[RewriteAngle]  # 5 persona-specific angles

    # For Discovery Engine
    discovery_signals: DiscoverySignals  # Authority, trends, virality

    # For Timing & Publishing
    content_freshness: ContentFreshness  # Age, relevance, urgency

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
        'post_id', 'platform', 'category', 'summary',
        'rewrite_angles', 'discovery_signals', 'content_freshness'
    ]

    for field in required_fields:
        if field not in data:
            print(f"Missing required field: {field}")
            return False

    # Validate rewrite_angles structure
    if not isinstance(data['rewrite_angles'], list):
        print("rewrite_angles must be a list")
        return False

    if len(data['rewrite_angles']) != 5:
        print(f"rewrite_angles must have 5 personas, got {len(data['rewrite_angles'])}")
        return False

    return True


def get_rewrite_angle(analysis: AnalyzedContent, persona: str) -> Optional[RewriteAngle]:
    """
    Extract the rewrite angle for a specific persona.

    Args:
        analysis: Complete analysis output
        persona: One of ["technical", "builder", "learner", "trendsetter", "thought_leader"]

    Returns:
        RewriteAngle for that persona or None
    """
    rewrite_angles = analysis.get('rewrite_angles', [])

    for angle in rewrite_angles:
        if angle.get('persona') == persona:
            return angle

    return None


# Example usage
if __name__ == "__main__":
    print("PrisMind Data Schemas")
    print("=====================")
    print()
    print("Available schemas:")
    print("  - RewriteAngle: Content transformation for each persona")
    print("  - DiscoverySignals: Signals for discovering similar content")
    print("  - ContentFreshness: Timing and relevance metrics")
    print("  - MediaInsight: Vision AI analysis of images")
    print("  - AnalyzedContent: Complete analysis output (main contract)")
    print("  - UserProfile: User preferences and personalization")
    print("  - Concept: Knowledge graph concepts")
    print("  - ConceptConnection: Relationships between concepts")
    print("  - PublishedPost: Tracking published content")
    print()
    print("These schemas ensure all PrisMind components communicate with")
    print("standardized, type-checked data structures.")
