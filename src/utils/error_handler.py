"""
BEYONDLINES Centralized Error Handler
================================

Standardized error handling patterns to reduce try/except bloat
and improve debugging capabilities.

Author: BEYONDLINES AI System
"""

import logging
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

# Import the new exception hierarchy
from .exceptions import APIError, AuthenticationError
from .exceptions import BEYONDLINESException as BEYONDLINESError
from .exceptions import (
    ConfigurationError,
    ContentProcessingError,
    DatabaseError,
    PublishingError,
    RateLimitError,
    RetryExhaustedError,
    ValidationError,
)

# Configure logging
logger = logging.getLogger(__name__)


# Add missing exception classes not in the new hierarchy
class BrowserAutomationError(BEYONDLINESError):
    """Browser automation errors"""

    pass


class ContentAnalysisError(BEYONDLINESError):
    """Content analysis errors"""

    pass


class ErrorHandler:
    """Centralized error handling with recovery strategies"""

    def __init__(self, logger_instance: Optional[logging.Logger] = None):
        self.logger = logger_instance or logger
        self.error_counts = {}
        self.last_errors = {}

    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict] = None,
        reraise: bool = False,
        default_return: Any = None,
        error_type: Optional[Type[BEYONDLINESError]] = None,
    ) -> Any:
        """Handle an error with logging and optional retry logic"""

        # Count error types
        error_type_name = type(error).__name__
        self.error_counts[error_type_name] = (
            self.error_counts.get(error_type_name, 0) + 1
        )
        self.last_errors[error_type_name] = {
            "error": str(error),
            "context": context,
            "timestamp": datetime.now().isoformat(),
        }

        # Log error
        self.logger.error(
            f"Error in {context.get('operation', 'unknown') if context else 'unknown'}: {error_type_name}: {str(error)}"
        )
        if context:
            self.logger.debug(f"Error context: {context}")

        # Log traceback for debugging
        self.logger.debug(f"Traceback: {traceback.format_exc()}")

        # Convert to BEYONDLINES error if specified
        if error_type and not isinstance(error, BEYONDLINESError):
            error = error_type(str(error), context=context)

        # Reraise or return default
        if reraise:
            raise error
        return default_return

    def retry_with_backoff(
        self,
        func: Callable,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        backoff_factor: float = 2.0,
        context: Optional[Dict] = None,
    ) -> Any:
        """Retry function with exponential backoff"""

        for attempt in range(max_attempts):
            try:
                return func()
            except Exception as e:
                if attempt == max_attempts - 1:
                    return self.handle_error(e, context, reraise=True)

                delay = base_delay * (backoff_factor**attempt)
                self.logger.warning(
                    f"Attempt {attempt + 1} failed in {context.get('operation', 'unknown') if context else 'unknown'}: {str(e)}. "
                    f"Retrying in {delay}s..."
                )

                import time

                time.sleep(delay)

        return None

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors"""
        return {
            "error_counts": self.error_counts,
            "last_errors": self.last_errors,
            "total_errors": sum(self.error_counts.values()),
        }


# Global error handler instance
global_error_handler = ErrorHandler()


def safe_execute(
    default_return: Any = None,
    error_type: Optional[Type[BEYONDLINESError]] = None,
    log_level: str = "error",
    context: Optional[Dict] = None,
):
    """Decorator for safe function execution with standardized error handling"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            operation_context = {
                "function": func.__name__,
                "module": func.__module__,
                **(context or {}),
            }

            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Choose appropriate log level
                if log_level == "error":
                    global_error_handler.logger.error(
                        f"Error in {func.__name__}: {str(e)}"
                    )
                elif log_level == "warning":
                    global_error_handler.logger.warning(
                        f"Warning in {func.__name__}: {str(e)}"
                    )
                else:
                    global_error_handler.logger.info(
                        f"Info in {func.__name__}: {str(e)}"
                    )

                return global_error_handler.handle_error(
                    e,
                    operation_context,
                    reraise=False,
                    default_return=default_return,
                    error_type=error_type,
                )

        return wrapper

    return decorator


