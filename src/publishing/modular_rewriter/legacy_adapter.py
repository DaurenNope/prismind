from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from src.publishing.rewriter import ContentRewriter


class LegacyRewriterAdapter:
    """
    Thin wrapper around the existing monolithic `ContentRewriter`.

    This lets the new modular orchestrator expose a stable interface while we
    gradually migrate functionality out of the legacy implementation.  Once the
    modular pipeline is fully featured, this adapter can be removed.
    """

    def __init__(self, rewriter: Optional[ContentRewriter] = None) -> None:
        self._rewriter = rewriter or ContentRewriter()
        self._lock = asyncio.Lock()

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
        Delegate to `ContentRewriter.rewrite_analyzed_post`.

        The legacy class is not thread-safe when it comes to persona loading,
        so we serialize access with an asyncio lock.
        """

        async with self._lock:
            return await self._rewriter.rewrite_analyzed_post(
                analyzed_content=analyzed_content,
                persona=persona,
                platform=platform,
                custom_prompt=custom_prompt,
                platform_constraints=platform_constraints,
                target_content_type=target_content_type,
            )


