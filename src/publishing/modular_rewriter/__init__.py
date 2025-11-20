"""
Modular rewriter package.

This package will gradually replace the legacy monolithic rewriter with a
composable architecture: planner → prompt builder → generation → validation →
RAG feedback.  For now, the orchestrator can fall back to the existing
`ContentRewriter` so callers can start integrating against the new interfaces
without losing functionality.
"""

from .schemas import RewriteRequest, RewriteResult
from .orchestrator import ModularRewriter

__all__ = ["RewriteRequest", "RewriteResult", "ModularRewriter"]

