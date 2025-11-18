#!/usr/bin/env python3
"""
BEYONDLINES Standardized Result Pattern
=====================================

Centralized result patterns to ensure consistent error handling
across the entire BEYONDLINES codebase.

This replaces inconsistent patterns:
- {"success": False, "error": "message"} ❌
- return False ❌
- return None ❌
- CollectionResult(...) ✅ (Good pattern)

Author: BEYONDLINES AI System
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class OperationResult:
    """
    Standardized result for all operations across BEYONDLINES.

    This replaces inconsistent error handling patterns with a single,
    predictable structure that works for all operation types.
    """

    success: bool
    operation: str
    message: Optional[str] = None
    data: Optional[Any] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    duration_seconds: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Compatibility fields for existing code
    platform: Optional[str] = None
    posts_collected: int = 0
    posts_analyzed: int = 0
    posts_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization/JSON"""
        return {
            "success": self.success,
            "operation": self.operation,
            "message": self.message,
            "data": self.data,
            "error": self.error,
            "error_code": self.error_code,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "platform": self.platform,
            "posts_collected": self.posts_collected,
            "posts_analyzed": self.posts_analyzed,
            "posts_failed": self.posts_failed,
        }

    def is_success(self) -> bool:
        """Check if operation was successful"""
        return self.success

    def has_data(self) -> bool:
        """Check if result contains data"""
        return self.data is not None

    def get_error_details(self) -> Dict[str, Any]:
        """Get error details as dictionary"""
        return {
            "error": self.error,
            "error_code": self.error_code,
            "operation": self.operation,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ResultFactory:
    """Factory for creating standardized results"""

    @staticmethod
    def success(
        operation: str,
        message: Optional[str] = None,
        data: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> OperationResult:
        """Create successful result"""
        return OperationResult(
            success=True,
            operation=operation,
            message=message or f"{operation} completed successfully",
            data=data,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            **kwargs,
        )

    @staticmethod
    def failure(
        operation: str,
        error: str,
        error_code: Optional[str] = None,
        data: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> OperationResult:
        """Create failure result"""
        return OperationResult(
            success=False,
            operation=operation,
            message=f"{operation} failed: {error}",
            data=data,
            error=error,
            error_code=error_code,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            **kwargs,
        )

    @staticmethod
    def from_exception(
        operation: str,
        exception: Exception,
        data: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> OperationResult:
        """Create result from exception"""
        error_type = type(exception).__name__
        error_message = str(exception)

        # Log the exception
        logger.error(f"Exception in {operation}: {error_type}: {error_message}")

        return ResultFactory.failure(
            operation=operation,
            error=error_message,
            error_code=error_type,
            data=data,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            **kwargs,
        )

    @staticmethod
    def collection_success(
        platform: str,
        posts_collected: int,
        duration_seconds: Optional[float] = None,
        data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """Create successful collection result (compatible with existing CollectionResult)"""
        return ResultFactory.success(
            operation="collection",
            message=f"Successfully collected {posts_collected} posts from {platform}",
            data=data,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            platform=platform,
            posts_collected=posts_collected,
        )

    @staticmethod
    def collection_failure(
        platform: str,
        error: str,
        posts_collected: int = 0,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """Create failed collection result (compatible with existing CollectionResult)"""
        return ResultFactory.failure(
            operation="collection",
            error=f"Collection from {platform} failed: {error}",
            data=None,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            platform=platform,
            posts_collected=posts_collected,
        )

    @staticmethod
    def posting_success(
        platform: str,
        message: Optional[str] = None,
        post_id: Optional[str] = None,
        data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """Create successful posting result"""
        msg = message or f"Successfully posted to {platform}"
        if post_id:
            msg += f" (ID: {post_id})"

        result = ResultFactory.success(
            operation="posting",
            message=msg,
            data=data,
            metadata=metadata or {},
            platform=platform,
        )

        if post_id:
            result.metadata["post_id"] = post_id

        return result

    @staticmethod
    def posting_failure(
        platform: str,
        error: str,
        data: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """Create failed posting result"""
        return ResultFactory.failure(
            operation="posting",
            error=f"Posting to {platform} failed: {error}",
            error_code="POSTING_ERROR",
            data=data,
            metadata=metadata or {},
            platform=platform,
        )

    @staticmethod
    def analysis_success(
        analysis_type: str,
        data: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """Create successful analysis result"""
        return ResultFactory.success(
            operation="analysis",
            message=f"Successfully completed {analysis_type} analysis",
            data=data,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            analysis_type=analysis_type,
        )

    @staticmethod
    def analysis_failure(
        analysis_type: str,
        error: str,
        data: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> OperationResult:
        """Create failed analysis result"""
        return ResultFactory.failure(
            operation="analysis",
            error=f"{analysis_type} analysis failed: {error}",
            error_code="ANALYSIS_ERROR",
            data=data,
            duration_seconds=duration_seconds,
            metadata=metadata or {},
            analysis_type=analysis_type,
        )


# Legacy compatibility functions
def convert_collection_result_to_operation_result(collection_result) -> OperationResult:
    """Convert existing CollectionResult to OperationResult for compatibility"""
    return OperationResult(
        success=collection_result.success,
        operation="collection",
        message=f"Collection { 'successful' if collection_result.success else 'failed' }",
        data=collection_result.to_dict(),
        error=collection_result.error,
        duration_seconds=collection_result.duration_seconds,
        platform=collection_result.platform,
        posts_collected=collection_result.posts_collected,
        posts_analyzed=getattr(collection_result, "posts_analyzed", 0),
        posts_failed=getattr(collection_result, "posts_failed", 0),
        metadata=getattr(collection_result, "metadata", {}),
    )


def convert_dict_result_to_operation_result(
    dict_result: Dict[str, Any], operation: str
) -> OperationResult:
    """Convert dict result with success/error to OperationResult"""
    success = dict_result.get("success", False)

    if success:
        return ResultFactory.success(
            operation=operation,
            message=dict_result.get("message"),
            data=dict_result.get("data"),
            metadata=dict_result.get("metadata", {}),
        )
    else:
        return ResultFactory.failure(
            operation=operation,
            error=dict_result.get("error", "Unknown error"),
            error_code=dict_result.get("error_code"),
            data=dict_result.get("data"),
            metadata=dict_result.get("metadata", {}),
        )


# Convenience decorator for automatic result conversion
def standardize_result(operation: str, default_success_message: Optional[str] = None):
    """
    Decorator to automatically convert function returns to OperationResult.

    For functions that currently return:
    - bool: True -> success result, False -> failure result
    - None -> success result (if no exception)
    - dict with success/error -> converted result
    - existing OperationResult -> passed through unchanged
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                start_time = datetime.now()
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()

                # Already standardized - just add duration
                if isinstance(result, OperationResult):
                    result.duration_seconds = duration
                    return result

                # Dict with success field (legacy pattern)
                if isinstance(result, dict) and "success" in result:
                    op_result = convert_dict_result_to_operation_result(
                        result, operation
                    )
                    op_result.duration_seconds = duration
                    return op_result

                # Boolean result
                if isinstance(result, bool):
                    if result:
                        return ResultFactory.success(
                            operation=operation,
                            message=default_success_message
                            or f"{operation} completed successfully",
                            duration_seconds=duration,
                        )
                    else:
                        return ResultFactory.failure(
                            operation=operation,
                            error=f"{operation} returned False",
                            duration_seconds=duration,
                        )

                # None result (assume success)
                if result is None:
                    return ResultFactory.success(
                        operation=operation,
                        message=default_success_message
                        or f"{operation} completed successfully",
                        duration_seconds=duration,
                    )

                # Any other data (assume success)
                return ResultFactory.success(
                    operation=operation,
                    message=default_success_message
                    or f"{operation} completed successfully",
                    data=result,
                    duration_seconds=duration,
                )

            except Exception as e:
                return ResultFactory.from_exception(
                    operation=operation,
                    exception=e,
                    duration=(datetime.now() - start_time).total_seconds(),
                )

        return wrapper

    return decorator


# Export main classes and functions
__all__ = [
    "OperationResult",
    "ResultFactory",
    "convert_collection_result_to_operation_result",
    "convert_dict_result_to_operation_result",
    "standardize_result",
]
