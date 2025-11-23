"""
Register specialized agents with existing framework

This module registers all specialized agents (Analyst, Skeptic, Historian) with the
AgentRegistry, sets up AgentMessaging for each agent, and ensures they're properly
integrated with the monitoring system.
"""

import os
import logging
from typing import List, Optional

from src.agents.registry import get_registry
from src.agents.messaging import AgentMessaging
from src.agents.specialized.analyst_agent import AnalystAgent
from src.agents.specialized.skeptic_agent import SkepticAgent
from src.agents.specialized.historian_agent import HistorianAgent

logger = logging.getLogger(__name__)


async def register_specialized_agents() -> List:
    """
    Register all specialized agents with framework.
    
    This function:
    1. Creates instances of all specialized agents
    2. Registers them with the AgentRegistry
    3. Sets up messaging for each agent
    4. Returns the list of registered agents
    
    Returns:
        List of registered agent instances
    """
    registry = get_registry()
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Create agents
    analyst = AnalystAgent()
    skeptic = SkepticAgent()
    historian = HistorianAgent()
    
    agents = [analyst, skeptic, historian]
    
    # Register with registry
    for agent in agents:
        try:
            registry.register(agent)
            logger.info(f"✅ Registered {agent.agent_name} (ID: {agent.agent_id})")
        except Exception as e:
            logger.error(f"❌ Failed to register {agent.agent_name}: {e}", exc_info=True)
            raise
    
    # Setup messaging for each agent
    for agent in agents:
        try:
            messaging = AgentMessaging(
                redis_url=redis_url,
                agent_id=agent.agent_id
            )
            await messaging.initialize()
            agent.set_event_publisher(messaging.get_publisher())
            logger.info(f"✅ Messaging setup for {agent.agent_id}")
        except Exception as e:
            logger.warning(f"⚠️ Messaging setup failed for {agent.agent_id}: {e}")
            # Continue even if messaging fails - agents can work without it
    
    logger.info("✅ All specialized agents registered")
    return agents


def register_specialized_agents_sync() -> List:
    """
    Synchronous wrapper for register_specialized_agents.
    
    Note: This will create an event loop if one doesn't exist, which may not
    be ideal in all contexts. Prefer using the async version when possible.
    
    Returns:
        List of registered agent instances
    """
    import asyncio
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to schedule this
            # For now, log a warning
            logger.warning(
                "Event loop is already running. Use register_specialized_agents() "
                "with await instead of register_specialized_agents_sync()"
            )
            # Try to run in executor or create task
            # For simplicity, we'll just log the warning
            return []
        else:
            return loop.run_until_complete(register_specialized_agents())
    except RuntimeError:
        # No event loop exists, create one
        return asyncio.run(register_specialized_agents())

