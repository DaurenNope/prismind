"""
Modular rewriter package.

This package will gradually replace the legacy monolithic rewriter with a
composable architecture: planner → prompt builder → generation → validation →
RAG feedback.  For now, the orchestrator can fall back to the existing
`ContentRewriter` so callers can start integrating against the new interfaces
without losing functionality.
"""

from .compat import CompatRewriter, create_compat_rewriter, get_rewriter
from .orchestrator import ModularRewriter, build_persona_context
from .schemas import RewriteRequest, RewriteResult

__all__ = [
    "RewriteRequest",
    "RewriteResult",
    "ModularRewriter",
    "build_persona_context",
    "CompatRewriter",
    "create_compat_rewriter",
    "get_rewriter",
]

