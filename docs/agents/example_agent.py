"""
Example Agent Implementation

This example demonstrates how to create a complete agent using the agent framework.
"""

import asyncio
import logging
from typing import Any, Dict

from src.agents import (
    AgentConfig,
    AgentMessaging,
    BaseAgent,
    AgentStatus,
    get_registry,
    load_agent_config,
)

logger = logging.getLogger(__name__)


class ExampleAgent(BaseAgent):
    """
    Example agent that processes data and publishes results.
    
    This agent demonstrates:
    - Configuration loading
    - Task execution
    - Event publishing
    - Metrics recording
    - Error handling
    """

    def __init__(self, agent_id: str = "example_agent", agent_name: str = "Example Agent"):
        """Initialize the example agent."""
        super().__init__(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_version="1.0.0",
            dependencies=[],  # No dependencies
        )
        self.config: AgentConfig | None = None
        self.messaging: AgentMessaging | None = None
        self.processed_count = 0

    async def initialize(self) -> bool:
        """
        Initialize the agent.
        
        Loads configuration, sets up messaging, and prepares for execution.
        """
        try:
            logger.info(f"Initializing {self.agent_name}...")

            # Load configuration
            self.config = load_agent_config(self.agent_id)
            logger.info(f"Loaded configuration for {self.agent_id}")

            # Check feature flags
            if self.config.is_feature_enabled("messaging"):
                # Initialize messaging
                redis_url = self.config.get("redis.url", "redis://localhost:6379")
                self.messaging = AgentMessaging(redis_url, self.agent_id)
                await self.messaging.initialize()

                # Set up event publisher
                publisher = self.messaging.get_publisher()
                self.set_event_publisher(publisher)

                # Subscribe to events
                subscriber = self.messaging.get_subscriber()
                subscriber.subscribe("task.requested", self._handle_task_request)
                await subscriber.start_consuming()

                logger.info("Messaging initialized")

            # Mark as initialized
            self._mark_initialized()
            logger.info(f"{self.agent_name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize {self.agent_name}: {e}", exc_info=True)
            self._set_status(AgentStatus.ERROR)
            return False

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a task.
        
        Args:
            task: Task dictionary containing:
                - action: Action to perform
                - data: Data to process
                - options: Optional processing options
        
        Returns:
            Dictionary with execution results
        """
        start_time = asyncio.get_event_loop().time()
        self._set_status(AgentStatus.RUNNING)

        try:
            action = task.get("action", "process")
            data = task.get("data", {})
            options = task.get("options", {})

            logger.info(f"Executing task: {action}")

            # Process based on action
            if action == "process":
                result = await self._process_data(data, options)
            elif action == "analyze":
                result = await self._analyze_data(data, options)
            else:
                raise ValueError(f"Unknown action: {action}")

            # Record metrics
            execution_time = asyncio.get_event_loop().time() - start_time
            self._update_execution_metrics(execution_time, success=True)
            self.record_metric("task_execution_time", execution_time, tags={"action": action})
            self.processed_count += 1

            # Publish event
            self.publish_event(
                "task.completed",
                {
                    "task_id": task.get("id"),
                    "action": action,
                    "result": result,
                },
            )

            self._set_status(AgentStatus.IDLE)
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            execution_time = asyncio.get_event_loop().time() - start_time
            self._update_execution_metrics(execution_time, success=False)
            self.record_metric("task_errors", 1, tags={"action": task.get("action", "unknown")})
            self._set_status(AgentStatus.ERROR)

            # Publish error event
            self.publish_event(
                "task.failed",
                {
                    "task_id": task.get("id"),
                    "error": str(e),
                },
            )

            return {"success": False, "error": str(e)}

    async def _process_data(self, data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Process data (example implementation)."""
        # Simulate processing
        await asyncio.sleep(0.1)

        # Apply rate limiting if configured
        if self.config:
            rate_limit = self.config.get_rate_limit("process")
            # Apply rate limiting logic here

        return {
            "processed": True,
            "data_size": len(str(data)),
            "options_applied": list(options.keys()),
        }

    async def _analyze_data(self, data: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data (example implementation)."""
        # Simulate analysis
        await asyncio.sleep(0.2)

        return {
            "analyzed": True,
            "insights": ["insight1", "insight2"],
            "confidence": 0.85,
        }

    async def _handle_task_request(self, event_data: Dict[str, Any]) -> None:
        """Handle task request event."""
        logger.info(f"Received task request event: {event_data}")
        task = event_data.get("task", {})
        if task:
            await self.execute(task)

    async def shutdown(self) -> None:
        """Shutdown the agent gracefully."""
        logger.info(f"Shutting down {self.agent_name}...")

        # Stop messaging
        if self.messaging:
            await self.messaging.shutdown()

        # Call parent shutdown
        await super().shutdown()

        logger.info(f"{self.agent_name} shutdown complete")


async def main():
    """Example usage of the agent."""
    # Create and register agent
    agent = ExampleAgent()
    registry = get_registry()
    registry.register(agent)

    # Initialize agent
    await registry.initialize_agent("example_agent")

    # Execute some tasks
    tasks = [
        {"id": "task1", "action": "process", "data": {"value": 1}},
        {"id": "task2", "action": "analyze", "data": {"value": 2}},
    ]

    for task in tasks:
        result = await agent.execute(task)
        print(f"Task {task['id']} result: {result}")

    # Check health
    health = await agent.health_check()
    print(f"Agent health: {health}")

    # Get metrics
    metrics = agent.get_metrics()
    print(f"Agent metrics: {metrics}")

    # Shutdown
    await agent.shutdown()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())



