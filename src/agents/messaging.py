"""
Agent Messaging Integration

Provides message queue integration for agents, including event publishing,
subscribing, and task queue management with retry logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from src.infrastructure.messaging.message_queue import (
    MessageQueue,
    QueueConfig,
    QueueMessage,
    QueuePriority,
    get_queue_manager,
    init_queue_manager,
)
from src.shared.utils.exceptions import QueueError

logger = logging.getLogger(__name__)


class AgentEventPublisher:
    """
    Event publisher for agents.

    Handles publishing events to the message queue system.
    """

    def __init__(self, queue: MessageQueue):
        """
        Initialize the event publisher.

        Args:
            queue: MessageQueue instance to use for publishing
        """
        self.queue = queue
        self._event_stream = f"agent_events"
        logger.debug(f"AgentEventPublisher initialized with queue: {queue.config.stream_name}")

    async def publish(
        self, event_type: str, event_data: Dict[str, Any], priority: QueuePriority = QueuePriority.NORMAL
    ) -> str:
        """
        Publish an event.

        Args:
            event_type: Type/category of the event
            event_data: Event data dictionary
            priority: Priority level for the event

        Returns:
            Message ID of the published event
        """
        try:
            message_id = await self.queue.send(
                payload=event_data,
                priority=priority,
                metadata={"type": "event", "event_type": event_type},
            )
            logger.debug(f"Published event '{event_type}' with ID: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish event '{event_type}': {e}", exc_info=True)
            raise QueueError(f"Failed to publish event: {e}") from e


class AgentEventSubscriber:
    """
    Event subscriber for agents.

    Handles subscribing to and receiving events from the message queue system.
    """

    def __init__(self, queue: MessageQueue, agent_id: str):
        """
        Initialize the event subscriber.

        Args:
            queue: MessageQueue instance to use for subscribing
            agent_id: ID of the agent subscribing to events
        """
        self.queue = queue
        self.agent_id = agent_id
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        logger.debug(f"AgentEventSubscriber initialized for agent: {agent_id}")

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Callback function to handle the event
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.info(
            f"Agent {self.agent_id} subscribed to event type '{event_type}'"
        )

    async def start_consuming(self) -> None:
        """Start consuming events from the queue."""
        if self._running:
            logger.warning(f"Event subscriber for agent {self.agent_id} is already running")
            return

        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_events())
        logger.info(f"Started event consumption for agent {self.agent_id}")

    async def stop_consuming(self) -> None:
        """Stop consuming events from the queue."""
        if not self._running:
            return

        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped event consumption for agent {self.agent_id}")

    async def _consume_events(self) -> None:
        """Internal method to consume events from the queue."""
        while self._running:
            try:
                message = await self.queue.receive(timeout=1)
                if message:
                    await self._handle_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error consuming events for agent {self.agent_id}: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(1)  # Brief delay before retrying

    async def _handle_message(self, message: QueueMessage) -> None:
        """Handle a received message."""
        try:
            event_data = message.payload
            event_type = message.metadata.get("event_type", "unknown")

            # Get handlers for this event type
            handlers = self._handlers.get(event_type, [])
            if not handlers:
                # Try wildcard handler
                handlers = self._handlers.get("*", [])

            if handlers:
                # Call all handlers
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event_data)
                        else:
                            handler(event_data)
                    except Exception as e:
                        logger.error(
                            f"Error in event handler for '{event_type}': {e}",
                            exc_info=True,
                        )
            else:
                logger.debug(
                    f"No handlers found for event type '{event_type}' "
                    f"for agent {self.agent_id}"
                )

            # Acknowledge message
            await self.queue.complete(message.id)

        except Exception as e:
            logger.error(
                f"Error handling message for agent {self.agent_id}: {e}",
                exc_info=True,
            )
            await self.queue.fail(message, str(e))


class AgentTaskQueue:
    """
    Task queue for agents.

    Manages task queuing, execution, and retry logic.
    """

    def __init__(self, queue: MessageQueue, agent_id: str):
        """
        Initialize the task queue.

        Args:
            queue: MessageQueue instance to use
            agent_id: ID of the agent using this task queue
        """
        self.queue = queue
        self.agent_id = agent_id
        self._task_handler: Optional[Callable] = None
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        logger.debug(f"AgentTaskQueue initialized for agent: {agent_id}")

    def set_handler(self, handler: Callable[[Dict[str, Any]], Any]) -> None:
        """
        Set the task handler function.

        Args:
            handler: Function to handle tasks (can be async or sync)
        """
        self._task_handler = handler
        logger.debug(f"Task handler set for agent {self.agent_id}")

    async def enqueue_task(
        self,
        task: Dict[str, Any],
        priority: QueuePriority = QueuePriority.NORMAL,
        delay: Optional[float] = None,
    ) -> str:
        """
        Enqueue a task for processing.

        Args:
            task: Task data dictionary
            priority: Priority level for the task
            delay: Optional delay in seconds before processing

        Returns:
            Message ID of the enqueued task
        """
        try:
            message_id = await self.queue.send(
                payload=task,
                priority=priority,
                delay=delay,
                metadata={"type": "task", "agent_id": self.agent_id},
            )
            logger.debug(f"Enqueued task for agent {self.agent_id} with ID: {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to enqueue task for agent {self.agent_id}: {e}", exc_info=True)
            raise QueueError(f"Failed to enqueue task: {e}") from e

    async def start_processing(self) -> None:
        """Start processing tasks from the queue."""
        if self._running:
            logger.warning(f"Task queue for agent {self.agent_id} is already processing")
            return

        if not self._task_handler:
            raise QueueError(f"No task handler set for agent {self.agent_id}")

        self._running = True
        self._consumer_task = asyncio.create_task(self._process_tasks())
        logger.info(f"Started task processing for agent {self.agent_id}")

    async def stop_processing(self) -> None:
        """Stop processing tasks from the queue."""
        if not self._running:
            return

        self._running = False
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped task processing for agent {self.agent_id}")

    async def _process_tasks(self) -> None:
        """Internal method to process tasks from the queue."""
        while self._running:
            try:
                message = await self.queue.receive(timeout=1)
                if message:
                    await self._handle_task(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error processing tasks for agent {self.agent_id}: {e}",
                    exc_info=True,
                )
                await asyncio.sleep(1)  # Brief delay before retrying

    async def _handle_task(self, message: QueueMessage) -> None:
        """Handle a task message."""
        if not self._task_handler:
            logger.error(f"No task handler set for agent {self.agent_id}")
            await self.queue.fail(message, "No task handler set")
            return

        try:
            task_data = message.payload

            # Execute the task handler
            if asyncio.iscoroutinefunction(self._task_handler):
                await self._task_handler(task_data)
            else:
                await asyncio.get_event_loop().run_in_executor(
                    None, self._task_handler, task_data
                )

            # Acknowledge message
            await self.queue.complete(message.id)
            logger.debug(f"Completed task {message.id} for agent {self.agent_id}")

        except Exception as e:
            logger.error(
                f"Error handling task {message.id} for agent {self.agent_id}: {e}",
                exc_info=True,
            )
            await self.queue.fail(message, str(e))


class AgentMessaging:
    """
    Unified messaging interface for agents.

    Provides event publishing, subscribing, and task queue management.
    """

    def __init__(
        self,
        redis_url: str,
        agent_id: str,
        event_stream: str = "agent_events",
        task_stream: Optional[str] = None,
    ):
        """
        Initialize agent messaging.

        Args:
            redis_url: Redis connection URL
            agent_id: ID of the agent
            event_stream: Stream name for events
            task_stream: Stream name for tasks (defaults to agent-specific stream)
        """
        self.redis_url = redis_url
        self.agent_id = agent_id
        self.event_stream = event_stream
        self.task_stream = task_stream or f"agent_tasks_{agent_id}"

        self._queue_manager: Optional[Any] = None
        self._event_queue: Optional[MessageQueue] = None
        self._task_queue: Optional[MessageQueue] = None
        self._publisher: Optional[AgentEventPublisher] = None
        self._subscriber: Optional[AgentEventSubscriber] = None
        self._task_queue_handler: Optional[AgentTaskQueue] = None
        self._initialized = False

        logger.debug(f"AgentMessaging initialized for agent: {agent_id}")

    async def initialize(self) -> None:
        """Initialize messaging connections."""
        if self._initialized:
            return

        try:
            # Initialize queue manager
            self._queue_manager = await init_queue_manager(self.redis_url)

            # Create event queue
            event_config = QueueConfig(
                stream_name=self.event_stream,
                consumer_group=f"agent_events_{self.agent_id}",
            )
            self._event_queue = await self._queue_manager.create_queue(event_config)

            # Create task queue
            task_config = QueueConfig(
                stream_name=self.task_stream,
                consumer_group=f"agent_tasks_{self.agent_id}",
            )
            self._task_queue = await self._queue_manager.create_queue(task_config)

            # Create publisher and subscriber
            self._publisher = AgentEventPublisher(self._event_queue)
            self._subscriber = AgentEventSubscriber(self._event_queue, self.agent_id)

            # Create task queue handler
            self._task_queue_handler = AgentTaskQueue(self._task_queue, self.agent_id)

            self._initialized = True
            logger.info(f"AgentMessaging initialized for agent: {self.agent_id}")

        except Exception as e:
            logger.error(
                f"Failed to initialize messaging for agent {self.agent_id}: {e}",
                exc_info=True,
            )
            raise QueueError(f"Failed to initialize messaging: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown messaging connections."""
        if not self._initialized:
            return

        try:
            if self._subscriber:
                await self._subscriber.stop_consuming()

            if self._task_queue_handler:
                await self._task_queue_handler.stop_processing()

            if self._queue_manager:
                await self._queue_manager.stop_all()

            self._initialized = False
            logger.info(f"AgentMessaging shutdown for agent: {self.agent_id}")

        except Exception as e:
            logger.error(
                f"Error shutting down messaging for agent {self.agent_id}: {e}",
                exc_info=True,
            )

    def get_publisher(self) -> AgentEventPublisher:
        """
        Get the event publisher.

        Returns:
            AgentEventPublisher instance

        Raises:
            QueueError: If messaging is not initialized
        """
        if not self._initialized or not self._publisher:
            raise QueueError("Messaging not initialized")
        return self._publisher

    def get_subscriber(self) -> AgentEventSubscriber:
        """
        Get the event subscriber.

        Returns:
            AgentEventSubscriber instance

        Raises:
            QueueError: If messaging is not initialized
        """
        if not self._initialized or not self._subscriber:
            raise QueueError("Messaging not initialized")
        return self._subscriber

    def get_task_queue(self) -> AgentTaskQueue:
        """
        Get the task queue handler.

        Returns:
            AgentTaskQueue instance

        Raises:
            QueueError: If messaging is not initialized
        """
        if not self._initialized or not self._task_queue_handler:
            raise QueueError("Messaging not initialized")
        return self._task_queue_handler



