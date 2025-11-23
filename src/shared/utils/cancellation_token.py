#!/usr/bin/env python3
"""
Cancellation Token for BEYONDLINES
Provides graceful shutdown mechanisms for long-running operations.
"""

import asyncio
import threading
from typing import Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CancellationToken:
    """
    Thread-safe cancellation token for coordinating graceful shutdowns.
    Supports both async and sync operations.
    """
    
    def __init__(self):
        """Initialize a cancellation token."""
        self._cancelled = False
        self._lock = threading.Lock()
        self._callbacks = []
        self._event = threading.Event()
    
    def cancel(self, reason: Optional[str] = None) -> None:
        """
        Cancel the token.
        
        Args:
            reason: Optional reason for cancellation
        """
        with self._lock:
            if self._cancelled:
                return
            
            self._cancelled = True
            self._event.set()
            
            if reason:
                logger.info(f"Cancellation requested: {reason}")
            else:
                logger.info("Cancellation requested")
        
        # Call registered callbacks
        for callback in self._callbacks:
            try:
                callback(reason)
            except Exception as e:
                logger.error(f"Error in cancellation callback: {e}")
    
    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        with self._lock:
            return self._cancelled
    
    def check_cancellation(self) -> None:
        """
        Check if cancellation has been requested and raise if so.
        
        Raises:
            CancelledError: If cancellation has been requested
        """
        if self.is_cancelled():
            raise CancelledError("Operation was cancelled")
    
    def register_callback(self, callback: callable) -> None:
        """
        Register a callback to be called when cancellation is requested.
        
        Args:
            callback: Function to call with optional reason string
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def wait(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for cancellation to be requested.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            True if cancelled, False if timeout
        """
        return self._event.wait(timeout)
    
    def reset(self) -> None:
        """Reset the cancellation token (for reuse in tests)."""
        with self._lock:
            self._cancelled = False
            self._event.clear()
            self._callbacks.clear()


class CancelledError(Exception):
    """Raised when an operation is cancelled."""
    pass


class GracefulShutdownManager:
    """
    Manages graceful shutdown for the application.
    Handles signal registration and cleanup.
    """
    
    def __init__(self):
        """Initialize graceful shutdown manager."""
        self.cancellation_token = CancellationToken()
        self._shutdown_hooks = []
        self._registered_signals = []
    
    def register_shutdown_hook(self, hook: callable) -> None:
        """
        Register a function to be called during shutdown.
        
        Args:
            hook: Function to call during shutdown
        """
        self._shutdown_hooks.append(hook)
    
    def shutdown(self, reason: Optional[str] = None) -> None:
        """
        Initiate graceful shutdown.
        
        Args:
            reason: Optional reason for shutdown
        """
        logger.info("Initiating graceful shutdown...")
        
        # Cancel all operations
        self.cancellation_token.cancel(reason or "Graceful shutdown requested")
        
        # Run shutdown hooks
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Error in shutdown hook: {e}")
        
        logger.info("Graceful shutdown complete")
    
    async def async_shutdown(self, reason: Optional[str] = None) -> None:
        """
        Initiate graceful async shutdown.
        
        Args:
            reason: Optional reason for shutdown
        """
        logger.info("Initiating graceful async shutdown...")
        
        # Cancel all operations
        self.cancellation_token.cancel(reason or "Graceful shutdown requested")
        
        # Run async shutdown hooks
        for hook in self._shutdown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook()
                else:
                    hook()
            except Exception as e:
                logger.error(f"Error in shutdown hook: {e}")
        
        logger.info("Graceful async shutdown complete")


# Global shutdown manager instance
_shutdown_manager: Optional[GracefulShutdownManager] = None


def get_shutdown_manager() -> GracefulShutdownManager:
    """Get the global GracefulShutdownManager instance."""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = GracefulShutdownManager()
    return _shutdown_manager


def get_cancellation_token() -> CancellationToken:
    """Get the global cancellation token."""
    return get_shutdown_manager().cancellation_token





