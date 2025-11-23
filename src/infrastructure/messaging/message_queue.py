"""
Message Queue System for Beyondlines
Provides reliable message processing with Redis Streams
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

import redis.asyncio as aioredis
from redis.asyncio import Redis

from src.shared.utils.exceptions import QueueError

T = TypeVar("T")
logger = logging.getLogger(__name__)


class MessageStatus(Enum):
    """Message processing status"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class QueuePriority(Enum):
    """Message priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class QueueMessage:
    """Message in the queue"""

    id: str
    payload: Any
    priority: QueuePriority = QueuePriority.NORMAL
    attempts: int = 0
    max_attempts: int = 3
    delay_until: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    status: MessageStatus = MessageStatus.PENDING
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "payload": self.payload,
            "priority": self.priority.value,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "delay_until": self.delay_until,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status.value,
            "error": self.error,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueMessage":
        """Create message from dictionary"""
        data["priority"] = QueuePriority(data["priority"])
        data["status"] = MessageStatus(data["status"])
        return cls(**data)


@dataclass
class QueueConfig:
    """Configuration for message queue"""

    stream_name: str
    consumer_group: str
    max_length: int = 10000
    consumer_timeout: int = 30
    batch_size: int = 10
    retry_delay: float = 60.0
    dead_letter_queue: str = "dead_letters"
    processing_timeout: int = 300


class MessageQueue:
    """Redis-based message queue implementation"""

    def __init__(self, redis_url: str, config: QueueConfig):
        self.redis_url = redis_url
        self.config = config
        self._redis: Optional[Redis] = None
        self._consumer_id: str = f"{config.consumer_group}-{uuid.uuid4().hex[:8]}"
        self._is_consuming = False
        self._handlers: Dict[str, Callable] = {}

    async def connect(self):
        """Connect to Redis"""
        try:
            self._redis = aioredis.from_url(self.redis_url, decode_responses=False)

            # Create consumer group if it doesn't exist
            try:
                await self._redis.xgroup_create(
                    self.config.stream_name,
                    self.config.consumer_group,
                    id="0",
                    mkstream=True,
                )
                logger.info(f"Created consumer group: {self.config.consumer_group}")
            except Exception as e:
                if "BUSYGROUP" not in str(e):
                    logger.warning(f"Consumer group creation warning: {e}")

            logger.info(f"Connected to Redis queue: {self.config.stream_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise QueueError(f"Redis connection failed: {e}")

    async def disconnect(self):
        """Disconnect from Redis"""
        if self._redis:
            await self._redis.close()
            logger.info("Disconnected from Redis")

    async def send(
        self,
        payload: Any,
        priority: QueuePriority = QueuePriority.NORMAL,
        delay: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send a message to the queue"""
        if not self._redis:
            raise QueueError("Redis connection not established")

        message = QueueMessage(
            id=str(uuid.uuid4()),
            payload=payload,
            priority=priority,
            delay_until=time.time() + delay if delay else None,
            metadata=metadata or {},
        )

        # Prepare message fields
        fields = {
            "id": message.id,
            "payload": json.dumps(message.payload),
            "priority": str(message.priority.value),
            "attempts": str(message.attempts),
            "max_attempts": str(message.max_attempts),
            "delay_until": str(message.delay_until) if message.delay_until else "",
            "created_at": str(message.created_at),
            "updated_at": str(message.updated_at),
            "status": message.status.value,
            "metadata": json.dumps(message.metadata),
        }

        # Send to Redis Stream
        message_id = await self._redis.xadd(
            self.config.stream_name, fields, maxlen=self.config.max_length
        )

        logger.debug(f"Sent message {message.id} to queue {self.config.stream_name}")
        return message_id.decode() if isinstance(message_id, bytes) else str(message_id)

    async def receive(self, timeout: Optional[int] = None) -> Optional[QueueMessage]:
        """Receive a message from the queue"""
        if not self._redis:
            raise QueueError("Redis connection not established")

        try:
            # Read messages from consumer group
            messages = await self._redis.xreadgroup(
                self.config.consumer_group,
                self._consumer_id,
                {self.config.stream_name: ">"},
                count=1,
                block=timeout or self.config.consumer_timeout * 1000,
            )

            if not messages:
                return None

            stream_name, stream_messages = messages[0]
            message_id, fields = stream_messages[0]

            # Parse message
            payload = json.loads(
                fields["payload"].decode()
                if isinstance(fields["payload"], bytes)
                else fields["payload"]
            )
            metadata = json.loads(
                fields["metadata"].decode()
                if isinstance(fields["metadata"], bytes)
                else fields["metadata"]
            )

            message = QueueMessage(
                id=fields["id"].decode()
                if isinstance(fields["id"], bytes)
                else fields["id"],
                payload=payload,
                priority=QueuePriority(
                    int(
                        fields["priority"].decode()
                        if isinstance(fields["priority"], bytes)
                        else fields["priority"]
                    )
                ),
                attempts=int(
                    fields["attempts"].decode()
                    if isinstance(fields["attempts"], bytes)
                    else fields["attempts"]
                ),
                max_attempts=int(
                    fields["max_attempts"].decode()
                    if isinstance(fields["max_attempts"], bytes)
                    else fields["max_attempts"]
                ),
                delay_until=float(fields["delay_until"].decode())
                if fields.get("delay_until")
                else None,
                created_at=float(
                    fields["created_at"].decode()
                    if isinstance(fields["created_at"], bytes)
                    else fields["created_at"]
                ),
                updated_at=float(
                    fields["updated_at"].decode()
                    if isinstance(fields["updated_at"], bytes)
                    else fields["updated_at"]
                ),
                status=MessageStatus(
                    fields["status"].decode()
                    if isinstance(fields["status"], bytes)
                    else fields["status"]
                ),
                metadata=metadata,
            )

            # Check if message is ready for processing
            if message.delay_until and message.delay_until > time.time():
                # Re-queue message for later processing
                await self._redis.xack(
                    self.config.stream_name, self.config.consumer_group, message_id
                )
                await self._redis.xadd(
                    self.config.stream_name,
                    {
                        "id": message.id,
                        "payload": json.dumps(message.payload),
                        "priority": str(message.priority.value),
                        "attempts": str(message.attempts),
                        "max_attempts": str(message.max_attempts),
                        "delay_until": str(message.delay_until),
                        "created_at": str(message.created_at),
                        "updated_at": str(message.updated_at),
                        "status": message.status.value,
                        "metadata": json.dumps(message.metadata),
                    },
                )
                return None

            message.status = MessageStatus.PROCESSING
            return message

        except Exception as e:
            logger.error(f"Error receiving message: {e}")
            raise QueueError(f"Failed to receive message: {e}")

    async def complete(self, message_id: str):
        """Mark a message as completed"""
        if not self._redis:
            raise QueueError("Redis connection not established")

        try:
            await self._redis.xack(
                self.config.stream_name, self.config.consumer_group, message_id
            )
            logger.debug(f"Completed message {message_id}")
        except Exception as e:
            logger.error(f"Error completing message {message_id}: {e}")
            raise QueueError(f"Failed to complete message: {e}")

    async def fail(self, message: QueueMessage, error: str):
        """Mark a message as failed and retry or send to dead letter queue"""
        if not self._redis:
            raise QueueError("Redis connection not established")

        message.attempts += 1
        message.error = error
        message.updated_at = time.time()

        if message.attempts >= message.max_attempts:
            # Send to dead letter queue
            message.status = MessageStatus.DEAD_LETTER
            await self._send_to_dead_letter_queue(message)
            await self._redis.xack(
                self.config.stream_name, self.config.consumer_group, message.id
            )
            logger.warning(
                f"Message {message.id} sent to dead letter queue after {message.attempts} attempts"
            )
        else:
            # Retry with delay
            message.status = MessageStatus.PENDING
            message.delay_until = time.time() + self.config.retry_delay

            # Re-add to stream with delay
            await self._redis.xack(
                self.config.stream_name, self.config.consumer_group, message.id
            )
            await self._redis.xadd(
                self.config.stream_name,
                {
                    "id": message.id,
                    "payload": json.dumps(message.payload),
                    "priority": str(message.priority.value),
                    "attempts": str(message.attempts),
                    "max_attempts": str(message.max_attempts),
                    "delay_until": str(message.delay_until),
                    "created_at": str(message.created_at),
                    "updated_at": str(message.updated_at),
                    "status": message.status.value,
                    "metadata": json.dumps(message.metadata),
                },
            )
            logger.warning(
                f"Message {message.id} failed, retry {message.attempts}/{message.max_attempts}"
            )

    async def _send_to_dead_letter_queue(self, message: QueueMessage):
        """Send message to dead letter queue"""
        if not self._redis:
            return

        await self._redis.xadd(
            self.config.dead_letter_queue,
            {
                "original_id": message.id,
                "payload": json.dumps(message.payload),
                "attempts": str(message.attempts),
                "error": message.error or "",
                "created_at": str(message.created_at),
                "failed_at": str(time.time()),
                "metadata": json.dumps(message.metadata),
            },
        )

    async def get_queue_info(self) -> Dict[str, Any]:
        """Get queue information and statistics"""
        if not self._redis:
            raise QueueError("Redis connection not established")

        try:
            # Get stream info
            stream_info = await self._redis.xinfo_stream(self.config.stream_name)
            group_info = await self._redis.xinfo_groups(self.config.stream_name)

            # Get pending messages count
            pending = await self._redis.xpending_range(
                self.config.stream_name, self.config.consumer_group, "-", "+", 1000
            )

            return {
                "stream_name": self.config.stream_name,
                "consumer_group": self.config.consumer_group,
                "total_messages": stream_info.get("length", 0),
                "pending_messages": len(pending),
                "groups": len(group_info),
                "consumer_id": self._consumer_id,
                "is_consuming": self._is_consuming,
            }

        except Exception as e:
            logger.error(f"Error getting queue info: {e}")
            return {"error": str(e)}

    async def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for specific message type"""
        self._handlers[message_type] = handler
        logger.info(f"Registered handler for message type: {message_type}")

    async def start_consuming(self):
        """Start consuming messages from the queue"""
        if not self._redis:
            raise QueueError("Redis connection not established")

        self._is_consuming = True
        logger.info(f"Started consuming messages from {self.config.stream_name}")

        while self._is_consuming:
            try:
                message = await self.receive(timeout=1)
                if message:
                    await self._process_message(message)
                else:
                    await asyncio.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(1)  # Delay before retrying

    async def stop_consuming(self):
        """Stop consuming messages"""
        self._is_consuming = False
        logger.info("Stopped consuming messages")

    async def _process_message(self, message: QueueMessage):
        """Process a single message"""
        try:
            # Get message type from metadata
            message_type = message.metadata.get("type", "default")

            # Find handler
            handler = self._handlers.get(message_type)
            if not handler:
                # Use default handler if available
                handler = self._handlers.get("default")
                if not handler:
                    logger.warning(f"No handler found for message type: {message_type}")
                    await self.fail(
                        message, f"No handler for message type: {message_type}"
                    )
                    return

            # Process message with timeout
            try:
                if asyncio.iscoroutinefunction(handler):
                    await asyncio.wait_for(
                        handler(message), timeout=self.config.processing_timeout
                    )
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: asyncio.wait_for(
                            asyncio.to_thread(handler, message),
                            timeout=self.config.processing_timeout,
                        ),
                    )

                await self.complete(message.id)
                logger.debug(f"Successfully processed message {message.id}")

            except asyncio.TimeoutError:
                error_msg = f"Message processing timeout after {self.config.processing_timeout}s"
                logger.error(f"Timeout processing message {message.id}: {error_msg}")
                await self.fail(message, error_msg)

            except Exception as e:
                error_msg = f"Message processing failed: {str(e)}"
                logger.error(f"Error processing message {message.id}: {error_msg}")
                await self.fail(message, error_msg)

        except Exception as e:
            logger.error(f"Unexpected error processing message: {e}")
            await self.fail(message, f"Unexpected error: {str(e)}")


class QueueManager:
    """Manages multiple message queues"""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.queues: Dict[str, MessageQueue] = {}

    async def create_queue(self, config: QueueConfig) -> MessageQueue:
        """Create a new message queue"""
        queue = MessageQueue(self.redis_url, config)
        await queue.connect()
        self.queues[config.stream_name] = queue
        return queue

    async def get_queue(self, stream_name: str) -> Optional[MessageQueue]:
        """Get an existing queue"""
        return self.queues.get(stream_name)

    async def stop_all(self):
        """Stop all queues"""
        for queue in self.queues.values():
            await queue.stop_consuming()
            await queue.disconnect()

    async def get_all_queue_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information for all queues"""
        info = {}
        for name, queue in self.queues.items():
            try:
                info[name] = await queue.get_queue_info()
            except Exception as e:
                logger.error(f"Error: {e}")
                info[name] = {"error": str(e)}
        return info


# Global queue manager
queue_manager: Optional[QueueManager] = None


async def init_queue_manager(redis_url: str) -> QueueManager:
    """Initialize global queue manager"""
    global queue_manager
    queue_manager = QueueManager(redis_url)
    return queue_manager


def get_queue_manager() -> Optional[QueueManager]:
    """Get global queue manager"""
    return queue_manager
