"""
Custom exceptions for BEYONDLINES application
Provides specific exception types for better error handling and debugging
"""

from typing import Any, Dict, Optional


class BEYONDLINESException(Exception):
    """Base exception for all BEYONDLINES application errors"""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }

    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


# Authentication and Authorization Exceptions
class AuthenticationError(BEYONDLINESException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(message, error_code="AUTH_ERROR", **kwargs)


class AuthorizationError(BEYONDLINESException):
    """Raised when user lacks permissions"""

    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, error_code="ACCESS_DENIED", **kwargs)


class SessionExpiredError(BEYONDLINESException):
    """Raised when user session has expired"""

    def __init__(self, message: str = "Session has expired", **kwargs):
        super().__init__(message, error_code="SESSION_EXPIRED", **kwargs)


# Database Exceptions
class DatabaseError(BEYONDLINESException):
    """Base class for database-related errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="DB_ERROR", **kwargs)


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""

    def __init__(self, message: str = "Database connection failed", **kwargs):
        super().__init__(message, error_code="DB_CONNECTION_ERROR", **kwargs)


class DatabaseQueryError(DatabaseError):
    """Raised when database query fails"""

    def __init__(self, query: str, message: str = "Database query failed", **kwargs):
        details = kwargs.get("details", {})
        details.update({"query": query})
        super().__init__(
            message, error_code="DB_QUERY_ERROR", details=details, **kwargs
        )


class DatabaseValidationError(DatabaseError):
    """Raised when database validation fails"""

    def __init__(self, message: str = "Data validation failed", **kwargs):
        super().__init__(message, error_code="DB_VALIDATION_ERROR", **kwargs)


class DatabaseMigrationError(DatabaseError):
    """Raised when database migration fails"""

    def __init__(
        self, migration: str, message: str = "Database migration failed", **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({"migration": migration})
        super().__init__(
            message, error_code="DB_MIGRATION_ERROR", details=details, **kwargs
        )


# API and Network Exceptions
class APIError(BEYONDLINESException):
    """Base class for API-related errors"""

    def __init__(self, message: str, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, error_code="API_ERROR", **kwargs)
        self.status_code = status_code


class APIRequestError(APIError):
    """Raised when API request fails"""

    def __init__(
        self, url: str, status_code: int, message: str = "API request failed", **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({"url": url, "status_code": status_code})
        super().__init__(
            message,
            status_code,
            error_code="API_REQUEST_ERROR",
            details=details,
            **kwargs,
        )


class APIResponseError(APIError):
    """Raised when API response is invalid"""

    def __init__(self, message: str = "Invalid API response", **kwargs):
        super().__init__(message, error_code="API_RESPONSE_ERROR", **kwargs)


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""

    def __init__(
        self, limit: int, window: int, message: str = "Rate limit exceeded", **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({"limit": limit, "window_seconds": window})
        super().__init__(
            message,
            status_code=429,
            error_code="RATE_LIMIT_ERROR",
            details=details,
            **kwargs,
        )


# Twitter-specific Exceptions
class TwitterInteractionError(BEYONDLINESException):
    """Raised when Twitter interaction operations fail"""

    def __init__(self, message: str = "Twitter interaction failed", **kwargs):
        super().__init__(message, error_code="TWITTER_INTERACTION_ERROR", **kwargs)


class TwitterScrapingError(BEYONDLINESException):
    """Raised when Twitter web scraping operations fail"""

    def __init__(self, message: str = "Twitter scraping failed", **kwargs):
        super().__init__(message, error_code="TWITTER_SCRAPING_ERROR", **kwargs)


# Content Processing Exceptions
class ContentProcessingError(BEYONDLINESException):
    """Base class for content processing errors"""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, error_code="CONTENT_PROCESSING_ERROR", **kwargs)


class ContentValidationError(ContentProcessingError):
    """Raised when content validation fails"""

    def __init__(
        self, field: str, message: str = "Content validation failed", **kwargs
    ):
        details = kwargs.get("details", {})
        details.update({"field": field})
        super().__init__(
            message, error_code="CONTENT_VALIDATION_ERROR", details=details, **kwargs
        )


class ContentTooLongError(ContentValidationError):
    """Raised when content exceeds maximum length"""

    def __init__(self, length: int, max_length: int, **kwargs):
        message = f"Content too long: {length} characters (max: {max_length})"
        details = kwargs.get("details", {})
        details.update({"actual_length": length, "max_length": max_length})
        super().__init__(
            "content_length",
            message,
            error_code="CONTENT_TOO_LONG",
            details=details,
            **kwargs,
        )


class ContentTooShortError(ContentValidationError):
    """Raised when content is too short"""

    def __init__(self, length: int, min_length: int, **kwargs):
        message = f"Content too short: {length} characters (min: {min_length})"
        details = kwargs.get("details", {})
        details.update({"actual_length": length, "min_length": min_length})
        super().__init__(
            "content_length",
            message,
            error_code="CONTENT_TOO_SHORT",
            details=details,
            **kwargs,
        )


# Publishing and Platform Exceptions
class PublishingError(BEYONDLINESException):
    """Base class for publishing errors"""

    def __init__(self, message: str, platform: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if platform:
            details.update({"platform": platform})
        super().__init__(
            message, error_code="PUBLISHING_ERROR", details=details, **kwargs
        )


class PlatformNotConfiguredError(PublishingError):
    """Raised when publishing platform is not configured"""

    def __init__(self, platform: str, **kwargs):
        message = f"Platform '{platform}' is not configured"
        super().__init__(
            message, platform, error_code="PLATFORM_NOT_CONFIGURED", **kwargs
        )


class PlatformAuthenticationError(PublishingError):
    """Raised when platform authentication fails"""

    def __init__(self, platform: str, **kwargs):
        message = f"Authentication failed for platform '{platform}'"
        super().__init__(message, platform, error_code="PLATFORM_AUTH_ERROR", **kwargs)


class PublishingRateLimitError(PublishingError):
    """Raised when publishing rate limit is exceeded"""

    def __init__(self, platform: str, retry_after: Optional[int] = None, **kwargs):
        message = f"Publishing rate limit exceeded for platform '{platform}'"
        details = kwargs.get("details", {})
        if retry_after:
            details.update({"retry_after_seconds": retry_after})
        super().__init__(
            message,
            platform,
            error_code="PUBLISHING_RATE_LIMIT",
            details=details,
            **kwargs,
        )


class ContentNotSuitableError(PublishingError):
    """Raised when content is not suitable for publishing"""

    def __init__(self, reason: str, **kwargs):
        message = f"Content not suitable for publishing: {reason}"
        details = kwargs.get("details", {})
        details.update({"reason": reason})
        super().__init__(
            message, error_code="CONTENT_NOT_SUITABLE", details=details, **kwargs
        )


# Extraction and Scraping Exceptions
class ExtractionError(BEYONDLINESException):
    """Base class for extraction errors"""

    def __init__(self, message: str, source: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if source:
            details.update({"source": source})
        super().__init__(
            message, error_code="EXTRACTION_ERROR", details=details, **kwargs
        )


class ScrapingError(ExtractionError):
    """Raised when web scraping fails"""

    def __init__(self, url: str, message: str = "Web scraping failed", **kwargs):
        details = kwargs.get("details", {})
        details.update({"url": url})
        super().__init__(
            message, source=url, error_code="SCRAPING_ERROR", details=details, **kwargs
        )


class AuthenticationExpiredError(ScrapingError):
    """Raised when scraping authentication expires"""

    def __init__(self, platform: str, **kwargs):
        message = f"Authentication expired for platform '{platform}'"
        super().__init__(
            f"https://{platform}.com", message, error_code="AUTH_EXPIRED", **kwargs
        )


class ContentNotFoundError(ExtractionError):
    """Raised when expected content is not found"""

    def __init__(self, content_type: str, identifier: str, **kwargs):
        message = f"{content_type} not found: {identifier}"
        details = kwargs.get("details", {})
        details.update({"content_type": content_type, "identifier": identifier})
        super().__init__(
            message, error_code="CONTENT_NOT_FOUND", details=details, **kwargs
        )


# AI/ML Processing Exceptions
class AIProcessingError(BEYONDLINESException):
    """Base class for AI/ML processing errors"""

    def __init__(self, message: str, model: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if model:
            details.update({"model": model})
        super().__init__(
            message, error_code="AI_PROCESSING_ERROR", details=details, **kwargs
        )


class ModelNotAvailableError(AIProcessingError):
    """Raised when AI model is not available"""

    def __init__(self, model: str, **kwargs):
        message = f"AI model '{model}' is not available"
        super().__init__(message, model, error_code="MODEL_NOT_AVAILABLE", **kwargs)


class ModelTimeoutError(AIProcessingError):
    """Raised when AI model processing times out"""

    def __init__(self, model: str, timeout: int, **kwargs):
        message = f"AI model '{model}' processing timed out after {timeout}s"
        details = kwargs.get("details", {})
        details.update({"timeout_seconds": timeout})
        super().__init__(
            message, model, error_code="MODEL_TIMEOUT", details=details, **kwargs
        )


class InsufficientCreditsError(AIProcessingError):
    """Raised when AI service has insufficient credits"""

    def __init__(self, service: str, message: str = "Insufficient credits", **kwargs):
        details = kwargs.get("details", {})
        details.update({"service": service})
        super().__init__(
            message, error_code="INSUFFICIENT_CREDITS", details=details, **kwargs
        )


# Configuration and Setup Exceptions
class ConfigurationError(BEYONDLINESException):
    """Raised when configuration is invalid or missing"""

    def __init__(self, config_key: str, message: str = "Configuration error", **kwargs):
        details = kwargs.get("details", {})
        details.update({"config_key": config_key})
        super().__init__(message, error_code="CONFIG_ERROR", details=details, **kwargs)


class MissingEnvironmentVariableError(ConfigurationError):
    """Raised when required environment variable is missing"""

    def __init__(self, env_var: str, **kwargs):
        message = f"Missing required environment variable: {env_var}"
        super().__init__(env_var, message, error_code="MISSING_ENV_VAR", **kwargs)


class InvalidConfigurationValueError(ConfigurationError):
    """Raised when configuration value is invalid"""

    def __init__(self, config_key: str, value: Any, expected_type: str, **kwargs):
        message = f"Invalid value for {config_key}: {value} (expected {expected_type})"
        details = kwargs.get("details", {})
        details.update({"value": value, "expected_type": expected_type})
        super().__init__(
            config_key,
            message,
            error_code="INVALID_CONFIG_VALUE",
            details=details,
            **kwargs,
        )


# Utility Exceptions
class RetryExhaustedError(BEYONDLINESException):
    """Raised when retry attempts are exhausted"""

    def __init__(self, attempts: int, last_error: Optional[Exception] = None, **kwargs):
        message = f"Operation failed after {attempts} retry attempts"
        details = kwargs.get("details", {})
        details.update({"retry_attempts": attempts})
        if last_error:
            details.update({"last_error": str(last_error)})
        super().__init__(
            message,
            error_code="RETRY_EXHAUSTED",
            details=details,
            cause=last_error,
            **kwargs,
        )


class ResourceNotFoundError(BEYONDLINESException):
    """Raised when a required resource is not found"""

    def __init__(self, resource_type: str, identifier: str, **kwargs):
        message = f"{resource_type} not found: {identifier}"
        details = kwargs.get("details", {})
        details.update({"resource_type": resource_type, "identifier": identifier})
        super().__init__(
            message, error_code="RESOURCE_NOT_FOUND", details=details, **kwargs
        )


class ValidationError(BEYONDLINESException):
    """Raised when validation fails"""

    def __init__(self, field: str, value: Any, constraint: str, **kwargs):
        message = f"Validation failed for {field}: {value} ({constraint})"
        details = kwargs.get("details", {})
        details.update({"field": field, "value": value, "constraint": constraint})
        super().__init__(
            message, error_code="VALIDATION_ERROR", details=details, **kwargs
        )


class CircuitBreakerOpenException(BEYONDLINESException):
    """Exception raised when circuit breaker is open"""

    def __init__(self, message: str, service_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if service_name:
            details.update({"service_name": service_name})
        super().__init__(
            message, error_code="CIRCUIT_BREAKER_OPEN", details=details, **kwargs
        )


class RateLimitExceededError(BEYONDLINESException):
    """Exception raised when rate limit is exceeded"""

    def __init__(self, message: str, retry_after: Optional[float] = None, **kwargs):
        details = kwargs.get("details", {})
        if retry_after:
            details.update({"retry_after": retry_after})
        super().__init__(
            message, error_code="RATE_LIMIT_EXCEEDED", details=details, **kwargs
        )


class GatewayError(BEYONDLINESException):
    """Exception raised for API gateway errors"""

    def __init__(self, message: str, gateway_service: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if gateway_service:
            details.update({"gateway_service": gateway_service})
        super().__init__(message, error_code="GATEWAY_ERROR", details=details, **kwargs)


class QueueError(BEYONDLINESException):
    """Exception raised for message queue errors"""

    def __init__(self, message: str, queue_name: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if queue_name:
            details.update({"queue_name": queue_name})
        super().__init__(message, error_code="QUEUE_ERROR", details=details, **kwargs)


class QueueTimeoutError(QueueError):
    """Exception raised when queue operation times out"""

    def __init__(self, message: str, timeout: Optional[float] = None, **kwargs):
        details = kwargs.get("details", {})
        if timeout:
            details.update({"timeout": timeout})
        super().__init__(message, error_code="QUEUE_TIMEOUT", details=details, **kwargs)


class TwitterInteractionError(BEYONDLINESException):
    """Exception raised for Twitter interaction errors"""

    def __init__(self, message: str, tweet_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if tweet_id:
            details.update({"tweet_id": tweet_id})
        super().__init__(
            message, error_code="TWITTER_INTERACTION_ERROR", details=details, **kwargs
        )


class SocialInteractionError(BEYONDLINESException):
    """Exception raised for social media interaction errors"""

    def __init__(self, message: str, platform: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if platform:
            details.update({"platform": platform})
        super().__init__(
            message, error_code="SOCIAL_INTERACTION_ERROR", details=details, **kwargs
        )


class ApprovalError(BEYONDLINESException):
    """Exception raised for approval workflow errors"""

    def __init__(self, message: str, interaction_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if interaction_id:
            details.update({"interaction_id": interaction_id})
        super().__init__(
            message, error_code="APPROVAL_ERROR", details=details, **kwargs
        )


class CacheError(BEYONDLINESException):
    """Exception raised for cache errors"""

    def __init__(self, message: str, cache_key: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if cache_key:
            details.update({"cache_key": cache_key})
        super().__init__(message, error_code="CACHE_ERROR", details=details, **kwargs)


class StateError(BEYONDLINESException):
    """Exception raised for state management errors"""

    def __init__(self, message: str, state_key: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if state_key:
            details.update({"state_key": state_key})
        super().__init__(message, error_code="STATE_ERROR", details=details, **kwargs)