def safe_api_call(api_name: str, default_return: Any = None, max_attempts: int = 3):
    """Decorator for API calls with retry logic"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = {"operation": f"{api_name}_api_call", "function": func.__name__}

            def api_call():
                return func(*args, **kwargs)

            return global_error_handler.retry_with_backoff(
                api_call, max_attempts=max_attempts, base_delay=1.0, context=context
            )

        return wrapper

    return decorator


def safe_database_operation(default_return: Any = None):
    """Decorator for database operations"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = {"operation": "database_operation", "function": func.__name__}

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error: {e}")
                # Convert to database error
                db_error = DatabaseError(
                    f"Database operation failed: {str(e)}", context=context
                )
                return global_error_handler.handle_error(
                    db_error, context, reraise=False, default_return=default_return
                )

        return wrapper

    return decorator


def safe_browser_operation(default_return: Any = None):
    """Decorator for browser automation operations"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = {"operation": "browser_automation", "function": func.__name__}

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error: {e}")
                # Convert to browser automation error
                browser_error = BrowserAutomationError(
                    f"Browser operation failed: {str(e)}", context=context
                )
                return global_error_handler.handle_error(
                    browser_error, context, reraise=False, default_return=default_return
                )

        return wrapper

    return decorator


def safe_analysis_operation(default_return: Any = None):
    """Decorator for content analysis operations"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            context = {"operation": "content_analysis", "function": func.__name__}

            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error: {e}")
                # Convert to analysis error
                analysis_error = ContentAnalysisError(
                    f"Analysis operation failed: {str(e)}", context=context
                )
                return global_error_handler.handle_error(
                    analysis_error,
                    context,
                    reraise=False,
                    default_return=default_return,
                )

        return wrapper

    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for preventing cascading failures"""

    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""

        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise BEYONDLINESError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            logger.error(f"Error: {e}")
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True

        import time

        return (time.time() - self.last_failure_time) >= self.timeout

    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"


# Convenience functions for common patterns
def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    return global_error_handler


def log_error_summary():
    """Log error summary for debugging"""
    summary = global_error_handler.get_error_summary()
    logger.info(f"Error Summary: {summary}")


def handle_errors(
    default_return: Any = None, error_type: Optional[Type[BEYONDLINESError]] = None
):
    """Decorator for synchronous error handling"""
    return safe_execute(default_return=default_return, error_type=error_type)


def async_handle_errors(
    default_return: Any = None, error_type: Optional[Type[BEYONDLINESError]] = None
):
    """Decorator for asynchronous error handling"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            operation_context = {"function": func.__name__, "module": func.__module__}

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Async error in {func.__name__}: {str(e)}")

                # Convert to specified error type if needed
                if error_type and not isinstance(e, BEYONDLINESError):
                    e = error_type(str(e), context=operation_context)

                return global_error_handler.handle_error(
                    e, operation_context, reraise=False, default_return=default_return
                )

        return wrapper

    return decorator


# Rewriter-specific error handling functions
def is_rate_limit_error_in_content(content: str) -> bool:
    """
    Check if content contains rate limit error indicators

    This is critical for two-stage pipelines where Stage 1 extraction
    might return an error message that Stage 2 would try to rewrite
    """
    if not content or len(content) < 10:
        return False

    content_lower = content.lower()

    # Rate limit indicators (English and Russian)
    rate_limit_keywords = [
        "error:",
        "exhausted",
        "rate limit",
        "quota",
        "api keys",
        "api key",
        "ключи",
        "лимит",
        "квота",
        "исчерпан",
        "выгорели",
    ]

    return any(keyword in content_lower for keyword in rate_limit_keywords)


def create_rate_limit_error_result(
    post_id: str,
    platform: str,
    persona_name: str,
    provider: str = "API",
    stage: str = "extraction",
) -> Dict[str, Any]:
    """
    Create standardized error result for rate limit failures

    This ensures the generation script can handle rate limit errors properly
    without treating them as valid content
    """
    return {
        "error": f"Rate limit hit during {stage} - all {provider} keys exhausted",
        "error_type": "rate_limit",
        "original_post_id": post_id,
        "original_platform": platform,
        "persona_name": persona_name,
        "platform": platform,
        "rewritten_content": "",
        "quality_score": 0,
        "quality_rating": "failed",
        "content_length": 0,
        "content_type": "error",
        "retryable": False,  # Don't retry when all keys are exhausted
        "should_skip": True,  # Skip this post entirely
    }
