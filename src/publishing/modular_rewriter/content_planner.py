from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .schemas import RewriteRequest


@dataclass(slots=True)
class RewritePlan:
    """Represents the high-level decisions for a rewrite."""

    hook: Optional[str]
    angle: Optional[str]
    call_to_action: Optional[str]
    notes: Dict[str, str] = field(default_factory=dict)
    human_draft: Optional[str] = None
    human_notes: Optional[str] = None


class ContentPlanner:
    """
    Placeholder planner.

    Today it simply relays whatever angle metadata already exists on the
    analyzed content.  Over time we can augment this with classifiers or
    retrieval-augmented strategy selection.
    """

    def plan(self, request: RewriteRequest) -> RewritePlan:
        angles = request.analyzed_content.get("rewrite_angles") or []
        persona_angle = next(
            (a for a in angles if a.get("persona") == request.persona.key), angles[0] if angles else {}
        )

        human_draft = (
            request.metadata.get("human_draft")
            or request.analyzed_content.get("human_draft")
        )
        human_notes = (
            request.metadata.get("human_notes")
            or request.analyzed_content.get("human_notes")
        )

        return RewritePlan(
            hook=persona_angle.get("hook"),
            angle=persona_angle.get("angle"),
            call_to_action=persona_angle.get("cta"),
            notes={"source": persona_angle.get("notes", "")} if persona_angle.get("notes") else {},
            human_draft=human_draft,
            human_notes=human_notes,
        )


