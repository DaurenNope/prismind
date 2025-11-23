#!/usr/bin/env python3
"""
System Status API Routes
========================

API endpoints for system status including circuit breakers and configuration.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from src.utils.circuit_breaker_wrapper import CircuitBreakerWrapper
from src.utils.config import get_config
from src.utils.config_validator import (
    create_beyondlines_config_validator,
    validate_config,
)
from src.utils.logging_config import get_logger

router = APIRouter(prefix="/api/system", tags=["system"])
logger = get_logger(__name__)


@router.get("/circuit-breakers")
async def get_circuit_breakers(request: Request):
    """Get status of all circuit breakers"""
    try:
        breakers = CircuitBreakerWrapper.get_all_status()

        return {
            "breakers": breakers,
            "total_breakers": len(breakers),
            "open_breakers": [
                name for name, status in breakers.items() if status["state"] == "open"
            ],
            "half_open_breakers": [
                name
                for name, status in breakers.items()
                if status["state"] == "half_open"
            ],
            "closed_breakers": [
                name for name, status in breakers.items() if status["state"] == "closed"
            ],
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting circuit breakers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/circuit-breakers/{breaker_name}")
async def get_circuit_breaker_status(request: Request, breaker_name: str):
    """Get status of a specific circuit breaker"""
    try:
        breaker = CircuitBreakerWrapper.get_breaker(breaker_name)
        status = breaker.get_status()
        return {"breaker": status, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Error getting circuit breaker {breaker_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/circuit-breakers/{breaker_name}/reset")
async def reset_circuit_breaker(request: Request, breaker_name: str):
    """Reset a circuit breaker"""
    try:
        breaker = CircuitBreakerWrapper.get_breaker(breaker_name)
        breaker.reset()

        return {
            "success": True,
            "message": f"Circuit breaker '{breaker_name}' reset successfully",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error resetting circuit breaker {breaker_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials")
async def get_credentials_status(request: Request):
    """Get current credentials status (masked for security)"""
    import os
    from pathlib import Path

    def mask_value(value: str, show_chars: int = 4) -> str:
        """Mask a credential value, showing only first few characters"""
        if not value:
            return "Not set"
        if len(value) <= show_chars:
            return "***"
        return (
            value[:show_chars] + "***" + value[-2:]
            if len(value) > show_chars + 2
            else value[:show_chars] + "***"
        )

    def check_file_exists(path_str: str) -> bool:
        """Check if a file path exists"""
        if not path_str:
            return False
        try:
            return Path(path_str).expanduser().exists()
        except:
            return False

    credentials = {
        "twitter": {
            "username": os.getenv("TWITTER_USERNAME", "Not set"),
            "password": "Set" if os.getenv("TWITTER_PASSWORD") else "Not set",
            "cookie_file": os.getenv("TWITTER_COOKIE_FILE")
            or os.getenv("TWITTER_COOKIES_FILE")
            or "config/cookies/twitter_cookies_*.json",
            "cookie_file_exists": check_file_exists(
                os.getenv("TWITTER_COOKIE_FILE", "")
            )
            or check_file_exists(os.getenv("TWITTER_COOKIES_FILE", "")),
        },
        "threads": {
            "username": os.getenv("THREADS_USERNAME", "Not set"),
            "password": "Set" if os.getenv("THREADS_PASSWORD") else "Not set",
            "cookie_file": os.getenv(
                "THREADS_COOKIE_FILE", "cookies/threads_cookies.json"
            ),
            "cookie_file_exists": check_file_exists(
                os.getenv("THREADS_COOKIE_FILE", "cookies/threads_cookies.json")
            ),
            "allowed_handles": os.getenv(
                "THREADS_ALLOWED_HANDLES", "Not set (collects all)"
            ),
        },
        "reddit": {
            "client_id": mask_value(os.getenv("REDDIT_CLIENT_ID", "")),
            "client_secret": "Set" if os.getenv("REDDIT_CLIENT_SECRET") else "Not set",
            "username": os.getenv("REDDIT_USERNAME", "Not set"),
            "password": "Set" if os.getenv("REDDIT_PASSWORD") else "Not set",
        },
        "supabase": {
            "url": mask_value(os.getenv("SUPABASE_URL", ""), 8),
            "key": "Set"
            if os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
            else "Not set",
        },
        "telegram": {
            "bot_token": mask_value(os.getenv("TELEGRAM_BOT_TOKEN", "")),
            "chat_id": os.getenv("TELEGRAM_CHAT_ID", "Not set"),
        },
    }

    return {"credentials": credentials, "timestamp": datetime.now().isoformat()}


@router.get("/configuration/status")
async def get_configuration_status(request: Request):
    """Get configuration validation status"""
    try:
        config = get_config()

        # Convert config to dict for validation
        config_dict = {
            "supabase_url": config.supabase_url,
            "supabase_service_role_key": config.supabase_service_role_key,
            "supabase_enabled": config.flags.get("supabase_enabled", True),
            "enable_sqlite_cache": config.flags.get("enable_sqlite_cache", False),
            "enable_analysis": config.flags.get("enable_analysis", True),
            "enable_threads": config.flags.get("enable_threads", False),
            "auto_pipeline_batch_limit": config.flags.get(
                "auto_pipeline_batch_limit", 25
            ),
            "rewriter_min_quality_score": config.flags.get(
                "rewriter_min_quality_score", 5.0
            ),
        }

        result = validate_config(config_dict)

        return {
            "is_valid": result.is_valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "validated_config": result.validated_config,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting configuration status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_system_status(request: Request):
    """Get overall system status including circuit breakers, configuration, and observability"""
    try:
        from src.utils.observability_hub import get_observability_hub

        # Get circuit breakers
        breakers = CircuitBreakerWrapper.get_all_status()

        # Get configuration status
        config = get_config()
        config_dict = {
            "supabase_url": config.supabase_url,
            "supabase_service_role_key": config.supabase_service_role_key,
            "supabase_enabled": config.flags.get("supabase_enabled", True),
            "enable_analysis": config.flags.get("enable_analysis", True),
        }
        config_result = validate_config(config_dict)

        # Get observability health
        hub = get_observability_hub()
        observability_health = hub.get_health_report()

        # Determine overall system health
        open_breakers = [
            name for name, status in breakers.items() if status["state"] == "open"
        ]

        system_health = "healthy"
        if open_breakers:
            system_health = "degraded"
        if not config_result.is_valid:
            system_health = "unhealthy"
        if observability_health["errors"]["total_errors"] > 100:
            system_health = "degraded"

        return {
            "system_health": system_health,
            "circuit_breakers": {
                "total": len(breakers),
                "open": len(open_breakers),
                "half_open": len(
                    [
                        name
                        for name, status in breakers.items()
                        if status["state"] == "half_open"
                    ]
                ),
                "closed": len(
                    [
                        name
                        for name, status in breakers.items()
                        if status["state"] == "closed"
                    ]
                ),
                "details": breakers,
            },
            "configuration": {
                "is_valid": config_result.is_valid,
                "error_count": len(config_result.errors),
                "warning_count": len(config_result.warnings),
            },
            "observability": {
                "metrics_count": observability_health["metrics"]["total_metrics"],
                "errors_count": observability_health["errors"]["total_errors"],
                "traces_count": observability_health["traces"].get("active_traces", 0),
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
