from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from .content_planner import ContentPlanner
from .post_processor import PostProcessor
from .prompt_builder import PromptBuilder
from .quality_gate import QualityGate
from .schemas import PersonaContext, RewriteRequest, RewriteResult
from .validators import FactCheckService, VoiceValidationService

if TYPE_CHECKING:
    from .legacy_adapter import LegacyRewriterAdapter

logger = logging.getLogger(__name__)


class ModularRewriter:
    """
    High-level entry point for the new modular rewriting pipeline.

    For the first iteration, this class delegates to the legacy adapter while
    exposing the new `RewriteRequest`/`RewriteResult` interfaces.  As we port
    individual stages (planner, prompt builder, validators, etc.) into dedicated
    components, this orchestrator will coordinate them before falling back to
    the adapter only when needed.
    """

    def __init__(
        self,
        *,
        legacy_adapter: Optional["LegacyRewriterAdapter"] = None,
        planner: Optional[ContentPlanner] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        post_processor: Optional[PostProcessor] = None,
        quality_gate: Optional[QualityGate] = None,
        fact_service: Optional[FactCheckService] = None,
        voice_service: Optional[VoiceValidationService] = None,
    ) -> None:
        # Lazy import to avoid circular dependency
        if legacy_adapter is None:
            from .legacy_adapter import LegacyRewriterAdapter
            legacy_adapter = LegacyRewriterAdapter()
        self.legacy_adapter = legacy_adapter
        self.planner = planner or ContentPlanner()
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.post_processor = post_processor or PostProcessor()
        self.quality_gate = quality_gate or QualityGate()
        self.fact_service = fact_service or FactCheckService()
        self.voice_service = voice_service or VoiceValidationService()

    async def rewrite(self, request: RewriteRequest) -> RewriteResult:
        """
        Rewrite content for the provided persona/platform.

        Parameters
        ----------
        request:
            Normalized rewrite request containing analysis metadata, persona
            context, platform, and any custom prompt/constraints.
        """

        logger.debug(
            "ModularRewriter: delegating rewrite for persona=%s platform=%s",
            request.persona.key,
            request.platform,
        )

        plan = self.planner.plan(request)
        draft = self.prompt_builder.build(request, plan)

        legacy_response = await self.legacy_adapter.rewrite(
            analyzed_content=request.analyzed_content,
            persona=request.persona.key,
            platform=request.platform,
            custom_prompt=draft.prompt,
            platform_constraints=request.platform_constraints,
            target_content_type=request.target_content_type,
        )

        rewritten_content = legacy_response.get("rewritten_content", "")
        processed_content = self.post_processor.run(rewritten_content)
        
        # Enforce platform length limits
        processed_content = self._enforce_length_limit(processed_content, request.platform)

        result = RewriteResult(
            persona=request.persona.key,
            platform=request.platform,
            rewritten_content=processed_content,
            quality_score=legacy_response.get("quality_score"),
            voice_consistency_score=legacy_response.get("voice_consistency_score"),
            fact_preservation_score=legacy_response.get("fact_preservation_score"),
            metadata={
                **legacy_response,
                "prompt_metadata": draft.prompt_metadata,
                "plan": {
                    "hook": plan.hook,
                    "angle": plan.angle,
                    "call_to_action": plan.call_to_action,
                },
                "voice_cues": plan.voice_cues,
            },
        )

        await self._run_validators(request, result)

        approved = self.quality_gate.approve(result)
        result.metadata["quality_approved"] = approved

        if not approved:
            logger.warning(
                "Quality gate rejected rewrite persona=%s platform=%s scores=%s",
                request.persona.key,
                request.platform,
                {
                    "quality": result.quality_score,
                    "voice": result.voice_consistency_score,
                    "fact": result.fact_preservation_score,
                },
            )

        return result

    def _enforce_length_limit(self, content: str, platform: str) -> str:
        """Truncate content to platform-specific limits if exceeded."""
        platform_limits = {
            "threads": 480,
            "twitter": 220,
            "telegram": 2000,
        }
        
        limit = platform_limits.get(platform.lower())
        if limit and len(content) > limit:
            original_len = len(content)
            # Try to truncate at sentence boundary
            truncated = content[:limit]
            last_period = truncated.rfind(".")
            last_newline = truncated.rfind("\n")
            cut_point = max(last_period, last_newline)
            
            if cut_point > limit * 0.7:  # Only use boundary if we keep 70%+ of content
                content = truncated[:cut_point + 1].strip()
            else:
                content = truncated.strip() + "…"
            
            logger.warning(
                "Truncated %s post from %d to %d chars",
                platform,
                original_len,
                len(content),
            )
        
        return content

    async def _run_validators(self, request: RewriteRequest, result: RewriteResult) -> None:
        fact_report = await self.fact_service.evaluate(request.analyzed_content, result.rewritten_content)
        if fact_report:
            result.fact_preservation_score = fact_report.get("preservation_score")
            result.metadata["fact_validation"] = fact_report

        voice_report = await self.voice_service.evaluate(request.persona.key, result.rewritten_content)
        if voice_report:
            result.voice_consistency_score = voice_report.get("consistency_score")
            result.metadata["voice_validation"] = voice_report


def build_persona_context(persona_key: str, persona_info: Optional[dict] = None) -> PersonaContext:
    """
    Helper that converts old-style persona dictionaries into `PersonaContext`.

    This lets existing callers migrate incrementally: they can pass whatever
    persona data they already have, and we normalize it for the modular API.
    """

    persona_info = persona_info or {}
    return PersonaContext(
        key=persona_key,
        name=persona_info.get("name"),
        language=persona_info.get("language", persona_info.get("default_language", "english")),
        tone=persona_info.get("tone"),
        platforms=persona_info.get("platforms", []),
    )


