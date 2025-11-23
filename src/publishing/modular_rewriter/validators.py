from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from src.domain.publishing.fact_validator import FactValidator
from src.domain.publishing.voice_validator import VoiceValidator


class FactCheckService:
    """Async wrapper around the legacy FactValidator."""

    def __init__(
        self,
        validator: Optional[FactValidator] = None,
        critical_threshold: float = 0.7,
    ) -> None:
        self.validator = validator or FactValidator()
        self.critical_threshold = critical_threshold

    async def evaluate(self, analyzed_content: Dict[str, Any], rewritten_text: str) -> Optional[Dict[str, Any]]:
        source = self._extract_source_text(analyzed_content)
        if not source or not rewritten_text:
            return None

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.validator.validate_preservation(
                source=source,
                output=rewritten_text,
                critical_threshold=self.critical_threshold,
            ),
        )

    @staticmethod
    def _extract_source_text(analyzed_content: Dict[str, Any]) -> str:
        candidates = [
            analyzed_content.get("content"),
            analyzed_content.get("original_content"),
            analyzed_content.get("body"),
            analyzed_content.get("raw_text"),
            analyzed_content.get("summary"),
        ]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        return ""


class VoiceValidationService:
    """Async wrapper around the legacy VoiceValidator."""

    def __init__(self, validator: Optional[VoiceValidator] = None) -> None:
        self.validator = validator or VoiceValidator()

    async def evaluate(self, persona_key: str, rewritten_text: str) -> Optional[Dict[str, Any]]:
        if not rewritten_text:
            return None

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.validator.validate_voice(text=rewritten_text, persona=persona_key, return_details=True),
        )


