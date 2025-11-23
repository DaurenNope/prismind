#!/usr/bin/env python3
"""
API Authentication Middleware for BEYONDLINES
Provides API key authentication for protected endpoints.
"""

import os
from typing import Optional

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.shared.utils.logging_config import get_logger
from src.shared.utils.secrets_manager import get_secrets_manager

logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)

# Environment detection
def _is_production() -> bool:
    """Check if running in production environment"""
    env = os.getenv("ENVIRONMENT", "").lower()
    node_env = os.getenv("NODE_ENV", "").lower()
    
    # Explicit production flag
    if env == "production" or node_env == "production":
        return True
    
    # Require API auth flag (explicit opt-in)
    require_auth = os.getenv("REQUIRE_API_AUTH", "false").lower() == "true"
    if require_auth:
        return True
    
    # Check for common production indicators
    # (but don't auto-enable based on these alone)
    if os.getenv("SUPABASE_URL") and not os.getenv("SUPABASE_URL").startswith("http://localhost"):
        # If Supabase is configured (non-local), treat as production
        # unless explicitly set to development
        if env not in ("development", "dev", "local"):
            return True
    
    return False


def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> str:
    """
    Verify API key from Authorization header.
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        
    Returns:
        Authentication status string ("authenticated" or "anonymous")
        
    Raises:
        HTTPException: If API key is invalid (401 Unauthorized)
    """
    secrets = get_secrets_manager()
    
    # Get expected API key from secrets manager
    expected_key = (
        secrets.get("API_KEY")
        or secrets.get("BEYONDLINES_API_KEY")
        or secrets.get("BEYONDLINES_API_SECRET")
    )
    
    # Check if running in production
    is_prod = _is_production()
    
    # No API key provided in request
    if credentials is None:
        # If no API key configured
        if not expected_key:
            if is_prod:
                # Production requires API key - fail hard
                logger.error(
                    "❌ PRODUCTION MODE: API authentication required but no API_KEY configured. "
                    "Set API_KEY or REQUIRE_API_AUTH=false to allow anonymous access."
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Server misconfiguration: API authentication required in production but not configured",
                )
            else:
                # Development mode - allow anonymous access
                logger.warning(
                    "⚠️ API authentication disabled - no API_KEY set. "
                    "Allowing anonymous access (development mode)"
                )
                return "anonymous"
        
        # API key required but not provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide 'Authorization: Bearer <api_key>' header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    api_key = credentials.credentials
    
    # No API key configured in environment
    if not expected_key:
        if is_prod:
            # Production requires API key - fail hard
            logger.error(
                f"❌ PRODUCTION MODE: API key provided but no API_KEY configured in environment. "
                f"Request from user with key: {secrets.redact(api_key)}"
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server misconfiguration: API authentication required in production but not configured",
            )
        else:
            # Development mode - allow anonymous access
            logger.warning(
                "⚠️ API authentication disabled - no API_KEY set. "
                f"Request from user with key: {secrets.redact(api_key)}"
            )
            return "anonymous"
    
    # Verify API key matches
    if api_key != expected_key:
        logger.warning(
            f"⚠️ Invalid API key attempted: {secrets.redact(api_key)}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug("✅ API key authenticated successfully")
    return "authenticated"


def optional_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[str]:
    """
    Optional API key verification (for public endpoints with optional auth).
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        
    Returns:
        Authentication status string or None if no credentials provided
    """
    if credentials is None:
        return None
    
    try:
        return verify_api_key(credentials)
    except HTTPException:
        # Invalid key provided but optional - return None to indicate unauthenticated
        return None


def require_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> str:
    """
    Require API key (strict authentication - no anonymous access).
    In development mode, allows anonymous access if no API_KEY is configured.
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        
    Returns:
        Authentication status string ("authenticated" or "anonymous" in dev)
        
    Raises:
        HTTPException: If API key is missing or invalid (401 Unauthorized)
    """
    secrets = get_secrets_manager()
    
    # Get expected API key from secrets manager
    expected_key = (
        secrets.get("API_KEY")
        or secrets.get("BEYONDLINES_API_KEY")
        or secrets.get("BEYONDLINES_API_SECRET")
    )
    
    # Check if running in production
    is_prod = _is_production()
    
    # If no API key is configured in environment, allow anonymous access (dev mode)
    # This allows development to work without API keys even if Supabase is configured
    if not expected_key:
        if credentials is None:
            logger.debug(
                "⚠️ Development mode: No API key configured, allowing anonymous access"
            )
            return "anonymous"
        # If credentials provided but no expected key, verify it anyway (will fail, but allow graceful handling)
        # Or if we want to allow any key in dev mode, we could return "anonymous" here too
    
    # If API key is configured, require authentication
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide 'Authorization: Bearer <api_key>' header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return verify_api_key(credentials)

