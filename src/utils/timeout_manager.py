#!/usr/bin/env python3
"""
Timeout Manager for BEYONDLINES
Provides centralized timeout management for all long-running operations.
"""

import asyncio
import signal
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class TimeoutError(Exception):
    """Raised when an operation exceeds its timeout."""
    pass


class TimeoutManager:
    """
    Manages timeouts for operations.
    Provides both async and sync timeout contexts.
    """
    
    DEFAULT_TIMEOUT = 30.0  # seconds
    DEFAULT_HTTP_TIMEOUT = 30.0
    DEFAULT_DB_TIMEOUT = 10.0
    DEFAULT_API_TIMEOUT = 60.0
    
    @staticmethod
    @contextmanager
    def timeout(seconds: float, operation_name: str = "operation"):
        """
        Context manager for timeout on synchronous operations.
        
        Args:
            seconds: Timeout in seconds
            operation_name: Name of operation for error messages
            
        Raises:
            TimeoutError: If operation exceeds timeout
        """
        def timeout_handler(signum, frame):
            raise TimeoutError(f"{operation_name} timed out after {seconds} seconds")
        
        # Set up signal handler for timeout
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(seconds))
        
        try:
            yield
        finally:
            # Restore old handler and cancel alarm
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    
    @staticmethod
    async def async_timeout(
        coro: Callable,
        timeout: float,
        operation_name: str = "operation",
        *args,
        **kwargs
    ) -> Any:
        """
        Execute an async operation with timeout.
        
        Args:
            coro: Async coroutine or callable
            timeout: Timeout in seconds
            operation_name: Name of operation for error messages
            *args, **kwargs: Arguments to pass to coro
            
        Returns:
            Result from coro
            
        Raises:
            asyncio.TimeoutError: If operation exceeds timeout
        """
        try:
            return await asyncio.wait_for(
                coro(*args, **kwargs) if callable(coro) else coro,
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"{operation_name} timed out after {timeout} seconds")
            raise TimeoutError(f"{operation_name} timed out after {timeout} seconds")
    
    @staticmethod
    def with_timeout(
        timeout_seconds: float = DEFAULT_TIMEOUT,
        operation_name: Optional[str] = None
    ):
        """
        Decorator to add timeout to async functions.
        
        Args:
            timeout_seconds: Timeout in seconds
            operation_name: Name of operation (defaults to function name)
        """
        def decorator(func: Callable) -> Callable:
            name = operation_name or func.__name__
            
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await TimeoutManager.async_timeout(
                    func,
                    timeout_seconds,
                    name,
                    *args,
                    **kwargs
                )
            
            return wrapper
        return decorator


# Convenience functions

def get_http_timeout() -> float:
    """Get default HTTP request timeout."""
    return TimeoutManager.DEFAULT_HTTP_TIMEOUT


def get_db_timeout() -> float:
    """Get default database operation timeout."""
    return TimeoutManager.DEFAULT_DB_TIMEOUT


def get_api_timeout() -> float:
    """Get default API call timeout."""
    return TimeoutManager.DEFAULT_API_TIMEOUT


# Global timeout manager instance
_timeout_manager: Optional[TimeoutManager] = None


def get_timeout_manager() -> TimeoutManager:
    """Get the global TimeoutManager instance."""
    global _timeout_manager
    if _timeout_manager is None:
        _timeout_manager = TimeoutManager()
    return _timeout_manager





