#!/usr/bin/env python3
"""
Circuit Breaker Wrapper for BEYONDLINES
====================================

Simple circuit breaker wrapper integrated with observability.
Protects external service calls from cascading failures.
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from src.utils.logging_config import get_logger
from src.utils.observability_hub import get_observability_hub

T = TypeVar("T")
logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker"""

    name: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0


class CircuitBreakerWrapper:
    """
    Simple circuit breaker wrapper integrated with observability.

    Usage:
        breaker = CircuitBreakerWrapper("supabase", failure_threshold=5, recovery_timeout=60)

        @breaker.protect
        def my_function():
            # This function is protected
            pass
    """

    _breakers: Dict[str, "CircuitBreakerWrapper"] = {}

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.state = CircuitBreakerState(name=name)
        self.hub = get_observability_hub()
        self._lock = asyncio.Lock()

        # Register this breaker
        CircuitBreakerWrapper._breakers[name] = self

    def _can_execute(self) -> bool:
        """Check if execution is allowed"""
        self.state.total_requests += 1

        if self.state.state == CircuitState.CLOSED:
            return True

        if self.state.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (
                self.state.last_failure_time
                and (time.time() - self.state.last_failure_time)
                >= self.recovery_timeout
            ):
                self.state.state = CircuitState.HALF_OPEN
                self.state.failure_count = 0
                self.state.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' transitioning to HALF_OPEN")
                return True
            return False

        if self.state.state == CircuitState.HALF_OPEN:
            return True

        return False

    def _on_success(self):
        """Handle successful execution"""
        self.state.success_count += 1
        self.state.last_success_time = time.time()

        if self.state.state == CircuitState.HALF_OPEN:
            if self.state.success_count >= self.success_threshold:
                self.state.state = CircuitState.CLOSED
                self.state.failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed (service recovered)")
                self.hub.metrics.increment(f"circuit_breaker.{self.name}.closed")

        self.hub.metrics.increment(f"circuit_breaker.{self.name}.success")

    def _on_failure(self, error: Exception):
        """Handle failed execution"""
        self.state.failure_count += 1
        self.state.total_failures += 1
        self.state.last_failure_time = time.time()

        if self.state.state == CircuitState.CLOSED:
            if self.state.failure_count >= self.failure_threshold:
                self.state.state = CircuitState.OPEN
                logger.warning(
                    f"Circuit breaker '{self.name}' OPENED after {self.state.failure_count} failures"
                )
                self.hub.metrics.increment(f"circuit_breaker.{self.name}.opened")
                self.hub.errors.capture_exception(
                    error,
                    context={
                        "circuit_breaker": self.name,
                        "state": "opened",
                        "failure_count": self.state.failure_count,
                    },
                )
        elif self.state.state == CircuitState.HALF_OPEN:
            self.state.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' re-opened (service still failing)"
            )
            self.hub.metrics.increment(f"circuit_breaker.{self.name}.reopened")

        self.hub.metrics.increment(f"circuit_breaker.{self.name}.failure")

    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to protect a function with circuit breaker"""

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not self._can_execute():
                error_msg = f"Circuit breaker '{self.name}' is OPEN"
                logger.warning(error_msg)
                self.hub.metrics.increment(f"circuit_breaker.{self.name}.rejected")
                raise RuntimeError(error_msg)

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                logger.error(f"Error: {e}")
                self._on_failure(e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self._can_execute():
                error_msg = f"Circuit breaker '{self.name}' is OPEN"
                logger.warning(error_msg)
                self.hub.metrics.increment(f"circuit_breaker.{self.name}.rejected")
                raise RuntimeError(error_msg)

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                logger.error(f"Error: {e}")
                self._on_failure(e)
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.state.value,
            "failure_count": self.state.failure_count,
            "success_count": self.state.success_count,
            "total_requests": self.state.total_requests,
            "total_failures": self.state.total_failures,
            "failure_rate": (
                self.state.total_failures / self.state.total_requests
                if self.state.total_requests > 0
                else 0
            ),
            "last_failure_time": self.state.last_failure_time,
            "last_success_time": self.state.last_success_time,
        }

    def reset(self):
        """Reset circuit breaker"""
        self.state = CircuitBreakerState(name=self.name)
        logger.info(f"Circuit breaker '{self.name}' reset")

    @classmethod
    def get_breaker(cls, name: str, **kwargs) -> "CircuitBreakerWrapper":
        """Get or create a circuit breaker"""
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreakerWrapper(name, **kwargs)
        return cls._breakers[name]

    @classmethod
    def get_all_status(cls) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {name: breaker.get_status() for name, breaker in cls._breakers.items()}


# Convenience function
def get_circuit_breaker(name: str, **kwargs) -> CircuitBreakerWrapper:
    """Get or create a circuit breaker"""
    return CircuitBreakerWrapper.get_breaker(name, **kwargs)
