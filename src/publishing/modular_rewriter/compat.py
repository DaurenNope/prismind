"""
Compatibility wrapper for ContentRewriter migration.

This module provides a compatibility interface that matches the old ContentRewriter.rewrite_analyzed_post()
method signature, making it easy to migrate code from ContentRewriter to ModularRewriter.
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .orchestrator import ModularRewriter

from .persona_manager import PersonaManager

logger = logging.getLogger(__name__)


def build_persona_context(persona_key: str, persona_info: Optional[dict] = None):
    """Lazy import wrapper for build_persona_context."""
    from .orchestrator import build_persona_context as _build_persona_context
    return _build_persona_context(persona_key, persona_info)

# Global instance for backward compatibility with get_rewriter()
_rewriter_instance: Optional["CompatRewriter"] = None


def create_compat_rewriter() -> "CompatRewriter":
    """Create a compatibility rewriter instance."""
    return CompatRewriter()


def get_rewriter() -> "CompatRewriter":
    """
    Get global rewriter instance (compatibility with old get_rewriter() function).
    
    This replaces the old ContentRewriter.get_rewriter() function.
    """
    global _rewriter_instance
    if _rewriter_instance is None:
        _rewriter_instance = CompatRewriter()
    return _rewriter_instance


class CompatRewriter:
    """
    Compatibility wrapper around ModularRewriter that provides the same interface
    as the deprecated ContentRewriter.rewrite_analyzed_post() method.
    
    This makes it easy to migrate code by simply replacing:
        from src.domain.publishing.rewriter import ContentRewriter
        rewriter = ContentRewriter()
        
    With:
        from src.domain.publishing.modular_rewriter.compat import create_compat_rewriter
        rewriter = create_compat_rewriter()
    
    The rewrite_analyzed_post() method signature and return format remain the same.
    """
    
    def __init__(self, modular_rewriter: Optional["ModularRewriter"] = None):
        self._rewriter = modular_rewriter
        self._persona_manager = PersonaManager()
    
    @property
    def rewriter(self) -> "ModularRewriter":
        """Lazy initialization to avoid circular import recursion."""
        if self._rewriter is None:
            from .orchestrator import ModularRewriter
            self._rewriter = ModularRewriter()
        return self._rewriter
    
    async def rewrite_analyzed_post(
        self,
        analyzed_content: Dict[str, Any],
        persona: str,
        platform: str = "auto",
        generate_variations: int = 1,
        custom_prompt: Optional[str] = None,
        platform_constraints: Optional[Dict[str, Any]] = None,
        target_content_type: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Rewrite analyzed content (compatibility interface).
        
        This method matches the signature of ContentRewriter.rewrite_analyzed_post()
        but uses ModularRewriter under the hood.
        
        Args:
            analyzed_content: Full analysis from IntelligentContentAnalyzer
            persona: Persona key (e.g., "qronoya", "aspandead")
            platform: Target platform
            generate_variations: Number of variations to generate (ignored for now)
            custom_prompt: Optional pre-built prompt
            platform_constraints: Optional platform constraints
            target_content_type: Optional content type
            language: Optional language override
            
        Returns:
            Dict with rewritten_content and metadata (same format as ContentRewriter)
        """
        from .schemas import RewriteRequest
        
        # Get persona context
        persona_context = self._persona_manager.get(persona)
        
        # Extract language from analyzed_content if not provided
        if not language:
            analyzed_lang = analyzed_content.get("language", "").lower()
            if analyzed_lang in ["ru", "russian", "ru-ru"]:
                language = "russian"
            elif analyzed_lang in ["en", "english", "en-us", "en-us"]:
                language = "english"
            # If still not set, use persona default (but default to English, not Russian)
            if not language:
                language = persona_context.language or "english"
        
        # Override language if provided or extracted
        if language:
            # Create a new PersonaContext with language override
            from .schemas import PersonaContext
            persona_context = PersonaContext(
                key=persona_context.key,
                name=persona_context.name,
                language=language,
                tone=persona_context.tone,
                platforms=persona_context.platforms,
            )
        
        # Handle platform "auto" - use platform from analyzed content or default to "threads"
        if platform == "auto":
            platform = analyzed_content.get("platform", "threads")
        
        # Create rewrite request
        request = RewriteRequest(
            analyzed_content=analyzed_content,
            persona=persona_context,
            platform=platform,
            custom_prompt=custom_prompt,
            platform_constraints=platform_constraints,
            target_content_type=target_content_type,
            metadata={**kwargs} if kwargs else {},
        )
        
        # Rewrite using ModularRewriter
        result = await self.rewriter.rewrite(request)
        
        # Convert RewriteResult to dict format matching ContentRewriter return
        return {
            "persona": result.persona,
            "persona_name": persona_context.name or persona,
            "persona_emoji": self._get_persona_emoji(persona),
            "platform": result.platform,
            "platform_fit": result.metadata.get("platform_fit", "single_post"),
            "original_post_id": analyzed_content.get("post_id"),
            "original_platform": analyzed_content.get("platform"),
            "original_url": analyzed_content.get("url", ""),
            "rewritten_content": result.rewritten_content,
            "angle_used": result.metadata.get("plan", {}).get("angle", ""),
            "hook_used": result.metadata.get("plan", {}).get("hook", ""),
            "tone_used": result.metadata.get("plan", {}).get("tone", ""),
            "call_to_action": result.metadata.get("plan", {}).get("call_to_action", ""),
            "quality_score": result.quality_score or 0.0,
            "voice_consistency_score": result.voice_consistency_score or 0.0,
            "fact_preservation_score": result.fact_preservation_score or 0.0,
            "quality_approved": result.metadata.get("quality_approved", False),
            # Include all other metadata
            **result.metadata,
        }
    
    def _get_persona_emoji(self, persona_key: str) -> str:
        """Get emoji for persona (fallback if not in metadata)."""
        emoji_map = {
            "qronoya": "💡",
            "aspandead": "🖤",
            "claimzilla": "💎",
        }
        return emoji_map.get(persona_key, "✨")
    
    # Expose other methods that might be called
    async def rewrite_for_persona(
        self,
        content: Dict[str, Any],
        persona: str,
        platform: str = "auto",
    ) -> Dict[str, Any]:
        """
        Compatibility method for rewrite_for_persona.
        
        This is a simplified interface that accepts content dict directly.
        """
        # Treat content as analyzed_content if it has analysis fields
        # Otherwise create a minimal analyzed_content structure
        analyzed_content = content.copy()
        
        # If content doesn't look like analyzed content, wrap it
        if "content" in content and "tldr" not in content:
            analyzed_content = {
                "content": content.get("content", ""),
                "title": content.get("title", ""),
                "url": content.get("url", ""),
                "platform": content.get("platform", "unknown"),
                "category": content.get("category", "Technology"),
                "topics": content.get("topics", []),
                "tldr": content.get("tldr", content.get("content_summary", "")),
                **{k: v for k, v in content.items() if k not in ["content", "title", "url", "platform"]},
            }
        
        return await self.rewrite_analyzed_post(
            analyzed_content=analyzed_content,
            persona=persona,
            platform=platform,
        )
    
    def get_available_personas(self) -> List[Dict[str, str]]:
        """
        Get list of available personas.
        
        Returns:
            List of dictionaries with keys: id, name, emoji, audience, style
        """
        personas = []
        config_dir = Path(__file__).resolve().parents[3] / "config" / "personas"
        
        # Emoji map for known personas (fallback)
        emoji_map = {
            "qronoya": "💡",
            "aspandead": "🖤",
            "claimzilla": "💎",
            "cryptoniard": "🔐",
            "macro-maverick": "📊",
        }
        
        # Audience and style descriptions (fallback)
        default_info = {
            "qronoya": {
                "audience": "tech professionals, entrepreneurs, career seekers",
                "style": "Basic but smart - practical tech advice and career insights",
            },
            "aspandead": {
                "audience": "humans seeking connection and truth",
                "style": "Deep writer - emotional depth, metaphors, unfiltered observations",
            },
            "claimzilla": {
                "audience": "crypto anons, defi degens, airdrop hunters",
                "style": "Crypto reply guy - alpha drops, market insights, technical breakdowns",
            },
        }
        
        if not config_dir.exists():
            logger.warning(f"Personas directory not found: {config_dir}")
            return personas
        
        # Load personas from config/personas/*.json files
        for persona_file in config_dir.glob("*.json"):
            # Skip examples and voice fragments files
            if persona_file.name.endswith("_examples.json") or persona_file.name.endswith("_voice_fragments.json"):
                continue
            
            persona_key = persona_file.stem
            try:
                with open(persona_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Extract persona info
                name = data.get("name", persona_key.title())
                emoji = data.get("emoji", emoji_map.get(persona_key, "🎭"))
                
                # Extract audience - try multiple fields
                audience = (
                    data.get("audience") or
                    (default_info.get(persona_key, {}).get("audience") if persona_key in default_info else None) or
                    "general audience"
                )
                
                # Extract style - try multiple fields
                style = (
                    data.get("style") or
                    data.get("voice_description") or
                    data.get("description") or
                    (default_info.get(persona_key, {}).get("style") if persona_key in default_info else None) or
                    ""
                )
                
                personas.append({
                    "id": persona_key,
                    "name": name,
                    "emoji": emoji,
                    "audience": audience,
                    "style": style,
                })
                
                logger.debug(f"Loaded persona: {persona_key} ({name})")
            except Exception as e:
                logger.warning(f"Failed to load persona from {persona_file}: {e}")
        
        return personas

