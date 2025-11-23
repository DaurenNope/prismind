"""
Error Tracking with Sentry Integration
=====================================

Provides error tracking and reporting using Sentry.
Falls back gracefully if Sentry is not configured.

Author: Prismind Production Team
"""

import os
import sys
from contextlib import contextmanager
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Sentry SDK (optional)
_sentry_sdk = None
_sentry_configured = False

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    _sentry_sdk = sentry_sdk
    logger.info("Sentry SDK available")
except ImportError:
    logger.debug("Sentry SDK not installed. Error tracking will use logging only.")


class ErrorTracker:
    """Error tracking and reporting"""

    def __init__(self):
        self.enabled = False
        self._configured = False

    def configure(
        self,
        dsn: Optional[str] = None,
        environment: Optional[str] = None,
        release: Optional[str] = None,
        traces_sample_rate: float = 0.1,
        enable_tracing: bool = True,
    ):
        """Configure Sentry error tracking"""
        if _sentry_sdk is None:
            logger.warning("Sentry SDK not available. Error tracking disabled.")
            return

        dsn = dsn or os.getenv("SENTRY_DSN")
        if not dsn:
            logger.info("Sentry DSN not configured. Error tracking disabled.")
            return

        environment = environment or os.getenv("ENVIRONMENT", "production")
        release = release or os.getenv("RELEASE_VERSION", "unknown")

        try:
            integrations = [
                LoggingIntegration(level=None, event_level=None),
            ]

            # Add framework-specific integrations if available
            try:
                integrations.append(FastApiIntegration())
            except Exception:
                pass

            try:
                integrations.append(RedisIntegration())
            except Exception:
                pass

            try:
                integrations.append(SqlalchemyIntegration())
            except Exception:
                pass

            _sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                release=release,
                integrations=integrations,
                traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
                enable_tracing=enable_tracing,
                before_send=self._before_send,
            )

            self.enabled = True
            self._configured = True
            logger.info(f"Sentry error tracking configured (env: {environment})")
        except Exception as e:
            logger.error(f"Failed to configure Sentry: {e}")
            self.enabled = False

    def _before_send(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter events before sending to Sentry"""
        # Filter out known non-critical errors
        if "exception" in event:
            exceptions = event["exception"].get("values", [])
            for exc in exceptions:
                exc_type = exc.get("type", "")
                exc_value = exc.get("value", "")

                # Filter duplicate key errors (common in database operations)
                if "23505" in str(exc_value) or "duplicate key" in str(exc_value).lower():
                    return None

                # Filter connection timeout errors if they're frequent
                if "connection timeout" in str(exc_value).lower():
                    # Could add rate limiting here
                    pass

        return event

    def capture_exception(
        self,
        exc: Exception,
        level: str = "error",
        tags: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Capture an exception"""
        if not self.enabled:
            # Fallback to logging
            logger.exception(f"Exception captured: {exc}", context=context)
            return

        try:
            with _sentry_sdk.push_scope() as scope:
                if tags:
                    scope.set_tags(tags)

                if context:
                    scope.set_context("custom", context)

                scope.level = level
                _sentry_sdk.capture_exception(exc)
        except Exception as e:
            logger.error(f"Failed to capture exception in Sentry: {e}")
            logger.exception(f"Original exception: {exc}")

    def capture_message(
        self,
        message: str,
        level: str = "info",
        tags: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Capture a message"""
        if not self.enabled:
            # Fallback to logging
            logger.log(getattr(logger, level.lower(), logger.info), message)
            return

        try:
            with _sentry_sdk.push_scope() as scope:
                if tags:
                    scope.set_tags(tags)

                if context:
                    scope.set_context("custom", context)

                scope.level = level
                _sentry_sdk.capture_message(message, level=level)
        except Exception as e:
            logger.error(f"Failed to capture message in Sentry: {e}")

    def set_user(self, user_id: Optional[str] = None, email: Optional[str] = None, username: Optional[str] = None):
        """Set user context for error tracking"""
        if not self.enabled:
            return

        try:
            _sentry_sdk.set_user(
                {
                    "id": user_id,
                    "email": email,
                    "username": username,
                }
            )
        except Exception as e:
            logger.debug(f"Failed to set user in Sentry: {e}")

    def clear_user(self):
        """Clear user context"""
        if not self.enabled:
            return

        try:
            _sentry_sdk.set_user(None)
        except Exception:
            pass

    def set_tag(self, key: str, value: str):
        """Set a tag for error tracking"""
        if not self.enabled:
            return

        try:
            _sentry_sdk.set_tag(key, value)
        except Exception as e:
            logger.debug(f"Failed to set tag in Sentry: {e}")

    def set_context(self, key: str, context: Dict[str, Any]):
        """Set context for error tracking"""
        if not self.enabled:
            return

        try:
            _sentry_sdk.set_context(key, context)
        except Exception as e:
            logger.debug(f"Failed to set context in Sentry: {e}")

    @contextmanager
    def span(self, op: str, description: Optional[str] = None):
        """Create a performance span"""
        if not self.enabled or not _sentry_sdk:
            yield
            return

        try:
            with _sentry_sdk.start_transaction(op=op, description=description):
                yield
        except Exception:
            # Fallback if tracing fails
            yield

    @contextmanager
    def capture_exceptions(self, context: Optional[Dict[str, Any]] = None):
        """Context manager to automatically capture exceptions"""
        try:
            yield
        except Exception as e:
            self.capture_exception(e, context=context)
            raise

    def flush(self, timeout: float = 2.0):
        """Flush pending events to Sentry"""
        if not self.enabled or not _sentry_sdk:
            return

        try:
            _sentry_sdk.flush(timeout=timeout)
        except Exception as e:
            logger.debug(f"Failed to flush Sentry events: {e}")


# Global error tracker instance
_error_tracker: Optional[ErrorTracker] = None


def get_error_tracker() -> ErrorTracker:
    """Get the global error tracker instance"""
    global _error_tracker
    if _error_tracker is None:
        _error_tracker = ErrorTracker()
        # Auto-configure if DSN is available
        dsn = os.getenv("SENTRY_DSN")
        if dsn:
            _error_tracker.configure(dsn=dsn)
    return _error_tracker


def configure_error_tracking(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
):
    """Configure error tracking globally"""
    tracker = get_error_tracker()
    tracker.configure(dsn=dsn, environment=environment, release=release)






