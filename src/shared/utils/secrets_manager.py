#!/usr/bin/env python3
"""
Centralized Secrets Manager for BEYONDLINES
Provides secure storage and retrieval of credentials and API keys.
Never logs sensitive information.
"""

import os
from typing import Optional
from functools import lru_cache

from dotenv import load_dotenv
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Load environment variables once
load_dotenv(override=True)


class SecretsManager:
    """
    Centralized secrets manager that:
    - Provides a single source of truth for all credentials
    - Never logs sensitive information
    - Supports environment variable fallbacks
    - Validates required secrets are present
    """

    def __init__(self):
        """Initialize the secrets manager."""
        self._cache = {}
        self._validated = set()

    def get(self, key: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
        """
        Get a secret value from environment or cache.
        
        Args:
            key: The environment variable name
            default: Default value if not found
            required: If True, raise ValueError if secret is missing
            
        Returns:
            The secret value or None/default
            
        Raises:
            ValueError: If required=True and secret is missing
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
        
        # Get from environment
        value = os.getenv(key, default)
        
        # Cache non-None values
        if value is not None:
            self._cache[key] = value
        
        # Validate required secrets
        if required and not value:
            raise ValueError(
                f"Required secret '{key}' is missing. "
                f"Please set it in your .env file or environment variables."
            )
        
        return value

    def get_multiple(self, keys: list[str], required: list[str] = None) -> dict[str, Optional[str]]:
        """
        Get multiple secrets at once.
        
        Args:
            keys: List of environment variable names to retrieve
            required: List of keys that must be present (subset of keys)
            
        Returns:
            Dictionary mapping keys to values
            
        Raises:
            ValueError: If any required secret is missing
        """
        if required is None:
            required = []
        
        result = {}
        for key in keys:
            is_required = key in required
            result[key] = self.get(key, required=is_required)
        
        return result

    def validate_required(self, keys: list[str]) -> None:
        """
        Validate that required secrets are present.
        
        Args:
            keys: List of environment variable names that must be present
            
        Raises:
            ValueError: If any required secret is missing
        """
        missing = []
        for key in keys:
            value = self.get(key)
            if not value:
                missing.append(key)
        
        if missing:
            raise ValueError(
                f"Missing required secrets: {', '.join(missing)}. "
                f"Please set them in your .env file or environment variables."
            )
        
        # Mark as validated
        self._validated.update(keys)

    def redact(self, value: Optional[str], length: int = 4) -> str:
        """
        Redact a secret value for logging (shows only first N characters).
        For security, prefer using this over logging raw values.
        
        Args:
            value: The secret value to redact
            length: Number of characters to show at the start
            
        Returns:
            Redacted string like "abcd..." or "[REDACTED]" if value is None
        """
        if not value:
            return "[REDACTED]"
        if len(value) <= length:
            return "[REDACTED]"
        return f"{value[:length]}..."

    def clear_cache(self) -> None:
        """Clear the secrets cache (useful for testing)."""
        self._cache.clear()
        self._validated.clear()


# Global singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get the global SecretsManager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager


# Convenience functions for common secret categories

def get_api_key(service: str) -> Optional[str]:
    """Get an API key for a service (e.g., 'GEMINI', 'MISTRAL')."""
    manager = get_secrets_manager()
    # Try common naming patterns
    for key_name in [
        f"{service}_API_KEY",
        f"{service}_KEY",
        f"{service}_TOKEN",
    ]:
        value = manager.get(key_name)
        if value:
            return value
    return None


def get_database_credentials() -> dict[str, Optional[str]]:
    """Get database credentials (Supabase, SQLite path, etc.)."""
    manager = get_secrets_manager()
    return manager.get_multiple([
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_KEY",
        "DATABASE_URL",
    ])


def get_social_media_credentials() -> dict[str, Optional[str]]:
    """Get social media platform credentials."""
    manager = get_secrets_manager()
    return manager.get_multiple([
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_TOKEN_SECRET",
        "THREADS_ACCESS_TOKEN",
        "THREADS_TOKEN_ACCESS",
        "THREADS_API_TOKEN",
        "THREADS_USER_ID",
        "THREADS_API_USER_ID",
    ])


def get_ai_service_credentials() -> dict[str, Optional[str]]:
    """Get AI service credentials."""
    manager = get_secrets_manager()
    # Get all Gemini keys (supporting multiple keys for rotation)
    gemini_keys = []
    for i in range(1, 10):  # Support up to 9 keys
        key = manager.get(f"GEMINI_API_KEY_{i}") or manager.get(f"GEMINI_KEY_{i}")
        if key:
            gemini_keys.append(key)
    
    # Fallback to single key
    if not gemini_keys:
        single_key = manager.get("GEMINI_API_KEY") or manager.get("GEMINI_KEY")
        if single_key:
            gemini_keys = [single_key]
    
    # Get Mistral keys
    mistral_keys = []
    for i in range(1, 10):
        key = manager.get(f"MISTRAL_API_KEY_{i}") or manager.get(f"MISTRAL_KEY_{i}")
        if key:
            mistral_keys.append(key)
    
    if not mistral_keys:
        single_key = manager.get("MISTRAL_API_KEY") or manager.get("MISTRAL_KEY")
        if single_key:
            mistral_keys = [single_key]
    
    return {
        "gemini_keys": gemini_keys,
        "mistral_keys": mistral_keys,
        "openai_key": manager.get("OPENAI_API_KEY"),
        "anthropic_key": manager.get("ANTHROPIC_API_KEY"),
    }





