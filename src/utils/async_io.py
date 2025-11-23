#!/usr/bin/env python3
"""
Async I/O Utilities for BEYONDLINES
Provides async wrappers for sync operations and utilities for avoiding async/sync mismatches.
"""

import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional, TypeVar

from src.shared.utils.logging_config import get_logger
from src.shared.utils.timeout_manager import get_timeout_manager

logger = get_logger(__name__)

T = TypeVar('T')

# Global thread pool executor for running sync operations
_executor: Optional[ThreadPoolExecutor] = None


def get_executor() -> ThreadPoolExecutor:
    """Get or create the global thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="async_io")
    return _executor


def run_in_executor(func: Callable[..., T], *args, **kwargs) -> asyncio.Future[T]:
    """
    Run a synchronous function in a thread pool executor.
    
    Args:
        func: Synchronous function to run
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        asyncio.Future that resolves to the function's return value
    """
    loop = asyncio.get_event_loop()
    executor = get_executor()
    return loop.run_in_executor(executor, functools.partial(func, *args, **kwargs))


async def run_sync_with_timeout(
    func: Callable[..., T],
    timeout: float,
    operation_name: str,
    *args,
    **kwargs
) -> T:
    """
    Run a synchronous function in executor with timeout.
    
    Args:
        func: Synchronous function to run
        timeout: Timeout in seconds
        operation_name: Name of operation for error messages
        *args, **kwargs: Arguments to pass to function
        
    Returns:
        Function return value
        
    Raises:
        TimeoutError: If operation exceeds timeout
    """
    timeout_manager = get_timeout_manager()
    return await timeout_manager.async_timeout(
        run_in_executor(func, *args, **kwargs),
        timeout,
        operation_name
    )


# Async HTTP client wrapper
try:
    import aiohttp
    
    async def async_http_get(
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> dict:
        """
        Async HTTP GET request.
        
        Args:
            url: URL to fetch
            params: Query parameters
            headers: Request headers
            timeout: Request timeout in seconds
            **kwargs: Additional aiohttp.ClientSession.get() arguments
            
        Returns:
            Response dictionary with 'status', 'data', 'headers' keys
        """
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url, params=params, headers=headers, **kwargs) as response:
                data = await response.json() if response.content_type == 'application/json' else await response.text()
                return {
                    'status': response.status,
                    'data': data,
                    'headers': dict(response.headers),
                }
    
    async def async_http_post(
        url: str,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> dict:
        """
        Async HTTP POST request.
        
        Args:
            url: URL to POST to
            data: Form data
            json: JSON data
            headers: Request headers
            timeout: Request timeout in seconds
            **kwargs: Additional aiohttp.ClientSession.post() arguments
            
        Returns:
            Response dictionary with 'status', 'data', 'headers' keys
        """
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.post(url, data=data, json=json, headers=headers, **kwargs) as response:
                data = await response.json() if response.content_type == 'application/json' else await response.text()
                return {
                    'status': response.status,
                    'data': data,
                    'headers': dict(response.headers),
                }
    
    ASYNC_HTTP_AVAILABLE = True
    
except ImportError:
    # Fallback: wrap requests library in executor
    ASYNC_HTTP_AVAILABLE = False
    logger.warning("aiohttp not available, using requests in executor (less efficient)")
    
    import requests
    
    async def async_http_get(
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> dict:
        """Async HTTP GET using requests in executor."""
        def _sync_get():
            response = requests.get(url, params=params, headers=headers, timeout=timeout, **kwargs)
            try:
                data = response.json()
            except ValueError:
                data = response.text
            return {
                'status': response.status_code,
                'data': data,
                'headers': dict(response.headers),
            }
        
        return await run_sync_with_timeout(_sync_get, timeout, f"HTTP_GET_{url}")
    
    async def async_http_post(
        url: str,
        data: Optional[dict] = None,
        json: Optional[dict] = None,
        headers: Optional[dict] = None,
        timeout: float = 30.0,
        **kwargs
    ) -> dict:
        """Async HTTP POST using requests in executor."""
        def _sync_post():
            response = requests.post(url, data=data, json=json, headers=headers, timeout=timeout, **kwargs)
            try:
                data = response.json()
            except ValueError:
                data = response.text
            return {
                'status': response.status_code,
                'data': data,
                'headers': dict(response.headers),
            }
        
        return await run_sync_with_timeout(_sync_post, timeout, f"HTTP_POST_{url}")


# Async SQLite wrapper
try:
    import aiosqlite
    
    async def async_sqlite_connect(db_path: str, **kwargs):
        """
        Async SQLite connection context manager.
        
        Args:
            db_path: Path to SQLite database
            **kwargs: Additional aiosqlite.connect() arguments
            
        Returns:
            Async context manager for database connection
        """
        return aiosqlite.connect(db_path, **kwargs)
    
    ASYNC_SQLITE_AVAILABLE = True
    
except ImportError:
    # Fallback: wrap sqlite3 in executor
    ASYNC_SQLITE_AVAILABLE = False
    logger.warning("aiosqlite not available, using sqlite3 in executor (less efficient)")
    
    import sqlite3
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def async_sqlite_connect(db_path: str, **kwargs):
        """Async SQLite connection using sqlite3 in executor."""
        def _sync_connect():
            return sqlite3.connect(db_path, **kwargs)
        
        conn = await run_in_executor(_sync_connect)
        try:
            yield conn
        finally:
            await run_in_executor(conn.close)


# Async sleep wrapper (just re-export asyncio.sleep for clarity)
async_sleep = asyncio.sleep


def sync_to_async(func: Callable[..., T]) -> Callable[..., asyncio.coroutine]:
    """
    Decorator to convert a synchronous function to async by running in executor.
    
    Usage:
        @sync_to_async
        def my_sync_function(x, y):
            return x + y
        
        # Now can be called with await
        result = await my_sync_function(1, 2)
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await run_in_executor(func, *args, **kwargs)
    
    return wrapper





