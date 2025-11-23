"""
Retry Handler with Exponential Backoff
Provides robust retry logic for API calls and database operations
"""

import asyncio
import logging
import time
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry (attempt_num, exception)

    Example:
        @retry_with_backoff(max_attempts=3, base_delay=1.0)
        async def api_call():
            # Your API call here
            pass
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts:
                            logger.error(
                                f"❌ {func.__name__} failed after {max_attempts} attempts: {e}",
                                exc_info=True,
                            )
                            raise

                        delay = min(
                            base_delay * (backoff_factor ** (attempt - 1)), max_delay
                        )
                        logger.warning(
                            f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )

                        if on_retry:
                            try:
                                on_retry(attempt, e)
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                pass  # Don't fail on retry callback

                        await asyncio.sleep(delay)

                # Should never reach here, but just in case
                if last_exception:
                    raise last_exception
                raise RuntimeError(
                    f"{func.__name__} failed after {max_attempts} attempts"
                )

            return async_wrapper
        else:

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_exception = e
                        if attempt == max_attempts:
                            logger.error(
                                f"❌ {func.__name__} failed after {max_attempts} attempts: {e}",
                                exc_info=True,
                            )
                            raise

                        delay = min(
                            base_delay * (backoff_factor ** (attempt - 1)), max_delay
                        )
                        logger.warning(
                            f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )

                        if on_retry:
                            try:
                                on_retry(attempt, e)
                            except Exception as e:
                                logger.error(f"Error: {e}")
                                pass  # Don't fail on retry callback

                        time.sleep(delay)

                # Should never reach here, but just in case
                if last_exception:
                    raise last_exception
                raise RuntimeError(
                    f"{func.__name__} failed after {max_attempts} attempts"
                )

            return sync_wrapper

    return decorator


async def retry_async(
    func: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs,
) -> Any:
    """
    Retry an async function with exponential backoff

    Args:
        func: Async function to retry
        *args: Positional arguments for func
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry
        **kwargs: Keyword arguments for func

    Returns:
        Result of func(*args, **kwargs)

    Example:
        result = await retry_async(
            api_call,
            url="https://api.example.com",
            max_attempts=3,
            base_delay=1.0
        )
    """
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt == max_attempts:
                logger.error(
                    f"❌ {func.__name__} failed after {max_attempts} attempts: {e}",
                    exc_info=True,
                )
                raise

            delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
            logger.warning(
                f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )

            await asyncio.sleep(delay)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError(f"{func.__name__} failed after {max_attempts} attempts")


def retry_sync(
    func: Callable,
    *args,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs,
) -> Any:
    """
    Retry a sync function with exponential backoff

    Args:
        func: Sync function to retry
        *args: Positional arguments for func
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for delay on each retry
        exceptions: Tuple of exception types to catch and retry
        **kwargs: Keyword arguments for func

    Returns:
        Result of func(*args, **kwargs)

    Example:
        result = retry_sync(
            db_operation,
            query="SELECT * FROM posts",
            max_attempts=3,
            base_delay=1.0
        )
    """
    last_exception = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt == max_attempts:
                logger.error(
                    f"❌ {func.__name__} failed after {max_attempts} attempts: {e}",
                    exc_info=True,
                )
                raise

            delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
            logger.warning(
                f"⚠️ {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                f"Retrying in {delay:.1f}s..."
            )

            time.sleep(delay)

    # Should never reach here, but just in case
    if last_exception:
        raise last_exception
    raise RuntimeError(f"{func.__name__} failed after {max_attempts} attempts")
