from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class PersonaContext:
    """Metadata about the persona we are rewriting for."""

    key: str
    name: Optional[str] = None
    language: str = "english"
    tone: Optional[str] = None
    platforms: List[str] = field(default_factory=list)


@dataclass
class RewriteRequest:
    """Normalized input for the modular rewriter."""

    analyzed_content: Dict[str, Any]
    persona: PersonaContext
    platform: str
    custom_prompt: Optional[str] = None
    platform_constraints: Optional[Dict[str, Any]] = None
    target_content_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RewriteDraft:
    """Intermediate representation after planning/prompting."""

    prompt: str
    max_tokens: int
    prompt_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RewriteResult:
    """Final response returned to callers."""

    persona: str
    platform: str
    rewritten_content: str
    quality_score: Optional[float] = None
    voice_consistency_score: Optional[float] = None
    fact_preservation_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


