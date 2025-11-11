#!/usr/bin/env python3
"""
Scoring utilities extracted from IntelligentContentAnalyzer.

Contains deterministic heuristics for persona fit, value/quality scoring,
topic/type inference, language guessing, and rewrite candidate checks.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from src.core.extraction.social_extractor_base import SocialPost
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------
# Persona fit heuristics
# ---------------------------

PERSONA_KEYWORDS = {
    "qronoya": [
        "productivity",
        "learning",
        "analysis",
        "execution",
        "improvement",
        "systems",
        "deep dive",
        "narrative",
    ],
    "aspandead": [
        "emotions",
        "relationships",
        "self worth",
        "vulnerability",
        "mindfulness",
        "mental health",
        "self care",
    ],
    "claimzilla": [
        "crypto",
        "defi",
        "market",
        "airdrop",
        "token",
        "trading",
        "chain",
        "bitcoin",
        "nft",
        "blockchain",
    ],
}


def compute_persona_fit(post: SocialPost, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Return persona fit scores and reasons."""
    summary_text = (analysis.get("ai_summary") or "") + " " + (post.content or "")
    summary_lower = summary_text.lower()

    persona_scores: Dict[str, float] = {}
    persona_reasons: Dict[str, List[str]] = {}

    for persona, keywords in PERSONA_KEYWORDS.items():
        score = 0.0
        reasons: List[str] = []
        for kw in keywords:
            if kw in summary_lower:
                score += 1.0
                reasons.append(f"Matched keyword '{kw}'")
        persona_scores[persona] = round(min(score / 5.0, 1.0), 2)  # normalize 0-1
        if reasons:
            persona_reasons[persona] = reasons

    # Pick the best persona
    best_persona = max(persona_scores, key=persona_scores.get, default=None)
    best_score = persona_scores.get(best_persona, 0.0) if best_persona else 0.0

    return {
        "scores": persona_scores,
        "reasons": persona_reasons,
        "best_persona": best_persona,
        "best_score": best_score,
    }


# ---------------------------
# Value / quality scoring
# ---------------------------

def score_value(summary: str, tags: List[str], concepts: List[str]) -> float:
    """Heuristic value score (0-10)."""
    value = 0.0
    if not summary:
        return value

    words = summary.split()
    length = len(words)
    value += min(length / 100.0, 6.0)  # reward longer summaries

    if tags:
        value += min(len(tags) * 0.5, 2.0)
    if concepts:
        value += min(len(concepts) * 0.5, 2.0)

    return round(min(value, 10.0), 2)


def score_quality(content: str, summary: str) -> float:
    """Heuristic quality score (0-10)."""
    if not summary:
        return 0.0

    quality = 5.0
    # Penalty for very short content
    if content and len(content) < 200:
        quality -= 1.0

    # Reward for longer summaries (assumed more detailed)
    quality += min(len(summary.split()) / 150.0, 3.0)

    # Basic heuristics for clarity
    if summary.strip().endswith("."):
        quality += 0.5

    return round(max(0.0, min(quality, 10.0)), 2)


# ---------------------------
# Topic / type / language heuristics
# ---------------------------

TOPIC_KEYWORDS = {
    "crypto": ["crypto", "defi", "bitcoin", "ethereum", "nft", "token", "airdrop"],
    "business": ["startup", "marketing", "sales", "growth", "customer", "revenue"],
    "productivity": ["productivity", "workflow", "system", "habit", "focus"],
    "learning": ["learn", "course", "tutorial", "study", "teacher", "education"],
    "tech": ["ai", "software", "framework", "code", "developer", "engineering"],
}

TYPE_KEYWORDS = {
    "guide": ["how to", "guide", "tutorial", "steps", "process"],
    "analysis": ["analysis", "breakdown", "deep dive", "insight"],
    "story": ["story", "journey", "experience", "narrative"],
    "news": ["breaking", "announced", "update", "released"],
}

LANGUAGE_KEYWORDS = {
    "english": ["the", "and", "is", "with"],
    "spanish": ["el", "la", "que", "para"],
    "french": ["le", "la", "et", "pour"],
}


def guess_topic(tags: List[str], concepts: List[str]) -> str:
    text = " ".join(tags + concepts).lower()
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return topic
    return "general"


def guess_type(post: SocialPost) -> str:
    content = (post.content or "").lower()
    for post_type, keywords in TYPE_KEYWORDS.items():
        if any(kw in content for kw in keywords):
            return post_type
    return "insight"


def guess_language(text: str) -> str:
    text_lower = (text or "").lower()
    for lang, keywords in LANGUAGE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return lang
    return "unknown"


# ---------------------------
# Rewrite candidate heuristic
# ---------------------------

def is_rewrite_candidate(
    analysis: Dict[str, Any],
    post: SocialPost,
    quality_score: float,
) -> bool:
    """Determine if a post is worth rewriting."""
    if quality_score < 5:
        return False

    summary = analysis.get("ai_summary") or ""
    if len(summary.split()) < 80:
        return False

    # Avoid rewriting very short or very long posts
    content_len = len(post.content or "")
    if content_len < 150 or content_len > 2000:
        return False

    return True

