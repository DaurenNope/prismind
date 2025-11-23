"""
Agents package for BEYONDLINES.

This package contains the agent framework foundation and implementations
of various AI agents used in the system.
"""

from src.agents.base_agent import AgentError, AgentStatus, BaseAgent
from src.agents.config import AgentConfig, load_agent_config
from src.agents.messaging import (
    AgentEventPublisher,
    AgentEventSubscriber,
    AgentMessaging,
    AgentTaskQueue,
)
from src.agents.registry import AgentRegistry, RegistryError, get_registry, reset_registry

# Agent implementations
from src.agents.rewriter_agent import RewriterAgent, get_rewriter_agent

__all__ = [
    # Base Agent
    "BaseAgent",
    "AgentStatus",
    "AgentError",
    # Registry
    "AgentRegistry",
    "RegistryError",
    "get_registry",
    "reset_registry",
    # Messaging
    "AgentMessaging",
    "AgentEventPublisher",
    "AgentEventSubscriber",
    "AgentTaskQueue",
    # Configuration
    "AgentConfig",
    "load_agent_config",
    # Agent Implementations
    "RewriterAgent",
    "get_rewriter_agent",
]
