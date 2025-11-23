"""
Base Agent Framework

Abstract base class for all agents in the system.
Provides common functionality including lifecycle management, metrics, events, and health checks.
"""

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from src.shared.utils.exceptions import BEYONDLINESException

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration"""

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    STOPPED = "stopped"


class AgentError(BEYONDLINESException):
    """Exception raised for agent-related errors"""

    def __init__(self, message: str, agent_id: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if agent_id:
            details.update({"agent_id": agent_id})
        super().__init__(message, error_code="AGENT_ERROR", details=details, **kwargs)


class BaseAgent(ABC):
    """
    Abstract base class for all agents.

    All agents must inherit from this class and implement the required abstract methods.
    The base class provides:
    - Lifecycle management (initialize, execute, shutdown)
    - Status tracking
    - Metrics collection
    - Event publishing/subscribing
    - Health checks
    - Dependency management
    """

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        agent_version: str = "1.0.0",
        dependencies: Optional[List[str]] = None,
    ):
        """
        Initialize the base agent.

        Args:
            agent_id: Unique identifier for the agent
            agent_name: Human-readable name for the agent
            agent_version: Version string for the agent
            dependencies: List of other agent IDs this agent depends on
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.agent_version = agent_version
        self.dependencies = dependencies or []
        self.status = AgentStatus.IDLE
        self.metrics: Dict[str, Any] = {}
        self._event_subscriptions: List[str] = []
        self._event_publisher: Optional[Any] = None
        self._initialized = False
        self._start_time: Optional[float] = None
        self._last_health_check: Optional[float] = None

        # Initialize default metrics
        self.metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "tasks_total": 0,
            "execution_time_avg": 0.0,
            "execution_time_total": 0.0,
            "last_execution_time": 0.0,
            "uptime_seconds": 0.0,
            "error_count": 0,
            "last_error": None,
        }

        logger.info(
            f"Initialized agent: {self.agent_name} (ID: {self.agent_id}, "
            f"Version: {self.agent_version})"
        )

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the agent.

        This method should:
        - Set up any required resources
        - Validate configuration
        - Connect to external services if needed
        - Prepare the agent for execution

        Returns:
            True if initialization was successful, False otherwise

        Raises:
            AgentError: If initialization fails
        """
        pass

    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task.

        This is the main execution method that should be implemented by each agent.
        The task dictionary contains the task-specific data.

        Args:
            task: Dictionary containing task data and parameters

        Returns:
            Dictionary containing execution results

        Raises:
            AgentError: If task execution fails
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the agent.

        Returns a dictionary containing health status information.

        Returns:
            Dictionary with health check results including:
            - status: Current agent status
            - healthy: Boolean indicating if agent is healthy
            - metrics: Current metrics snapshot
            - dependencies: Status of dependencies
            - uptime: Agent uptime in seconds
            - last_health_check: Timestamp of last health check
        """
        current_time = time.time()
        self._last_health_check = current_time

        # Calculate uptime
        uptime = 0.0
        if self._start_time:
            uptime = current_time - self._start_time

        # Determine if agent is healthy
        healthy = (
            self.status != AgentStatus.ERROR
            and self.status != AgentStatus.STOPPED
            and self._initialized
        )

        health_data = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_version": self.agent_version,
            "status": self.status.value,
            "healthy": healthy,
            "initialized": self._initialized,
            "metrics": self.metrics.copy(),
            "dependencies": self.dependencies,
            "uptime_seconds": uptime,
            "last_health_check": current_time,
        }

        logger.debug(f"Health check for {self.agent_id}: {health_data}")
        return health_data

    async def shutdown(self) -> None:
        """
        Shutdown the agent gracefully.

        This method should:
        - Stop any running tasks
        - Close connections
        - Clean up resources
        - Save state if needed
        """
        logger.info(f"Shutting down agent: {self.agent_name} (ID: {self.agent_id})")

        self.status = AgentStatus.STOPPED

        # Publish shutdown event
        self.publish_event("agent.shutdown", {"agent_id": self.agent_id})

        logger.info(f"Agent {self.agent_id} shutdown complete")

    def publish_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publish an event.

        Events are published to the message queue system for other agents
        or services to consume.

        Args:
            event_type: Type/category of the event
            data: Event data dictionary
        """
        if not self._event_publisher:
            logger.warning(
                f"Event publisher not set for agent {self.agent_id}, "
                f"event '{event_type}' not published"
            )
            return

        try:
            event = {
                "event_type": event_type,
                "agent_id": self.agent_id,
                "agent_name": self.agent_name,
                "timestamp": time.time(),
                "data": data,
            }

            # Use the event publisher if available
            if hasattr(self._event_publisher, "publish"):
                # If it's an async method, schedule it (fire and forget)
                if asyncio.iscoroutinefunction(self._event_publisher.publish):
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(self._event_publisher.publish(event_type, event))
                        else:
                            # If no running loop, this is a sync context - log warning
                            logger.warning(
                                f"Cannot publish async event from sync context for agent {self.agent_id}"
                            )
                    except RuntimeError:
                        # No event loop available
                        logger.warning(
                            f"No event loop available to publish event for agent {self.agent_id}"
                        )
                else:
                    # Sync method
                    self._event_publisher.publish(event_type, event)
            else:
                logger.warning(
                    f"Event publisher does not have publish method for agent {self.agent_id}"
                )

            logger.debug(f"Published event '{event_type}' from agent {self.agent_id}")

        except Exception as e:
            logger.error(
                f"Failed to publish event '{event_type}' from agent {self.agent_id}: {e}",
                exc_info=True,
            )

    def subscribe_to_events(self, event_types: List[str]) -> None:
        """
        Subscribe to specific event types.

        Args:
            event_types: List of event type strings to subscribe to
        """
        self._event_subscriptions.extend(event_types)
        logger.info(
            f"Agent {self.agent_id} subscribed to events: {', '.join(event_types)}"
        )

    def record_metric(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a metric.

        Metrics are stored in the agent's metrics dictionary and can be
        used for monitoring and observability.

        Args:
            name: Metric name
            value: Metric value (numeric)
            tags: Optional tags for the metric (key-value pairs)
        """
        metric_key = name
        if tags:
            # Create a composite key with tags
            tag_str = "_".join(f"{k}:{v}" for k, v in sorted(tags.items()))
            metric_key = f"{name}_{tag_str}"

        self.metrics[metric_key] = {
            "value": value,
            "timestamp": time.time(),
            "tags": tags or {},
        }

        logger.debug(f"Recorded metric '{metric_key}' = {value} for agent {self.agent_id}")

    def _update_execution_metrics(self, execution_time: float, success: bool) -> None:
        """
        Update execution-related metrics.

        Internal method to update metrics after task execution.

        Args:
            execution_time: Time taken to execute the task in seconds
            success: Whether the execution was successful
        """
        self.metrics["tasks_total"] += 1
        self.metrics["last_execution_time"] = execution_time

        if success:
            self.metrics["tasks_completed"] += 1
        else:
            self.metrics["tasks_failed"] += 1
            self.metrics["error_count"] += 1

        # Update average execution time
        total_time = self.metrics["execution_time_total"] + execution_time
        total_tasks = self.metrics["tasks_total"]
        self.metrics["execution_time_total"] = total_time
        self.metrics["execution_time_avg"] = total_time / total_tasks if total_tasks > 0 else 0.0

    def _set_status(self, status: AgentStatus) -> None:
        """
        Set the agent status.

        Internal method to update agent status and publish status change events.

        Args:
            status: New status for the agent
        """
        old_status = self.status
        self.status = status

        if old_status != status:
            logger.info(
                f"Agent {self.agent_id} status changed: {old_status.value} -> {status.value}"
            )
            self.publish_event(
                "agent.status_change",
                {
                    "agent_id": self.agent_id,
                    "old_status": old_status.value,
                    "new_status": status.value,
                },
            )

    def _mark_initialized(self) -> None:
        """Mark the agent as initialized and start uptime tracking."""
        self._initialized = True
        self._start_time = time.time()
        self._set_status(AgentStatus.IDLE)
        logger.info(f"Agent {self.agent_id} initialized and ready")

    def set_event_publisher(self, publisher: Any) -> None:
        """
        Set the event publisher for this agent.

        Args:
            publisher: Event publisher instance (from messaging integration)
        """
        self._event_publisher = publisher
        logger.debug(f"Event publisher set for agent {self.agent_id}")

    def get_status(self) -> AgentStatus:
        """
        Get the current agent status.

        Returns:
            Current agent status
        """
        return self.status

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.

        Returns:
            Copy of the current metrics dictionary
        """
        return self.metrics.copy()

    def get_dependencies(self) -> List[str]:
        """
        Get agent dependencies.

        Returns:
            List of agent IDs this agent depends on
        """
        return self.dependencies.copy()

