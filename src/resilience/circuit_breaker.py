"""
Circuit Breaker Pattern Implementation for Beyondlines
Provides fault tolerance for external service calls
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from ..utils.exceptions import CircuitBreakerOpenException

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, calls fail fast
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception type that triggers circuit
    success_threshold: int = 2  # Successes needed to close circuit in half-open
    timeout: float = 30.0  # Individual call timeout


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring"""

    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0
    state_changes: int = 0


class CircuitBreaker:
    """Circuit breaker implementation with async support"""

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        metrics_collector: Optional[Callable] = None,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.metrics = CircuitBreakerMetrics()
        self.state = CircuitState.CLOSED
        self.metrics_collector = metrics_collector
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        """Async context manager entry"""
        if not await self._can_execute():
            raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is OPEN")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if exc_type is not None:
            await self._on_failure()
        else:
            await self._on_success()

    def call(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator for circuit breaker protection"""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async with self:
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection"""
        async with self:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

    async def _can_execute(self) -> bool:
        """Check if execution is allowed"""
        async with self._lock:
            self.metrics.total_requests += 1

            if self.state == CircuitState.CLOSED:
                return True

            if self.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                if (
                    time.time() - self.metrics.last_failure_time
                ) >= self.config.recovery_timeout:
                    self._transition_to(CircuitState.HALF_OPEN)
                    return True
                return False

            if self.state == CircuitState.HALF_OPEN:
                return True

            return False

    async def _on_success(self):
        """Handle successful execution"""
        async with self._lock:
            self.metrics.success_count += 1
            self.metrics.last_success_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                if self.metrics.success_count >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
                    self.metrics.failure_count = 0

    async def _on_failure(self):
        """Handle failed execution"""
        async with self._lock:
            self.metrics.failure_count += 1
            self.metrics.total_failures += 1
            self.metrics.last_failure_time = time.time()

            if self.state == CircuitState.CLOSED:
                if self.metrics.failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
            elif self.state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState):
        """Transition to new state and record metrics"""
        old_state = self.state
        self.state = new_state
        self.metrics.state_changes += 1

        logger.info(
            f"Circuit breaker '{self.name}' transitioned from {old_state.value} to {new_state.value}"
        )

        if self.metrics_collector:
            self.metrics_collector(self.name, old_state, new_state, self.metrics)

    def get_state(self) -> Dict[str, Any]:
        """Get current state and metrics"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "total_requests": self.metrics.total_requests,
            "total_failures": self.metrics.total_failures,
            "failure_rate": (
                self.metrics.total_failures / self.metrics.total_requests
                if self.metrics.total_requests > 0
                else 0
            ),
            "last_failure_time": self.metrics.last_failure_time,
            "last_success_time": self.metrics.last_success_time,
            "state_changes": self.metrics.state_changes,
        }

    def reset(self):
        """Reset circuit breaker to initial state"""

        async def _reset():
            async with self._lock:
                self.state = CircuitState.CLOSED
                self.metrics = CircuitBreakerMetrics()
                logger.info(f"Circuit breaker '{self.name}' has been reset")

        return asyncio.run(_reset())


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(
        self, name: str, config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create circuit breaker"""
        async with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
            return self._breakers[name]

    def get_all_breakers(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {name: breaker.get_state() for name, breaker in self._breakers.items()}

    async def reset_all(self):
        """Reset all circuit breakers"""
        async with self._lock:
            for breaker in self._breakers.values():
                await breaker.reset()

    def get_breakers_by_state(self, state: CircuitState) -> list[str]:
        """Get list of breakers in specific state"""
        return [
            name for name, breaker in self._breakers.items() if breaker.state == state
        ]


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


# Pre-configured breakers for common services
AI_SERVICES_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=10,
    recovery_timeout=120.0,
    expected_exception=ConnectionError,
    success_threshold=3,
    timeout=45.0,
)

DATABASE_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=12,
    recovery_timeout=180.0,
    expected_exception=ConnectionError,
    success_threshold=4,
    timeout=15.0,
)

EXTERNAL_API_BREAKER_CONFIG = CircuitBreakerConfig(
    failure_threshold=8,
    recovery_timeout=150.0,
    expected_exception=ConnectionError,
    success_threshold=3,
    timeout=20.0,
)


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    timeout: float = 30.0,
):
    """Decorator factory for circuit breaker"""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            timeout=timeout,
        )

        async def async_wrapper(*args, **kwargs):
            breaker = await circuit_breaker_registry.get_breaker(name, config)
            return await breaker.execute(func, *args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
