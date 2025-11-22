from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .schemas import RewriteRequest
from .voice_fragments import VoiceFragmentLibrary

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RewritePlan:
    """Represents the high-level decisions for a rewrite."""

    hook: Optional[str]
    angle: Optional[str]
    call_to_action: Optional[str]
    notes: Dict[str, str] = field(default_factory=dict)
    human_draft: Optional[str] = None
    human_notes: Optional[str] = None
    voice_cues: List[Dict[str, str]] = field(default_factory=list)


class ContentPlanner:
    """
    Placeholder planner.

    Today it simply relays whatever angle metadata already exists on the
    analyzed content.  Over time we can augment this with classifiers or
    retrieval-augmented strategy selection.
    """

    def __init__(self) -> None:
        self.voice_library = VoiceFragmentLibrary()

    def plan(self, request: RewriteRequest) -> RewritePlan:
        raw_angles = request.analyzed_content.get("rewrite_angles") or []
        angles = raw_angles if isinstance(raw_angles, list) else []

        persona_angle = next(
            (a for a in angles if a.get("persona") == request.persona.key), None
        )

        if persona_angle is None:
            persona_angle = angles[0] if angles else {}

        if not persona_angle:
            persona_angle = {
                "hook": request.metadata.get("fallback_hook")
                or request.analyzed_content.get("primary_hook"),
                "angle": request.metadata.get("fallback_angle")
                or request.analyzed_content.get("primary_angle"),
                "cta": request.metadata.get("fallback_cta")
                or request.analyzed_content.get("call_to_action"),
                "notes": request.metadata.get("planner_notes")
                or request.analyzed_content.get("rewrite_notes"),
            }

        human_draft = (
            request.metadata.get("human_draft")
            or request.analyzed_content.get("human_draft")
        )
        human_notes = (
            request.metadata.get("human_notes")
            or request.analyzed_content.get("human_notes")
        )

        voice_cues = self.voice_library.select_fragments(
            request.persona.key, request.analyzed_content
        )

        if voice_cues:
            logger.debug(
                "Selected %d voice fragment(s) for persona=%s",
                len(voice_cues),
                request.persona.key,
            )

        return RewritePlan(
            hook=persona_angle.get("hook"),
            angle=persona_angle.get("angle"),
            call_to_action=persona_angle.get("cta"),
            notes={"source": persona_angle.get("notes", "")} if persona_angle.get("notes") else {},
            human_draft=human_draft,
            human_notes=human_notes,
            voice_cues=voice_cues,
        )


