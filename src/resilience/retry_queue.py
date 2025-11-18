"""
Sophisticated Request Queue with Exponential Backoff and Circuit Breaker Integration
Provides resilient request processing with intelligent retry logic
"""

import asyncio
import json
import logging
import random
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from ..utils.exceptions import QueueTimeoutError, RetryExhaustedError
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(Enum):
    """Retry strategies"""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    FIBONACCI_BACKOFF = "fibonacci_backoff"


class RequestStatus(Enum):
    """Status of requests in queue"""

    PENDING = "pending"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(Enum):
    """Request priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    URGENT = 5


@dataclass
class RetryConfig:
    """Configuration for retry logic"""

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    retry_on: List[type] = field(default_factory=lambda: [Exception])


@dataclass
class Request:
    """Represents a request in the retry queue"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    func: Optional[Callable] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    status: RequestStatus = RequestStatus.PENDING
    attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    scheduled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[Exception] = None
    retry_config: Optional[RetryConfig] = None
    circuit_breaker: Optional[str] = None
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "priority": self.priority.value,
            "status": self.status.value,
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat(),
            "scheduled_at": self.scheduled_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "result": str(self.result) if self.result else None,
            "error": str(self.error) if self.error else None,
            "metadata": self.metadata,
            "tags": self.tags,
        }

    def calculate_next_delay(self) -> float:
        """Calculate delay for next retry attempt"""
        if not self.retry_config:
            return 0

        config = self.retry_config
        delay = 0

        if config.strategy == RetryStrategy.FIXED_INTERVAL:
            delay = config.base_delay

        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * self.attempts

        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (
                config.backoff_multiplier ** (self.attempts - 1)
            )

        elif config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = self._fibonacci(self.attempts) * config.base_delay

        # Apply max delay limit
        delay = min(delay, config.max_delay)

        # Add jitter if enabled
        if config.jitter:
            jitter_amount = delay * config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay += jitter

        return max(0, delay)

    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number"""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


class RetryQueue:
    """
    Sophisticated retry queue with exponential backoff and circuit breaker integration
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_queue_size: int = 1000,
        cleanup_interval: int = 60,
        circuit_breakers: Optional[Dict[str, CircuitBreaker]] = None,
    ):
        self.max_concurrent = max_concurrent
        self.max_queue_size = max_queue_size
        self.cleanup_interval = cleanup_interval

        # Request storage
        self._pending_requests: Dict[Priority, deque] = defaultdict(deque)
        self._active_requests: Dict[str, Request] = {}
        self._completed_requests: Dict[str, Request] = {}

        # Circuit breakers
        self.circuit_breakers: Dict[str, CircuitBreaker] = circuit_breakers or {}

        # Statistics
        self.stats = {
            "total_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "retry_attempts": 0,
            "circuit_breaker_trips": 0,
            "queue_full_rejections": 0,
        }

        # Control
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._condition = asyncio.Condition()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the retry queue"""
        self._running = True

        # Start worker tasks
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(worker)

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        logger.info(f"Retry queue started with {self.max_concurrent} workers")

    async def stop(self):
        """Stop the retry queue"""
        self._running = False

        # Cancel workers
        for worker in self._workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)

        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()

        logger.info("Retry queue stopped")

    async def submit(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        priority: Priority = Priority.NORMAL,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[str] = None,
        timeout: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Submit a request to the queue"""
        if len(self._active_requests) >= self.max_queue_size:
            self.stats["queue_full_rejections"] += 1
            raise QueueTimeoutError("Queue is full")

        request = Request(
            func=func,
            args=args,
            kwargs=kwargs or {},
            priority=priority,
            retry_config=retry_config,
            circuit_breaker=circuit_breaker,
            timeout=timeout,
            tags=tags or [],
            metadata=metadata or {},
        )

        # Add to appropriate priority queue
        self._pending_requests[priority].append(request)
        self.stats["total_requests"] += 1

        # Notify workers
        async with self._condition:
            self._condition.notify()

        logger.debug(f"Submitted request {request.id} with priority {priority.name}")
        return request.id

    async def get_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific request"""
        # Check active requests
        if request_id in self._active_requests:
            return self._active_requests[request_id].to_dict()

        # Check completed requests
        if request_id in self._completed_requests:
            return self._completed_requests[request_id].to_dict()

        # Search pending requests
        for priority_queue in self._pending_requests.values():
            for request in priority_queue:
                if request.id == request_id:
                    return request.to_dict()

        return None

    async def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request"""
        # Search pending requests
        for priority_queue in self._pending_requests.values():
            for i, request in enumerate(priority_queue):
                if request.id == request_id:
                    request.status = RequestStatus.CANCELLED
                    del priority_queue[i]
                    logger.info(f"Cancelled request {request_id}")
                    return True

        return False

    async def get_statistics(self) -> Dict[str, Any]:
        """Get queue statistics"""
        pending_count = sum(len(queue) for queue in self._pending_requests.values())
        active_count = len(self._active_requests)
        completed_count = len(self._completed_requests)

        return {
            **self.stats,
            "pending_requests": pending_count,
            "active_requests": active_count,
            "completed_requests": completed_count,
            "total_capacity": self.max_queue_size,
            "available_capacity": self.max_queue_size - pending_count - active_count,
            "workers_running": len(self._workers),
            "is_running": self._running,
            "circuit_breakers": {
                name: breaker.get_state()
                for name, breaker in self.circuit_breakers.items()
            },
        }

    async def _worker(self, worker_name: str):
        """Worker task for processing requests"""
        logger.debug(f"Worker {worker_name} started")

        while self._running:
            try:
                # Get next request
                request = await self._get_next_request()
                if not request:
                    await asyncio.sleep(0.1)
                    continue

                # Process the request
                await self._process_request(request, worker_name)

            except asyncio.CancelledError:
                logger.error(f"Error: {e}")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)

        logger.debug(f"Worker {worker_name} stopped")

    async def _get_next_request(self) -> Optional[Request]:
        """Get next request from priority queues"""
        async with self._condition:
            # Check priorities in order (highest first)
            for priority in sorted(Priority, key=lambda p: p.value, reverse=True):
                if self._pending_requests[priority]:
                    return self._pending_requests[priority].popleft()

            # Wait for new request
            await self._condition.wait()
            return None

    async def _process_request(self, request: Request, worker_name: str):
        """Process a single request"""
        request.status = RequestStatus.PROCESSING
        self._active_requests[request.id] = request

        logger.debug(f"Worker {worker_name} processing request {request.id}")

        while request.attempts < (
            request.retry_config.max_attempts if request.retry_config else 1
        ):
            try:
                request.attempts += 1
                self.stats["retry_attempts"] = max(
                    self.stats["retry_attempts"], request.attempts
                )

                # Check circuit breaker if configured
                if (
                    request.circuit_breaker
                    and request.circuit_breaker in self.circuit_breakers
                ):
                    breaker = self.circuit_breakers[request.circuit_breaker]
                    async with breaker:
                        result = await self._execute_request(request)
                else:
                    result = await self._execute_request(request)

                # Success!
                request.result = result
                request.status = RequestStatus.COMPLETED
                request.completed_at = datetime.now(timezone.utc)
                self.stats["completed_requests"] += 1

                # Move to completed
                del self._active_requests[request.id]
                self._completed_requests[request.id] = request

                logger.info(
                    f"Request {request.id} completed successfully after {request.attempts} attempts"
                )
                return

            except Exception as e:
                request.error = e
                logger.warning(
                    f"Request {request.id} attempt {request.attempts} failed: {e}"
                )

                # Check if we should retry
                if await self._should_retry(request, e):
                    # Calculate delay and schedule retry
                    delay = request.calculate_next_delay()
                    request.scheduled_at = datetime.now(timezone.utc) + timedelta(
                        seconds=delay
                    )
                    request.status = RequestStatus.RETRYING

                    # Wait for delay
                    if delay > 0:
                        await asyncio.sleep(delay)

                    continue
                else:
                    # No more retries
                    break

        # Request failed
        request.status = RequestStatus.FAILED
        request.completed_at = datetime.now(timezone.utc)
        self.stats["failed_requests"] += 1

        # Move to completed
        del self._active_requests[request.id]
        self._completed_requests[request.id] = request

        logger.error(
            f"Request {request.id} failed after {request.attempts} attempts: {request.error}"
        )

    async def _execute_request(self, request: Request) -> Any:
        """Execute the request function"""
        if not request.func:
            raise ValueError("Request has no function to execute")

        try:
            if asyncio.iscoroutinefunction(request.func):
                if request.timeout:
                    return await asyncio.wait_for(
                        request.func(*request.args, **request.kwargs),
                        timeout=request.timeout,
                    )
                else:
                    return await request.func(*request.args, **request.kwargs)
            else:
                if request.timeout:
                    return await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(
                            None, lambda: request.func(*request.args, **request.kwargs)
                        ),
                        timeout=request.timeout,
                    )
                else:
                    return await asyncio.get_event_loop().run_in_executor(
                        None, lambda: request.func(*request.args, **request.kwargs)
                    )

        except Exception as e:
            logger.error(f"Error: {e}")
            # Check if this error type should trigger a retry
            if request.retry_config:
                should_retry = any(
                    isinstance(e, retry_error)
                    for retry_error in request.retry_config.retry_on
                )
                if not should_retry:
                    # This error type shouldn't be retried
                    raise

            raise

    async def _should_retry(self, request: Request, error: Exception) -> bool:
        """Determine if request should be retried"""
        if not request.retry_config:
            return False

        # Check if max attempts reached
        if request.attempts >= request.retry_config.max_attempts:
            return False

        # Check if error type is in retry list
        should_retry = any(
            isinstance(error, retry_error)
            for retry_error in request.retry_config.retry_on
        )

        return should_retry

    async def _cleanup_loop(self):
        """Background cleanup of completed requests"""
        while self._running:
            try:
                await self._cleanup_completed_requests()
                await asyncio.sleep(self.cleanup_interval)
            except asyncio.CancelledError:
                logger.error(f"Error: {e}")
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(60)

    async def _cleanup_completed_requests(self):
        """Clean up old completed requests"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)

        to_remove = []
        for request_id, request in self._completed_requests.items():
            if request.completed_at and request.completed_at < cutoff_time:
                to_remove.append(request_id)

        for request_id in to_remove:
            del self._completed_requests[request_id]

        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} completed requests")


# Global queue instance
retry_queue: Optional[RetryQueue] = None


async def init_retry_queue(
    max_concurrent: int = 10,
    max_queue_size: int = 1000,
    circuit_breakers: Optional[Dict[str, CircuitBreaker]] = None,
) -> RetryQueue:
    """Initialize global retry queue"""
    global retry_queue
    retry_queue = RetryQueue(
        max_concurrent=max_concurrent,
        max_queue_size=max_queue_size,
        circuit_breakers=circuit_breakers,
    )
    await retry_queue.start()
    return retry_queue


def get_retry_queue() -> Optional[RetryQueue]:
    """Get global retry queue"""
    return retry_queue


# Decorator for automatic retry queue submission
def retry_queue_submit(
    priority: Priority = Priority.NORMAL,
    retry_config: Optional[RetryConfig] = None,
    circuit_breaker: Optional[str] = None,
    timeout: Optional[float] = None,
    tags: Optional[List[str]] = None,
):
    """Decorator to automatically submit functions to retry queue"""

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            queue = get_retry_queue()
            if not queue:
                # Fallback to direct execution
                return (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )

            # Submit to queue
            request_id = await queue.submit(
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                retry_config=retry_config,
                circuit_breaker=circuit_breaker,
                timeout=timeout,
                tags=tags,
            )

            # Wait for completion (in a real system, you might want to return the request_id instead)
            while True:
                status = await queue.get_status(request_id)
                if status and status["status"] in ["completed", "failed", "cancelled"]:
                    if status["status"] == "completed":
                        return status["result"]
                    elif status["status"] == "failed":
                        raise RetryExhaustedError(
                            f"Request {request_id} failed: {status['error']}"
                        )
                    else:
                        raise RetryExhaustedError(f"Request {request_id} was cancelled")
                await asyncio.sleep(0.1)

        return wrapper

    return decorator
