from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from .compat import CompatRewriter


class LegacyRewriterAdapter:
    """
    Thin wrapper around ModularRewriter via CompatRewriter.

    DEPRECATED: This adapter is kept for backward compatibility but now uses
    ModularRewriter under the hood. Consider migrating to ModularRewriter directly.
    """

    def __init__(self, rewriter: Optional["CompatRewriter"] = None) -> None:
        self._rewriter = rewriter
        self._lock = asyncio.Lock()

    @property
    def rewriter(self) -> "CompatRewriter":
        """Lazy initialization to avoid circular import recursion."""
        if self._rewriter is None:
            from .compat import CompatRewriter
            self._rewriter = CompatRewriter()
        return self._rewriter

    async def rewrite(
        self,
        analyzed_content: Dict[str, Any],
        persona: str,
        platform: str,
        *,
        custom_prompt: Optional[str] = None,
        platform_constraints: Optional[Dict[str, Any]] = None,
        target_content_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delegate to CompatRewriter.rewrite_analyzed_post (uses ModularRewriter).

        The compat layer provides the same interface as ContentRewriter.
        """

        async with self._lock:
            return await self.rewriter.rewrite_analyzed_post(
                analyzed_content=analyzed_content,
                persona=persona,
                platform=platform,
                custom_prompt=custom_prompt,
                platform_constraints=platform_constraints,
                target_content_type=target_content_type,
            )


