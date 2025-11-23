"""
Agent Registry

Central registry for all agents in the system.
Provides agent discovery, registration, dependency resolution, and health aggregation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from src.agents.base_agent import AgentError, AgentStatus, BaseAgent
from src.utils.exceptions import BEYONDLINESException

logger = logging.getLogger(__name__)


class RegistryError(BEYONDLINESException):
    """Exception raised for registry-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="REGISTRY_ERROR", **kwargs)


class AgentRegistry:
    """
    Central registry for all agents.

    Manages agent registration, discovery, dependency resolution, and health aggregation.
    """

    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_names: Dict[str, str] = {}  # name -> agent_id mapping
        self._initialized_agents: Set[str] = set()
        logger.info("Agent registry initialized")

    def register(self, agent: BaseAgent) -> None:
        """
        Register an agent with the registry.

        Args:
            agent: Agent instance to register

        Raises:
            RegistryError: If agent ID or name is already registered
        """
        if agent.agent_id in self._agents:
            raise RegistryError(
                f"Agent with ID '{agent.agent_id}' is already registered"
            )

        if agent.agent_name in self._agent_names:
            existing_id = self._agent_names[agent.agent_name]
            raise RegistryError(
                f"Agent with name '{agent.agent_name}' is already registered "
                f"(existing ID: {existing_id})"
            )

        self._agents[agent.agent_id] = agent
        self._agent_names[agent.agent_name] = agent.agent_id

        logger.info(
            f"Registered agent: {agent.agent_name} (ID: {agent.agent_id}, "
            f"Version: {agent.agent_version})"
        )

    def unregister(self, agent_id: str) -> None:
        """
        Unregister an agent from the registry.

        Args:
            agent_id: ID of the agent to unregister

        Raises:
            RegistryError: If agent is not found
        """
        if agent_id not in self._agents:
            raise RegistryError(f"Agent with ID '{agent_id}' is not registered")

        agent = self._agents[agent_id]
        del self._agents[agent_id]
        del self._agent_names[agent.agent_name]
        self._initialized_agents.discard(agent_id)

        logger.info(f"Unregistered agent: {agent.agent_name} (ID: {agent_id})")

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by ID.

        Args:
            agent_id: ID of the agent to retrieve

        Returns:
            Agent instance if found, None otherwise
        """
        return self._agents.get(agent_id)

    def get_agent_by_name(self, agent_name: str) -> Optional[BaseAgent]:
        """
        Get an agent by name.

        Args:
            agent_name: Name of the agent to retrieve

        Returns:
            Agent instance if found, None otherwise
        """
        agent_id = self._agent_names.get(agent_name)
        if agent_id:
            return self._agents.get(agent_id)
        return None

    def list_agents(self) -> List[Dict[str, Any]]:
        """
        List all registered agents.

        Returns:
            List of dictionaries containing agent information
        """
        agents = []
        for agent_id, agent in self._agents.items():
            agents.append(
                {
                    "agent_id": agent_id,
                    "agent_name": agent.agent_name,
                    "agent_version": agent.agent_version,
                    "status": agent.get_status().value,
                    "dependencies": agent.get_dependencies(),
                    "initialized": agent_id in self._initialized_agents,
                }
            )
        return agents

    def resolve_dependencies(self, agent_id: str) -> List[str]:
        """
        Resolve agent dependencies in order.

        Returns a list of agent IDs in the order they should be initialized,
        respecting dependency relationships.

        Args:
            agent_id: ID of the agent to resolve dependencies for

        Returns:
            List of agent IDs in initialization order

        Raises:
            RegistryError: If circular dependencies are detected or
                          if a dependency is not found
        """
        if agent_id not in self._agents:
            raise RegistryError(f"Agent '{agent_id}' is not registered")

        agent = self._agents[agent_id]
        resolved: List[str] = []
        visited: Set[str] = set()
        visiting: Set[str] = set()

        def visit(current_id: str) -> None:
            """Visit an agent and its dependencies (topological sort)."""
            if current_id in visiting:
                raise RegistryError(
                    f"Circular dependency detected involving agent '{current_id}'"
                )

            if current_id in visited:
                return

            visiting.add(current_id)

            current_agent = self._agents.get(current_id)
            if not current_agent:
                raise RegistryError(
                    f"Dependency '{current_id}' not found for agent '{agent_id}'"
                )

            # Visit all dependencies first
            for dep_id in current_agent.get_dependencies():
                if dep_id not in self._agents:
                    raise RegistryError(
                        f"Dependency '{dep_id}' not found for agent '{current_id}'"
                    )
                visit(dep_id)

            visiting.remove(current_id)
            visited.add(current_id)
            resolved.append(current_id)

        visit(agent_id)
        return resolved

    def resolve_all_dependencies(self) -> List[str]:
        """
        Resolve dependencies for all agents.

        Returns a list of all agent IDs in initialization order.

        Returns:
            List of agent IDs in initialization order

        Raises:
            RegistryError: If circular dependencies are detected
        """
        resolved: List[str] = []
        visited: Set[str] = set()
        visiting: Set[str] = set()

        def visit(agent_id: str) -> None:
            """Visit an agent and its dependencies (topological sort)."""
            if agent_id in visiting:
                raise RegistryError(
                    f"Circular dependency detected involving agent '{agent_id}'"
                )

            if agent_id in visited:
                return

            visiting.add(agent_id)

            agent = self._agents[agent_id]

            # Visit all dependencies first
            for dep_id in agent.get_dependencies():
                if dep_id not in self._agents:
                    raise RegistryError(
                        f"Dependency '{dep_id}' not found for agent '{agent_id}'"
                    )
                visit(dep_id)

            visiting.remove(agent_id)
            visited.add(agent_id)
            resolved.append(agent_id)

        # Visit all agents
        for agent_id in self._agents.keys():
            if agent_id not in visited:
                visit(agent_id)

        return resolved

    async def initialize_agent(self, agent_id: str) -> bool:
        """
        Initialize an agent and its dependencies.

        Args:
            agent_id: ID of the agent to initialize

        Returns:
            True if initialization was successful, False otherwise

        Raises:
            RegistryError: If agent is not found or dependencies fail
        """
        if agent_id not in self._agents:
            raise RegistryError(f"Agent '{agent_id}' is not registered")

        if agent_id in self._initialized_agents:
            logger.debug(f"Agent '{agent_id}' is already initialized")
            return True

        # Resolve dependencies
        init_order = self.resolve_dependencies(agent_id)

        # Initialize dependencies first
        for dep_id in init_order[:-1]:  # All except the last (target agent)
            if dep_id not in self._initialized_agents:
                logger.info(f"Initializing dependency: {dep_id}")
                agent = self._agents[dep_id]
                try:
                    success = await agent.initialize()
                    if not success:
                        raise RegistryError(
                            f"Failed to initialize dependency '{dep_id}' for agent '{agent_id}'"
                        )
                    self._initialized_agents.add(dep_id)
                except Exception as e:
                    raise RegistryError(
                        f"Error initializing dependency '{dep_id}': {e}"
                    ) from e

        # Initialize the target agent
        logger.info(f"Initializing agent: {agent_id}")
        agent = self._agents[agent_id]
        try:
            success = await agent.initialize()
            if success:
                self._initialized_agents.add(agent_id)
                agent._mark_initialized()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize agent '{agent_id}': {e}", exc_info=True)
            raise RegistryError(f"Error initializing agent '{agent_id}': {e}") from e

    async def initialize_all(self) -> Dict[str, bool]:
        """
        Initialize all agents in dependency order.

        Returns:
            Dictionary mapping agent IDs to initialization success status
        """
        results: Dict[str, bool] = {}
        init_order = self.resolve_all_dependencies()

        for agent_id in init_order:
            try:
                if agent_id not in self._initialized_agents:
                    success = await self.initialize_agent(agent_id)
                    results[agent_id] = success
                else:
                    results[agent_id] = True
            except Exception as e:
                logger.error(f"Failed to initialize agent '{agent_id}': {e}", exc_info=True)
                results[agent_id] = False

        return results

    async def aggregate_health(self) -> Dict[str, Any]:
        """
        Aggregate health status from all agents.

        Returns:
            Dictionary containing aggregated health information
        """
        health_data = {
            "total_agents": len(self._agents),
            "initialized_agents": len(self._initialized_agents),
            "healthy_agents": 0,
            "unhealthy_agents": 0,
            "agents": {},
            "overall_healthy": True,
        }

        for agent_id, agent in self._agents.items():
            try:
                health = await agent.health_check()
                is_healthy = health.get("healthy", False)
                health_data["agents"][agent_id] = health

                if is_healthy:
                    health_data["healthy_agents"] += 1
                else:
                    health_data["unhealthy_agents"] += 1
                    health_data["overall_healthy"] = False
            except Exception as e:
                logger.error(
                    f"Error getting health for agent '{agent_id}': {e}", exc_info=True
                )
                health_data["agents"][agent_id] = {
                    "error": str(e),
                    "healthy": False,
                }
                health_data["unhealthy_agents"] += 1
                health_data["overall_healthy"] = False

        return health_data

    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary containing registry statistics
        """
        status_counts: Dict[str, int] = {}
        for agent in self._agents.values():
            status = agent.get_status().value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_agents": len(self._agents),
            "initialized_agents": len(self._initialized_agents),
            "status_breakdown": status_counts,
        }


# Global registry instance
_registry: Optional[AgentRegistry] = None


def get_registry() -> AgentRegistry:
    """
    Get the global agent registry instance.

    Returns:
        Global AgentRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (mainly for testing)."""
    global _registry
    _registry = None



